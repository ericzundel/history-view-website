#!/usr/bin/env bash
# Copyright 2025 Eric Z. Ayers. All rights reserved
#
# Common preamble for all shell scripts in this project
#
# Usage:
#   Source this file at the beginning of your script:
#
#   #!/usr/bin/env bash
#   source "$(dirname "$(realpath "$0")")/../common/preamble.sh" || exit 1
#   init_preamble
#
# This will:
#   - Enable strict error handling (set -euo pipefail)
#   - Set WORKSPACE_ROOT to the project root directory
#   - Activate the Python virtual environment if present
#   - Export all environment variables from .env file

# Function to initialize the common environment
init_preamble() {
    # Enable strict error handling
    set -euo pipefail

    # Determine workspace root (assumes script is in scripts/ or scripts/lib/)
    local script_dir

    # Use BASH_SOURCE[1] if available (when sourced from a script),
    # otherwise use BASH_SOURCE[0] (when sourced interactively)
    if [ ${#BASH_SOURCE[@]} -gt 1 ]; then
        script_dir=$(dirname "$(realpath "${BASH_SOURCE[1]}")")
    else
        script_dir=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
    fi

    # Check if we're in scripts/lib/ or scripts/
    if [[ "${script_dir}" == */scripts/lib ]]; then
        WORKSPACE_ROOT="${script_dir}/../.."
    elif [[ "${script_dir}" == */scripts ]]; then
        WORKSPACE_ROOT="${script_dir}/.."
    else
        # Fallback: assume we're being called from workspace root
        WORKSPACE_ROOT="${script_dir}"
    fi

    # Normalize the path
    WORKSPACE_ROOT=$(cd "${WORKSPACE_ROOT}" && pwd)
    export WORKSPACE_ROOT

    # Load Python virtual environment
    if [ -d "${WORKSPACE_ROOT}/.venv/bin/" ]; then
        # shellcheck source=/dev/null
        source "${WORKSPACE_ROOT}/.venv/bin/activate"
    else
       echo "⚠️  Warning: virtual environment named '.venv' not found at ${WORKSPACE_ROOT}/.venv"
       echo "⚠️  You can create it by running 'uv venv --python ${PYTHON_VERSION}'"
    fi

    # Load environment variables from .env file and export them
    if [ -f "${WORKSPACE_ROOT}/.env" ]; then
        set -o allexport
        # shellcheck source=/dev/null
        source "${WORKSPACE_ROOT}/.env"
        set +o allexport
    else
        echo "⚠️  Warning: .env file not found at ${WORKSPACE_ROOT}/.env"
    fi

}

# run_with_timeout <seconds> cmd ...
#
# If a timeout command is installed in a known path, it will run the
# command with a timeout. Otherwise, it will run with no timeout.
run_with_timeout() {
    duration=$1
    shift

    paths="/bin/timeout  /usr/bin/timeout /opt/homebrew/bin/timeout \
           /bin/gtimeout /usr/bin/gtimeout /opt/homebrew/bin/gtimeout"

    timeout_cmd=""
    for i in paths ; do
        if [[ -x $i ]]; then
            timeout_cmd=$i
            break
        fi
    done
    if [[ -n $timeout_cmd ]]; then
        ${timeout_cmd} ${duration} $*
    else
        # Run the command without timeout
        $*
    fi
}

# get_elapsed <start_time> [<end_time>]
# if end_time is not provided, uses current time
get_elapsed() {
    local start_time=$1
    local end_time=${2:-$SECONDS}
    local elapsed=$((end_time - start_time))

    local hours=$((elapsed / 3600))
    local minutes=$(( (elapsed % 3600) / 60 ))
    local seconds=$((elapsed % 60))

    printf "%02d:%02d:%02d" "${hours}" "${minutes}" "${seconds}"
}