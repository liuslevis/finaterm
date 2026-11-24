#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
dashboard_root="$(cd -- "$script_dir/.." && pwd)"
python="$dashboard_root/.venv/bin/python"
port="${FINANCE_DASHBOARD_PORT:-63000}"
state_dir="$HOME/Library/Application Support/FinanceDashboard"
log_dir="$HOME/Library/Logs/FinanceDashboard"
pid_file="$state_dir/dashboard.pid"
log_file="$log_dir/dashboard.log"
health_url="http://127.0.0.1:$port/__finance_dashboard_health"

if [[ ! -x "$python" ]]; then
  echo "Dashboard virtual environment not found. Run 'uv sync' in $dashboard_root first." >&2
  exit 1
fi

mkdir -p "$state_dir" "$log_dir"

if [[ -f "$pid_file" ]]; then
  existing_pid="$(cat "$pid_file")"
  if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "Finance dashboard is already running with PID $existing_pid."
    exit 0
  fi
  rm -f "$pid_file"
fi

if [[ "$(curl --silent --fail --max-time 2 "$health_url" 2>/dev/null || true)" == "finance-dashboard-uv-v2" ]]; then
  echo "Finance dashboard is already responding at http://127.0.0.1:$port/."
  exit 0
fi

if "$python" -c \
  'import socket, sys; sock = socket.socket(); sock.settimeout(0.5); sys.exit(0 if sock.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)' \
  "$port"; then
  echo "Port $port is already in use by another service." >&2
  exit 1
fi

cd "$dashboard_root"
nohup "$python" dashboard_server.py \
  --port "$port" \
  --no-browser \
  </dev/null >>"$log_file" 2>&1 &
dashboard_pid=$!
echo "$dashboard_pid" > "$pid_file"

for _ in {1..30}; do
  if [[ "$(curl --silent --fail --max-time 2 "$health_url" 2>/dev/null || true)" == "finance-dashboard-uv-v2" ]]; then
    echo "Finance dashboard started with PID $dashboard_pid at http://127.0.0.1:$port/."
    echo "Log: $log_file"
    exit 0
  fi
  if ! kill -0 "$dashboard_pid" 2>/dev/null; then
    break
  fi
  sleep 1
done

rm -f "$pid_file"
echo "Finance dashboard failed to start. Check $log_file." >&2
exit 1
