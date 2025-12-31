#!/usr/bin/env bash
source "$(dirname "$(realpath "$0")")/common/preamble.sh" || exit 1
init_preamble

: "${DEPLOY_HOST:?Set DEPLOY_HOST in .env}"
: "${DEPLOY_USER:?Set DEPLOY_USER in .env}"
: "${DEPLOY_PORT:=22}"
: "${DEPLOY_PATH:?Set DEPLOY_PATH in .env}"

BUILD_DIR="${WORKSPACE_ROOT}/dist"

if [ ! -d "${BUILD_DIR}" ]; then
  echo "Build output not found at ${BUILD_DIR}. Run scripts/build.sh first."
  exit 1
fi

echo "Deploying ${BUILD_DIR} to ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH} (port ${DEPLOY_PORT})"
scp -P "${DEPLOY_PORT}" -r "${BUILD_DIR}/." "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}"
