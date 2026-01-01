#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

# Run pytest with coverage and print summary. Use --html to emit an HTML report.

HTML_REPORT=0
if [[ "${1:-}" == "--html" ]]; then
    HTML_REPORT=1
    shift
fi

cov_reports="term-missing"
if [[ "${HTML_REPORT}" -eq 1 ]]; then
    cov_reports+=" html:${WORKSPACE_ROOT}/html_cov"
fi

uv run pytest \
    --cov=scripts \
    --cov-branch \
    --cov-report="${cov_reports}" \
    scripts/tests \
    "$@"
