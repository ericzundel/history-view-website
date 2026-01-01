#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from lib.aggregator import (
    DEFAULT_CATEGORIES_PATH,
    DEFAULT_DOMAIN_MAP_PATH,
    DEFAULT_OUTPUT_DIR,
    write_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate level0/level1 JSON files and favicon sprites from the SQLite store."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: data/history.db).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write JSON outputs (default: data/viz_data).",
    )
    parser.add_argument(
        "--categories",
        type=Path,
        default=DEFAULT_CATEGORIES_PATH,
        help="Path to categories.yaml (default: config/categories.yaml).",
    )
    parser.add_argument(
        "--domain-map",
        type=Path,
        default=DEFAULT_DOMAIN_MAP_PATH,
        help="Path to domain-category-map.yaml (default: config/domain-category-map.yaml).",
    )
    parser.add_argument(
        "--sprites",
        type=Path,
        default=None,
        help="Directory to write sprite SVGs (default: <output>/sprites).",
    )
    parser.add_argument(
        "--skip-sprites",
        action="store_true",
        help="Skip sprite generation (sprite paths will be omitted from JSON).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = write_outputs(
        db_path=args.db,
        output_dir=args.output,
        categories_path=args.categories,
        domain_map_path=args.domain_map,
        sprite_dir=args.sprites,
        skip_sprites=args.skip_sprites,
    )
    sprite_clause = (
        f"sprites: {summary.sprite_files}" if not args.skip_sprites else "sprites: skipped"
    )
    print(
        "Generated level0.json "
        f"({summary.level0_entries} entries), level1-*.json "
        f"({summary.level1_files} files), {sprite_clause}"
    )


if __name__ == "__main__":
    main()
