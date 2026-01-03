#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from lib.history_db import resolve_db_path
from lib.utils import normalize_domain

DEFAULT_MAP_PATH = Path(__file__).resolve().parent.parent / "config" / "domain-category-map.yaml"


# @dataclass tells Python to auto-generate common boilerplate for a class
#  based on its type-annotated fields. It creates methods like __init__,
# __repr__, and __eq__ (and optionally ordering, default values, etc.)
@dataclass
class DomainMapping:
    domain: str
    primary: str | None
    secondary: list[str]


@dataclass
class UpdateStats:
    domains_seen: int = 0
    domains_missing: int = 0
    domains_updated: int = 0
    secondary_inserted: int = 0
    secondary_deleted: int = 0


def _normalize_tag(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text.startswith("#"):
        text = text[1:]
    return text or None


def load_domain_map(path: Path) -> list[DomainMapping]:
    if not path.exists():
        raise FileNotFoundError(f"Domain map not found: {path}")
    payload_raw: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload_raw, dict):
        raise ValueError(f"Expected mapping in {path}")
    payload = cast(dict[str, Any], payload_raw)
    domains_raw = payload.get("domains")
    if not isinstance(domains_raw, list):
        raise ValueError(f"Expected 'domains' list in {path}")

    mappings: list[DomainMapping] = []
    for entry_obj in cast(list[object], domains_raw):
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, object], entry_obj)
        domain_raw = entry.get("domain")
        if domain_raw is None:
            continue
        domain = normalize_domain(str(domain_raw))
        if not domain:
            continue
        primary = _normalize_tag(entry.get("primary"))
        secondary_raw = entry.get("secondary") or []
        secondary: list[str] = []
        if isinstance(secondary_raw, list):
            for item in cast(list[object], secondary_raw):
                tag = _normalize_tag(item)
                if tag:
                    secondary.append(tag)
        seen: set[str] = set()
        deduped_secondary: list[str] = []
        for tag in secondary:
            if tag in seen:
                continue
            seen.add(tag)
            deduped_secondary.append(tag)
        mappings.append(DomainMapping(domain=domain, primary=primary, secondary=deduped_secondary))
    return mappings


def apply_mappings(
    conn: sqlite3.Connection, mappings: list[DomainMapping], *, dry_run: bool
) -> UpdateStats:
    stats = UpdateStats()
    for mapping in mappings:
        stats.domains_seen += 1
        exists = conn.execute(
            "SELECT 1 FROM domains WHERE domain = ? LIMIT 1", (mapping.domain,)
        ).fetchone()
        if not exists:
            stats.domains_missing += 1
            continue

        if dry_run:
            stats.domains_updated += 1
            stats.secondary_deleted += 1
            stats.secondary_inserted += len(mapping.secondary)
            continue

        if mapping.primary is None:
            conn.execute(
                "UPDATE domains SET main_category = NULL WHERE domain = ?", (mapping.domain,)
            )
        else:
            conn.execute(
                "UPDATE domains SET main_category = ? WHERE domain = ?",
                (mapping.primary, mapping.domain),
            )
        stats.domains_updated += 1

        cursor = conn.execute(
            "DELETE FROM secondary_categories WHERE domain = ?", (mapping.domain,)
        )
        if cursor.rowcount > 0:
            stats.secondary_deleted += cursor.rowcount
        for tag in mapping.secondary:
            conn.execute(
                "INSERT INTO secondary_categories (domain, tag) VALUES (?, ?)",
                (mapping.domain, tag),
            )
            stats.secondary_inserted += 1
    return stats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Populate domain categories from config/domain-category-map.yaml."
    )
    parser.add_argument(
        "--db", type=Path, default=None, help="Path to SQLite database (default: data/history.db)."
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=DEFAULT_MAP_PATH,
        help="Path to domain-category-map YAML.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report actions without writing to the database."
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = resolve_db_path(args.db)
    mappings = load_domain_map(args.map)
    if not mappings:
        print(f"No mappings found in {args.map}")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        if args.dry_run:
            stats = apply_mappings(conn, mappings, dry_run=True)
        else:
            with conn:
                stats = apply_mappings(conn, mappings, dry_run=False)
    finally:
        conn.close()

    print(
        f"Processed {stats.domains_seen} domains ({stats.domains_missing} missing). "
        f"Updated {stats.domains_updated} domains. "
        f"Secondary categories: {stats.secondary_deleted} deleted, "
        f"{stats.secondary_inserted} inserted."
    )


if __name__ == "__main__":
    main()
