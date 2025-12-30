#!/usr/bin/env python3
"""
Placeholder favicon enrichment utility.

Spec requirements (to implement):
- Iterate domains needing favicon/title data.
- Fetch homepages with redirects, prefer SVG icons; store raw data + MIME type.
- Update domains table, set checked flag + timestamp.
- Support rate limiting, --dry-run, and --limit.
"""


def main() -> None:
    raise NotImplementedError("Implement favicon enrichment per docs/SPEC_v1.md")


if __name__ == "__main__":
    main()
