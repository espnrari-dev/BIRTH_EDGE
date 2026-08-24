#!/bin/bash
cd ~/BIRTH_EDGE
nohup python3 watchdog.py > data/watchdog_daemon.log 2>&1 &
nohup python3 engine.py > data/engine_daemon.log 2>&1 &
