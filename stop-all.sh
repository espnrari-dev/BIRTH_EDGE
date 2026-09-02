#!/bin/bash
cd ~/BIRTH_EDGE
if [ -f logs/app.pid ]; then
  kill $(cat logs/app.pid) 2>/dev/null
fi
pkill -f "python3 main.py" 2>/dev/null
rm -f logs/*.pid
echo "BIRTH_EDGE stopped"
