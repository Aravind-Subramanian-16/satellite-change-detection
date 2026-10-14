#!/usr/bin/env bash
# End-to-end smoke test. The staged UI text is an approximation; this script tests real HTTP work.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-./venv/bin/python}"
PORT="${PORT:-8011}"
"$PYTHON" -m pytest -q
"$PYTHON" -m uvicorn app:app --host 127.0.0.1 --port "$PORT" > /tmp/satellite-change-verify.log 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT
for _ in {1..30}; do curl -fsS "http://127.0.0.1:$PORT/health" && break || sleep 1; done
curl -fsS "http://127.0.0.1:$PORT/health" > /tmp/health.json
curl -fsS -X POST "http://127.0.0.1:$PORT/predict" -F "image_a=@dataset/test/A/test_100_0_0.png" -F "image_b=@dataset/test/B/test_100_0_256.png" > /tmp/predict.json
curl -fsS -X POST "http://127.0.0.1:$PORT/report" -H 'content-type: application/json' --data-binary @<("$PYTHON" -c 'import json; print(json.dumps({"result": json.load(open("/tmp/predict.json"))}))') -o /tmp/change-report.pdf
test -s /tmp/change-report.pdf
echo "verify: health, prediction, PDF and pytest passed"
