#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from lib.history_db import (
    is_ip_or_local,
    load_blocklist,
    open_connection,
    resolve_db_path,
    should_skip_blocklisted,
)

USER_AGENT = "history-view-favicon-fetcher/0.1"
MAX_ICON_BYTES = 256 * 1024


@dataclass
class FaviconResult:
    domain: str
    title: str | None
    mime_type: str | None
    data: bytes | None


@dataclass
class FaviconStats:
    processed: int = 0
    updated: int = 0
    missing: int = 0
    errors: int = 0


def _pending_domains(
    conn: sqlite3.Connection, limit: int | None, *, ignore_checked: bool
) -> list[tuple[str, str | None]]:
    where_clause = (
        "checked = 0 OR checked IS NULL OR favicon_data IS NULL"
        if ignore_checked
        else "checked = 0 OR checked IS NULL"
    )
    cursor = conn.execute(
        """
        SELECT domain, title
        FROM domains
        WHERE """
        + where_clause
        + """
        ORDER BY domain
        """
        + (" LIMIT ?" if limit is not None else ""),
        (() if limit is None else (limit,)),
    )
    return [(row[0], row[1]) for row in cursor.fetchall()]


def _extract_title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        text = soup.title.string.strip()
        return text or None
    return None


def _size_score(sizes: str | None) -> int:
    if not sizes:
        return 0
    parts = sizes.split()
    scores: list[int] = []
    for part in parts:
        if "x" in part:
            try:
                width = int(part.split("x")[0])
                scores.append(width)
            except ValueError:
                continue
    return max(scores) if scores else 0


def _select_icon(soup: BeautifulSoup, base_url: str) -> tuple[str, str | None]:
    candidates: list[tuple[str, str | None, int]] = []
    for link in soup.find_all("link"):
        rel_attr = link.get("rel")
        rel: list[str] = rel_attr if isinstance(rel_attr, list) else []
        rel_values = [val.lower() for val in rel]
        if not any("icon" in val for val in rel_values):
            continue
        href = link.get("href")
        if not href or not isinstance(href, str):
            continue
        icon_type_raw = link.get("type")
        icon_type: str | None = icon_type_raw if isinstance(icon_type_raw, str) else None
        sizes_attr = link.get("sizes")
        size_hint: str | None = sizes_attr if isinstance(sizes_attr, str) else None
        href_str = str(href)
        candidates.append((href_str, icon_type, _size_score(size_hint)))

    if candidates:
        svg = next((c for c in candidates if c[1] and "svg" in c[1].lower()), None)
        if svg:
            return urljoin(base_url, svg[0]), svg[1]
        href, icon_type, _ = max(candidates, key=lambda item: item[2])
        return urljoin(base_url, href), icon_type

    return urljoin(base_url, "/favicon.ico"), "image/x-icon"


def _fetch_icon(client: httpx.Client, url: str, type_hint: str | None) -> tuple[bytes, str | None]:
    inline = _decode_inline_icon(url, type_hint)
    if inline is not None:
        data, mime = inline
        if len(data) > MAX_ICON_BYTES:
            raise httpx.HTTPError(f"Inline icon exceeds size limit ({len(data)} bytes)")
        return data, mime

    response = client.get(url)
    response.raise_for_status()
    mime = type_hint
    content_type = response.headers.get("content-type")
    if content_type:
        mime = content_type.split(";")[0].strip()
    content = response.content
    if len(content) > MAX_ICON_BYTES:
        raise httpx.HTTPError(f"Icon exceeds size limit ({len(content)} bytes)")
    return content, mime


def _decode_inline_icon(url: str, type_hint: str | None) -> tuple[bytes, str | None] | None:
    marker = "base64,"
    if marker not in url:
        return None

    idx = url.find(marker)
    header = url[:idx]
    encoded = url[idx + len(marker) :]

    if "data:" in header:
        header = header.split("data:", 1)[1]

    mime = type_hint
    if "image/" in header:
        after = header.split("image/", 1)[1]
        token = after.split(";")[0].split(",")[0].strip("/")
        if token:
            mime = f"image/{token}"

    try:
        data = base64.b64decode(encoded, validate=False)
    except Exception:
        return None
    return data, mime


def _process_domain(client: httpx.Client, domain: str) -> FaviconResult:
    base_url = f"https://{domain}/"
    response = client.get(base_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_title = _extract_title(soup)
    icon_url, icon_type = _select_icon(soup, base_url)

    data: bytes | None = None
    mime: str | None = icon_type
    data, mime = _fetch_icon(client, icon_url, icon_type)

    return FaviconResult(domain=domain, title=page_title, mime_type=mime, data=data)


def _persist_result(conn: sqlite3.Connection, result: FaviconResult, *, dry_run: bool) -> None:
    if dry_run:
        return

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        if result.data is not None:
            cursor = conn.execute(
                """
                UPDATE domains
                SET checked = 1,
                    check_timestamp = ?,
                    title = CASE
                        WHEN (title IS NULL OR TRIM(title) = '') AND ? IS NOT NULL THEN ?
                        ELSE title
                    END,
                    favicon_type = ?,
                    favicon_data = ?
                WHERE domain = ?
                """,
                (now, result.title, result.title, result.mime_type, result.data, result.domain),
            )
        else:
            cursor = conn.execute(
                """
                UPDATE domains
                SET checked = 1,
                    check_timestamp = ?,
                    title = CASE
                        WHEN (title IS NULL OR TRIM(title) = '') AND ? IS NOT NULL THEN ?
                        ELSE title
                    END
                WHERE domain = ?
                """,
                (now, result.title, result.title, result.domain),
            )
    if cursor.rowcount == 0:
        raise RuntimeError(f"Domain {result.domain} not found in database.")


def refresh_favicons(
    db_path: Path,
    *,
    dry_run: bool,
    limit: int | None,
    delay: float,
    verbose: bool,
    quiet: bool = False,
    blocklist: set[str] | None = None,
    client: httpx.Client | None = None,
    ignore_checked: bool = False,
) -> FaviconStats:
    stats = FaviconStats()
    conn = open_connection(db_path, dry_run)
    close_client = False
    if client is None:
        client = httpx.Client(
            follow_redirects=True, timeout=10.0, headers={"User-Agent": USER_AGENT}
        )
        close_client = True

    try:
        pending = _pending_domains(conn, limit, ignore_checked=ignore_checked)
        for idx, (domain, _) in enumerate(pending, start=1):
            stats.processed += 1
            if not quiet and stats.processed % 10 == 0:
                print(".", end="", flush=True)
            if should_skip_blocklisted(domain, blocklist):
                stats.missing += 1
                if verbose:
                    print(f"[skip] {domain}: blocklisted")
                _mark_checked(conn, domain, dry_run=dry_run)
                continue
            if is_ip_or_local(domain):
                stats.missing += 1
                if verbose:
                    print(f"[skip] {domain}: skipping IP/local development entry")
                _mark_checked(conn, domain, dry_run=dry_run)
                continue
            try:
                result: FaviconResult | None = None
                for attempt in range(3):
                    try:
                        result = _process_domain(client, domain)
                        break
                    except httpx.TimeoutException as exc:
                        if attempt < 2:
                            if verbose:
                                print(f"[retry] {domain}: timeout ({attempt + 1}/3), retrying...")
                            continue
                        stats.errors += 1
                        if verbose:
                            print(f"[timeout] {domain}: {exc}, marking checked")
                        _mark_checked(conn, domain, dry_run=dry_run)
                        raise
                if result is None:
                    continue
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if 400 <= status < 500:
                    stats.missing += 1
                    if verbose:
                        print(f"[skip] {domain}: {status} response, marking checked")
                    _mark_checked(conn, domain, dry_run=dry_run)
                    continue
                stats.errors += 1
                print(f"[error] {domain}: {exc}")
                continue
            except httpx.HTTPError as exc:
                stats.errors += 1
                print(f"[error] {domain}: {exc}")
                continue

            try:
                _persist_result(conn, result, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001
                stats.errors += 1
                print(f"[error] {domain}: {exc}")
                continue
            if result.data:
                stats.updated += 1
                if verbose:
                    print(
                        f"[stored] {domain} "
                        f"({len(result.data)} bytes, {result.mime_type or 'unknown'})"
                    )
            else:
                stats.missing += 1
                if verbose:
                    print(f"[missing] {domain} (no icon found)")

            if delay > 0 and idx < len(pending):
                time.sleep(delay)
    finally:
        conn.close()
        if close_client:
            client.close()

    return stats


def _mark_checked(conn: sqlite3.Connection, domain: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute(
            """
            UPDATE domains
            SET checked = 1,
                check_timestamp = ?
            WHERE domain = ?
            """,
            (now, domain),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch favicons and titles for domains table entries."
    )
    parser.add_argument(
        "--db", type=Path, default=None, help="Path to SQLite database (default: data/history.db)."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process only the first N pending domains."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Log actions without writing to the database."
    )
    parser.add_argument(
        "--delay", type=float, default=0.0, help="Sleep for N seconds between requests."
    )
    parser.add_argument("--verbose", action="store_true", help="Print per-domain actions.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress dots.")
    parser.add_argument(
        "--blocklist",
        type=Path,
        default=None,
        help="Path to domain blocklist YAML (default: config/domain-blocklist.yml).",
    )
    parser.add_argument(
        "--ignore-checked",
        action="store_true",
        help="Process entries even if checked is already set to 1.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = resolve_db_path(args.db)
    stats = refresh_favicons(
        db_path,
        dry_run=args.dry_run,
        limit=args.limit,
        delay=args.delay,
        verbose=args.verbose,
        quiet=args.quiet,
        blocklist=load_blocklist(args.blocklist),
        ignore_checked=args.ignore_checked,
    )
    print(
        f"{'Dry-run' if args.dry_run else 'Updated'}: processed {stats.processed}, "
        f"updated {stats.updated}, missing {stats.missing}, errors {stats.errors}"
    )


if __name__ == "__main__":
    main()
