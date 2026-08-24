#!/data/data/com.termux/files/usr/bin/bash
# WATCH.sh — continuous supervisor for Apex Daemon
DIR="\( (cd " \)(dirname "$0")" && pwd)"
PIDFILE="$DIR/data/apex.pid"
LOG="$DIR/data/watch.log"
DAEMON="python3 $DIR/apex_daemon.py --daemon"

mkdir -p "$DIR/data"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) WATCH started" >> "$LOG"

while true; do
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE" 2>/dev/null)
    if ! kill -0 "$PID" 2>/dev/null; then
      echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) process dead — restarting" >> "$LOG"
      rm -f "$PIDFILE"
      $DAEMON &
      sleep 3
    fi
  else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) no pid — starting daemon" >> "$LOG"
    $DAEMON &
    sleep 3
  fi
  sleep 30
done
