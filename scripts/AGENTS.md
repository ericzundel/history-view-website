- These python scripts are checked with `mypy` and `pyright`. Make sure that these checks run clean when you are making changes.
- The scripts are formatted with `ruff` . Run `ruff format` to format files after making changes.

Before saying you are finished editing python files,

1. run the tests with `UV_CACHE_DIR=$(mktemp -d) uv run pytest scripts/tests`
2. run pre-commit hooks `UV_CACHE_DIR=$(mktemp -d) PRE_COMMIT_HOME=$(mktemp -d) pre-commit run --all-files`
