#!/usr/bin/env bash
# Starts the backend (port 8000) and the frontend dev server (port 5173) together.
# Press Ctrl+C to stop both.
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
backend_pid=""
frontend_pid=""

stop_all() {
  trap - INT TERM EXIT
  for pid in "$backend_pid" "$frontend_pid"; do
    if [ -n "$pid" ]; then
      # Stop the whole process group so child servers go down with their launchers.
      kill -TERM "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap stop_all INT TERM EXIT

if [ ! -d "$root/frontend/node_modules" ]; then
  (cd "$root/frontend" && npm install)
fi

# set -m gives each background job its own process group so stop_all can kill it whole.
set -m
(cd "$root/backend" && exec uv run uvicorn app.main:app --port 8000) &
backend_pid=$!
(cd "$root/frontend" && exec npm run dev) &
frontend_pid=$!
set +m

echo "Backend:  http://localhost:8000/api/health"
echo "Frontend: http://localhost:5173"

# Exit as soon as either server stops, then the trap stops the other.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done
