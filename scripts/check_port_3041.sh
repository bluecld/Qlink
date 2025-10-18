#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 [HOST] [PORT]" >&2
    echo "  HOST defaults to \$VANTAGE_IP (or local check if unset)." >&2
    echo "  PORT defaults to \$VANTAGE_PORT or 3041." >&2
    exit 1
}

if [[ $# -gt 2 ]]; then
    usage
fi

HOST="${VANTAGE_IP:-}"
PORT="${VANTAGE_PORT:-3041}"

if [[ $# -ge 1 ]]; then
    HOST="$1"
fi
if [[ $# -ge 2 ]]; then
    PORT="$2"
fi

if [[ -z "${PORT}" || ! "${PORT}" =~ ^[0-9]+$ ]]; then
    echo "Invalid port: ${PORT}" >&2
    exit 2
fi

check_local_port() {
    local port="$1"

    if command -v ss >/dev/null 2>&1; then
        if ss -ltn "sport = :${port}" 2>/dev/null | grep -q .; then
            echo "Port ${port} is LISTENING locally."
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | awk '{print $4}' | grep -q ":${port}\$"; then
            echo "Port ${port} is LISTENING locally."
            return 0
        fi
    else
        echo "'ss' or 'netstat' is required for local checks." >&2
        return 3
    fi

    echo "Port ${port} is NOT listening locally."
    return 1
}

check_remote_port() {
    local host="$1"
    local port="$2"

    if command -v python3 >/dev/null 2>&1; then
        REMOTE_HOST="${host}" REMOTE_PORT="${port}" python3 - <<'PY'
import os
import socket
import sys

host = os.environ["REMOTE_HOST"]
port = int(os.environ["REMOTE_PORT"])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3.0)
try:
    sock.connect((host, port))
except OSError as exc:
    print(f"Port {port} on {host} is CLOSED or unreachable: {exc}")
    sys.exit(1)
else:
    print(f"Port {port} on {host} is REACHABLE.")
finally:
    sock.close()
PY
        return $?
    elif command -v nc >/dev/null 2>&1; then
        if nc -z -w 3 "${host}" "${port}"; then
            echo "Port ${port} on ${host} is REACHABLE."
            return 0
        fi
        echo "Port ${port} on ${host} is CLOSED or unreachable."
        return 1
    else
        echo "python3 or nc (netcat) is required for remote checks." >&2
        return 4
    fi
}

if [[ -z "${HOST}" || "${HOST}" == "localhost" || "${HOST}" == "127.0.0.1" ]]; then
    echo "Checking local port ${PORT}..."
    check_local_port "${PORT}"
else
    echo "Checking TCP ${HOST}:${PORT} from $(hostname)..."
    check_remote_port "${HOST}" "${PORT}"
fi
