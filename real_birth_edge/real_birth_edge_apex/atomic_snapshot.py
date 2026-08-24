#!/usr/bin/env python3
import sqlite3
import json
import hashlib
import pathlib
from typing import Dict, Any
from contextlib import contextmanager

STATE_FILE = pathlib.Path("data/homeostasis_state.json")
DB_PATH = "agent_state.db"

@contextmanager
def acquire_atomic_lock(db_path: str):
    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
    try:
        yield conn.cursor()
    finally:
        conn.commit()
        conn.close()

def generate_atomic_snapshot() -> Dict[str, Any]:
    snapshot = {}
    
    # 1. Homeostatic State
    if STATE_FILE.exists():
        snapshot["homeostasis"] = json.loads(STATE_FILE.read_text())
    else:
        snapshot["homeostasis"] = {"mode": "nominal", "error": "file_missing"}

    # 2. Tripartite State
    with acquire_atomic_lock(DB_PATH) as cursor:
        cursor.execute("SELECT * FROM birth_edge ORDER BY id DESC LIMIT 1")
        birth_edge_row = cursor.fetchone()
        snapshot["birth_edge_latest"] = birth_edge_row if birth_edge_row else "NULL"
        
        cursor.execute("SELECT heuristic_weights, heal_cycles FROM cognition ORDER BY id DESC LIMIT 1")
        cognition_row = cursor.fetchone()
        snapshot["cognition_latest"] = cognition_row if cognition_row else "NULL"

    # 3. Hash Generation
    snapshot_string = json.dumps(snapshot, sort_keys=True)
    snapshot_hash = hashlib.sha256(snapshot_string.encode('utf-8')).hexdigest()
    
    snapshot["ATOMIC_HASH"] = snapshot_hash
    snapshot["DETERMINISTIC_LLM_SEED"] = int(snapshot_hash[:8], 16)

    return snapshot

if __name__ == "__main__":
    print("[SYSTEM] Initiating Atomic Snapshot...")
    final_state = generate_atomic_snapshot()
    
    print("\n--- [ATOMIC SNAPSHOT LOCKED] ---")
    print(f"MODE:  {final_state['homeostasis'].get('mode', 'UNKNOWN')}")
    print(f"HASH:  {final_state['ATOMIC_HASH']}")
    print(f"SEED:  {final_state['DETERMINISTIC_LLM_SEED']}")
    print("--------------------------------\n")
