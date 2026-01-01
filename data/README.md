# Generated Data

This directory stores generated artifacts created by the data-prep tooling:
- SQLite databases with normalized visit data
- Aggregated JSON files (`level0.json`, `level1-<day>-<hour>.json`) under `viz_data/`
- Favicon sprites under `viz_data/sprites/` and related logs

Everything here is ignored by Git except this README and `.gitignore`. Regenerate contents via the Python loaders and helper scripts in `scripts/`.

To rebuild visualization assets from the SQLite database, run:

```
uv run python scripts/generate-datasets.py --db data/history.db --output data/viz_data
```

Sprites land in `data/viz_data/sprites/level1-<day>-<hour>.svg` alongside JSON buckets. Pass `--skip-sprites` if you only need the JSON outputs.
