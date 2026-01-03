#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from lib.history_db import resolve_db_path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_DATA_DIR = REPO_ROOT / "data"


def timestamp_suffix() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def backup_file(source: Path, backup_dir: Path, suffix: str) -> Path | None:
    if not source.exists():
        print(f"[warn] Missing source file: {source}")
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / f"{source.name}.{suffix}"
    shutil.copy2(source, destination)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backup category config and history database files with timestamps."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: data/history.db).",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help="Path to config directory (default: config).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Path to data directory (default: data).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    suffix = timestamp_suffix()

    categories_path = args.config_dir / "categories.yaml"
    domain_map_path = args.config_dir / "domain-category-map.yaml"
    db_path = resolve_db_path(args.db)

    backups = [
        (categories_path, args.config_dir / "backups"),
        (domain_map_path, args.config_dir / "backups"),
        (db_path, args.data_dir / "backups"),
    ]

    for source, backup_dir in backups:
        destination = backup_file(source, backup_dir, suffix)
        if destination:
            print(f"[ok] {source} -> {destination}")


if __name__ == "__main__":
    main()
