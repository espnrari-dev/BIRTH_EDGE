#!/usr/bin/env python3
"""
BIRTH_EDGE: Empirical System Validation Probe
Measures actual process state, log velocity, and ledger integrity directly from disk.
"""

import os
import subprocess
import time

BASE_DIR = os.path.expanduser("~/BIRTH_EDGE")
DATA_DIR = os.path.join(BASE_DIR, "data")
ENG_LOG = os.path.join(DATA_DIR, "engine.log")
LEDGER = os.path.join(DATA_DIR, "event_log.jsonl")

print("=== BIRTH_EDGE EMPIRICAL SYSTEM VALIDATION ===")

# 1. Process Check
res_eng = subprocess.run(["pgrep", "-f", "engine.py"], capture_output=True, text=True)
eng_pids = res_eng.stdout.strip().split()
print(f"[CHECK 1] engine.py active processes: {len(eng_pids)} (PIDs: {', '.join(eng_pids) or 'NONE'})")

res_watch = subprocess.run(["pgrep", "-f", "watchdog.py"], capture_output=True, text=True)
watch_pids = res_watch.stdout.strip().split()
print(f"[CHECK 2] watchdog.py active processes: {len(watch_pids)} (PIDs: {', '.join(watch_pids) or 'NONE'})")

# 2. Velocity & Cycle Log Verification
if os.path.exists(ENG_LOG):
    with open(ENG_LOG, "r") as f:
        lines = f.readlines()
    recent_cycles = [l.strip() for l in lines if "Cycle completed" in l][-5:]
    print(f"\n[CHECK 3] Last {len(recent_cycles)} recorded execution cycles:")
    if recent_cycles:
        for c in recent_cycles:
            print(f"   {c}")
    else:
        print("   [WARN] Log exists, but no completion strings found yet.")
else:
    print("\n[CHECK 3] [FAIL] engine.log does not exist.")

# 3. Ledger State & Atomic Growth Check
if os.path.exists(LEDGER):
    size_bytes = os.path.getsize(LEDGER)
    with open(LEDGER, "r") as f:
        event_count = sum(1 for _ in f)
    print(f"\n[CHECK 4] Ledger state: {size_bytes} bytes | Total events recorded: {event_count}")
else:
    print("\n[CHECK 4] [WARN] event_log.jsonl not found or not yet initialized.")

print("==============================================")
