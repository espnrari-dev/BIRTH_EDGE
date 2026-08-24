#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import json
import time
import uuid
from pathlib import Path

# --- SYSTEM CONFIG ---
WORKSPACE = Path("./tessera_workspace")
DB_PATH = Path("./tessera_ledger.db")

def init_system():
    """Bootstraps the physical environment and the immutable ledger."""
    WORKSPACE.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS state_ledger (
            cycle INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            file_count INTEGER,
            directory_size INTEGER,
            state_hash TEXT,
            deterministic_action TEXT
        )
    """)
    conn.commit()
    conn.close()

def audit_environment() -> dict:
    """Reads the exact physical state of the filesystem."""
    files = list(WORKSPACE.glob("*.dat"))
    file_count = len(files)
    total_size = sum(f.stat().st_size for f in files)
    
    # We include the names of the files to ensure extreme cryptographic sensitivity
    file_names = sorted([f.name for f in files]) 
    
    return {
        "file_count": file_count,
        "total_size_bytes": total_size,
        "file_manifest": file_names,
        "read_time": time.time()
    }

def execute_deterministic_loop(max_cycles=5):
    """The autonomous emergent loop."""
    print("=== TESSERA NODE ONLINE ===")
    print("Tracking environment entropy and enforcing state equilibrium...\n")
    
    for cycle in range(1, max_cycles + 1):
        # 1. AUDIT
        env_state = audit_environment()
        
        # 2. LOCK (Hash the state)
        state_string = json.dumps(env_state, sort_keys=True)
        state_hash = hashlib.sha256(state_string.encode('utf-8')).hexdigest()
        
        # 3. REASON (Derive strict action from the hash)
        # We take the first 8 characters of the hash, turn it into an integer, and use modulo arithmetic.
        seed_int = int(state_hash[:8], 16)
        
        # Action matrix based strictly on the deterministic seed
        action_code = seed_int % 3 
        
        if env_state["file_count"] == 0:
            action = "SPAWN" # Forced override if empty
        elif env_state["file_count"] > 10:
            action = "PURGE_ALL" # Forced homeostasis if overloaded
        elif action_code == 0:
            action = "OPTIMIZE" # Remove oldest file
        elif action_code == 1:
            action = "SPAWN" # Add new file
        else:
            action = "STANDBY" # Do nothing
            
        # 4. ACT
        if action == "SPAWN":
            # Generate a junk file to increase entropy
            new_file = WORKSPACE / f"entropy_{uuid.uuid4().hex[:6]}.dat"
            new_file.write_text("01010101" * 1024) 
        elif action == "OPTIMIZE":
            # Find oldest file and delete it
            files = sorted(WORKSPACE.glob("*.dat"), key=os.path.getmtime)
            if files: files[0].unlink()
        elif action == "PURGE_ALL":
            for f in WORKSPACE.glob("*.dat"): f.unlink()
            
        # 5. LOG (Write to immutable ledger)
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO state_ledger (timestamp, file_count, directory_size, state_hash, deterministic_action) VALUES (?, ?, ?, ?, ?)",
            (time.time(), env_state["file_count"], env_state["total_size_bytes"], state_hash, action)
        )
        conn.commit()
        conn.close()
        
        # 6. REPORT
        print(f"[CYCLE {cycle:02d}] Bloat: {env_state['file_count']} files | Size: {env_state['total_size_bytes']}b")
        print(f"            Hash:   {state_hash[:16]}...")
        print(f"            Action: {action}\n")
        
        time.sleep(1) # Emergent pacing

if __name__ == "__main__":
    init_system()
    execute_deterministic_loop(max_cycles=8)
    print("=== TESSERA NODE OFFLINE ===")
    print("Run 'sqlite3 tessera_ledger.db \"SELECT * FROM state_ledger;\"' to verify the immutable timeline.")
