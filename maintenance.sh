#!/data/data/com.termux/files/usr/bin/bash
cd ~/BIRTH_EDGE
while true; do
    sqlite3 data/birth_edge.db "PRAGMA quick_check;" >> logs/maintenance.log 2>&1
    sqlite3 data/learning.db   "PRAGMA quick_check;" >> logs/maintenance.log 2>&1
    sqlite3 data/cognition.db  "PRAGMA quick_check;" >> logs/maintenance.log 2>&1
    sqlite3 data/birth_edge.db "VACUUM;" >> logs/maintenance.log 2>&1
    sqlite3 data/learning.db   "VACUUM;" >> logs/maintenance.log 2>&1
    sqlite3 data/cognition.db  "VACUUM;" >> logs/maintenance.log 2>&1
    sleep 21600
done
