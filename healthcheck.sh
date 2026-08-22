#!/data/data/com.termux/files/usr/bin/bash
cd ~/BIRTH_EDGE

echo "=== TMUX ==="
tmux ls 2>/dev/null || echo "NO TMUX SESSION"

echo "=== DB INTEGRITY ==="
for db in data/birth_edge.db data/learning.db data/cognition.db; do
  if [ -f "$db" ]; then
    echo "--- $db ---"
    sqlite3 "$db" "PRAGMA quick_check;" 2>&1 | head -1
    case "$db" in
      data/birth_edge.db)
        sqlite3 "$db" "SELECT 'tokens: '||COUNT(*) FROM tokens; SELECT 'ipos: '||COUNT(*) FROM ipos;"
        ;;
      data/learning.db)
        sqlite3 "$db" "SELECT 'learning_results: '||COUNT(*) FROM learning_results;"
        ;;
      data/cognition.db)
        sqlite3 "$db" "SELECT 'events: '||COUNT(*) FROM events;"
        ;;
    esac
  else
    echo "$db MISSING"
  fi
done

echo "=== LAST LOG ==="
tail -n 10 logs/main.log 2>/dev/null || echo "no main.log"

echo "=== DISK ==="
df -h ~ | tail -1
