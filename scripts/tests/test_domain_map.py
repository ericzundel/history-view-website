from pathlib import Path

import yaml
from lib.domain_map import DomainMapping, load_domain_map, update_domain_map, write_domain_map


def test_load_domain_map_missing_file_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    assert load_domain_map(missing) == {}


def test_load_domain_map_parses_and_normalizes(tmp_path: Path) -> None:
    path = tmp_path / "domain-map.yaml"
    path.write_text(
        "\n".join(
            [
                "domains:",
                "  - domain: Example.COM",
                "    primary: '#News'",
                "    secondary:",
                "      - '#Tech'",
                "      - ' other '",
                "      - null",
                "  - domain: ''",
                "    primary: '#ignore'",
            ]
        ),
        encoding="utf-8",
    )

    mapping = load_domain_map(path)
    assert set(mapping.keys()) == {"example.com"}
    entry = mapping["example.com"]
    assert entry.primary == "news"
    assert entry.secondary == ["tech", "other"]


def test_write_domain_map_sorts_domains(tmp_path: Path) -> None:
    path = tmp_path / "domain-map.yaml"
    mapping = {
        "b.com": DomainMapping(primary="news", secondary=["tech"]),
        "a.com": DomainMapping(primary="other", secondary=[]),
    }

    write_domain_map(path, mapping)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert payload["domains"][0]["domain"] == "a.com"
    assert payload["domains"][1]["domain"] == "b.com"


def test_update_domain_map_merges_entries(tmp_path: Path) -> None:
    path = tmp_path / "domain-map.yaml"
    base = {
        "a.com": DomainMapping(primary="news", secondary=["tech"]),
    }
    write_domain_map(path, base)

    update_domain_map(
        path,
        {
            "a.com": DomainMapping(primary=None, secondary=["world"]),
            "b.com": DomainMapping(primary="other", secondary=["misc"]),
        },
    )

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    domains = {entry["domain"]: entry for entry in payload["domains"]}

    assert domains["a.com"]["primary"] == "news"
    assert domains["a.com"]["secondary"] == ["tech", "world"]
    assert domains["b.com"]["primary"] == "other"
    assert domains["b.com"]["secondary"] == ["misc"]
