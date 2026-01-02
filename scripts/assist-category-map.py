#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx
import yaml
from dotenv import load_dotenv
from lib.history_db import resolve_db_path

DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

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


@dataclass
class DomainMapping:
    primary: str | None = None
    secondary: list[str] = field(default_factory=lambda: [])


def normalize_tag(tag: str | None) -> str | None:
    if tag is None:
        return None
    normalized = tag.strip().lower()
    if normalized.startswith("#"):
        normalized = normalized[1:]
    return normalized or None


def _ensure_mapping(value: object, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {context}.")
    return cast(dict[str, Any], value)


def _ensure_list(value: object, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {context}.")
    return [cast(Any, item) for item in cast(list[object], value)]


def _coerce_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_categories(path: Path) -> tuple[list[CategoryTag], list[CategoryTag]]:
    payload_obj: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload = _ensure_mapping(payload_obj, context=f"{path}")
    if "categories" not in payload:
        raise ValueError(f"Expected categories list in {path}")
    raw_categories = _ensure_list(payload["categories"], context=f"{path} categories")

    primary: list[CategoryTag] = []
    secondary: list[CategoryTag] = []
    for entry_obj in raw_categories:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, Any], entry_obj)
        raw_tag_value = _coerce_str(entry.get("tag"))
        raw_tag = normalize_tag(raw_tag_value) if raw_tag_value else None
        if not raw_tag:
            continue
        label = _coerce_str(entry.get("label")) or raw_tag
        is_primary = (_coerce_str(entry.get("type")) or "").lower() == "primary"
        tag = CategoryTag(tag=raw_tag, label=label, is_primary=is_primary)
        if is_primary:
            primary.append(tag)
        else:
            secondary.append(tag)

    if not primary:
        raise ValueError(f"No primary categories found in {path}")
    return primary, secondary


def load_domain_map(path: Path) -> dict[str, DomainMapping]:
    if not path.exists():
        return {}
    payload_obj: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    payload = _ensure_mapping(payload_obj, context=f"{path}")
    domains = payload.get("domains", []) or [{}]
    raw_domains = _ensure_list(domains, context=f"{path} domains")

    mapping: dict[str, DomainMapping] = {}
    for entry_obj in raw_domains:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, Any], entry_obj)
        domain = (_coerce_str(entry.get("domain")) or "").lower()
        if not domain:
            continue
        primary = normalize_tag(_coerce_str(entry.get("primary")))
        secondary_raw: object = entry.get("secondary") or []
        secondary: list[str] = []
        if isinstance(secondary_raw, list):
            for tag_obj in cast(list[object], secondary_raw):
                normalized = normalize_tag(_coerce_str(tag_obj))
                if normalized:
                    secondary.append(normalized)
        mapping[domain] = DomainMapping(primary=primary, secondary=secondary)
    return mapping


def write_domain_map(path: Path, mapping: dict[str, DomainMapping]) -> None:
    domains_payload: list[dict[str, Any]] = []
    for domain in sorted(mapping.keys()):
        entry = mapping[domain]
        domains_payload.append(
            {
                "domain": domain,
                "primary": entry.primary,
                "secondary": entry.secondary,
            }
        )

    payload = {"domains": domains_payload}
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


def update_domain_map(path: Path, mapping: dict[str, DomainMapping]) -> None:
    existing_mapping = load_domain_map(path)
    for domain, entry in mapping.items():
        if domain in existing_mapping:
            existing_entry = existing_mapping[domain]
            if entry.primary is not None:
                existing_entry.primary = entry.primary
            existing_entry.secondary = merge_secondary(existing_entry.secondary, entry.secondary)
        else:
            existing_mapping[domain] = entry
    write_domain_map(path, existing_mapping)


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
    return _ensure_mapping(parsed, context="response payload")


def merge_secondary(existing: list[str], incoming: list[str]) -> list[str]:
    seen = set(existing)
    merged = list(existing)
    for tag in incoming:
        if tag not in seen:
            merged.append(tag)
            seen.add(tag)
    return merged


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
        default=Path("config/categories.yaml"),
        help="Path to categories YAML.",
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=Path("config/domain-category-map.yaml"),
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
            items = _ensure_list(items_raw, context="response items")

            for item_obj in items:
                if not isinstance(item_obj, dict):
                    continue
                item = cast(dict[str, Any], item_obj)
                domain = (_coerce_str(item.get("domain")) or "").lower()
                if not domain:
                    continue
                existing = domain_map.get(domain, DomainMapping())
                primary_raw = normalize_tag(_coerce_str(item.get("primary")))
                secondary_raw: object = item.get("secondary", [])
                secondary_list: list[str] = []
                if isinstance(secondary_raw, list):
                    secondary_list = list(
                        filter(
                            None, (_coerce_str(tag) for tag in cast(list[object], secondary_raw))
                        )
                    )

                if not existing.primary:
                    if primary_raw and primary_raw in primary_tags:
                        existing.primary = primary_raw
                secondary_valid = filter_valid(secondary_list, all_tags)
                if secondary_valid:
                    existing.secondary = merge_secondary(existing.secondary, secondary_valid)
                domain_map[domain] = existing

            if args.dry_run:
                print("Dry run enabled; not writing domain-category-map.yaml.")
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
