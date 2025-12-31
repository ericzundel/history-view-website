# Agent Onboarding Notes

Context to get up to speed quickly on this repo.

## Key references

- Product spec: `docs/SPEC_v1.md` (working requirements; mirrors `prompts/initial_prompt.md`).
- Development setup: `README_development.md`.
- Project overview: `README.md`.
- Taxonomy: `config/README.md` and `config/categories.yaml` (currently empty placeholder).

## Tech expectations (from spec)

- Front-end: Vite + TypeScript (strict), modern browsers only. Provide bubble-heatmap + treemap overlays with animations and client-side routing.
- Node: use `nvm` with Node 24.
- Python: 3.14 managed via `uv` (install deps with `uv pip install -r requirements.txt` / tools via `uvx`); tooling uses Ruff + mypy + pyright; tests required.
- If PyPI/network is blocked, run Python tests from the local venv instead: `source .venv/bin/activate && pytest scripts/tests`. Use the same pattern for other CLI checks to avoid uv build-time downloads.
- Deployment: static assets via `scp` to shared hosting using `.env` variables; Apache `.htaccess` routing assumed.
- Git hooks should enforce lint/format/type checks.

## Repository layout (scaffolded)

- `src/`, `public/`, `mocks/` (design mock pages).
- `scripts/`: `dev.sh`, `build.sh`, `deploy.sh`, placeholder loaders (`load-*.py`), `find-favicons.py`, `scripts/tests/` for Python tests. Common Bash preamble in `scripts/common/preamble.sh`.
- `data/`: generated artifacts (README + .gitignore only tracked).
- `raw-data/`: source exports (README + .gitignore tracked).
- `config/`: taxonomy files and blocklists.
- `docs/`: spec + docs README.
- `.env-example`: deployment variables template.
- LICENSE: CC BY-NC-SA.

## Immediate next steps to continue build

1. Initialize front-end (Vite, TS strict, ESLint/Prettier/Vitest) and wire `scripts/dev.sh`/`build.sh`.
2. Flesh out Python environment files (requirements, pyproject/ruff/mypy/pyright configs) and implement loader/favicons scripts with tests.
3. Populate `config/categories.yaml` with ~40 primary + ~200 secondary tags; document mapping rules.
4. Add git hooks (Husky or pre-commit) to run lint/format/type checks.
5. Create data-generation pipeline to emit `level0.json`, `level1-<day>-<hour>.json`, and sprites; stub client data fetchers.
