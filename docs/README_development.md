# Development Guide

## JavaScript / Node
- Install Node 24 with `nvm install 24 && nvm use 24`.
- Install deps: `npm install` (package.json will be added alongside Vite setup).
- Run dev server: `scripts/dev.sh` (wraps `npm run dev -- --host`).
- Build production bundle: `scripts/build.sh` (wraps `npm run build`).
- Lint/format/test: ESLint + Prettier + Vitest (scripts to be added in package.json).

## Python
- Requires Python 3.14 managed by `uv` (assumed installed).
- Create venv: `uv venv --python 3.14` then `source .venv/bin/activate`.
- Install deps (placeholder): `uv pip install -r requirements.txt` (file to be added).
- Data loaders live in `scripts/` (`load-chrome.py`, `load-edge.py`, `load-takeout.py`) with tests in `scripts/tests/`.
- Favicon enrichment: `scripts/find-favicons.py`.
- Run format/lint/type checks: Ruff, mypy, pyright (scripts to be added).

## Environment
- Copy `.env-example` to `.env` and fill deployment host/user/port and any API tokens.
- Git hooks (Husky or similar) will enforce linting/formatting/type checks before commits.

## Data workflow (high level)
1. Drop source exports into `raw-data/`.
2. Run loader scripts to populate SQLite in `data/`.
3. Generate aggregated JSON (`level0`, `level1-*`) and sprites for the front-end.
4. Build and deploy static assets via `scripts/deploy.sh`.
