from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wiki_hs_parser import (
    PatchEntry,
    PatchGroup,
    build_result,
    canonical_page_url,
    mediawiki_query,
    render_patch_markdown,
    render_result_markdown,
)


INDEX_VERSION = 1
QUERY_LIMIT = 500
SCOPES = ("card", "bg-minion", "bg-hero")

SOURCE_CONFIGS: dict[str, dict[str, str]] = {
    "card": {
        "source_url": "https://hearthstone.wiki.gg/wiki/Special:RunQuery/Card",
        "tables": "Card,CustomCard,CardTag",
        "join_on": "Card.dbfId=CustomCard.dbfId,Card.dbfId=CardTag.dbfId",
        "fields": ",".join(
            [
                "CustomCard._pageName=page",
                "Card.name=name",
                "Card.id=card_id",
                "Card.dbfId=dbf_id",
                "Card.artistName=artist",
                "Card.flavorText=flavor_text",
                "CardTag.typeId=type_id",
                "CardTag.cost=cost",
                "CardTag.attack=attack",
                "CardTag.health=health",
                "CardTag.armor=armor",
                "CardTag.isCollectible=is_collectible",
                "CardTag.isElite=is_elite",
            ]
        ),
        "where": "",
        "order_by": "Card.dbfId",
    },
    "bg-minion": {
        "source_url": "https://hearthstone.wiki.gg/wiki/Special:RunQuery/BG/Minion",
        "tables": "Card,CustomCard,CardTagBg,CardTag",
        "join_on": "Card.dbfId=CustomCard.dbfId,Card.dbfId=CardTagBg.dbfId,Card.dbfId=CardTag.dbfId",
        "fields": ",".join(
            [
                "CustomCard._pageName=page",
                "CustomCard.bgPage=bg_page",
                "Card.name=name",
                "Card.id=card_id",
                "Card.dbfId=dbf_id",
                "Card.artistName=artist",
                "Card.flavorText=flavor_text",
                "CardTag.typeId=type_id",
                "CardTag.cost=cost",
                "CardTag.attack=attack",
                "CardTag.health=health",
                "CardTag.isCollectible=is_collectible",
                "CardTagBg.tier=tier",
                "CardTagBg.isPoolMinion=is_pool_minion",
                "CardTagBg.normalDbfId=normal_dbf_id",
                "CardTagBg.premiumDbfId=premium_dbf_id",
                "CardTagBg.bannedInSolo=banned_in_solo",
                "CardTagBg.bannedInDuos=banned_in_duos",
            ]
        ),
        "where": 'CardTagBg.tier IS NOT NULL AND CardTagBg.tier <> "" AND CardTag.typeId=4',
        "order_by": "Card.dbfId",
    },
    "bg-hero": {
        "source_url": "https://hearthstone.wiki.gg/wiki/Special:RunQuery/BG/Hero",
        "tables": "Card,CustomCard,CardTagBg,CardTag",
        "join_on": "Card.dbfId=CustomCard.dbfId,Card.dbfId=CardTagBg.dbfId,Card.dbfId=CardTag.dbfId",
        "fields": ",".join(
            [
                "CustomCard._pageName=page",
                "CustomCard.bgPage=bg_page",
                "Card.name=name",
                "Card.id=card_id",
                "Card.dbfId=dbf_id",
                "Card.artistName=artist",
                "Card.flavorText=flavor_text",
                "CardTag.health=health",
                "CardTag.armor=armor",
                "CardTagBg.isDraftableHero=is_draftable_hero",
                "CardTagBg.duosArmorValue=duos_armor",
                "CardTagBg.buddyDbfId=buddy_dbf_id",
                "CardTagBg.skinParentDbfId=skin_parent_dbf_id",
            ]
        ),
        "where": "CardTagBg.isDraftableHero=1",
        "order_by": "Card.name",
    },
}


def clean_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def parse_int_field(value: Any) -> int | None:
    text = clean_string(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    return int(match.group(0)) if match else None


def parse_bool_field(value: Any) -> bool | None:
    text = clean_string(value).lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def lookup_key(value: Any) -> str:
    return clean_string(value).lower()


def is_dbf_id(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def cargo_rows(config: dict[str, str], offset: int) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "action": "cargoquery",
        "tables": config["tables"],
        "join_on": config["join_on"],
        "fields": config["fields"],
        "limit": QUERY_LIMIT,
        "offset": offset,
        "format": "json",
    }
    if config.get("where"):
        params["where"] = config["where"]
    if config.get("order_by"):
        params["order_by"] = config["order_by"]

    data = mediawiki_query(params)
    if "error" in data:
        raise RuntimeError(f"Cargo API error: {data['error'].get('info', data['error'])}")
    return [item.get("title", {}) for item in data.get("cargoquery", [])]


def query_scope(scope: str) -> list[dict[str, Any]]:
    config = SOURCE_CONFIGS[scope]
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = cargo_rows(config, offset)
        rows.extend(batch)
        if len(batch) < QUERY_LIMIT:
            break
        offset += QUERY_LIMIT
    return rows


def entry_details(row: dict[str, Any]) -> dict[str, Any]:
    numeric_fields = {
        "type_id",
        "cost",
        "attack",
        "health",
        "armor",
        "tier",
        "normal_dbf_id",
        "premium_dbf_id",
        "duos_armor",
        "buddy_dbf_id",
        "skin_parent_dbf_id",
    }
    bool_fields = {
        "is_collectible",
        "is_elite",
        "is_pool_minion",
        "banned_in_solo",
        "banned_in_duos",
        "is_draftable_hero",
    }
    ignored = {"page", "bg_page", "name", "card_id", "dbf_id"}
    details: dict[str, Any] = {}
    for key, value in row.items():
        if key in ignored:
            continue
        if key in numeric_fields:
            parsed = parse_int_field(value)
        elif key in bool_fields:
            parsed = parse_bool_field(value)
        else:
            parsed = clean_string(value)
        if parsed is not None and parsed != "":
            details[key] = parsed
    return details


def normalize_entry(scope: str, row: dict[str, Any]) -> dict[str, Any] | None:
    page_title = clean_string(row.get("bg_page")) or clean_string(row.get("page"))
    card_id = clean_string(row.get("card_id"))
    dbf_id = parse_int_field(row.get("dbf_id"))
    if not page_title or not card_id or dbf_id is None:
        return None

    return {
        "scope": scope,
        "source_url": SOURCE_CONFIGS[scope]["source_url"],
        "page_title": page_title,
        "page_url": canonical_page_url(page_title),
        "name": clean_string(row.get("name")),
        "card_id": card_id,
        "dbf_id": dbf_id,
        "details": entry_details(row),
    }


def add_lookup(lookups: dict[str, dict[str, list[int]]], group: str, key: Any, index: int) -> None:
    normalized = lookup_key(key)
    if not normalized:
        return
    lookups[group].setdefault(normalized, []).append(index)


def rebuild_lookups(entries: list[dict[str, Any]]) -> dict[str, dict[str, list[int]]]:
    lookups: dict[str, dict[str, list[int]]] = {
        "by_card_id": {},
        "by_dbf_id": {},
        "by_name": {},
    }
    for index, entry in enumerate(entries):
        add_lookup(lookups, "by_card_id", entry.get("card_id"), index)
        add_lookup(lookups, "by_dbf_id", entry.get("dbf_id"), index)
        add_lookup(lookups, "by_name", entry.get("name"), index)
    return lookups


def build_index(scopes: list[str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[tuple[str, str, int, str]] = set()

    for scope in scopes:
        count = 0
        for row in query_scope(scope):
            entry = normalize_entry(scope, row)
            if not entry:
                continue
            identity = (entry["scope"], entry["card_id"], entry["dbf_id"], entry["page_title"])
            if identity in seen:
                continue
            seen.add(identity)
            entries.append(entry)
            count += 1
        counts[scope] = count

    return {
        "version": INDEX_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {scope: SOURCE_CONFIGS[scope]["source_url"] for scope in scopes},
        "counts": counts,
        "entries": entries,
        "lookups": rebuild_lookups(entries),
    }


def merge_index(existing: dict[str, Any] | None, refreshed: dict[str, Any], scopes: list[str]) -> dict[str, Any]:
    if not existing:
        return refreshed

    kept_entries = [entry for entry in existing.get("entries", []) if entry.get("scope") not in scopes]
    entries = kept_entries + refreshed["entries"]
    counts: dict[str, int] = {}
    for entry in entries:
        scope = entry.get("scope", "")
        counts[scope] = counts.get(scope, 0) + 1

    sources = dict(existing.get("sources", {}))
    sources.update(refreshed.get("sources", {}))
    return {
        "version": INDEX_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "counts": counts,
        "entries": entries,
        "lookups": rebuild_lookups(entries),
    }


def load_index(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != INDEX_VERSION:
        return None
    return data


def save_index(path: Path, index: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def required_scopes(scope: str) -> list[str]:
    return list(SCOPES) if scope == "all" else [scope]


def load_or_refresh_index(path: Path, scope: str, refresh: bool) -> tuple[dict[str, Any], bool]:
    needed = required_scopes(scope)
    existing = load_index(path)
    existing_scopes = set((existing or {}).get("counts", {}).keys())
    missing = [item for item in needed if item not in existing_scopes]

    if refresh or missing or existing is None:
        refresh_scopes = needed if refresh or existing is None else missing
        refreshed = build_index(refresh_scopes)
        index = merge_index(existing, refreshed, refresh_scopes)
        save_index(path, index)
        return index, True
    return existing, False


def filter_scope(entries: list[dict[str, Any]], scope: str) -> list[dict[str, Any]]:
    if scope == "all":
        return entries
    return [entry for entry in entries if entry.get("scope") == scope]


def lookup_entries(index: dict[str, Any], value: str | None, name: str | None, scope: str) -> list[dict[str, Any]]:
    entries = index.get("entries", [])
    lookups = index.get("lookups", {})
    indexes: list[int] = []

    if value:
        group = "by_dbf_id" if is_dbf_id(value) else "by_card_id"
        indexes.extend(lookups.get(group, {}).get(lookup_key(value), []))
    if name:
        indexes.extend(lookups.get("by_name", {}).get(lookup_key(name), []))

    seen: set[int] = set()
    matches: list[dict[str, Any]] = []
    for index in indexes:
        if index in seen or index >= len(entries):
            continue
        seen.add(index)
        matches.append(entries[index])
    return filter_scope(matches, scope)


def write_full_result(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "result.md").write_text(render_result_markdown(result), encoding="utf-8")
    (output_dir / "patch-changes.md").write_text(
        render_patch_markdown(
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
        ),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fast Hearthstone Wiki lookup by card id or dbfId.")
    parser.add_argument("--id", help="Card id such as OG_280 or dbfId such as 38857")
    parser.add_argument("--name", help="Exact card name fallback, for example C'Thun")
    parser.add_argument("--scope", choices=("all", *SCOPES), default="all", help="Lookup source to use")
    parser.add_argument("--index-path", default="out/wiki-card-index.json", help="Local JSON index cache")
    parser.add_argument("--refresh-index", action="store_true", help="Rebuild the selected scope in the local index")
    parser.add_argument("--fetch", action="store_true", help="Run the full page parser for the first match")
    parser.add_argument("--output-dir", default="out/lookup", help="Directory for lookup.json and optional parser output")
    parser.add_argument("--no-download", action="store_true", help="When --fetch is used, do not download art files")
    args = parser.parse_args(argv)

    if not args.id and not args.name and not args.refresh_index:
        parser.error("Provide --id, --name, or --refresh-index")

    index_path = Path(args.index_path)
    index, refreshed = load_or_refresh_index(index_path, args.scope, args.refresh_index)
    matches = lookup_entries(index, args.id, args.name, args.scope)

    payload: dict[str, Any] = {
        "query": {
            "id": args.id,
            "name": args.name,
            "scope": args.scope,
            "index_path": str(index_path),
            "index_refreshed": refreshed,
        },
        "index_counts": index.get("counts", {}),
        "matches": matches,
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.fetch and matches:
        selected = matches[0]
        result = build_result(selected["page_title"], download=not args.no_download, output_dir=output_dir)
        payload["selected_match"] = selected
        payload["result"] = result
        write_full_result(output_dir, result)

    (output_dir / "lookup.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if matches or args.refresh_index else 2


if __name__ == "__main__":
    raise SystemExit(main())
