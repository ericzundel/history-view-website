from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from lib.history_db import (
    SCHEMA,
    LoaderStats,
    VisitRecord,
    process_records,
    resolve_db_path,
    should_skip_blocklisted,
    should_skip_url,
)
from lib.utils import (
    extract_domain,
    is_ip_or_local,
    normalize_timestamp,
)


def test_normalize_timestamp_handles_iso_and_millis() -> None:
    iso_value = "2024-06-01T12:34:56Z"
    millis_value = 1717245296000

    assert normalize_timestamp(iso_value) == "2024-06-01 12:34:56"
    assert normalize_timestamp(millis_value) == "2024-06-01 12:34:56"


def test_extract_domain_strips_scheme_and_www() -> None:
    assert extract_domain("https://www.example.com/path") == "example.com"
    assert extract_domain("sub.domain.test/page") == "sub.domain.test"
    assert extract_domain("http://192.168.1.5/page") == "local_development"
    assert extract_domain("https://8.8.8.8/") == "8.8.8.8"


def test_should_skip_url_protocol_handling() -> None:
    assert should_skip_url("https://example.com") == (False, None)
    assert should_skip_url("http://example.com") == (False, None)
    assert should_skip_url("file:///tmp/test") == (True, None)
    assert should_skip_url("mailto:test@example.com") == (True, None)
    assert should_skip_url("ftp://example.com") == (
        True,
        "Skipping unsupported scheme 'ftp' for URL: ftp://example.com",
    )


def test_is_ip_or_local_detects_ip_and_sentinel() -> None:
    assert is_ip_or_local("local_development")
    assert is_ip_or_local("10.0.0.1")
    assert is_ip_or_local("192.168.1.1")
    assert not is_ip_or_local("example.com")


def test_process_records_inserts_and_deduplicates(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    records = [
        VisitRecord(domain="example.com", timestamp="2024-06-01 12:00:00", title="Example"),
        VisitRecord(domain="example.com", timestamp="2024-06-01 12:00:00", title="Example"),
        VisitRecord(domain="example.com", timestamp="2024-06-01 13:00:00", title=None),
    ]

    stats: LoaderStats = process_records(
        records, db_path, dry_run=False, limit=None, verbose=False, quiet=True
    )

    assert stats.processed == 3
    assert stats.inserted == 2
    assert stats.skipped == 1
    conn = sqlite3.connect(db_path)
    visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    domain_row = conn.execute(
        "SELECT num_visits, title, checked FROM domains WHERE domain = ?", ("example.com",)
    ).fetchone()
    conn.close()
    assert visits == 2
    assert domain_row == (2, "Example", 0)


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()

    records = [VisitRecord(domain="example.com", timestamp="2024-06-01 12:00:00", title="Example")]
    stats = process_records(records, db_path, dry_run=True, limit=None, verbose=False, quiet=True)

    assert stats.inserted == 0
    conn = sqlite3.connect(db_path)
    visits = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    conn.close()
    assert visits == 0


def test_process_records_respects_blocklist(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    records = [
        VisitRecord(domain="blocked.com", timestamp="2024-06-01 12:00:00", title=None),
        VisitRecord(domain="sub.blocked.com", timestamp="2024-06-01 12:30:00", title=None),
        VisitRecord(domain=" Allowed.com", timestamp="2024-06-01 13:00:00", title=None),
    ]

    stats = process_records(
        records,
        db_path,
        dry_run=False,
        limit=None,
        verbose=False,
        quiet=True,
        blocklist={"blocked.com"},
    )

    assert stats.processed == 3
    assert stats.inserted == 1
    assert stats.skipped == 2
    conn = sqlite3.connect(db_path)
    domains = {row[0] for row in conn.execute("SELECT domain FROM domains")}
    count = {int(row[0]) for row in conn.execute("SELECT count(domain) FROM domains")}

    conn.close()
    assert domains == {"allowed.com"}
    assert count == {1}


def test_should_skip_blocklisted_helper() -> None:
    blocklist = {"blocked.com"}
    assert should_skip_blocklisted("blocked.com", blocklist)
    assert should_skip_blocklisted("sub.blocked.com", blocklist)
    assert not should_skip_blocklisted("other.com", blocklist)
    assert not should_skip_blocklisted("blocked.com", None)


def test_resolve_db_path_defaults_to_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_script_dir = tmp_path / "scripts" / "lib"
    fake_script_dir.mkdir(parents=True)

    def fake_resolve(_self: Path, strict: bool = False) -> Path:  # noqa: ARG001
        return fake_script_dir / "history_db.py"

    monkeypatch.setattr("lib.history_db.Path.resolve", fake_resolve)

    resolved = resolve_db_path(None)
    assert resolved == tmp_path / "data" / "history.db"

    custom = resolve_db_path(tmp_path / "custom.db")
    assert custom == tmp_path / "custom.db"
