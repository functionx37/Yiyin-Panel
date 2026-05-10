#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly TEMPLATE_PATH="${REPO_ROOT}/nginx/yiyin.conf.example"
readonly NGINX_CONF_PATH="/etc/nginx/nginx.conf"
readonly NGINX_INCLUDE_LINE="include /etc/nginx/conf.d/*.conf;"
readonly NGINX_SITE_DIR="/etc/nginx/conf.d"
readonly NGINX_SITE_PATH="${NGINX_SITE_DIR}/yiyin.conf"
readonly FRONTEND_DIST_PATH="/var/www/yiyin/dist"
DATA_SYNC_REMOTE_HOST=""

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

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "Please run this script with sudo so it can write nginx config files." >&2
        exit 1
    fi
}

require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "Missing required command: ${cmd}" >&2
        exit 1
    fi
}

require_env() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required environment variable: ${name}" >&2
        exit 1
    fi
}

parse_data_sync_remote() {
    local remote="${DATA_SYNC_REMOTE:-}"

    if [[ -z "${remote}" ]]; then
        return
    fi

    if [[ ! "${remote}" =~ ^([^:]+):((~|/).*)$ ]]; then
        echo "Invalid DATA_SYNC_REMOTE: ${remote}" >&2
        echo "Expected format: user@host:/path/to/Yiyin-Panel or user@host:~/Yiyin-Panel" >&2
        exit 1
    fi

    DATA_SYNC_REMOTE_HOST="${BASH_REMATCH[1]##*@}"
}

apply_default_env() {
    local site_host="${SITE_BASE_URL:-}"

    parse_data_sync_remote

    site_host="${site_host#*://}"
    site_host="${site_host%%/*}"

    export YIYIN_SERVER_NAME="${YIYIN_SERVER_NAME:-${DATA_SYNC_REMOTE_HOST:-${site_host}}}"
    export YIYIN_BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
    export YIYIN_BACKEND_PORT="${BACKEND_PORT:-8000}"
}

ensure_nginx_include() {
    python3 - "${NGINX_CONF_PATH}" "${NGINX_INCLUDE_LINE}" <<'PY'
from pathlib import Path
import sys

nginx_conf = Path(sys.argv[1])
include_line = sys.argv[2]

content = nginx_conf.read_text()

if include_line in content:
    print(f"{include_line} already exists in {nginx_conf}")
    raise SystemExit(0)

lines = content.splitlines()
result = []
inserted = False

for line in lines:
    result.append(line)
    if not inserted and line.strip() == "http {":
        result.append(f"    {include_line}")
        inserted = True

if not inserted:
    raise SystemExit(f"Could not find 'http {{' block in {nginx_conf}")

nginx_conf.write_text("\n".join(result) + "\n")
print(f"Added {include_line} to {nginx_conf}")
PY
}

main() {
    load_env_file
    require_root
    require_command nginx
    require_command envsubst
    require_command python3
    apply_default_env

    require_env YIYIN_SERVER_NAME
    require_env YIYIN_BACKEND_HOST
    require_env YIYIN_BACKEND_PORT

    if [[ ! -f "${TEMPLATE_PATH}" ]]; then
        echo "Template file not found: ${TEMPLATE_PATH}" >&2
        exit 1
    fi

    mkdir -p "${NGINX_SITE_DIR}"
    ensure_nginx_include

    export YIYIN_FRONTEND_DIST="${FRONTEND_DIST_PATH}"

    envsubst '${YIYIN_SERVER_NAME} ${YIYIN_FRONTEND_DIST} ${YIYIN_BACKEND_HOST} ${YIYIN_BACKEND_PORT}' \
        < "${TEMPLATE_PATH}" \
        > "${NGINX_SITE_PATH}"

    nginx -t

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet nginx; then
            systemctl reload nginx
        else
            systemctl enable --now nginx
        fi
    fi

    echo "Wrote nginx site config to ${NGINX_SITE_PATH}"
    echo "Server name: ${YIYIN_SERVER_NAME}"
    echo "Frontend dist path: ${FRONTEND_DIST_PATH}"
}

main "$@"
