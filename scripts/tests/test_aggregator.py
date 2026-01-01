from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from lib.aggregator import write_outputs
from lib.history_db import SCHEMA


def _write_categories(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "categories:",
                "  - tag: news",
                "    label: News",
                "    type: primary",
                "  - tag: learning",
                "    label: Learning",
                "    type: primary",
                "  - tag: tutorials",
                "    label: Tutorials",
            ]
        ),
        encoding="utf-8",
    )


def _write_domain_map(path: Path, domain: str) -> None:
    path.write_text(
        "\n".join(
            [
                "domains:",
                f"  - domain: {domain}",
                "    primary: '#learning'",
                "    secondary:",
                "      - '#tutorials'",
            ]
        ),
        encoding="utf-8",
    )


def test_generates_level_json_and_sprites(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, ?, ?, ?)
        """,
        ("example.com", "Example", "image/png", b"\x89PNG", "news"),
    )
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, NULL, NULL, NULL)
        """,
        ("learning.test", "Learning Site"),
    )
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, NULL, NULL, NULL)
        """,
        ("unknown.test", None),
    )
    conn.execute(
        "INSERT INTO secondary_categories (domain, tag) VALUES (?, ?)",
        ("example.com", "#tutorials"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("example.com", "2024-06-02 01:00:00"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("example.com", "2024-06-02 01:45:00"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("learning.test", "2024-06-03 14:00:00"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("unknown.test", "2024-06-03 14:15:00"),
    )
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    domain_map_path = tmp_path / "domain-map.yaml"
    _write_categories(categories_path)
    _write_domain_map(domain_map_path, "learning.test")

    output_dir = tmp_path / "out"
    summary = write_outputs(
        db_path=db_path,
        output_dir=output_dir,
        categories_path=categories_path,
        domain_map_path=domain_map_path,
    )

    assert summary.level0_entries == 2
    assert summary.level1_files == 2
    assert summary.sprite_files == 2

    level0 = json.loads((output_dir / "level0.json").read_text(encoding="utf-8"))
    assert level0 == [
        {"day": 0, "hour": 1, "value": 2, "size": 100},
        {"day": 1, "hour": 14, "value": 2, "size": 100},
    ]

    level1_sunday = json.loads((output_dir / "level1-0-01.json").read_text(encoding="utf-8"))
    assert level1_sunday["categories"][0]["tag"] == "#news"
    assert level1_sunday["categories"][0]["value"] == 2
    site = level1_sunday["categories"][0]["sites"][0]
    assert site["value"] == 2
    assert site["favicon_symbol_id"].startswith("fav-example")
    assert site["secondary_tags"] == ["#tutorials"]
    sprite_sunday = (output_dir / "sprites" / "level1-0-01.svg").read_text(encoding="utf-8")
    assert "fav-example" in sprite_sunday
    assert "image/png" in sprite_sunday

    level1_monday = json.loads((output_dir / "level1-1-14.json").read_text(encoding="utf-8"))
    category = level1_monday["categories"][0]
    assert category["tag"] == "#learning"
    assert category["label"] == "Learning"
    assert category["value"] == 1
    assert level1_monday["uncategorized"][0]["domain"] == "unknown.test"
    assert "sprite" in level1_monday


def test_skip_sprites_omits_sprite_files(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, NULL, NULL, 'news')
        """,
        ("example.com", "Example"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("example.com", "2024-06-02 01:00:00"),
    )
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    categories_path.write_text("categories:\n  - tag: news\n    label: News\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    summary = write_outputs(
        db_path=db_path,
        output_dir=output_dir,
        categories_path=categories_path,
        skip_sprites=True,
    )

    assert summary.sprite_files == 0
    assert not (output_dir / "sprites").exists()
    level1 = json.loads((output_dir / "level1-0-01.json").read_text(encoding="utf-8"))
    assert "sprite" not in level1


def test_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    categories_path.write_text("categories:\n  - tag: misc\n    label: Misc\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    summary = write_outputs(
        db_path=db_path,
        output_dir=output_dir,
        categories_path=categories_path,
        domain_map_path=tmp_path / "domain-map.yaml",
    )

    assert summary.level0_entries == 0
    assert summary.level1_files == 0
    assert summary.sprite_files == 0
    assert json.loads((output_dir / "level0.json").read_text(encoding="utf-8")) == []
    assert list(output_dir.glob("level1-*.json")) == []
    sprite_dir = output_dir / "sprites"
    assert sprite_dir.exists()
    assert list(sprite_dir.iterdir()) == []


def test_malformed_categories_yaml(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    categories_path.write_text("categories: not-a-list", encoding="utf-8")

    with pytest.raises(ValueError, match="categories.yaml must contain"):
        write_outputs(
            db_path=db_path,
            output_dir=tmp_path / "out",
            categories_path=categories_path,
            domain_map_path=tmp_path / "domain-map.yaml",
        )


def test_missing_favicon_data(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, ?, NULL, ?)
        """,
        ("example.com", "Example", "image/png", "news"),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("example.com", "2024-06-02 01:00:00"),
    )
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    categories_path.write_text("categories:\n  - tag: news\n    label: News\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    summary = write_outputs(
        db_path=db_path,
        output_dir=output_dir,
        categories_path=categories_path,
        domain_map_path=tmp_path / "domain-map.yaml",
    )

    assert summary.level1_files == 1
    level1 = json.loads((output_dir / "level1-0-01.json").read_text(encoding="utf-8"))
    site_entry = level1["categories"][0]["sites"][0]
    assert "favicon_symbol_id" not in site_entry
    sprite_content = (output_dir / "sprites" / "level1-0-01.svg").read_text(encoding="utf-8")
    assert "<symbol" not in sprite_content


def test_domain_without_primary_category(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits, checked, check_timestamp,
                             favicon_type, favicon_data, main_category)
        VALUES (?, ?, 0, 1, NULL, NULL, NULL, NULL)
        """,
        ("no-category.test", None),
    )
    conn.execute(
        "INSERT INTO visits (domain, timestamp) VALUES (?, ?)",
        ("no-category.test", "2024-06-03 09:00:00"),
    )
    conn.commit()
    conn.close()

    categories_path = tmp_path / "categories.yaml"
    categories_path.write_text("categories:\n  - tag: misc\n    label: Misc\n", encoding="utf-8")

    output_dir = tmp_path / "out"
    summary = write_outputs(
        db_path=db_path,
        output_dir=output_dir,
        categories_path=categories_path,
        domain_map_path=tmp_path / "domain-map.yaml",
    )

    assert summary.level1_files == 1
    level1 = json.loads((output_dir / "level1-1-09.json").read_text(encoding="utf-8"))
    assert level1["categories"] == []
    uncategorized = level1["uncategorized"]
    assert len(uncategorized) == 1
    assert uncategorized[0]["domain"] == "no-category.test"
