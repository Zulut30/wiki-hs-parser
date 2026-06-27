from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
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
class CardLink:
    title: str
    href: str
    card_code: str | None = None
    image_alt: str | None = None
    image_url: str | None = None


@dataclass
class InfoboxField:
    source: str
    label: str
    value_text: str
    value_html: str | None = None
    links: list[CardLink] = field(default_factory=list)


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


@dataclass
class CardGroup:
    heading: str
    cards: list[CardLink]


@dataclass
class GeneratedCardPool:
    description: str
    query_url: str
    cards: list[CardLink]


_CARD_CODE_CACHE: dict[str, str | None] = {}


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


def get_section_node(tree: html.HtmlElement, headline_id: str) -> html.HtmlElement | None:
    found = tree.xpath(f'//span[@id="{headline_id}"]/ancestor::h2[1]')
    return found[0] if found else None


def iter_section_nodes(tree: html.HtmlElement, headline_id: str) -> list[html.HtmlElement]:
    start = get_section_node(tree, headline_id)
    if start is None:
        return []

    nodes: list[html.HtmlElement] = []
    node = start.getnext()
    while node is not None:
        if node.tag == "h2":
            break
        nodes.append(node)
        node = node.getnext()
    return nodes


def element_links(node: html.HtmlElement) -> list[CardLink]:
    links: list[CardLink] = []
    for a in node.xpath('.//a[@href]'):
        href = a.get("href") or ""
        if not href.startswith("/wiki/"):
            continue
        title = a.get("title") or extract_text(a)
        image = a.xpath(".//img[1]")
        image_alt = image[0].get("alt") if image else None
        image_url = image[0].get("src") if image else None
        links.append(
            CardLink(
                title=title.strip(),
                href=f"{WIKI_BASE}{href}",
                card_code=resolve_card_code(f"{WIKI_BASE}{href}"),
                image_alt=image_alt,
                image_url=f"{WIKI_BASE}{image_url}" if image_url and image_url.startswith("/") else image_url,
            )
        )
    return links


def resolve_card_code(page_url: str) -> str | None:
    cached = _CARD_CODE_CACHE.get(page_url)
    if page_url in _CARD_CODE_CACHE:
        return cached

    try:
        rendered_html = get_rendered_html(normalize_title(page_url))
    except Exception:
        _CARD_CODE_CACHE[page_url] = None
        return None

    tree = html.fromstring(rendered_html)
    field = tree.xpath('//*[@data-source="id"]')
    if not field:
        _CARD_CODE_CACHE[page_url] = None
        return None

    value_node = field[0].xpath('.//*[contains(@class,"pi-data-value")][1]')
    code = extract_text(value_node[0]) if value_node else extract_text(field[0])
    code = code.strip()
    _CARD_CODE_CACHE[page_url] = code or None
    return _CARD_CODE_CACHE[page_url]


def extract_infobox_fields(rendered_html: str) -> list[InfoboxField]:
    tree = html.fromstring(rendered_html)
    aside = tree.xpath('//aside[contains(@class,"portable-infobox")]')
    if not aside:
        return []
    infobox = aside[0]

    fields: list[InfoboxField] = []
    for node in infobox.xpath('.//*[@data-source]'):
        source = node.get("data-source") or ""
        if not source or source.startswith("image"):
            continue
        if node.tag == "figure":
            continue

        label_node = node.xpath('.//*[contains(@class,"pi-data-label")][1]')
        value_node = node.xpath('.//*[contains(@class,"pi-data-value")][1]')
        label = (extract_text(label_node[0]) if label_node else source).rstrip(":")
        value_el = value_node[0] if value_node else node

        value_text = extract_text(value_el)
        value_html = html.tostring(value_el, encoding="unicode", with_tail=False)
        links = element_links(value_el)

        if not value_text and not links:
            continue
        fields.append(
            InfoboxField(
                source=source,
                label=label,
                value_text=value_text,
                value_html=value_html,
                links=links,
            )
        )
    return fields


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


def extract_card_groups(rendered_html: str, section_id: str) -> list[CardGroup]:
    tree = html.fromstring(rendered_html)
    groups: list[CardGroup] = []
    nodes = iter_section_nodes(tree, section_id)
    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        heading = ""
        if node.tag in {"h3", "h4"}:
            heading = extract_text(node)
        if heading and idx + 1 < len(nodes):
            next_node = nodes[idx + 1]
            if next_node.tag == "div" and "list-cards" in (next_node.get("class") or ""):
                cards: list[CardLink] = []
                for card in next_node.xpath('./div[contains(@class,"card-div")]'):
                    anchor = card.xpath('.//a[starts-with(@href,"/wiki/")][1]')
                    if not anchor:
                        continue
                    a = anchor[0]
                    img = card.xpath('.//img[1]')
                    cards.append(
                        CardLink(
                            title=a.get("title") or extract_text(a),
                            href=f"{WIKI_BASE}{a.get('href')}",
                            card_code=resolve_card_code(f"{WIKI_BASE}{a.get('href')}"),
                            image_alt=img[0].get("alt") if img else None,
                            image_url=img[0].get("src") if img else None,
                        )
                    )
                groups.append(CardGroup(heading=heading, cards=cards))
                idx += 2
                continue
        idx += 1
    return groups


def extract_generated_card_pools(rendered_html: str) -> list[dict[str, Any]]:
    tree = html.fromstring(rendered_html)
    pools: list[dict[str, Any]] = []
    for li in tree.xpath('//span[@id="Generated_cards"]/ancestor::h2[1]/following-sibling::ul[1]/li'):
        description = extract_text(li)
        runquery_links = [
            f"{WIKI_BASE}{href}"
            for href in li.xpath('.//a[contains(@href,"Special:RunQuery/WikiCardPool")]/@href')
        ]
        for query_url in runquery_links:
            cards = extract_card_pool(query_url)
            pools.append(
                asdict(
                    GeneratedCardPool(
                        description=description,
                        query_url=query_url,
                        cards=cards,
                    )
                )
            )
    return pools


def extract_card_pool(query_url: str) -> list[CardLink]:
    resp = Request(query_url, headers={"User-Agent": USER_AGENT})
    with urlopen(resp) as handle:
        rendered_html = handle.read().decode("utf-8")
    tree = html.fromstring(rendered_html)
    cards: list[CardLink] = []
    for card in tree.xpath('//div[contains(@class,"list-cards")]//div[@class="card-div"]'):
        anchor = card.xpath('.//a[starts-with(@href,"/wiki/")][1]')
        if not anchor:
            continue
        a = anchor[0]
        img = card.xpath('.//img[1]')
        cards.append(
            CardLink(
                title=a.get("title") or extract_text(a),
                href=f"{WIKI_BASE}{a.get('href')}",
                card_code=resolve_card_code(f"{WIKI_BASE}{a.get('href')}"),
                image_alt=img[0].get("alt") if img else None,
                image_url=img[0].get("src") if img else None,
            )
        )
    return cards


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


def render_result_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = [f"# {result['page_title']}"]

    if result.get("infobox_fields"):
        lines.append("\n## Infobox")
        for field in result["infobox_fields"]:
            lines.append(f"- **{field['label']}**: {field['value_text']}")

    if result.get("arts"):
        lines.append("\n## Art variants")
        for art in result["arts"]:
            lines.append(f"- **{art['label']}**: {art['file_url']}")

    if result.get("related_cards"):
        lines.append("\n## Related cards")
        for group in result["related_cards"]:
            lines.append(f"### {group['heading']}")
            for card in group["cards"]:
                code = f" `{card['card_code']}`" if card.get("card_code") else ""
                lines.append(f"- [{card['title']}]({card['href']}){code}")

    if result.get("generated_cards"):
        lines.append("\n## Generated cards")
        for pool in result["generated_cards"]:
            lines.append(f"- {pool['description']}")
            lines.append(f"  - Query: {pool['query_url']}")
            for card in pool["cards"]:
                code = f" `{card['card_code']}`" if card.get("card_code") else ""
                lines.append(f"  - [{card['title']}]({card['href']}){code}")

    if result.get("patch_changes"):
        lines.append("\n" + render_patch_markdown(
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
        ).rstrip())

    return "\n".join(lines).rstrip() + "\n"


def build_result(title: str, download: bool, output_dir: Path) -> dict[str, Any]:
    rendered_html = get_rendered_html(title)
    infobox_fields = extract_infobox_fields(rendered_html)
    arts = extract_art_variants(rendered_html)
    related_cards = extract_card_groups(rendered_html, "Related_cards")
    generated_cards = extract_generated_card_pools(rendered_html)
    patches = extract_patch_changes(rendered_html)

    if download:
        art_dir = output_dir / "arts"
        art_dir.mkdir(parents=True, exist_ok=True)
        for idx, art in enumerate(arts, start=1):
            art.downloaded_path = download_art(art, art_dir, idx)

    result = {
        "page_title": title,
        "page_url": canonical_page_url(title),
        "infobox_fields": [asdict(field) for field in infobox_fields],
        "arts": [asdict(art) for art in arts],
        "related_cards": [asdict(group) for group in related_cards],
        "generated_cards": generated_cards,
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
    result_md_path = output_dir / "result.md"
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
    result_md_path.write_text(render_result_markdown(result), encoding="utf-8")

    print(json_path)
    print(result_md_path)
    print(md_path)
    for art in result["arts"]:
        print(art["downloaded_path"] or art["file_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
