import hashlib, json, os, datetime
LOG_DIR="logs"
os.makedirs(LOG_DIR, exist_ok=True)
CHAIN=f"{LOG_DIR}/hash_chain.jsonl"

def log_hash(tag, data):
    if not isinstance(data, str):
        data = json.dumps(data, sort_keys=True, default=str)
    h = hashlib.sha256(data.encode()).hexdigest()
    entry = {"ts": datetime.datetime.now().isoformat(), "tag": tag, "sha256": h, "data_preview": data[:500]}
    with open(CHAIN, "a") as f:
        f.write(json.dumps(entry)+"\n")
    print(f"[HASH] {tag} {h[:16]}")
    return h
