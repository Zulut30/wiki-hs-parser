import argparse
import json
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wiki_hs_lookup import SCOPES, filter_scope, load_or_refresh_index
from wiki_hs_parser import build_result, safe_filename


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def grouped_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        title = entry["page_title"]
        if title not in grouped:
            grouped[title] = {
                "page_title": title,
                "page_url": entry["page_url"],
                "scopes": [],
                "lookups": [],
            }
        page = grouped[title]
        if entry["scope"] not in page["scopes"]:
            page["scopes"].append(entry["scope"])
        page["lookups"].append(entry)
    return list(grouped.values())


def cache_path(cache_dir: Path, page_title: str) -> Path:
    return cache_dir / f"{safe_filename(page_title)}.json"


def load_cached_page(cache_dir: Path, page_title: str) -> dict[str, Any] | None:
    path = cache_path(cache_dir, page_title)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_cached_page(cache_dir: Path, page_title: str, result: dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path(cache_dir, page_title).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def sleep_between_requests(delay_seconds: float, jitter_seconds: float) -> None:
    wait = max(0.0, delay_seconds)
    if jitter_seconds > 0:
        wait += random.uniform(0, jitter_seconds)
    if wait:
        time.sleep(wait)


def fetch_page(
    page_title: str,
    cache_dir: Path,
    refresh_pages: bool,
    retries: int,
) -> tuple[dict[str, Any], str]:
    if not refresh_pages:
        cached = load_cached_page(cache_dir, page_title)
        if cached is not None:
            return cached, "cache"

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = build_result(page_title, download=False, output_dir=cache_dir)
            save_cached_page(cache_dir, page_title, result)
            return result, "network"
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2**attempt)
    raise RuntimeError(f"Failed to fetch {page_title!r}: {last_error}") from last_error


def build_export_record(page: dict[str, Any], page_result: dict[str, Any] | None, source: str) -> dict[str, Any]:
    return {
        "source": "hearthstone.wiki.gg",
        "fetched_from": source,
        "exported_at": utc_now(),
        "page_title": page["page_title"],
        "page_url": page["page_url"],
        "scopes": page["scopes"],
        "lookups": page["lookups"],
        "result": page_result,
    }


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def init_sqlite(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            page_title TEXT PRIMARY KEY,
            page_url TEXT NOT NULL,
            scopes_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            exported_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lookup_cards (
            scope TEXT NOT NULL,
            card_id TEXT NOT NULL,
            dbf_id INTEGER NOT NULL,
            name TEXT,
            page_title TEXT NOT NULL,
            page_url TEXT NOT NULL,
            details_json TEXT NOT NULL,
            exported_at TEXT NOT NULL,
            PRIMARY KEY (scope, card_id, dbf_id)
        )
        """
    )
    return conn


def write_sqlite(records: list[dict[str, Any]], output_path: Path) -> None:
    conn = init_sqlite(output_path)
    try:
        with conn:
            for record in records:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO pages
                    (page_title, page_url, scopes_json, payload_json, exported_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record["page_title"],
                        record["page_url"],
                        json.dumps(record["scopes"], ensure_ascii=False),
                        json.dumps(record, ensure_ascii=False),
                        record["exported_at"],
                    ),
                )
                for lookup in record["lookups"]:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO lookup_cards
                        (scope, card_id, dbf_id, name, page_title, page_url, details_json, exported_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lookup["scope"],
                            lookup["card_id"],
                            lookup["dbf_id"],
                            lookup.get("name"),
                            lookup["page_title"],
                            lookup["page_url"],
                            json.dumps(lookup.get("details", {}), ensure_ascii=False),
                            record["exported_at"],
                        ),
                    )
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Hearthstone Wiki parser data to JSONL and SQLite safely.")
    parser.add_argument("--scope", required=True, choices=("all", *SCOPES), help="Explicit export scope. Use all only when you really want every supported scope.")
    parser.add_argument("--index-path", default="out/wiki-card-index.json", help="Local lookup index path")
    parser.add_argument("--refresh-index", action="store_true", help="Refresh the selected lookup scope before export")
    parser.add_argument("--cache-dir", default="out/export-cache", help="Per-page parser result cache")
    parser.add_argument("--refresh-pages", action="store_true", help="Ignore cached page results and fetch pages again")
    parser.add_argument("--index-only", action="store_true", help="Export lookup records without fetching full wiki pages")
    parser.add_argument("--max-pages", type=int, help="Safety limit for test exports")
    parser.add_argument("--delay-seconds", type=float, default=1.2, help="Base delay after each network page fetch")
    parser.add_argument("--jitter-seconds", type=float, default=0.4, help="Random extra delay after each network page fetch")
    parser.add_argument("--retries", type=int, default=3, help="Retry count per page")
    parser.add_argument("--output-jsonl", default="out/export/wiki-hs-export.jsonl", help="JSONL export path")
    parser.add_argument("--output-sqlite", help="Optional SQLite export path")
    args = parser.parse_args(argv)

    index, refreshed = load_or_refresh_index(Path(args.index_path), args.scope, args.refresh_index)
    entries = filter_scope(index.get("entries", []), args.scope)
    pages = grouped_entries(entries)
    if args.max_pages is not None:
        pages = pages[: max(0, args.max_pages)]

    records: list[dict[str, Any]] = []
    cache_dir = Path(args.cache_dir)
    for number, page in enumerate(pages, start=1):
        source = "index-only"
        result = None
        if not args.index_only:
            result, source = fetch_page(page["page_title"], cache_dir, args.refresh_pages, args.retries)
            if source == "network" and number < len(pages):
                sleep_between_requests(args.delay_seconds, args.jitter_seconds)
        records.append(build_export_record(page, result, source))
        print(f"[{number}/{len(pages)}] {page['page_title']} ({source})", file=sys.stderr)

    write_jsonl(records, Path(args.output_jsonl))
    if args.output_sqlite:
        write_sqlite(records, Path(args.output_sqlite))

    summary = {
        "scope": args.scope,
        "index_refreshed": refreshed,
        "pages_exported": len(records),
        "jsonl": args.output_jsonl,
        "sqlite": args.output_sqlite,
        "cache_dir": args.cache_dir,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
