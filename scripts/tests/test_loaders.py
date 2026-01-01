from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from pytest import CaptureFixture


def _load_module(name: str) -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


chrome = _load_module("load-chrome")
edge = _load_module("load-edge")
takeout = _load_module("load-takeout")


def test_load_chrome_inserts_records(tmp_path: Path, capsys: CaptureFixture[str]) -> None:
    export = [
        {"url": "https://example.com/one", "title": "Example", "visitTime": "2024-06-01T10:00:00Z"},
        {"url": "https://example.com/two", "visitTime": 1717239600000},
        {"url": "mailto:someone@example.com", "visitTime": 1717239600000},
        {"url": "ftp://example.com/file", "visitTime": 1717239600000},
    ]
    export_path = tmp_path / "chrome.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    db_path = tmp_path / "history.db"

    chrome.load_file(
        export_path, db_path, dry_run=False, limit=None, verbose=False, quiet=True, blocklist=None
    )
    captured = capsys.readouterr()

    conn = sqlite3.connect(db_path)
    visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    domain = conn.execute("SELECT num_visits FROM domains WHERE domain = 'example.com'").fetchone()[
        0
    ]
    conn.close()

    assert visits == 2
    assert domain == 2
    assert "Skipping unsupported scheme 'ftp'" in captured.out


def test_load_edge_respects_limit(tmp_path: Path) -> None:
    export = [
        {
            "url": "https://edge.test/one",
            "title": "Edge One",
            "date": "2024-06-01",
            "time": "12:00",
        },
        {
            "url": "https://edge.test/two",
            "title": "Edge Two",
            "date": "2024-06-01",
            "time": "13:00",
        },
    ]
    export_path = tmp_path / "edge.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    db_path = tmp_path / "history.db"

    edge.load_file(
        export_path, db_path, dry_run=False, limit=1, verbose=False, quiet=True, blocklist=None
    )

    conn = sqlite3.connect(db_path)
    visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    conn.close()

    assert visits == 1


def test_load_takeout_parses_microseconds(tmp_path: Path) -> None:
    export = {
        "Browser History": [
            {"url": "https://takeout.test/page", "title": "Takeout", "time_usec": 1717243200000000}
        ]
    }
    export_path = tmp_path / "takeout.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    db_path = tmp_path / "history.db"

    takeout.load_file(
        export_path,
        db_path,
        dry_run=False,
        limit=None,
        verbose=False,
        quiet=True,
        blocklist=None,
    )

    conn = sqlite3.connect(db_path)
    timestamp = conn.execute("SELECT timestamp FROM visits").fetchone()[0]
    conn.close()

    assert timestamp == "2024-06-01 12:00:00"


def test_loaders_normalize_private_ip_to_sentinel(tmp_path: Path) -> None:
    export = [
        {"url": "http://192.168.1.25/page", "title": "LAN", "visitTime": "2024-06-01T10:00:00Z"},
        {"url": "http://8.8.8.8/page", "title": "Public IP", "visitTime": "2024-06-01T11:00:00Z"},
    ]
    chrome_path = tmp_path / "chrome.json"
    chrome_path.write_text(json.dumps(export), encoding="utf-8")
    db_path = tmp_path / "history.db"

    chrome.load_file(
        chrome_path,
        db_path,
        dry_run=False,
        limit=None,
        verbose=False,
        quiet=True,
        blocklist=None,
    )

    conn = sqlite3.connect(db_path)
    domains = conn.execute("SELECT domain FROM domains ORDER BY domain").fetchall()
    conn.close()

    assert [row[0] for row in domains] == ["8.8.8.8", "local_development"]
