#!/usr/bin/env bash
# Start the Cisco Phone Controller app (development mode)
# This runs with the local browser. For the single-window experience, use main.py.
set -e

cd "$(dirname "$0")"

if command -v uv &>/dev/null; then
    uv run python main.py
else
    python3 main.py
fi