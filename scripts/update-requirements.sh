#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

# Regenerate pinned requirements using uv's resolver.
cd "${WORKSPACE_ROOT}"
uv pip compile requirements.txt > requirements_lock.txt
