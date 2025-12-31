# Raw Data Inputs

This folder holds browser history exports that are **not** checked into Git. Place source files here before running the Python loaders.

Expected sources:
- Chrome JSON exports: `chrome-history-export-<date>.json`
- Edge JSON exports: `edge-history-export-<date>.json`
- Google Takeout exports: either the raw Takeout ZIP or extracted JSON files

Notes:
- Files remain ignored; only this README and `.gitignore` are tracked.
- Keep filenames dated to distinguish runs.
- Do not store processed or generated artifacts here—use `data/` instead.
