#!/usr/bin/env bash
# Start a clean take: reset the take database, start the API on it (copilot on), make
# sure the web app runs, and warm the planner's brief so no one waits on camera.
set -euo pipefail
cd "$(dirname "$0")"
DB=${TAKE_DB:-/tmp/datalens-take.db}
pkill -f "uvicorn app.main:app --port 8000" 2>/dev/null || true
sleep 1
python3 reset_take.py --db "$DB"
(cd ../backend && DATABASE_URL="sqlite:///$DB" DATALENS_MEDIA_DIR=/tmp/datalens-take-media \
  nohup uv run uvicorn app.main:app --port 8000 > /tmp/datalens-take-api.log 2>&1 &)
if ! curl -s -o /dev/null http://localhost:5173; then
  (cd ../frontend && nohup npx vite --port 5173 > /tmp/datalens-take-web.log 2>&1 &)
fi
for _ in $(seq 1 60); do curl -s -o /dev/null http://localhost:8000/api/health && break; sleep 1; done
JAR=$(mktemp)
curl -s -c "$JAR" -X POST http://localhost:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"email":"daniel.mensah@mirsalterminals.com","password":"welcome@123"}' > /dev/null
curl -s -b "$JAR" http://localhost:8000/api/home > /dev/null
rm -f "$JAR"
echo "Take servers ready on :8000 and :5173."
