#!/usr/bin/env bash
# BIRTH_EDGE persistent background runner with auto-restart
set -u

cd "$(dirname "$0")"

# Use termux-wake-lock if available
if command -v termux-wake-lock >/dev/null 2>&1; then
    echo "Acquiring wake lock..."
    termux-wake-lock
fi

mkdir -p logs

# Find tmux, else use nohup+loop
if command -v tmux >/dev/null 2>&1; then
    echo "Using tmux session 'birtheedge'"
    if tmux has-session -t birtheedge 2>/dev/null; then
        echo "Session already exists; attach with: tmux attach -t birtheedge"
        exit 0
    fi
    tmux new-session -d -s birtheedge "python -u main.py 2>&1 | tee logs/run.log"
    echo "Started BIRTH_EDGE in tmux session 'birtheedge'."
    echo "To attach: tmux attach -t birtheedge"
    echo "To detach: Ctrl+B then D"
    exit 0
fi

# Fallback: nohup with restart loop
echo "tmux not found, using nohup + watchdog loop."

run_process() {
    nohup python -u main.py >> logs/run.log 2>&1 &
    echo $! > logs/birtheedge.pid
    echo "Started BIRTH_EDGE with PID $(cat logs/birtheedge.pid)"
}

run_process

# Watchdog loop
while true; do
    pid=$(cat logs/birtheedge.pid 2>/dev/null || echo "")
    if [ -z "$pid" ] || ! kill -0 "$pid" 2>/dev/null; then
        echo "$(date) - BIRTH_EDGE died, restarting..."
        run_process
    fi
    sleep 30
done
