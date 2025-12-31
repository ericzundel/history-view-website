# History View Website

Visualization of personal browsing history as a static single-page app with supporting data-prep tooling.

## What this is

- Front-end: Vite + TypeScript (strict), delivering a bubble heatmap with drill-down treemap overlays.
- Tooling: Python 3.14 with `uv`, SQLite-backed loaders, favicon harvesting, and JSON/sprite generation.
- Everything deploys as static assets to shared hosting.

## Repo map (planned)

- `src/` front-end SPA code
- `public/` static assets and sprites
- `mocks/` design explorations (palettes, layout prototypes)
- `scripts/` dev/build/deploy helpers and Python loaders (`scripts/tests/` for Python tests)
- `data/` generated DB/JSON/sprites (ignored except README)
- `raw-data/` source exports (ignored except README)
- `categories/` taxonomy definitions and docs
- `docs/` deeper documentation (specs, ADRs, etc.)

See `docs/SPEC_v1.md` for the current working specification and `README_development.md` for setup instructions.
