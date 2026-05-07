#!/usr/bin/env bash
#
# file-watcher.sh — Background file watcher that regenerates maps on change
# Usage: ./.agent/scripts/file-watcher.sh start|stop|status
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PIDFILE="${REPO_ROOT}/.agent/.watcher.pid"
LOGFILE="${REPO_ROOT}/.agent/.watcher.log"

start_watcher() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Watcher already running (PID: $(cat "$PIDFILE"))"
    return 0
  fi
  
  echo "Starting file watcher..."
  nohup bash -c "
    cd '$REPO_ROOT'
    while true; do
      inotifywait -e modify,create,delete -r \
        --exclude '(node_modules|.git|__pycache__|.next|dist|data|briefs|runs)' \
        pipeline/src web/src supabase/migrations sql/ workers/ docs/ .cursor/ .kimi/ \
        2>/dev/null | while read path action file; do
          if [[ '\$file' == *.py || '\$file' == *.ts || '\$file' == *.tsx || '\$file' == *.sql || '\$file' == *.md ]]; then
            echo \"[\\\"$(date -Iseconds)\\\"] Change detected: \\$path\\\$file (\\\$action)\" >> '$LOGFILE'
            '$REPO_ROOT/.agent/scripts/regenerate-maps.sh' watcher 2>>'$LOGFILE'
          fi
        done
      sleep 2
    done
  " > /dev/null 2>&1 &
  
  echo $! > "$PIDFILE"
  echo "Watcher started (PID: $!)"
  echo "Logs: $LOGFILE"
}

stop_watcher() {
  if [[ -f "$PIDFILE" ]]; then
    local pid=$(cat "$PIDFILE")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "Watcher stopped (PID: $pid)"
    else
      echo "Watcher not running"
    fi
    rm -f "$PIDFILE"
  else
    echo "Watcher not running"
  fi
}

status_watcher() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "Watcher running (PID: $(cat "$PIDFILE"))"
    echo "Last 5 log entries:"
    tail -n 5 "$LOGFILE" 2>/dev/null || echo "No logs yet"
  else
    echo "Watcher not running"
  fi
}

case "${1:-status}" in
  start) start_watcher ;;
  stop) stop_watcher ;;
  status) status_watcher ;;
  *) echo "Usage: $0 start|stop|status" ;;
esac
