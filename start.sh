#!/bin/bash
# start.sh -- Render startup script
# Kills run_agent cleanly when gunicorn stops to prevent duplicate key on redeploy.

set -e
cd croo_backend

echo "[start.sh] Starting LedgerOps..."

agent_loop() {
    echo "[start.sh] Waiting 15s for previous WebSocket to expire..."
    sleep 15
    while true; do
        echo "[start.sh] Starting run_agent..."
        timeout 7200 python manage.py run_agent || true
        echo "[start.sh] run_agent exited, retrying in 15s..."
        sleep 15
    done
}

agent_loop &
AGENT_PID=$!
echo "[start.sh] Agent loop PID: $AGENT_PID"

cleanup() {
    echo "[start.sh] Shutdown -- killing agent (PID $AGENT_PID)..."
    kill "$AGENT_PID" 2>/dev/null || true
    wait "$AGENT_PID" 2>/dev/null || true
    echo "[start.sh] Done."
}
trap cleanup EXIT TERM INT

echo "[start.sh] Starting gunicorn..."
gunicorn --bind "0.0.0.0:$PORT" --chdir croo_backend croo_backend.wsgi:application
