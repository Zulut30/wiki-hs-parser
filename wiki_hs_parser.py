from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from lxml import html


API_BASE = "https://hearthstone.wiki.gg/api.php"
WIKI_BASE = "https://hearthstone.wiki.gg"
USER_AGENT = "wiki-hs-parser/1.0 (+https://github.com/Zulut30/wiki-hs-parser)"


@dataclass
class ArtVariant:
    label: str
    source: str
    file_title: str
    file_url: str
    file_page_url: str
    size: int | None
    sha1: str | None
    downloaded_path: str | None = None


@dataclass
class PatchEntry:
    patch: str
    patch_url: str
    date: str
    items: list[str]


@dataclass
class PatchGroup:
    heading: str
    entries: list[PatchEntry]


def http_get_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def http_get_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req) as resp:
        return resp.read()


def normalize_title(value: str) -> str:
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        path = parsed.path
        if "/wiki/" in path:
            value = unquote(path.split("/wiki/", 1)[1])
        else:
            value = unquote(path.rsplit("/", 1)[-1])
    else:
        value = unquote(value)
    value = value.replace("_", " ").strip("/")
    return value


def canonical_page_url(title: str) -> str:
    safe = quote(title.replace(" ", "_"), safe="()!,-.")
    return f"{WIKI_BASE}/wiki/{safe}"


def mediawiki_query(params: dict[str, Any]) -> dict[str, Any]:
    query = urlencode(params, doseq=True)
    return http_get_json(f"{API_BASE}?{query}")


def get_rendered_html(title: str) -> str:
    data = mediawiki_query(
        {
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "redirects": 1,
        }
    )
    return data["parse"]["text"]["*"]


def get_file_info(file_title: str) -> dict[str, Any]:
    data = mediawiki_query(
        {
            "action": "query",
            "titles": file_title,
            "prop": "imageinfo",
            "iiprop": "url|size|sha1",
            "format": "json",
        }
    )
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    imageinfo = page.get("imageinfo") or []
    if not imageinfo:
        raise RuntimeError(f"No imageinfo found for {file_title}")
    return imageinfo[0]


def extract_text(node: html.HtmlElement) -> str:
    text = " ".join(part.strip() for part in node.itertext())
    return re.sub(r"\s+", " ", unescape(text)).strip()


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w.\-]+", "_", value, flags=re.UNICODE)
    value = re.sub(r"_+", "_", value).strip("_.")
    return value or "asset"


def extract_art_variants(rendered_html: str) -> list[ArtVariant]:
    tree = html.fromstring(rendered_html)
    label_map: dict[str, str] = {}
    for tab in tree.xpath('//aside[contains(@class,"portable-infobox")]//li[contains(@class,"pi-section-tab")]'):
        ref = tab.get("data-ref")
        label = extract_text(tab.xpath('.//div[contains(@class,"pi-section-label")]')[0]) if tab.xpath('.//div[contains(@class,"pi-section-label")]') else ""
        if ref and label:
            label_map[ref] = label

    variants: list[ArtVariant] = []
    for figure in tree.xpath('//aside[contains(@class,"portable-infobox")]//figure[@data-source]'):
        source = figure.get("data-source") or ""
        if not source.startswith("image"):
            continue
        content = figure.xpath('ancestor::div[contains(@class,"pi-section-content")][1]')
        ref = content[0].get("data-ref") if content else None
        label = label_map.get(ref or "", source)
        file_href = figure.xpath('.//a[starts-with(@href,"/wiki/File:")][1]/@href')
        if not file_href:
            continue
        file_title = unquote(file_href[0].split("/wiki/", 1)[1])
        info = get_file_info(file_title)
        file_url = info["url"]
        variants.append(
            ArtVariant(
                label=label,
                source=source,
                file_title=file_title,
                file_url=file_url,
                file_page_url=f"{WIKI_BASE}{file_href[0]}",
                size=info.get("size"),
                sha1=info.get("sha1"),
            )
        )
    return variants


def extract_patch_changes(rendered_html: str) -> list[PatchGroup]:
    tree = html.fromstring(rendered_html)
    start = tree.xpath('//span[@id="Patch_changes"]/ancestor::h2[1]')
    if not start:
        return []

    node = start[0].getnext()
    section_parts: list[str] = []
    while node is not None:
        if node.tag == "h2" and node.xpath('.//span[@id="References"]'):
            break
        section_parts.append(html.tostring(node, encoding="unicode"))
        node = node.getnext()

    if not section_parts:
        return []

    section_root = html.fragment_fromstring("".join(section_parts), create_parent=True)
    groups: list[PatchGroup] = []
    children = list(section_root)
    idx = 0
    while idx < len(children):
        child = children[idx]
        heading = ""
        if child.tag == "p":
            big_nodes = child.xpath(".//big")
            if big_nodes:
                heading = extract_text(big_nodes[0])
        if heading and idx + 1 < len(children):
            box = children[idx + 1]
            if box.tag == "div" and "patch-changes-box" in (box.get("class") or ""):
                groups.append(PatchGroup(heading=heading, entries=parse_patch_box(box)))
                idx += 2
                continue
        idx += 1
    return groups


def parse_patch_box(box: html.HtmlElement) -> list[PatchEntry]:
    entries: list[PatchEntry] = []
    for li in box.xpath('.//ul/li[./b/a[contains(@href,"/wiki/Patch_")]]'):
        patch_link = li.xpath('.//b/a[contains(@href,"/wiki/Patch_")][1]')
        if not patch_link:
            continue
        patch_el = patch_link[0]
        patch = extract_text(patch_el)
        patch_url = f"{WIKI_BASE}{patch_el.get('href')}"
        patch_date_match = re.search(r"\(([^)]+)\):?$", extract_text(li.xpath(".//b")[0]) if li.xpath(".//b") else "")
        date = patch_date_match.group(1) if patch_date_match else ""
        items = []
        for nested in li.xpath("./ul/li"):
            item = extract_text(nested)
            if item:
                items.append(item)
        entries.append(PatchEntry(patch=patch, patch_url=patch_url, date=date, items=items))
    return entries


def download_art(variant: ArtVariant, out_dir: Path, index: int) -> str:
    url = variant.file_url
    suffix = Path(urlparse(url).path).suffix or ".bin"
    base = safe_filename(f"{index:02d}_{variant.label}_{Path(urlparse(url).path).stem}")
    target = out_dir / f"{base}{suffix}"
    target.write_bytes(http_get_bytes(url))
    return str(target)


def render_patch_markdown(groups: Iterable[PatchGroup]) -> str:
    lines: list[str] = ["## Patch changes"]
    for group in groups:
        lines.append(f"### {group.heading}")
        for entry in group.entries:
            lines.append(f"- [{entry.patch}]({entry.patch_url}) ({entry.date})")
            for item in entry.items:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_result(title: str, download: bool, output_dir: Path) -> dict[str, Any]:
    rendered_html = get_rendered_html(title)
    arts = extract_art_variants(rendered_html)
    patches = extract_patch_changes(rendered_html)

    if download:
        art_dir = output_dir / "arts"
        art_dir.mkdir(parents=True, exist_ok=True)
        for idx, art in enumerate(arts, start=1):
            art.downloaded_path = download_art(art, art_dir, idx)

    result = {
        "page_title": title,
        "page_url": canonical_page_url(title),
        "arts": [asdict(art) for art in arts],
        "patch_changes": [
            {
                "heading": group.heading,
                "entries": [asdict(entry) for entry in group.entries],
            }
            for group in patches
        ],
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract Hearthstone wiki art variants and patch changes.")
    parser.add_argument("--page", required=True, help="Wiki page title or URL, for example C'Thun or https://hearthstone.wiki.gg/wiki/C%27Thun")
    parser.add_argument("--output-dir", default="out", help="Directory where JSON, markdown, and art images are written")
    parser.add_argument("--no-download", action="store_true", help="Do not download the art image files")
    args = parser.parse_args(argv)

    title = normalize_title(args.page)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = build_result(title, download=not args.no_download, output_dir=output_dir)

    json_path = output_dir / "result.json"
    md_path = output_dir / "patch-changes.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_patch_markdown(
        PatchGroup(
            heading=item["heading"],
            entries=[
                PatchEntry(
                    patch=entry["patch"],
                    patch_url=entry["patch_url"],
                    date=entry["date"],
                    items=entry["items"],
                )
                for entry in item["entries"]
            ],
        )
        for item in result["patch_changes"]
    ), encoding="utf-8")

    print(json_path)
    print(md_path)
    for art in result["arts"]:
        print(art["downloaded_path"] or art["file_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
