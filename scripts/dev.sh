#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

# Launch Vite dev server with host binding for remote access.
npm run dev -- --host "$@"
