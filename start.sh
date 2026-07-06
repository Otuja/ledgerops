#!/bin/bash
# start.sh — Render startup script
# Ensures run_agent is always killed cleanly when gunicorn stops,
# preventing the "duplicate key" WebSocket error on redeploy.

set -e

cd croo_backend

echo "[start.sh] Starting LedgerOps..."

# ── Background agent loop ─────────────────────────────────────────────────
agent_loop() {
    echo "[start.sh] Agent: waiting 15s for old WebSocket to expire..."
    sleep 15
    while true; do
        echo "[start.sh] Agent: starting run_agent..."
        timeout 7200 python manage.py run_agent || true
        echo "[start.sh] Agent: exited, retrying in 15s..."
        sleep 15
    done
}

agent_loop &
AGENT_PID=$!
echo "[start.sh] Agent loop PID: $AGENT_PID"

# ── Cleanup: kill agent when this script exits for any reason ────────────
cleanup() {
    echo "[start.sh] Shutting down — killing agent loop (PID $AGENT_PID)..."
    kill "$AGENT_PID" 2>/dev/null || true
    wait "$AGENT_PID" 2>/dev/null || true
    echo "[start.sh] Agent loop stopped cleanly."
}
trap cleanup EXIT TERM INT

# ── Gunicorn in foreground ────────────────────────────────────────────────
echo "[start.sh] Starting gunicorn..."
gunicorn --bind "0.0.0.0:$PORT" --chdir croo_backend croo_backend.wsgi:application

# When gunicorn exits (TERM from Render), the shell continues here,
# runs cleanup() via the EXIT trap, which kills the agent loop.
