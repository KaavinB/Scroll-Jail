#!/usr/bin/env bash
# Scroll Jail — single script to launch all 3 processes.
# Usage: ./start.sh
# Ctrl+C stops everything.

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin/python"

if [ ! -f "$VENV" ]; then
    echo "Setting up venv..."
    python3 -m venv "$DIR/.venv"
    "$VENV" -m pip install -r "$DIR/requirements.txt" -q
fi

cleanup() {
    echo ""
    echo "Shutting down Scroll Jail..."
    kill $PID_WATCHER $PID_WEB 2>/dev/null
    wait $PID_WATCHER $PID_WEB 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

echo "=== Scroll Jail ==="
echo ""

# 1) Watcher (polls Chrome, writes state.json)
"$VENV" "$DIR/watcher.py" &
PID_WATCHER=$!
echo "[started] watcher.py  (pid $PID_WATCHER)"

# 2) Web UI (Flask dashboard)
"$VENV" "$DIR/web.py" &
PID_WEB=$!
echo "[started] web.py      (pid $PID_WEB) → http://localhost:5050"

echo ""
echo "MCP server (server.py) runs via Claude — no need to start it manually."
echo "Press Ctrl+C to stop everything."
echo ""

wait
