from __future__ import annotations

import base64
import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

import httpx
from lib.history_db import SCHEMA


def _load_favicon_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "find-favicons.py"
    spec = importlib.util.spec_from_file_location("find_favicons", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load find-favicons module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


favicons = _load_favicon_module()


def _build_mock_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            html = """
            <html>
              <head>
                <title>Example Domain</title>
                <link rel="icon" href="/icon.svg" type="image/svg+xml" sizes="any">
                <link rel="icon" href="/icon-32.png" type="image/png" sizes="16x16 32x32">
              </head>
              <body></body>
            </html>
            """
            return httpx.Response(200, text=html)
        if request.url.path == "/icon.svg":
            return httpx.Response(
                200, content=b"<svg></svg>", headers={"content-type": "image/svg+xml"}
            )
        if request.url.path == "/icon-32.png":
            return httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, follow_redirects=True)


def _build_mock_client_inline(icon_href: str) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/":
            html = f"""
            <html>
              <head>
                <title>Inline Icon</title>
                <link rel="icon" href="{icon_href}" type="image/png">
              </head>
              <body></body>
            </html>
            """
            return httpx.Response(200, text=html)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, follow_redirects=True)


def _build_mock_client_404() -> httpx.Client:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not found")

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, follow_redirects=True)


def _seed_domain(db_path: Path, domain: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        """
        INSERT INTO domains (domain, title, num_visits,
           checked, check_timestamp, favicon_type,
           favicon_data, main_category)
        VALUES (?, NULL, 0, 0, NULL, NULL, NULL, NULL)
        """,
        (domain,),
    )
    conn.commit()
    conn.close()


def test_refresh_favicons_updates_icon_and_title(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    _seed_domain(db_path, "example.com")

    client = _build_mock_client()
    stats = favicons.refresh_favicons(
        db_path,
        dry_run=False,
        limit=None,
        delay=0.0,
        verbose=False,
        client=client,
    )
    client.close()

    assert stats.processed == 1
    assert stats.updated == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        """
        SELECT title, favicon_type, favicon_data, checked, check_timestamp
        FROM domains WHERE domain = ?
        """,
        ("example.com",),
    ).fetchone()
    conn.close()

    assert row is not None
    title, mime_type, data, checked, timestamp = row
    assert title == "Example Domain"
    assert mime_type == "image/svg+xml"
    assert data is not None and len(data) > 0
    assert checked == 1
    assert timestamp is not None


def test_refresh_favicons_dry_run_leaves_database_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    _seed_domain(db_path, "dryrun.test")

    client = _build_mock_client()
    stats = favicons.refresh_favicons(
        db_path,
        dry_run=True,
        limit=None,
        delay=0.0,
        verbose=False,
        client=client,
    )
    client.close()

    assert stats.processed == 1
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT checked, favicon_data FROM domains WHERE domain = ?", ("dryrun.test",)
    ).fetchone()
    conn.close()

    assert row == (0, None)


def test_refresh_favicons_skips_ip_and_marks_checked(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    _seed_domain(db_path, "LOCAL_DEVELOPMENT")

    client = _build_mock_client()
    stats = favicons.refresh_favicons(
        db_path,
        dry_run=False,
        limit=None,
        delay=0.0,
        verbose=False,
        client=client,
    )
    client.close()

    assert stats.processed == 1
    assert stats.missing == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT checked, favicon_data FROM domains WHERE domain = ?", ("LOCAL_DEVELOPMENT",)
    ).fetchone()
    conn.close()

    assert row == (1, None)


def test_refresh_favicons_marks_checked_on_4xx(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    _seed_domain(db_path, "missing.test")

    client = _build_mock_client_404()
    stats = favicons.refresh_favicons(
        db_path,
        dry_run=False,
        limit=None,
        delay=0.0,
        verbose=False,
        client=client,
    )
    client.close()

    assert stats.processed == 1
    assert stats.missing == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT checked, favicon_data FROM domains WHERE domain = ?", ("missing.test",)
    ).fetchone()
    conn.close()

    assert row == (1, None)


def test_refresh_favicons_handles_inline_data_uri(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    _seed_domain(db_path, "inline.test")

    raw_icon = b"PNGDATA"
    encoded = base64.b64encode(raw_icon).decode("ascii")
    href = f"data:image/png;base64,{encoded}"

    client = _build_mock_client_inline(href)
    stats = favicons.refresh_favicons(
        db_path,
        dry_run=False,
        limit=None,
        delay=0.0,
        verbose=False,
        client=client,
    )
    client.close()

    assert stats.processed == 1
    assert stats.updated == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT favicon_type, favicon_data FROM domains WHERE domain = ?", ("inline.test",)
    ).fetchone()
    conn.close()

    assert row is not None
    mime, data = row
    assert mime == "image/png"
    assert data == raw_icon
