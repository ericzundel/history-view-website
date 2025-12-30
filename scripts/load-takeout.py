#!/usr/bin/env python3
"""
Placeholder loader for Google Takeout Chrome exports.

Spec requirements (to implement):
- Parse Takeout exports, normalize timestamps (UTC, YYYY-MM-DD HH:MM:SS).
- Insert visits into SQLite, ensure domains table exists/updated.
- Support --dry-run and --limit flags; log human-friendly progress.
"""


def main() -> None:
    raise NotImplementedError("Implement Takeout loader per docs/SPEC_v1.md")


if __name__ == "__main__":
    main()
