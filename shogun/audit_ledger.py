import hashlib, json, time, pathlib
LEDGER = pathlib.Path("data/ledger_chain.jsonl")

def hash_obj(o): return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()

def append(entry: dict):
    LEDGER.parent.mkdir(exist_ok=True)
    prev_hash = "GENESIS"
    if LEDGER.exists():
        try:
            last = LEDGER.read_text().strip().splitlines()[-1]
            prev_hash = json.loads(last)["curr_hash"]
        except: pass
    payload = {"ts": time.time(), "prev_hash": prev_hash, "entry": entry}
    curr_hash = hash_obj(payload)
    payload["curr_hash"] = curr_hash
    with LEDGER.open("a") as f:
        f.write(json.dumps(payload)+"\n")
    return curr_hash

def verify():
    if not LEDGER.exists(): return True, "empty"
    prev = "GENESIS"
    for line in LEDGER.read_text().splitlines():
        j=json.loads(line)
        if j["prev_hash"] != prev: return False, f"break at {j['curr_hash'][:8]}"
        check = hash_obj({"ts": j["ts"], "prev_hash": j["prev_hash"], "entry": j["entry"]})
        if check != j["curr_hash"]: return False, "hash mismatch"
        prev = j["curr_hash"]
    return True, f"chain ok len={prev[:8]}"
