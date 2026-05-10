#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly FRONTEND_DIR="${REPO_ROOT}/frontend"
readonly DIST_DIR="${FRONTEND_DIR}/dist"

DATA_SYNC_REMOTE_VALUE=""
DEPLOY_PORT="22"
SSH_TARGET=""
REMOTE_PANEL_ROOT=""
REMOTE_DIST_DIR=""
SKIP_BUILD=0

usage() {
    cat <<'EOF'
Usage:
  ./scripts/deploy-frontend-dist.sh [options]

Options:
  --remote <target>          Remote target in user@host:/path/to/Yiyin-Panel format
  --port <port>              Remote SSH port, default: 22
  --remote-dist <path>       Remote dist path, overrides parsed /frontend/dist path
  --skip-build               Skip local npm build and only upload existing dist
  -h, --help                 Show this help message

Examples:
  ./scripts/deploy-frontend-dist.sh \
    --remote ubuntu@example.com:/srv/Yiyin-Panel

  DATA_SYNC_REMOTE=ubuntu@example.com:/srv/Yiyin-Panel \
  ./scripts/deploy-frontend-dist.sh
EOF
}

load_env_file() {
    local env_file="${REPO_ROOT}/.env"
    local line

    if [[ -f "${env_file}" ]]; then
        while IFS= read -r line || [[ -n "${line}" ]]; do
            line="${line%$'\r'}"
            [[ -z "${line//[[:space:]]/}" ]] && continue
            [[ "${line}" =~ ^[[:space:]]*# ]] && continue
            [[ "${line}" == export\ * ]] && line="${line#export }"
            export "${line}"
        done < "${env_file}"
    fi
}

require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Missing required command: ${cmd}" >&2
        exit 1
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --remote)
                DATA_SYNC_REMOTE_VALUE="${2:-}"
                shift 2
                ;;
            --port)
                DEPLOY_PORT="${2:-}"
                shift 2
                ;;
            --remote-dist)
                REMOTE_DIST_DIR="${2:-}"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                usage >&2
                exit 1
                ;;
        esac
    done
}

parse_data_sync_remote() {
    local remote="$1"

    if [[ ! "${remote}" =~ ^([^:]+):((~|/).*)$ ]]; then
        echo "Invalid DATA_SYNC_REMOTE: ${remote}" >&2
        echo "Expected format: user@host:/path/to/Yiyin-Panel or user@host:~/Yiyin-Panel" >&2
        exit 1
    fi

    SSH_TARGET="${BASH_REMATCH[1]}"
    REMOTE_PANEL_ROOT="${BASH_REMATCH[2]%/}"

    if [[ "${SSH_TARGET}" != *@* ]]; then
        echo "Invalid SSH target in DATA_SYNC_REMOTE: ${SSH_TARGET}" >&2
        echo "Expected format: user@host:/path/to/Yiyin-Panel or user@host:~/Yiyin-Panel" >&2
        exit 1
    fi
}

validate_config() {
    DATA_SYNC_REMOTE_VALUE="${DATA_SYNC_REMOTE_VALUE:-${DATA_SYNC_REMOTE:-}}"

    if [[ -z "${DATA_SYNC_REMOTE_VALUE}" ]]; then
        echo "Remote target is required. Set DATA_SYNC_REMOTE in .env or pass --remote." >&2
        exit 1
    fi

    parse_data_sync_remote "${DATA_SYNC_REMOTE_VALUE}"

    if [[ -z "${REMOTE_DIST_DIR}" ]]; then
        REMOTE_DIST_DIR="${REMOTE_PANEL_ROOT%/}/frontend/dist"
    fi
}

install_dependencies_if_needed() {
    if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
        echo "Installing frontend dependencies locally..."
        (
            cd "${FRONTEND_DIR}"
            npm install
        )
    fi
}

build_frontend() {
    if [[ "${SKIP_BUILD}" -eq 1 ]]; then
        echo "Skipping local build and reusing ${DIST_DIR}"
        return
    fi

    install_dependencies_if_needed

    echo "Building frontend locally..."
    (
        cd "${FRONTEND_DIR}"
        npm run build
    )
}

prepare_remote_dir() {
    echo "Ensuring remote directory exists: ${SSH_TARGET}:${REMOTE_DIST_DIR}"
    if [[ "${REMOTE_DIST_DIR}" == "~" || "${REMOTE_DIST_DIR}" == "~/"* ]]; then
        ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" "mkdir -p ${REMOTE_DIST_DIR}"
    else
        local escaped_remote_dir
        escaped_remote_dir="$(printf '%q' "${REMOTE_DIST_DIR}")"
        ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" "mkdir -p ${escaped_remote_dir}"
    fi
}

upload_dist() {
    if [[ ! -d "${DIST_DIR}" ]]; then
        echo "Local dist directory not found: ${DIST_DIR}" >&2
        exit 1
    fi

    echo "Uploading dist to ${SSH_TARGET}:${REMOTE_DIST_DIR}"
    rsync -avz --delete \
        -e "ssh -p ${DEPLOY_PORT}" \
        "${DIST_DIR}/" \
        "${SSH_TARGET}:${REMOTE_DIST_DIR}/"
}

main() {
    load_env_file
    parse_args "$@"

    require_command npm
    require_command ssh
    require_command rsync

    if [[ ! -d "${FRONTEND_DIR}" ]]; then
        echo "Frontend directory not found: ${FRONTEND_DIR}" >&2
        exit 1
    fi

    validate_config
    build_frontend
    prepare_remote_dir
    upload_dist

    echo "Deployment finished."
    echo "Remote dist path: ${REMOTE_DIST_DIR}"
}

main "$@"
