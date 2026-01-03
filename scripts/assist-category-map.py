#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from dotenv import load_dotenv
from lib import (
    DEFAULT_CATEGORY_FILENAME,
    DEFAULT_DOMAIN_MAP_FILENAME,
    DEFAULT_MODEL,
    OPENAI_ENDPOINT,
)
from lib.domain_map import DomainMapping, load_domain_map, update_domain_map
from lib.history_db import resolve_db_path
from lib.utils import coerce_str, ensure_list, ensure_mapping, merge_lists, normalize_tag

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class CategoryTag:
    tag: str
    label: str
    is_primary: bool


@dataclass
class DomainEntry:
    domain: str
    title: str | None


def load_categories(path: Path) -> tuple[list[CategoryTag], list[CategoryTag]]:
    payload_obj: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload = ensure_mapping(payload_obj, context=f"{path}")
    if "categories" not in payload:
        raise ValueError(f"Expected categories list in {path}")
    raw_categories = ensure_list(payload["categories"], context=f"{path} categories")

    primary: list[CategoryTag] = []
    secondary: list[CategoryTag] = []
    for entry_obj in raw_categories:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, Any], entry_obj)
        raw_tag_value = coerce_str(entry.get("tag"))
        raw_tag = normalize_tag(raw_tag_value) if raw_tag_value else None
        if not raw_tag:
            continue
        label = coerce_str(entry.get("label")) or raw_tag
        is_primary = (coerce_str(entry.get("type")) or "").lower() == "primary"
        tag = CategoryTag(tag=raw_tag, label=label, is_primary=is_primary)
        if is_primary:
            primary.append(tag)
        else:
            secondary.append(tag)

    if not primary:
        raise ValueError(f"No primary categories found in {path}")
    return primary, secondary


def load_domains_from_db(db_path: Path) -> list[DomainEntry]:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute("SELECT domain, title FROM domains")
        return [DomainEntry(domain=row[0], title=row[1]) for row in cursor.fetchall()]
    finally:
        conn.close()


def build_prompt(
    batch: Iterable[dict[str, Any]],
    *,
    primary_categories: list[CategoryTag],
    secondary_categories: list[CategoryTag],
    mode: str,
) -> list[dict[str, str]]:
    primary_payload = [{"tag": cat.tag, "label": cat.label} for cat in primary_categories]
    secondary_payload = [{"tag": cat.tag, "label": cat.label} for cat in secondary_categories]

    system = (
        "You classify domains into categories. Return strict JSON with an 'items' list. "
        "Tags must match the provided categories (lowercase, no leading '#'). "
        "Pick exactly one primary tag. Choose up to 5 secondary tags. "
        "Treat subdomains independently. If a domain is unclear, use 'other' as primary "
        "and add the most relevant secondary tags. Use 'securityprivacy' as a secondary "
        "tag when the domain suggests tracking or privacy-sensitive tooling."
    )
    user = {
        "mode": mode,
        "categories": {
            "primary": primary_payload,
            "secondary": secondary_payload,
        },
        "domains": list(batch),
        "response_format": {
            "items": [
                {
                    "domain": "example.com",
                    "primary": "news",
                    "secondary": ["technews", "worldnews"],
                }
            ]
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=True)},
    ]


def request_classifications(
    client: httpx.Client,
    *,
    model: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    logger.info("Requesting classifications from OpenAI API")
    response = client.post(
        OPENAI_ENDPOINT,
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        },
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed: object = json.loads(content)
    return ensure_mapping(parsed, context="response payload")


def filter_valid(tags: Iterable[str], allowed: set[str]) -> list[str]:
    valid: list[str] = []
    for tag in tags:
        normalized = normalize_tag(tag)
        if normalized and normalized in allowed:
            valid.append(normalized)
    return valid


def iter_batches(items: list[dict[str, Any]], batch_size: int) -> Iterable[list[dict[str, Any]]]:
    for idx in range(0, len(items), batch_size):
        yield items[idx : idx + batch_size]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Use ChatGPT to assist with categorizing domains into primary/secondary tags."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to SQLite database (default: data/history.db).",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional domains file (domain|title) to classify instead of querying the DB.",
    )
    parser.add_argument(
        "--categories",
        type=Path,
        default=Path(DEFAULT_CATEGORY_FILENAME),
        help="Path to categories YAML.",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=Path(DEFAULT_DOMAIN_MAP_FILENAME),
        help="Path to domain-category map YAML.",
    )
    parser.add_argument(
        "--mode",
        choices=["primary", "secondary", "both"],
        default="both",
        help="Which tags to fill in.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model to use (default: env OPENAI_MODEL or gpt-4o-mini).",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key (default: env OPENAI_API_KEY).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Number of domains per API request.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=5.0,
        help="Seconds to sleep between API requests.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of domains processed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write updates to domain-category-map.yaml.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip over domains that already have a category assigned in the map.",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    args = build_parser().parse_args()
    if not args.api_key:
        raise SystemExit("Missing OPENAI_API_KEY (or pass --api-key).")

    primary_categories, secondary_categories = load_categories(args.categories)
    all_tags = {cat.tag for cat in primary_categories + secondary_categories}
    primary_tags = {cat.tag for cat in primary_categories}

    domain_map = load_domain_map(args.map)

    db_path = resolve_db_path(args.db)
    domains = load_domains_from_db(db_path)

    pending: list[dict[str, Any]] = []
    for entry in domains:
        domain = entry.domain.lower()
        existing = domain_map.get(domain, DomainMapping())
        if args.skip_existing and (existing.primary):
            continue
        if args.mode == "secondary" and not existing.primary:
            continue
        needs_primary = args.mode in {"primary", "both"} and not existing.primary
        needs_secondary = args.mode in {"secondary", "both"} and not existing.secondary
        if not (needs_primary or needs_secondary):
            continue
        payload: dict[str, Any] = {"domain": domain, "title": entry.title}
        if existing.primary:
            payload["primary"] = existing.primary
        pending.append(payload)

    if args.limit is not None:
        pending = pending[: args.limit]

    if not pending:
        print("No domains require classification.")
        return

    headers = {"Authorization": f"Bearer {args.api_key}"}
    client = httpx.Client(headers=headers)
    try:
        for batch in iter_batches(pending, args.batch_size):
            start_time = time.monotonic()
            messages = build_prompt(
                batch,
                primary_categories=primary_categories,
                secondary_categories=secondary_categories,
                mode=args.mode,
            )
            response = request_classifications(client, model=args.model, messages=messages)
            items_raw: object = response.get("items", [])
            items = ensure_list(items_raw, context="response items")

            for item_obj in items:
                if not isinstance(item_obj, dict):
                    continue
                item = cast(dict[str, Any], item_obj)
                domain = (coerce_str(item.get("domain")) or "").lower()
                if not domain:
                    continue
                existing = domain_map.get(domain, DomainMapping())
                primary_raw = normalize_tag(coerce_str(item.get("primary")))
                secondary_raw: object = item.get("secondary", [])
                secondary_list: list[str] = []
                if isinstance(secondary_raw, list):
                    secondary_list = list(
                        filter(None, (coerce_str(tag) for tag in cast(list[object], secondary_raw)))
                    )

                if not existing.primary:
                    if primary_raw and primary_raw in primary_tags:
                        existing.primary = primary_raw
                secondary_valid = filter_valid(secondary_list, all_tags)
                if secondary_valid:
                    existing.secondary = merge_lists(existing.secondary, secondary_valid)
                domain_map[domain] = existing

            if args.dry_run:
                print(f"Dry run enabled; not writing {args.map}.")
            else:
                update_domain_map(args.map, domain_map)

            end_time = time.monotonic()
            logging.info(f"Batch processed in {end_time - start_time:.2f} seconds.")
            if args.delay:
                logging.info(f"Sleeping for {args.delay} seconds before next batch...")
                time.sleep(args.delay)
    finally:
        client.close()

    print(f"Updated {args.map}")


if __name__ == "__main__":
    main()
