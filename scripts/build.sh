#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

# Build production bundle.
npm run build "$@"
