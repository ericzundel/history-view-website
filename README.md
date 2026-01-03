# History View Website

Visualization of personal browsing history as a static single-page app with supporting data-prep tooling.

## Overview

This script processes data from Google Takeout and browsing history files from the web browser to
produce a visualization of browzing activity. Intended to be just a fun visualization for
my personal website.

## Repo map

- `src/` front-end SPA code
- `public/` static assets and sprites
- `mocks/` design explorations (palettes, layout prototypes)
- `scripts/` dev/build/deploy helpers and Python loaders (`scripts/tests/` for Python tests)
- `data/` generated DB/JSON/sprites (ignored except README)
- `raw-data/` source exports (ignored except README)
- `config/` taxonomy definitions and blocklists
- `docs/` deeper documentation (specs, ADRs, etc.)

See `docs/SPEC_v1.md` for the current working specification and `README_development.md` for setup instructions.
