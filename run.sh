#!/usr/bin/env bash
# Start the Cisco Phone Controller app
set -e

cd "$(dirname "$0")"

# Use uv if available, otherwise python3 -m uvicorn
if command -v uv &>/dev/null; then
    uv run uvicorn app:app --host 127.0.0.1 --port 8000 --reload
else
    python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
fi
