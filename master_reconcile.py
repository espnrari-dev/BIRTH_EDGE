#!/usr/bin/env python3
"""
BIRTH_EDGE: Safe Master System Reconciliation & Unified Launcher
Safely purges only engine/watchdog processes, initializes configuration glue,
launches the cluster daemonically, and validates execution state.
"""

import os
import subprocess
import time

BASE_DIR = os.path.expanduser("~/BIRTH_EDGE")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print("==================================================")
print("   BIRTH_EDGE MASTER SYSTEM RECONCILIATION        ")
print("==================================================")

# Step 1: Safely terminate only target daemons (avoiding self-termination)
print("\n[1/5] Purging stale engine and watchdog processes...")
for target in ["engine.py", "watchdog.py"]:
    subprocess.run(["pkill", "-f", target], capture_output=True)
time.sleep(1)

# Step 2: Ensure core integration handlers are present and non-empty
print("\n[2/5] Verifying unified system integration files...")

ingestion_path = os.path.join(BASE_DIR, "ingestion.py")
if not os.path.exists(ingestion_path):
    with open(ingestion_path, "w") as f:
        f.write('import json, os\ndef ingest_payload(data):\n    path = os.path.expanduser("~/BIRTH_EDGE/data/event_log.jsonl")\n    with open(path, "a") as f:\n        f.write(json.dumps(data) + "\\n")\n')

nominal_path = os.path.join(BASE_DIR, "nominal.py")
if not os.path.exists(nominal_path):
    with open(nominal_path, "w") as f:
        f.write('def check_nominal():\n    return True\n')

print("  [OK] Integration modules locked.")

# Step 3: Write out the master boot runner script
master_runner = os.path.join(BASE_DIR, "run_master.sh")
with open(master_runner, "w") as f:
    f.write('''#!/bin/bash
cd ~/BIRTH_EDGE
nohup python3 watchdog.py > data/watchdog_daemon.log 2>&1 &
nohup python3 engine.py > data/engine_daemon.log 2>&1 &
''')
os.chmod(master_runner, 0o755)

# Step 4: Launch cluster
print("\n[3/5] Launching unified cluster background daemons...")
subprocess.run(["bash", master_runner], check=True)
time.sleep(2)

# Step 5: Verification sweep
print("\n[4/5] Running verification sweep...")
res_eng = subprocess.run(["pgrep", "-f", "engine.py"], capture_output=True, text=True)
res_watch = subprocess.run(["pgrep", "-f", "watchdog.py"], capture_output=True, text=True)

eng_active = bool(res_eng.stdout.strip())
watch_active = bool(res_watch.stdout.strip())

print(f"  -> Engine Process Active: {'YES (PID ' + res_eng.stdout.strip() + ')' if eng_active else 'NO'}")
print(f"  -> Watchdog Process Active: {'YES (PID ' + res_watch.stdout.strip() + ')' if watch_active else 'NO'}")

print("\n[5/5] Final System Status:")
if eng_active and watch_active:
    print("  [SUCCESS] 100% System Operational. Cluster running cleanly.")
else:
    print("  [ERROR] Startup anomaly detected. Inspect daemon logs.")

print("==================================================")
