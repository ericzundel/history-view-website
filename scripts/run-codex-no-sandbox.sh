#!/usr/bin/env bash
# Script to execute the flyway tool that runs database migrations

###################################
# Common preamble to setup environment
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

codex --dangerously-bypass-approvals-and-sandbox "$@"