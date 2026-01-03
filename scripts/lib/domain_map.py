"""Helpers for reading/writing the domain-to-category mapping YAML.

This module manages `config/domain-category-map.yaml`, which pins domains to one
primary category and optional secondary tags using the taxonomy defined in
`config/categories.yaml`.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

from lib.utils import coerce_str, ensure_list, ensure_mapping, merge_lists, normalize_tag


# @dataclass tells Python to auto-generate common boilerplate for a class
#  based on its type-annotated fields. It creates methods like __init__,
# __repr__, and __eq__ (and optionally ordering, default values, etc.)
@dataclass
class DomainMapping:
    """Mapping entry for a single domain.

    Primary and secondary values are normalized tag names from
    `config/categories.yaml` (lowercase, no leading "#").
    """

    primary: str | None = None
    secondary: list[str] = field(default_factory=lambda: [])


def load_domain_map(path: Path) -> dict[str, DomainMapping]:
    """Load domain mappings from a YAML file.

    Returns a dict keyed by lowercase domain. Missing files return an empty dict.
    """
    if not path.exists():
        return {}
    payload_obj: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    payload = ensure_mapping(payload_obj, context=f"{path}")
    domains = payload.get("domains", []) or [{}]
    raw_domains = ensure_list(domains, context=f"{path} domains")

    mapping: dict[str, DomainMapping] = {}
    for entry_obj in raw_domains:
        if not isinstance(entry_obj, dict):
            continue
        entry = cast(dict[str, Any], entry_obj)
        domain = (coerce_str(entry.get("domain")) or "").lower()
        if not domain:
            continue
        primary = normalize_tag(coerce_str(entry.get("primary")))
        secondary_raw: object = entry.get("secondary") or []
        secondary: list[str] = []
        if isinstance(secondary_raw, list):
            for tag_obj in cast(list[object], secondary_raw):
                normalized = normalize_tag(coerce_str(tag_obj))
                if normalized:
                    secondary.append(normalized)
        mapping[domain] = DomainMapping(primary=primary, secondary=secondary)
    return mapping


def write_domain_map(path: Path, mapping: dict[str, DomainMapping]) -> None:
    """Write domain mappings to YAML, sorting by domain for stable output."""
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
    """Merge mappings into the YAML file, preserving existing entries.

    Primary tags overwrite only when provided; secondary tags are de-duped via
    merge_lists.
    """
    existing_mapping = load_domain_map(path)
    for domain, entry in mapping.items():
        if domain in existing_mapping:
            existing_entry = existing_mapping[domain]
            if entry.primary is not None:
                existing_entry.primary = entry.primary
            existing_entry.secondary = merge_lists(existing_entry.secondary, entry.secondary)
        else:
            existing_mapping[domain] = entry
    write_domain_map(path, existing_mapping)
