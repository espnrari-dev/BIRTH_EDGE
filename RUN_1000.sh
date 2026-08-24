#!/bin/bash
set -e
cd ~/BIRTH_EDGE

# 1. WATCH master - subsecond chain (KATANA/WHALE/beacon) - 1 instance only
nohup bash ~/SHOGUN_OS/WATCH.sh > data/watch.log 2>&1 &
echo "WATCH master PID $!"

# 2. BIRTH fast loop ONLY - no IPO block (IPO runs separate)
nohup python3 -u -c "
import asyncio
from main import birth_filtered_loop
asyncio.run(birth_filtered_loop())
" > data/birth_1000.log 2>&1 &
echo "BIRTH 1000% PID $!"

# 3. LEARNING updater - pumps/rugs every 5m
nohup bash -c 'while true; do python3 -c "import learning; learning.update_outcomes(1)" ; sleep 300; done' > data/learning_loop.log 2>&1 &
echo "LEARNING loop PID $!"

# 4. NOMINAL healer every 15m
nohup bash -c 'while true; do python3 nominal.py >> data/nominal.log 2>&1; sleep 900; done' > /dev/null 2>&1 &
echo "NOMINAL loop PID $!"

ps | grep -E "WATCH|main|learning|nominal"
