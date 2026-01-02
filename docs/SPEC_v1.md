# History View Website Specification Draft (Codex-Execution-Friendly)

I am building a visualization of my browsing history to make interesting content on my personal website. I have raw data from my browser and exports from Google Takeout. I manually assemble, curate, and process this data, then publish derived static assets for visualization. This project processes only my own locally generated data.

---

## 1. Project Overview

- Build a single-page application (SPA) that can be hosted entirely as static files (HTML/CSS/JS) without a dedicated server process.
- Static assets may be split across multiple files for caching and download efficiency.
- Provide companion tooling to gather, normalize, and persist browsing-history data into SQLite, JSON, and SVG assets.
- All data-preparation tooling is executed manually during explicit data-prep runs.
- The goal is exploratory and interesting insight into browsing behavior rather than formal analytics.
- Overall tone should be engaging and informative, not playful or gimmicky.
- A github icon should be placed inconspicuously in the top right of the top level page that will link to the github repo for this project `https://github.com/ericzundel/history-view-website`

---

## 2. Technology & Development Environment

### Front-End

- JavaScript / TypeScript using Vite.
- Target Node.js 24, managed via `nvm`.
- TypeScript must run in `strict` mode and follow established best practices.
- Target modern evergreen browsers only.

### Linting, Formatting, and Testing

- ESLint (TypeScript configuration).
- Prettier.
- Vitest for unit and component tests.
- Representative UI tests must be included.

### Python Tooling

- Python 3.14.
- Environment managed with `uv` (assumed installed).
- Formatting and linting: Ruff.
- Type checking: **both mypy and pyright** (run independently).
- Tests required for Python scripts.

### Tooling & Automation

- Shell scripts manage development, build, and deployment workflows.
- Freely available libraries may be used (e.g., D3.js for visualization).
- Git hooks enforce linting, formatting, and type-checking before commits.

---

## 3. Repository Structure & Supporting Files

- License: Creative Commons BY-NC-SA.
- `README.md`: high-level project overview and quick start.
- `README_development.md`: environment setup and workflows only.
- `docs/`: deeper documentation (architecture decisions, historical specs, etc.).
- `config/`: taxonomy (`categories.yaml`), domain blocklists, and related docs.
- `raw-data/`: browser history exports (ignored except README).
- `data/`: generated assets only (ignored except README). Visualization JSON/sprites live under `data/viz_data/`.
- `scripts/`: shell scripts and Python tooling.
- `scripts/tests/`: Python tests.
- `mocks/`: design mock pages.
- `.env-example`: deployment configuration variables.

---

## 4. Front-End Visualization Requirements

### Initial View

- Full-page bubble heatmap inspired by:
  https://www.amcharts.com/demos/bubble-based-heat-map/
- Y-axis: days of the week (Sunday–Saturday).
- X-axis: hours of day (00:00–23:00).
- Bubble size represents visit count.
- Hover enlarges bubbles and displays numeric values.
- Click dims background to ~20% opacity and displays overlay.

### Animations

- Initial load.
- View switches.
- Overlay appearance/disappearance.
- Hover and click interactions.

### Primary Data Source: `level0.json`

```json
{
  "day": 0,
  "hour": 1,
  "value": 12345,
  "size": 88
}
```

### Overlay Drill-Down (`level1-<day>-<hour>.json`)

```json
{
  "day": 0,
  "hour": 1,
  "categories": [
    {
      "tag": "#news",
      "label": "News",
      "value": 120,
      "sites": [
        {
          "title": "Example Site",
          "url": "https://example.com",
          "domain": "example.com",
          "value": 12,
          "favicon_symbol_id": "id-example"
        }
      ]
    }
  ],
  "uncategorized": []
}
```

- One favicon sprite per day/hour.
- Client-side routing supported; Apache `.htaccess` rewrites required.
- Generated visualization assets (level0.json, level1-\*.json, sprites) are written under `data/viz_data/` by the data-prep scripts.

---

## 5. Raw Data Inputs

- Chrome JSON exports.
- Edge JSON exports.
- Google Takeout Chrome exports.

---

## 6. Database Schema

All timestamps are UTC (`YYYY-MM-DD HH:MM:SS`).

- Dataset generation converts UTC timestamps into a configurable local timezone for day/hour
  bucketing. `scripts/generate-datasets.py` accepts `--timezone` (IANA timezone name) and defaults
  to `America/New_York` (Eastern Time).

```sql
create table visits (
  id INTEGER PRIMARY KEY,
  domain TEXT NOT NULL,
  timestamp TEXT NOT NULL
);

create table domains (
  domain TEXT PRIMARY KEY,
  title TEXT,
  num_visits INTEGER NOT NULL,
  checked BOOLEAN NOT NULL CHECK (checked IN (0, 1)),
  check_timestamp TEXT,
  favicon_type TEXT,
  favicon_data BLOB,
  main_category TEXT
);

create index idx_visits_domain_timestamp on visits(domain, timestamp);
create index idx_visits_timestamp_domain on visits(timestamp, domain);
```

---

## 7. Categories

```yaml
categories:
  - tag: '#news'
    label: 'News'
    type: 'primary'
  - tag: '#python'
    label: 'Python Programming'
```

- Categories configuration lives in `config/categories.yaml`; keep primary tags at the top with `type: primary`, and omit `type` for secondary tags.

---

## 8. Python Tooling

- Loader scripts: `load-chrome.py`, `load-edge.py`, `load-takeout.py`
- Browser cache favicon extraction script.
- Network favicon fallback with rate limiting and guardrails.
- Scripts are idempotent, support `--dry-run` and `--limit`.
- URL handling: only `http` and `https` URLs are processed. `file:` and `mailto:` entries are skipped silently. Any other protocol should emit a warning, skip that entry, and continue processing.
- Domain blocklist: `config/domain-blocklist.yml` (gitignored) lists domain suffixes to skip during loaders/favicons runs. If the blocklist contains `foo.com`, skip both `foo.com` and any domains ending in `.foo.com`. To speed implementation, assume the suffix is always on a '.' boundary for the domain name so you can keep the blocklist as a Python `set()`
- Favicon fetching: if a `<link rel="icon">` uses a data URL (e.g., `data:image/png;base64,...`), decode the base64 payload directly and store it with the derived MIME type (no network fetch required).

---

## 9. Deployment

- Static asset deployment via `scp` to InMotion Hosting.
- Apache-compatible `.htaccess` assumed.

---

## 10. Repository Layout

(See previous message for full tree; unchanged.)
