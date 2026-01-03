from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from lib.utils import (
    normalize_domain,
)

logger = logging.getLogger(__name__)

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS visits (
  id INTEGER PRIMARY KEY,
  domain TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  FOREIGN KEY(domain) REFERENCES domains(domain) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_visits_domain_timestamp ON visits(domain, timestamp);
CREATE INDEX IF NOT EXISTS idx_visits_timestamp_domain ON visits(timestamp, domain);
CREATE INDEX IF NOT EXISTS idx_visits_domain ON visits(domain);

CREATE TABLE IF NOT EXISTS domains (
  domain TEXT PRIMARY KEY,
  title TEXT,
  num_visits INTEGER NOT NULL,
  checked BOOLEAN NOT NULL CHECK (checked IN (0, 1)),
  check_timestamp TEXT,
  favicon_type TEXT,
  favicon_data BLOB,
  main_category TEXT
);

CREATE TABLE IF NOT EXISTS secondary_categories (
  domain TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (domain, tag),
  FOREIGN KEY(domain) REFERENCES domains(domain) ON DELETE CASCADE
);

""".strip()

DEFAULT_BLOCKLIST_PATH = Path(__file__).resolve().parent.parent / "config" / "domain-blocklist.yml"


@dataclass
class VisitRecord:
    domain: str
    timestamp: str
    title: str | None = None


@dataclass
class LoaderStats:
    processed: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: int = 0


def resolve_db_path(db_arg: Path | None) -> Path:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    print(f"repo root is {repo_root}")
    default_path = repo_root / "data" / "history.db"
    return db_arg if db_arg is not None else default_path


def load_blocklist(path: Path | None = None) -> set[str]:
    blocklist_path = path or DEFAULT_BLOCKLIST_PATH
    if not blocklist_path.exists():
        return set()

    entries: set[str] = set()
    for line in blocklist_path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            stripped = stripped.lstrip("-").strip()
        if stripped:
            entries.add(stripped.lower())
    return entries


def should_skip_url(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if not scheme or scheme in {"http", "https"}:
        return False, None
    if scheme in {"file", "mailto", "chrome-extension"}:
        return True, None
    return True, f"Skipping unsupported scheme '{scheme}' for URL: {url}"


def should_skip_blocklisted(domain: str, blocklist: set[str] | None) -> bool:
    if not blocklist:
        return False
    parts = domain.lower().split(".")
    for idx in range(len(parts) - 1):
        candidate = ".".join(parts[idx:])
        if candidate in blocklist:
            return True
    return False


def open_connection(db_path: Path, dry_run: bool) -> sqlite3.Connection:
    if dry_run:
        if not db_path.exists():
            raise FileNotFoundError(f"Database not found for dry-run: {db_path}")
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        _validate_schema(conn)
        return conn

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _validate_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in cursor.fetchall()}
    required = {"visits", "domains"}
    missing = required - existing
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(f"Database missing tables: {missing_list}. Run init-db.py first.")


class HistoryWriter:
    def __init__(self, conn: sqlite3.Connection, dry_run: bool) -> None:
        self.conn = conn
        self.dry_run = dry_run

    def close(self) -> None:
        self.conn.close()

    def record_visit(self, record: VisitRecord) -> bool:
        if self.dry_run:
            return False

        with self.conn:
            self.ensure_domain(record.domain, record.title)
            inserted = self._insert_visit_if_new(record.domain, record.timestamp)
        return inserted

    def ensure_domain(self, domain: str, title: str | None) -> None:
        row = self.conn.execute("SELECT title FROM domains WHERE domain = ?", (domain,)).fetchone()
        if row is None:
            self.conn.execute(
                """
                INSERT INTO domains (
                    domain,
                    title,
                    num_visits,
                    checked,
                    check_timestamp,
                    favicon_type,
                    favicon_data,
                    main_category
                )
                VALUES (?, ?, 0, 0, NULL, NULL, NULL, NULL)
                """,
                (domain, title),
            )
            return

        has_title = row[0] is not None and str(row[0]).strip() != ""
        if title and not has_title:
            self.conn.execute("UPDATE domains SET title = ? WHERE domain = ?", (title, domain))

    def _insert_visit_if_new(self, domain: str, timestamp: str) -> bool:
        existing = self.conn.execute(
            "SELECT 1 FROM visits WHERE domain = ? AND timestamp = ? LIMIT 1",
            (domain, timestamp),
        ).fetchone()
        if existing:
            return False

        self.conn.execute(
            "INSERT INTO visits (domain, timestamp) VALUES (?, ?)", (domain, timestamp)
        )
        self.conn.execute(
            "UPDATE domains SET num_visits = num_visits + 1 WHERE domain = ?", (domain,)
        )
        return True


def process_records(
    records: Iterable[VisitRecord],
    db_path: Path,
    *,
    dry_run: bool,
    limit: int | None,
    verbose: bool,
    quiet: bool,
    blocklist: set[str] | None = None,
    feedback_interval: int = 100,
) -> LoaderStats:
    stats = LoaderStats()
    conn = open_connection(db_path, dry_run)
    writer = HistoryWriter(conn, dry_run)

    try:
        for record in records:
            if limit is not None and stats.processed >= limit:
                break
            record.domain = normalize_domain(record.domain) or ""
            stats.processed += 1
            if should_skip_blocklisted(record.domain, blocklist):
                stats.skipped += 1
                continue
            if not quiet and (stats.processed % feedback_interval == 0):
                print(".", end="", flush=True)
            try:
                inserted = writer.record_visit(record)
            except Exception as exc:  # noqa: BLE001
                stats.errors += 1
                print(f"[error] #{stats.processed}: {exc}")
                continue

            if inserted:
                stats.inserted += 1
                if verbose:
                    print(f"[insert] {record.domain} @ {record.timestamp}")
            else:
                stats.skipped += 1
                if verbose:
                    print(f"[skip] {record.domain} @ {record.timestamp}")
    finally:
        writer.close()

    return stats


def summarize_stats(stats: LoaderStats, dry_run: bool) -> str:
    action = "Dry-run" if dry_run else "Applied"
    return (
        f"\n{action}: processed {stats.processed}, "
        f"inserted {stats.inserted}, skipped {stats.skipped}, errors {stats.errors}"
    )
