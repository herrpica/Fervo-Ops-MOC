#!/usr/bin/env bash
# Fervo OMOC — local run script (macOS / Linux)
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
echo "Installing dependencies..."
./.venv/bin/python -m pip install --upgrade pip --quiet
./.venv/bin/python -m pip install -r requirements.txt --quiet

PORT=8000
echo "Starting OMOC app at http://127.0.0.1:$PORT  (Ctrl+C to stop)"
( sleep 1 && (open "http://127.0.0.1:$PORT" 2>/dev/null || xdg-open "http://127.0.0.1:$PORT" 2>/dev/null) ) &
./.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port $PORT
