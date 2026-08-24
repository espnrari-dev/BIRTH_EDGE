#!/usr/bin/env python3
"""
Aegis-Tessera Production Kernel
"""
import os
import sqlite3
import hashlib
import json
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager

WORKSPACE = Path("./tessera_workspace")
DB_PATH = Path("agent_state.db")
STATE_FILE = Path("data/homeostasis_state.json")

@dataclass
class Thresholds:
    max_symbol_len: int = 24
    min_liquidity: float = 300.0
    max_z: float = 4.5
    min_entropy_symbol: float = 1.1

@dataclass
class ControllerState:
    thresholds: Thresholds
    last_entropy: float = 0.0
    last_kl: float = 0.0
    integrity: float = 1.0
    mode: str = "nominal"

def init_production_architecture():
    # Self-heal: nuke corrupted DB from previous broken runs
    if DB_PATH.exists():
        DB_PATH.unlink()
    WORKSPACE.mkdir(exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE birth_edge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_symbol TEXT NOT NULL,
            contract_address TEXT NOT NULL,
            liquidity REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER,
            state_hash TEXT,
            action_taken TEXT,
            timestamp INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE cognition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            heuristic_weights TEXT NOT NULL,
            mode TEXT,
            timestamp INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@contextmanager
def acquire_atomic_lock(db_path: str):
    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
    try:
        yield conn.cursor()
    finally:
        conn.commit()
        conn.close()

def audit_environment() -> dict:
    files = list(WORKSPACE.glob("*.dat"))
    return {
        "file_count": len(files),
        "total_size_bytes": sum(f.stat().st_size for f in files),
        "file_manifest": sorted([f.name for f in files]),
        "read_time": time.time()
    }

def update_homeostasis(file_count: int) -> ControllerState:
    entropy = float(file_count * 0.5)
    kl = 0.05 * file_count
    integrity = max(0.1, 1.0 - (file_count * 0.08))
    mode = "nominal"
    th = Thresholds()
    if entropy > 4.4 or file_count > 8:
        mode = "tight"
        th = Thresholds(max_symbol_len=18, min_liquidity=600.0, max_z=3.2, min_entropy_symbol=1.4)
    elif entropy < 2.0 and file_count < 2:
        mode = "relaxed"
        th = Thresholds(max_symbol_len=28, min_liquidity=200.0, max_z=5.0, min_entropy_symbol=0.9)
    state = ControllerState(thresholds=th, last_entropy=entropy, last_kl=kl, integrity=integrity, mode=mode)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))
    return state

def generate_atomic_snapshot(env_state: dict, controller_state: ControllerState) -> dict:
    snapshot = {"environment": env_state, "homeostasis": asdict(controller_state)}
    with acquire_atomic_lock(str(DB_PATH)) as cursor:
        cursor.execute("SELECT COUNT(*) FROM birth_edge")
        snapshot["tripartite_row_count"] = cursor.fetchone()[0]
    s = json.dumps(snapshot, sort_keys=True)
    h = hashlib.sha256(s.encode('utf-8')).hexdigest()
    snapshot["ATOMIC_HASH"] = h
    snapshot["DETERMINISTIC_SEED"] = int(h[:8], 16)
    return snapshot

def run_production_kernel(max_cycles=6):
    print("=== AEGIS-TESSERA PRODUCTION KERNEL ONLINE ===")
    init_production_architecture()
    for cycle in range(1, max_cycles + 1):
        env_state = audit_environment()
        ctrl_state = update_homeostasis(env_state["file_count"])
        snapshot = generate_atomic_snapshot(env_state, ctrl_state)
        state_hash = snapshot["ATOMIC_HASH"]
        seed_int = snapshot["DETERMINISTIC_SEED"]
        action_code = seed_int % 3
        if env_state["file_count"] == 0:
            action = "SPAWN_ENTROPY"
        elif ctrl_state.mode == "tight" or env_state["file_count"] > 7:
            action = "PURGE_ENTROPY"
        elif action_code == 0:
            action = "OPTIMIZE_STATE"
        elif action_code == 1:
            action = "SPAWN_ENTROPY"
        else:
            action = "STANDBY"
        if action == "SPAWN_ENTROPY":
            (WORKSPACE / f"node_{uuid.uuid4().hex[:6]}.dat").write_text("AEGIS_DATA_PAYLOAD" * 512)
        elif action == "OPTIMIZE_STATE":
            files = sorted(WORKSPACE.glob("*.dat"), key=os.path.getmtime)
            if files: files[0].unlink()
        elif action == "PURGE_ENTROPY":
            for f in WORKSPACE.glob("*.dat"): f.unlink()
        with acquire_atomic_lock(str(DB_PATH)) as cursor:
            cursor.execute("INSERT INTO birth_edge (token_symbol, contract_address, liquidity, timestamp) VALUES (?,?,?,?)",
                           ("SYS_NODE", f"0x{state_hash[:10]}", float(env_state["file_count"] * 150), int(time.time())))
            cursor.execute("INSERT INTO cognition (heuristic_weights, mode, timestamp) VALUES (?,?,?)",
                           (json.dumps(asdict(ctrl_state.thresholds)), ctrl_state.mode, int(time.time())))
            cursor.execute("INSERT INTO learning (cycle_id, state_hash, action_taken, timestamp) VALUES (?,?,?,?)",
                           (cycle, state_hash, action, int(time.time())))
        print(f"[CYCLE {cycle:02d}] Mode: {ctrl_state.mode.upper():<8} | Files: {env_state['file_count']} | Integrity: {ctrl_state.integrity:.2f}")
        print(f" Hash: {state_hash[:16]}...")
        print(f" Action: {action}\n")
        time.sleep(1)
    print("=== PRODUCTION KERNEL OFFLINE ===")

if __name__ == "__main__":
    run_production_kernel()
