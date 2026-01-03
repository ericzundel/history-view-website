#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from lib.domain_map import DomainMapping, load_domain_map
from lib.history_db import resolve_db_path

DEFAULT_MAP_PATH = Path(__file__).resolve().parent.parent / "config" / "domain-category-map.yaml"


@dataclass
class UpdateStats:
    domains_seen: int = 0
    domains_missing: int = 0
    domains_updated: int = 0
    secondary_inserted: int = 0
    secondary_deleted: int = 0


def apply_mappings(
    conn: sqlite3.Connection, mappings: dict[str, DomainMapping], *, dry_run: bool
) -> UpdateStats:
    """Populate the history database from the domain mappings.

    Populates the primary_category in the domains table and the
    rows in the secondary_categories table.
    """
    stats = UpdateStats()
    for domain, mapping in mappings.items():
        stats.domains_seen += 1
        exists = conn.execute(
            "SELECT 1 FROM domains WHERE domain = ? LIMIT 1", (domain,)
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
            conn.execute("UPDATE domains SET main_category = NULL WHERE domain = ?", (domain,))
        else:
            conn.execute(
                "UPDATE domains SET main_category = ? WHERE domain = ?",
                (mapping.primary, domain),
            )
        stats.domains_updated += 1

        cursor = conn.execute("DELETE FROM secondary_categories WHERE domain = ?", (domain,))
        if cursor.rowcount > 0:
            stats.secondary_deleted += cursor.rowcount
        for tag in mapping.secondary:
            conn.execute(
                "INSERT INTO secondary_categories (domain, tag) VALUES (?, ?)",
                (domain, tag),
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
