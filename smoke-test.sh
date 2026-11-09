#!/bin/bash
# End-to-end smoke test: backend (from project root) + Vite dev server.
# Run from the doubtsahayak/ folder. Exits 0 only if the proxied API answers.
set -u
cd "$(dirname "$0")"
.venv/bin/uvicorn backend.app:app --port 8000 --app-dir . > /tmp/ds-backend.log 2>&1 &
BEPID=$!
npm run dev -- --port 5173 > /tmp/ds-frontend.log 2>&1 &
FEPID=$!
trap 'kill $BEPID $FEPID 2>/dev/null' EXIT
sleep 6
echo "--- page title check:"
curl -s http://localhost:5173/ | grep -o "<title>[^<]*</title>"
echo "--- proxied API (Hindi mean/median/mode):"
curl -s -X POST http://localhost:5173/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"Data 7, 3, 9, 3, 12, 5. Find mean, median, mode.","language":"Hindi","subject":"Probability & Stats"}' \
  | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print('mode:', d['mode'], '| grounded:', d['grounded']); print(d['answer'][:220])"
