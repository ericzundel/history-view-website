#!/usr/bin/env python3
"""
Initialize the SQLite database used for browsing history processing.

Creates the visits/domains tables and supporting indexes as described in docs/SPEC_v1.md.
Defaults to data/history.db relative to the repo root.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from lib.history_db import SCHEMA
from lib.history_db import resolve_db_path as resolve_db_path_from_lib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize SQLite database for history data.")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database file (default: data/history.db relative to repo root).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database file if present.",
    )
    return parser.parse_args()


def init_db(db_path: Path, force: bool) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists() and force:
        db_path.unlink()
    elif db_path.exists() and not force:
        print(f"Database already exists at {db_path}. Use --force to recreate.")
        return

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        # conn.commit() # Not needed when using `with` context manager

    print(f"Initialized database schema at {db_path}")


def main() -> None:
    args = parse_args()
    db_path = resolve_db_path_from_lib(args.db)
    init_db(db_path, args.force)


if __name__ == "__main__":
    main()
