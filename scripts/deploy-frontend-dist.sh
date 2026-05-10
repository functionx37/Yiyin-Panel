#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly FRONTEND_DIR="${REPO_ROOT}/frontend"
readonly DIST_DIR="${FRONTEND_DIR}/dist"
readonly DEFAULT_REMOTE_DIST_DIR="/var/www/yiyin/dist"

DATA_SYNC_REMOTE_VALUE=""
DEPLOY_PORT="22"
SSH_TARGET=""
REMOTE_DIST_DIR=""
REMOTE_STAGING_DIR=""
SKIP_BUILD=0

usage() {
    cat <<'EOF'
Usage:
  ./scripts/deploy-frontend-dist.sh [options]

Options:
  --remote <target>          Remote target in user@host:/path/to/Yiyin-Panel format
  --port <port>              Remote SSH port, default: 22
  --remote-dist <path>       Remote dist path, default: /var/www/yiyin/dist
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
        REMOTE_DIST_DIR="${DEFAULT_REMOTE_DIST_DIR}"
    fi
}

shell_escape() {
    printf '%q' "$1"
}

verify_remote_dependencies() {
    if ! ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
        "command -v mktemp >/dev/null 2>&1 && command -v rsync >/dev/null 2>&1 && command -v sudo >/dev/null 2>&1"; then
        echo "Remote host must have mktemp, rsync, and sudo available." >&2
        exit 1
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

create_remote_staging_dir() {
    REMOTE_STAGING_DIR="$(
        ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
            "mktemp -d /tmp/yiyin-panel-dist.XXXXXX"
    )"

    if [[ -z "${REMOTE_STAGING_DIR}" ]]; then
        echo "Failed to create remote staging directory." >&2
        exit 1
    fi

    echo "Created remote staging directory: ${REMOTE_STAGING_DIR}"
}

prepare_remote_dir() {
    local escaped_remote_dir
    escaped_remote_dir="$(shell_escape "${REMOTE_DIST_DIR}")"

    echo "Ensuring remote directory exists: ${SSH_TARGET}:${REMOTE_DIST_DIR}"
    ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
        "sudo mkdir -p ${escaped_remote_dir}"
}

cleanup_remote_staging_dir() {
    local escaped_remote_staging_dir

    if [[ -z "${REMOTE_STAGING_DIR}" ]]; then
        return
    fi

    escaped_remote_staging_dir="$(shell_escape "${REMOTE_STAGING_DIR}")"
    ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
        "rm -rf ${escaped_remote_staging_dir}" >/dev/null 2>&1 || true
}

upload_dist() {
    if [[ ! -d "${DIST_DIR}" ]]; then
        echo "Local dist directory not found: ${DIST_DIR}" >&2
        exit 1
    fi

    echo "Uploading dist to staging directory ${SSH_TARGET}:${REMOTE_STAGING_DIR}"
    rsync -avz --delete \
        -e "ssh -p ${DEPLOY_PORT}" \
        "${DIST_DIR}/" \
        "${SSH_TARGET}:${REMOTE_STAGING_DIR}/"
}

install_dist() {
    local escaped_remote_dist_dir
    local escaped_remote_staging_dir

    escaped_remote_dist_dir="$(shell_escape "${REMOTE_DIST_DIR}")"
    escaped_remote_staging_dir="$(shell_escape "${REMOTE_STAGING_DIR}")"

    echo "Installing dist into ${REMOTE_DIST_DIR}"
    ssh -p "${DEPLOY_PORT}" "${SSH_TARGET}" \
        "sudo rsync -a --delete --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r ${escaped_remote_staging_dir}/ ${escaped_remote_dist_dir}/"
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

    trap cleanup_remote_staging_dir EXIT

    validate_config
    verify_remote_dependencies
    build_frontend
    create_remote_staging_dir
    prepare_remote_dir
    upload_dist
    install_dist
    cleanup_remote_staging_dir
    REMOTE_STAGING_DIR=""

    echo "Deployment finished."
    echo "Remote dist path: ${REMOTE_DIST_DIR}"
}

main "$@"
