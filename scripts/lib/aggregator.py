from __future__ import annotations

import json
import sqlite3
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast
from zoneinfo import ZoneInfo

import yaml

from lib.history_db import open_connection, resolve_db_path
from lib.utils import as_str, normalize_domain

# scripts/lib -> scripts -> repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CATEGORIES_PATH = ROOT_DIR / "config" / "categories.yaml"
DEFAULT_DOMAIN_MAP_PATH = ROOT_DIR / "config" / "domain-category-map.yaml"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "viz_data"


def _new_str_set() -> set[str]:
    return set()


def _new_str_int_dict() -> dict[str, int]:
    return {}


@dataclass
class CategoryDef:
    tag: str
    label: str
    type: str | None = None


@dataclass
class DomainOverride:
    primary: str | None
    secondary: list[str]


@dataclass
class DomainMetadata:
    domain: str
    title: str | None
    primary_tag: str | None
    secondary_tags: set[str] = field(default_factory=_new_str_set)
    favicon_type: str | None = None
    favicon_data: bytes | None = None


@dataclass
class SlotAggregate:
    day: int
    hour: int
    total: int = 0
    per_domain: dict[str, int] = field(default_factory=_new_str_int_dict)


@dataclass
class SpriteSymbol:
    domain: str
    symbol_id: str
    mime_type: str | None
    data: bytes


@dataclass
class GenerationSummary:
    level0_entries: int
    level1_files: int
    sprite_files: int


class SiteEntry(TypedDict, total=False):
    domain: str
    title: str
    url: str
    value: int
    favicon_symbol_id: NotRequired[str]
    secondary_tags: NotRequired[list[str]]


class CategoryGroup(TypedDict):
    tag: str
    label: str
    value: int
    sites: list[SiteEntry]


def normalize_tag(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = raw.strip().lower()
    if not cleaned:
        return None
    if cleaned.startswith("#"):
        return cleaned
    return f"#{cleaned}"


def load_categories(path: Path = DEFAULT_CATEGORIES_PATH) -> dict[str, CategoryDef]:
    if not path.exists():
        raise FileNotFoundError(f"Categories file not found: {path}")

    payload_raw: object | None = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload_raw is None:
        raise ValueError("categories.yaml must contain a top-level 'categories' list")
    if not isinstance(payload_raw, dict):
        raise ValueError("categories.yaml must contain a top-level 'categories' list")
    payload: dict[str, Any] = cast(dict[str, Any], payload_raw)

    categories_raw = payload.get("categories")
    if not isinstance(categories_raw, list):
        raise ValueError("categories.yaml must contain a list under 'categories'")

    categories: dict[str, CategoryDef] = {}
    category_entries = cast(list[object], categories_raw)
    for entry_obj in category_entries:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, object], entry_obj)
        tag = normalize_tag(as_str(entry.get("tag")))
        label = as_str(entry.get("label")) or (tag[1:] if tag else "")
        cat_type = as_str(entry.get("type"))
        if tag:
            categories[tag] = CategoryDef(tag=tag, label=label, type=cat_type)
    return categories


def load_domain_overrides(
    path: Path = DEFAULT_DOMAIN_MAP_PATH,
) -> dict[str, DomainOverride]:
    if not path.exists():
        return {}
    payload_raw: object | None = yaml.safe_load(path.read_text(encoding="utf-8"))
    if payload_raw is None:
        return {}
    if not isinstance(payload_raw, dict):
        return {}
    payload: dict[str, Any] = cast(dict[str, Any], payload_raw)
    domains_raw = payload.get("domains")
    if not isinstance(domains_raw, list):
        return {}

    overrides: dict[str, DomainOverride] = {}
    domain_entries = cast(list[object], domains_raw)
    for entry_obj in domain_entries:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, object], entry_obj)
        domain = as_str(entry.get("domain"))
        if not domain:
            continue
        primary = normalize_tag(as_str(entry.get("primary")))
        secondary: list[str] = []
        secondary_raw = entry.get("secondary")
        if isinstance(secondary_raw, list):
            items = cast(list[object], secondary_raw)
            for item in items:
                tag = normalize_tag(as_str(item))
                if tag:
                    secondary.append(tag)
        overrides[domain.lower()] = DomainOverride(primary=primary, secondary=secondary)
    return overrides


def _load_secondary_categories(conn: sqlite3.Connection) -> dict[str, set[str]]:
    cursor = conn.execute("SELECT domain, tag FROM secondary_categories")
    mapping: dict[str, set[str]] = {}
    for domain, tag in cursor.fetchall():
        normalized = normalize_tag(as_str(tag))
        if not normalized:
            continue
        domain_name = normalize_domain(domain)
        if not domain_name:
            continue
        mapping.setdefault(domain_name, _new_str_set()).add(normalized)
    return mapping


def _load_domain_metadata(
    conn: sqlite3.Connection, overrides: dict[str, DomainOverride]
) -> dict[str, DomainMetadata]:
    secondary_map = _load_secondary_categories(conn)
    cursor = conn.execute(
        "SELECT domain, title, main_category, favicon_type, favicon_data FROM domains"
    )
    metadata: dict[str, DomainMetadata] = {}
    for domain, title, main_cat, mime, data in cursor.fetchall():
        domain_name = normalize_domain(domain) or ""
        override = overrides.get(domain_name)
        primary_tag = override.primary if override else normalize_tag(as_str(main_cat))
        base_secondary = secondary_map.get(domain_name)
        secondary_tags: set[str] = set(base_secondary) if base_secondary else set()
        if override:
            secondary_tags.update(override.secondary)
        favicon_bytes = bytes(data) if isinstance(data, (bytes, bytearray)) else None
        metadata[domain_name] = DomainMetadata(
            domain=domain_name,
            title=as_str(title),
            primary_tag=primary_tag,
            secondary_tags=secondary_tags,
            favicon_type=as_str(mime),
            favicon_data=favicon_bytes,
        )
    return metadata


def aggregate_visits(
    conn: sqlite3.Connection, local_tz: ZoneInfo
) -> dict[tuple[int, int], SlotAggregate]:
    cursor = conn.execute("SELECT domain, timestamp FROM visits ORDER BY timestamp")
    aggregates: dict[tuple[int, int], SlotAggregate] = {}
    for domain, ts in cursor.fetchall():
        domain_name = normalize_domain(domain) or ""
        timestamp = as_str(ts)
        if not timestamp:
            continue
        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=UTC).astimezone(local_tz)
        weekday = dt.weekday()  # Monday=0
        day = (weekday + 1) % 7  # Sunday=0
        hour = dt.hour
        key = (day, hour)
        bucket = aggregates.get(key)
        if bucket is None:
            bucket = SlotAggregate(day=day, hour=hour)
            aggregates[key] = bucket
        bucket.total += 1
        bucket.per_domain[domain_name] = bucket.per_domain.get(domain_name, 0) + 1
    return aggregates


def generate_level0(aggregates: dict[tuple[int, int], SlotAggregate]) -> list[dict[str, int]]:
    if not aggregates:
        return []
    max_total = max(bucket.total for bucket in aggregates.values())
    entries: list[dict[str, int]] = []
    for _, bucket in sorted(aggregates.items()):
        size = int(round(bucket.total / max_total * 100)) if max_total else 0
        entries.append(
            {
                "day": bucket.day,
                "hour": bucket.hour,
                "value": bucket.total,
                "size": size,
            }
        )
    return entries


def _symbol_id_for_domain(domain: str) -> str:
    sanitized = "".join(ch if ch.isalnum() else "-" for ch in domain.lower())
    compact = "-".join(filter(None, sanitized.split("-")))
    return f"fav-{compact}"


def _build_sprite_symbols(
    bucket: SlotAggregate, metadata: dict[str, DomainMetadata]
) -> list[SpriteSymbol]:
    symbols: list[SpriteSymbol] = []
    seen: set[str] = set()
    for domain in bucket.per_domain:
        meta = metadata.get(domain)
        if not meta or not meta.favicon_data:
            continue
        if domain in seen:
            continue
        seen.add(domain)
        symbols.append(
            SpriteSymbol(
                domain=domain,
                symbol_id=_symbol_id_for_domain(domain),
                mime_type=meta.favicon_type,
                data=bytes(meta.favicon_data),
            )
        )
    return symbols


def _render_sprite(symbols: list[SpriteSymbol]) -> str:
    lines = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'width="0" height="0" style="position:absolute">'
        ),
    ]
    for symbol in symbols:
        # NB(zundel): This re-encodes the sprite for each datapoint.
        # If this were to be a long running action, we could store the
        # SVG icon back into the domains table to avoid repeated encoding,
        # but it may be faster to just re-encode it every time.
        encoded = b64encode(symbol.data).decode("ascii")
        mime = symbol.mime_type or "image/png"
        lines.append(f'  <symbol id="{symbol.symbol_id}" viewBox="0 0 64 64">')
        lines.append(
            "    <image "
            f'href="data:{mime};base64,{encoded}" '
            'width="64" height="64" preserveAspectRatio="xMidYMid meet" />'
        )
        lines.append("  </symbol>")
    lines.append("</svg>")
    return "\n".join(lines)


def _label_for_tag(tag: str, categories: dict[str, CategoryDef]) -> str:
    category = categories.get(tag)
    if category:
        return category.label
    return tag.lstrip("#")


def _build_level1_entry(
    bucket: SlotAggregate,
    metadata: dict[str, DomainMetadata],
    categories: dict[str, CategoryDef],
    sprite_relpath: str | None,
) -> dict[str, Any]:
    category_groups: dict[str, CategoryGroup] = {}
    uncategorized: list[SiteEntry] = []
    for domain, count in sorted(bucket.per_domain.items(), key=lambda item: (-item[1], item[0])):
        meta = metadata.get(domain)
        primary = meta.primary_tag if meta else None
        symbol_id = _symbol_id_for_domain(domain) if meta and meta.favicon_data else None
        site_entry: SiteEntry = {
            "domain": domain,
            "title": (meta.title if meta and meta.title else domain),
            "url": f"https://{domain}/",
            "value": count,
        }
        if symbol_id:
            site_entry["favicon_symbol_id"] = symbol_id
        if meta and meta.secondary_tags:
            site_entry["secondary_tags"] = sorted(meta.secondary_tags)

        if primary:
            tag = primary
            if tag not in category_groups:
                category_groups[tag] = {
                    "tag": tag,
                    "label": _label_for_tag(tag, categories),
                    "value": 0,
                    "sites": [],
                }
            group = category_groups[tag]
            group["value"] += count
            group["sites"].append(site_entry)
        else:
            uncategorized.append(site_entry)

    return {
        "day": bucket.day,
        "hour": bucket.hour,
        "categories": list(category_groups.values()),
        "uncategorized": uncategorized,
        **({"sprite": sprite_relpath} if sprite_relpath else {}),
    }


def write_outputs(
    db_path: Path | None = None,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    categories_path: Path = DEFAULT_CATEGORIES_PATH,
    domain_map_path: Path = DEFAULT_DOMAIN_MAP_PATH,
    sprite_dir: Path | None = None,
    skip_sprites: bool = False,
    timezone_name: str = "America/New_York",
) -> GenerationSummary:
    resolved_db = resolve_db_path(db_path)
    conn = open_connection(resolved_db, dry_run=True)
    try:
        local_tz = ZoneInfo(timezone_name)
        aggregates = aggregate_visits(conn, local_tz)
        categories = load_categories(categories_path)
        overrides = load_domain_overrides(domain_map_path)
        metadata = _load_domain_metadata(conn, overrides)
    finally:
        conn.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    level0_data = generate_level0(aggregates)
    level0_path = output_dir / "level0.json"
    level0_path.write_text(json.dumps(level0_data, indent=2), encoding="utf-8")

    level1_written = 0
    sprite_written = 0
    sprite_root = sprite_dir or (output_dir / "sprites")
    if not skip_sprites:
        sprite_root.mkdir(parents=True, exist_ok=True)

    for (day, hour), bucket in sorted(aggregates.items()):
        relative_sprite: str | None = None
        symbols = _build_sprite_symbols(bucket, metadata)
        if not skip_sprites:
            sprite_name = f"level1-{day}-{hour:02d}.svg"
            sprite_path = sprite_root / sprite_name
            sprite_content = _render_sprite(symbols)
            sprite_path.write_text(sprite_content, encoding="utf-8")
            sprite_written += 1
            relative_sprite = str(Path("sprites") / sprite_name)

        level1 = _build_level1_entry(bucket, metadata, categories, relative_sprite)
        level1_path = output_dir / f"level1-{day}-{hour:02d}.json"
        level1_path.write_text(json.dumps(level1, indent=2), encoding="utf-8")
        level1_written += 1

    return GenerationSummary(
        level0_entries=len(level0_data), level1_files=level1_written, sprite_files=sprite_written
    )
