#!/bin/bash
pkill -f WATCH.sh; pkill -f birth_filtered; pkill -f learning_loop; sleep 2
cd ~/BIRTH_EDGE
# 1. Dex watcher subsecond
nohup bash ~/SHOGUN_OS/WATCH.sh > data/watch.log 2>&1 &
# 2. Birth fast 2s poll (SCORE_MIN_BUY=76 already set)
nohup python3 -u -c "import asyncio; from main import birth_filtered_loop; asyncio.run(birth_filtered_loop())" > data/birth_1000.log 2>&1 &
# 3. Outcome labeler every 5m
nohup bash -c 'while true; do python3 -c "import learning; learning.update_outcomes(1)" >> data/learning_loop.log 2>&1; sleep 300; done' &
echo "SCHOLARLY 1000% RUNNING"
ps aux | grep -E "WATCH|birth|learning" | grep -v grep
