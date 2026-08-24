#!/usr/bin/env python3
"""
BIRTH_EDGE: Autonomous Watchdog & Diagnostic Loop
Zero-Footprint Concurrency / Edge-Primitive Engineering
"""

import os
import time
import subprocess

BASE_DIR = os.path.expanduser("~/BIRTH_EDGE")
DATA_DIR = os.path.join(BASE_DIR, "data")
ENGINE_LOG = os.path.join(DATA_DIR, "engine.log")
DIAG_LOG = os.path.join(DATA_DIR, "diag.log")

def log_diag(msg):
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} {msg}"
    print(line, flush=True)
    try:
        with open(DIAG_LOG, "a") as f:
            f.write(line + "\n")
    except:
        pass

def check_engine():
    res = subprocess.run(["pgrep", "-f", "engine.py"], capture_output=True, text=True)
    if not res.stdout.strip():
        log_diag("[DIAG] ENGINE_DEAD: restarting engine.py")
        subprocess.run(["nohup", "python3", "-u", os.path.join(BASE_DIR, "engine.py"), ">", ENGINE_LOG, "2>&1", "&"])
        return False
    return True

def check_stale_logs():
    if os.path.exists(ENGINE_LOG):
        mtime = os.path.getmtime(ENGINE_LOG)
        if time.time() - mtime > 60:
            log_diag("[DIAG] ENGINE_STALE: log flatlined > 60s, restarting")
            subprocess.run(["pkill", "-9", "-f", "engine.py"])
            time.sleep(1)
            subprocess.run(["nohup", "python3", "-u", os.path.join(BASE_DIR, "engine.py"), ">", ENGINE_LOG, "2>&1", "&"])
            return False
    return True

if __name__ == "__main__":
    log_diag("=== WATCHDOG V2 ACTIVE ===")
    while True:
        try:
            alive = check_engine()
            if alive:
                stale = check_stale_logs()
                if stale:
                    log_diag("[OK] nominal")
        except Exception as e:
            log_diag(f"[DIAG ERR] {e}")
        time.sleep(30)
