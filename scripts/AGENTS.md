- These python scripts are checked with `mypy` and `pyright`. Make sure that these checks run clean when you are making changes.
- The scripts are formatted with `ruff` . Run `ruff format` to format files after making changes.

Before saying you are finished editing python files, run the tests and make sure the pre-commit hooks all pass as follows:

`UV_CACHE_DIR=$(mktemp -d) PRE_COMMIT_HOME=$(mktemp -d) pre-commit run --all-files`
