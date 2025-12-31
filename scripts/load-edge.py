#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from lib.history_db import (
    LoaderStats,
    VisitRecord,
    extract_domain,
    normalize_timestamp,
    process_records,
    resolve_db_path,
    should_skip_url,
    summarize_stats,
)


def parse_edge_records(payload: object) -> Iterable[VisitRecord]:
    records: list[dict[str, object]] = []
    if isinstance(payload, list):
        for entry_obj in cast(list[object], payload):
            if isinstance(entry_obj, dict):
                entry_dict = cast(dict[str, object], entry_obj)
                records.append(entry_dict)
    elif isinstance(payload, dict):
        payload_dict = cast(dict[str, Any], payload)
        candidate = (
            payload_dict.get("records") or payload_dict.get("history") or payload_dict.get("items")
        )
        if not isinstance(candidate, list):
            raise ValueError(
                "Unsupported Edge export structure; expected list under records/history."
            )
        for entry_obj in cast(list[object], candidate):
            if isinstance(entry_obj, dict):
                entry_dict = cast(dict[str, object], entry_obj)
                records.append(entry_dict)
    else:
        raise ValueError("Edge export must be a list or dict containing records/history.")

    for entry in records:
        url = entry.get("url")
        if url is None:
            continue

        raw_url = str(url)
        skip, warning = should_skip_url(raw_url)
        if skip:
            if warning:
                print(f"[warn] {warning}")
            continue

        timestamp_raw = (
            entry.get("datetime")
            or entry.get("timestamp")
            or _combine_date_time(entry.get("date"), entry.get("time"))
        )
        if timestamp_raw is None:
            continue

        domain = extract_domain(raw_url)
        timestamp = normalize_timestamp(timestamp_raw)
        title = entry.get("title")
        yield VisitRecord(domain=domain, timestamp=timestamp, title=str(title) if title else None)


def _combine_date_time(date: object | None, time: object | None) -> str | None:
    if date is None or time is None:
        return None
    return f"{date} {time}"


def load_file(
    path: Path,
    db_path: Path,
    *,
    dry_run: bool,
    limit: int | None,
    verbose: bool,
    quiet: bool,
    blocklist: set[str] | None = None,
) -> LoaderStats:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    records = parse_edge_records(payload)
    return process_records(
        records,
        db_path,
        dry_run=dry_run,
        limit=limit,
        verbose=verbose,
        quiet=quiet,
        blocklist=blocklist,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load Edge history export into SQLite.")
    parser.add_argument("input", type=Path, help="Path to edge-history-export JSON file.")
    parser.add_argument(
        "--db", type=Path, default=None, help="Path to SQLite database (default: data/history.db)."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without writing to the database."
    )
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N records.")
    parser.add_argument("--verbose", action="store_true", help="Print per-record actions.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress dots.")
    parser.add_argument(
        "--blocklist",
        type=Path,
        default=None,
        help="Path to domain blocklist YAML (default: config/domain-blocklist.yml).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = resolve_db_path(args.db)
    from lib.history_db import load_blocklist

    blocklist = load_blocklist(args.blocklist)
    stats = load_file(
        args.input,
        db_path,
        dry_run=args.dry_run,
        limit=args.limit,
        verbose=args.verbose,
        quiet=args.quiet,
        blocklist=blocklist,
    )
    print(summarize_stats(stats, args.dry_run))


if __name__ == "__main__":
    main()
