#!/data/data/com.termux/files/usr/bin/bash
set -e
cd ~/BIRTH_EDGE

mkdir -p backups
[ -f data/birth_edge.db ] && cp data/birth_edge.db backups/birth_edge_$(date +%Y%m%d_%H%M%S).db
[ -f data/learning.db ]   && cp data/learning.db   backups/learning_$(date +%Y%m%d_%H%M%S).db
[ -f data/cognition.db ]  && cp data/cognition.db  backups/cognition_$(date +%Y%m%d_%H%M%S).db

ls -1t backups/birth_edge_*.db  | tail -n +21 | xargs -r rm -f
ls -1t backups/learning_*.db    | tail -n +21 | xargs -r rm -f
ls -1t backups/cognition_*.db   | tail -n +21 | xargs -r rm -f

tmux kill-session -t birtheedge 2>/dev/null || true

tmux new-session -d -s birtheedge "
while true; do
    echo \"[\$(date)] Starting main.py\"
    export PYTHONUNBUFFERED=1
    python3 main.py >> logs/main.log 2>&1
    echo \"[\$(date)] main.py exited, restarting in 5s\"
    sleep 5
done
"
echo "Supervisor started in tmux session 'birtheedge'"
