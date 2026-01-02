# Agent Onboarding Notes

Context to get up to speed quickly on this repo.

## Key references

- Product spec: `docs/SPEC_v1.md` (working requirements; mirrors `prompts/initial_prompt.md`).
- Development setup: `docs/README_development.md`.
- Project overview: `README.md`.
- Taxonomy: `config/README.md` and `config/categories.yaml` (currently empty placeholder).

## Tech expectations (from spec)

- Front-end: Vite + TypeScript (strict), modern browsers only. Provide bubble-heatmap + treemap overlays with animations and client-side routing.
- Node: use `nvm` with Node 24.
- Python: 3.14 managed via `uv` dependencies are managed in `pyproject.toml` you can run some tools with `uvx`; checking/formatting:wq uses Ruff + mypy + pyright; tests required.
- If PyPI/network is blocked, run Python tests from the local venv instead: `source .venv/bin/activate && pytest scripts/tests`. Use the same pattern for other CLI checks to avoid uv build-time downloads.
- Deployment: static assets via `scp` to shared hosting using `.env` variables; Apache `.htaccess` routing assumed.
- Git hooks should enforce lint/format/type checks.

## Repository layout (scaffolded)

- `src/`, `public/`, `mocks/` (design mock pages).
- `scripts/`: `dev.sh`, `build.sh`, `deploy.sh`, placeholder loaders (`load-*.py`), `find-favicons.py`, `scripts/tests/` for Python tests. Common Bash preamble in `scripts/common/preamble.sh`.
- `data/`: generated artifacts (README + .gitignore only tracked).
- `raw-data/`: source exports (README + .gitignore tracked).
- `config/`: taxonomy files and blocklists.
- `docs/`: spec + development setup docs.
- `prompts/`: prompt history and spec mirrors.
- `dist/`: built static assets (generated).
- `node_modules/`: local Node dependencies (generated).
- `.env` and `.env-example`: deployment variables (example + local).
- LICENSE: CC BY-NC-SA.
