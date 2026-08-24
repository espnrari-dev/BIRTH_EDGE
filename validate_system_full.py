#!/usr/bin/env python3
"""
BIRTH_EDGE: Comprehensive Full-System Empirical Validator
Probes every active process, log velocity, and file state across the entire architecture.
"""

import os
import subprocess

BASE_DIR = os.path.expanduser("~/BIRTH_EDGE")
DATA_DIR = os.path.join(BASE_DIR, "data")
HOME_DIR = os.path.expanduser("~")
PRAO_DIR = os.path.join(HOME_DIR, "T_PRAO_L4")

print("==================================================")
print("     BIRTH_EDGE FULL-SYSTEM EMPIRICAL VALIDATOR   ")
print("==================================================")

# 1. Full Process Topology Check
targets = [
    ("Watchdog", "watchdog.py"),
    ("Engine", "engine.py"),
    ("Capture Kernel", "capture.py"),
    ("Off-Grid Kernel V3", "OFFGRID_KERNEL_V3.py"),
    ("Price Feed", "PRICE_FEED.py"),
    ("Diagnostics Daemon", "DIAGNOSE.py"),
    ("Auto-Heal Daemon", "AUTO_HEAL.py")
]

print("\n--- 1. PROCESS TOPOLOGY & DAEMON HEALTH ---")
for name, script in targets:
    res = subprocess.run(["pgrep", "-f", script], capture_output=True, text=True)
    pids = res.stdout.strip().split()
    status = f"ACTIVE (PIDs: {', '.join(pids)})" if pids else "DEAD / INACTIVE"
    print(f"  [{'OK' if pids else 'WARN'}] {name} ({script}): {status}")

# 2. Log Velocity & Trailing State Check
logs = [
    ("Engine Log", os.path.join(DATA_DIR, "engine.log")),
    ("Watchdog Log", os.path.join(DATA_DIR, "watchdog.log")),
    ("Diagnostic Log", os.path.join(DATA_DIR, "diag.log")),
]

print("\n--- 2. RUNTIME LOG VELOCITY & TAIL CHECK ---")
for name, path in logs:
    if os.path.exists(path):
        size = os.path.getsize(path)
        try:
            with open(path, "r") as f:
                last_line = f.readlines()[-1].strip()
        except IndexError:
            last_line = "[EMPTY LOG]"
        print(f"  [OK] {name} ({size} bytes):")
        print(f"       -> {last_line}")
    else:
        print(f"  [WARN] {name} not found at {path}")

# 3. Core Ledger & Data State Check
ledgers = [
    ("Event Ledger", os.path.join(DATA_DIR, "event_log.jsonl")),
    ("Treasury Ledger", os.path.join(DATA_DIR, "treasury.jsonl")),
]

print("\n--- 3. DATA LEDGER INTEGRITY ---")
for name, path in ledgers:
    if os.path.exists(path):
        size = os.path.getsize(path)
        with open(path, "r") as f:
            count = sum(1 for _ in f)
        print(f"  [OK] {name}: {size} bytes | {count} records indexed")
    else:
        print(f"  [WARN] {name} not found or not initialized.")

print("==================================================")
