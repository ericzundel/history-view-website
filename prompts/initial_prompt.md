# History View Website Specification Draft

I am building a visualization of my browsing history to make some interesting content on my website.  I have some raw data from my browser and a download from Google Takeout. I'm going to assemble and curate this data and then publish it on my personal website.

## 1. Project Overview
- Build a single-page application (SPA) that can be hosted as static files without a dedicated server process. Static assets may be split across multiple files for download efficiency.
- Provide companion tooling to gather, normalize, and persist browsing-history data into JSON and SVG assets. These scripts are executed manually during data-prep runs.
- Primary goal is exploratory/interesting insights into browsing behavior rather than formal analytics; tone should be engaging but not silly/playful.

## 2. Technology & Development Environment
- Front-end: JavaScript/TypeScript with Vite. Target Node.js 24 managed via `nvm`.
- TypeScript must run in `strict` mode and follow widely accepted best practices.
- Linting/formatting/testing:
  - ESLint (with TypeScript config) + Prettier.
  - Vitest for unit/component coverage; create representative UI tests.
  - Python tooling formatted and linted with Ruff, type-checked with `pyright` (or `typer`? user said "ty"? need interpret; maybe "pyright"? but user wrote "ty" maybe "pyright"? Hmm "Python formatting and typechecking should use ruff + ty". maybe "ty" is `pytype`? maybe `typing`? Could be tool "pyright"? "ty" ??? Hmm there is CLI "pytype"? Could "ty" mean "pyright"? but fosters? maybe "pyproject tool `ty`"? w/out clarity ask later, but spec should capture requirement as `ty`. We'll write "ty (type checker)".*** reread instructions: "Python formatting and typechecking should use ruff + ty". There is tool "pyright"? But specify as given.***
  - Provide tests for both UI components and Python scripts.
- Shell scripts manage development workflows.
- Data cleaning and transformation tooling is written in Python 3.14, with typing, executed via the `uv` environment manager (assumed installed).
- Any freely available libraries may be used (e.g., D3.js for visualization).
- Target modern evergreen browsers (no legacy support requirements).
- Git hooks enforce linting/formatting before commits (e.g., via Husky or simple `pre-commit` scripts).

## 3. Repository Structure & Supporting Files
- License: Creative Commons BY-NC-SA.
- `README.md`: project overview and quick start; deeper docs live elsewhere.
- `README_development.md`
  - Split into a JavaScript/Node section (Vite install, run dev server, build) and a Python section (setting up `uv`, running data scripts, refreshing JSON/SVG assets).
  - Focus on environment setup and workflow tasks (not business-logic details).
- `docs/`
  - Additional documentation (architecture decisions, spec versions, etc.).
- `raw-data/`
  - Contains browsing-history JSON exports (ignored by Git except for README).
  - Include a `README.md` describing expected file formats/sources.
- `data/`
  - Generated assets: SQLite DBs, processed JSON (`level0`, `level1-*`), favicon sprites, logs.
  - Only `data/README.md` tracked; other contents ignored via `.gitignore`.
- `scripts/`
  - Shell script to launch the Vite dev server with `-- --host` for remote access.
  - Shell script to build the production bundle into static HTML assets.
  - Shell script to deploy the production bundle via `scp` (see deployment section).
  - Python utility scripts (detailed later) for data loading.
- `.env-example` lists configurable development/deployment variables such as deployment target host, username, and `scp` port.
- Additional docs near the category data (see Section 8).

## 4. Front-End Visualization Requirements
- Initial view: full-page bubble heatmap inspired by [AMCharts Bubble Heat Map](https://www.amcharts.com/demos/bubble-based-heat-map/).
  - Y-axis: days of the week (Sunday–Saturday).
  - X-axis: 24 columns labeled `00:00`–`23:00`.
  - Bubble size corresponds to visit counts; hover reveals the numeric value and enlarges the bubble.
  - Clicking a bubble triggers an overlay while dimming the base heatmap (20% opacity with subdued colors).
- Animations should occur:
  - On initial load.
  - When switching views.
  - When overlays appear/disappear.
  - On hover and click interactions targeting individual details.
- Primary data source: `level0.json`, a static file fetched on page load with entries such as:

```
{
  "day": "0",          // 0 = Sunday, 1 = Monday, etc.
  "hour": "1",         // 0 = 00:00, 1 = 01:00, ... 23 = 23:00
  "value": "12345",    // visit count displayed on hover
  "size": "88"         // linear scale 0..100, drives bubble size
}
```
- Color palette: subdued oranges/browns/reds; experiment by building ~12 color variations showcased on a dedicated mock page to review aesthetics before finalizing.

- Overlay presents a drill-down treemap.
  - Top-level tiles represent category assignments (see Section 8). Initial data may omit categories until classification pipeline is implemented; overlay should handle missing categories gracefully.
  - Clicking a category loads a second treemap with website titles and favicon imagery; each tile links to its website.
- Each drill-down dataset lives in its own JSON file fetched on demand.
  - Files use the `level1-<day>-<hour>.json` pattern, e.g., `level1-0-01.json`.
  - File structure:

```
{
  "title": "Example Site Title",        // text from <title>
  "url": "https://example.com",         // destination link
  "favicon": "example.svg",             // raw favicon filename stored in raw-data
  "favicon_symbol_id": "id-example"     // sprite symbol identifier
}
```

- Provide one favicon sprite per day/hour combination for use in the treemap overlay.

## 6. Raw Data Inputs
- `raw-data/` initially contains any of the following JSON exports:
  1. `chrome-history-export-<date>.json`: array entries include fields such as `id`, `visitTime`, `title`, `url`, etc.
  2. `edge-history-export-<date>.json`: array entries with fields like `order`, `date`, `time`, `title`, `url`, etc.
  3. Google Takeout Chrome data (standard export format).

## 7. Database Schema
- Load raw data into a SQLite database with tables:

```
create table visits (
  id INTEGER PRIMARY KEY,            -- autogenerated
  domain TEXT NOT NULL,              -- domain name
  timestamp TEXT NOT NULL            -- visit time in YYYY-MM-DD HH:MM:SS (24h)
);

create table domains (
  domain TEXT PRIMARY KEY,           -- domain name
  title TEXT,                        -- optional
  num_visits INTEGER NOT NULL,       -- count of visits in visits table
  checked BOOLEAN NOT NULL CHECK (checked IN (0, 1)),
  check_timestamp TEXT,              -- UTC YYYY-MM-DD HH:MM:SS
  favicon_type TEXT,                 -- MIME type
  favicon_data BLOB,                 -- raw icon data
  main_category TEXT,                -- primary category. Should be a value from the categories.yaml file can be NULL
);
```
- Ensure the schema supports long-term (all-time) history with efficient querying for time-of-day/day-of-week aggregations. Index `visits(domain, timestamp)` to support the heatmap queries. Avoid speculative columns; add only when a requirement demands it.

## 8. Categories

This is a hand maintained list of categories stored in a categories.yaml file. This file is checked in to the repository

The categories are used to classify websites by type
```
  - category: 
    - tag: <hashtag for category id>
    - label: Human Readable Name for display
    - type: primary

 - category
   - tag: <hashtag for category id>
   - label:
   
 ``` 

 Please pre-populate this file with up to  40 different primary categories you might use to classify websites in general such as:

 ```
 Primary
   #news  News
   #social  Social Media
   #games  Games
   #office  Spreadsheets, Word Processors, etc
   #productivity Productivity software
   #messaging Email and Messaging
   #software_dev Software Development
   #entertainment  Entertainment
   ...
```
Also come up with around 200 secondary categories based on the primary categories
```
Secondary:
  #java  Java Programming Languages
  #python Python Programming Language
  #rust
  #spreadsheet
  #wordprocessor
  #calculator
  #worldnews
  #localnews
  #wordgame
  #puzzlegame
  #sms
  #security
  #videos
  #shorts
  #engineering
  ...
```

If a category does not have a 'type: primary' value, it's assumed to be secondary type. Don't fill in 'secondary' for each one. Organize primary categories at the top of the file.

- Please include documentation about this in a README file somewhere close to the category file.
- Pre-populate with ~40 primary categories and ~200 secondary categories; expect future manual adjustments.

## 9. Python Tooling
- Create separate loader scripts named `load-<datasource>.py`, each accepting a filename:
  - Extract the domain from each URL (e.g., `https://foo.com/path` → `foo.com`).
  - Normalize timestamps to `YYYY-MM-DD HH:MM:SS`.
  - Insert domain/timestamp rows into `visits`.
  - Ensure the domain exists in `domains`, populating title if provided and initializing boolean fields to `0`.
  - Increment `num_visits` if the domain already exists.
- Create `find-favicons.py` to enrich the `domains` table:
  - Iterate over domains with `checked = 0` or null favicon data.
  - Request `https://<domain>/`, following redirects.
  - Update missing titles from the retrieved page `<title>`.
  - Gather favicon links, preferring SVG (`<link rel="icon" href="/icon.svg" type="image/svg+xml" sizes="any">`).
  - If an SVG is found, download and store its data and MIME type; otherwise, fall back to the highest-resolution convertible format.
  - After processing a domain, persist data, set `checked = 1`, and update `check_timestamp` to current UTC datetime.
- Loader scripts must be idempotent, support a `--dry-run` flag, provide an option to process only N entries (limit applies whether or not dry-run is active), and log human-readable progress/errors.

## 10. Deployment Expectations
- Production build outputs stand-alone HTML/CSS/JS assets ready for static hosting.
- Deployment script pushes the production build via `scp`/`ssh` to the InMotion hosting account’s `public_html` directory (credentials/port driven by `.env-example`). Host uses cPanel and Apache-style `.htaccess` (assume compatibility).
- Provide separate scripts for development server launch, production build, and deployment (see Section 3).

## 11. Proposed Repository Layout (Draft)
```
/
├── README.md
├── LICENSE            # CC BY-NC-SA
├── README_development.md
├── package.json / vite.config.ts / tsconfig.json
├── src/               # front-end SPA code
├── public/            # static assets (favicons sprites, etc.)
├── mocks/             # design mock pages (color palettes, layout prototypes)
├── data/              # generated DB + visualization JSON/sprites (gitignored except README)
├── raw-data/          # source exports + README
├── scripts/
│   ├── dev.sh
│   ├── build.sh
│   ├── deploy.sh
│   ├── load-chrome.py
│   ├── load-edge.py
│   ├── load-takeout.py
│   └── find-favicons.py
├── categories/
│   ├── categories.yaml
│   └── README.md      # explains taxonomy usage/updating
├── docs/
│   └── (architecture, spec history, etc.)
└── .env-example
```
- Open questions: Should `mocks/` live under `docs/` instead? Any need for additional top-level folders (e.g., `tests/` for integration scripts) beyond what Vite/Python structures already provide?
