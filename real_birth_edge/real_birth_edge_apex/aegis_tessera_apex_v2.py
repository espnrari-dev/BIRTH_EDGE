#!/usr/bin/env python3
"""
AEGIS-TESSERA APEX v2 - LIVE ORACLE EDITION
One phone = one oracle. Hash-chained, content-addressed, signed.
"""
import os, sqlite3, hashlib, json, time, uuid, math, random, base64
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from collections import Counter
from urllib.request import urlopen, Request

WORKSPACE = Path("./tessera_workspace")
DB_PATH = Path("agent_state.db")
STATE_FILE = Path("data/homeostasis_state.json")
PUBLIC_LEDGER = Path("data/public_ledger.jsonl")
KEY_PATH = Path("data/apex.key")
PUB_PATH = Path("data/apex.pub")
GENESIS_FILE = Path("data/GENESIS.txt")
PROOF_FILE = Path("data/GENESIS_PROOF.txt")

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    CRYPTO = True
except:
    CRYPTO = False

def shannon_entropy(s: str) -> float:
    if not s: return 0.0
    counts = Counter(s)
    total = len(s)
    return -sum((c/total) * math.log2(c/total) for c in counts.values())

def kl_divergence_uniform(sizes):
    if not sizes or len(sizes) < 2: return 0.0
    total = sum(sizes)
    if total == 0: return 0.0
    probs = [x/total for x in sizes]
    uniform = 1.0 / len(sizes)
    return max(0.0, sum(p * math.log2(p / uniform) for p in probs if p > 0))

def content_address(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(',',':'))
    return hashlib.sha256(canonical.encode()).hexdigest()

def load_or_create_identity():
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        priv_bytes = bytes.fromhex(KEY_PATH.read_text().strip())
    else:
        priv_bytes = os.urandom(32)
        KEY_PATH.write_text(priv_bytes.hex())
        os.chmod(KEY_PATH, 0o600)
        print(f"[IDENTITY] New oracle key generated: {KEY_PATH}")
    if CRYPTO:
        try:
            if PUB_PATH.exists():
                pub_hex = PUB_PATH.read_text().strip()
            else:
                priv_obj = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
                pub_bytes = priv_obj.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
                pub_hex = pub_bytes.hex()
                PUB_PATH.write_text(pub_hex)
            return priv_bytes, pub_hex
        except: pass
    pub_hex = hashlib.sha256(priv_bytes).hexdigest()[:64]
    if not PUB_PATH.exists(): PUB_PATH.write_text(pub_hex)
    return priv_bytes, pub_hex

def sign_message(priv_bytes: bytes, message: bytes) -> str:
    if CRYPTO:
        try:
            priv_obj = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
            return priv_obj.sign(message).hex()
        except: pass
    return hashlib.sha256(priv_bytes + message).hexdigest()

@dataclass
class Thresholds:
    max_symbol_len: int = 24
    min_liquidity: float = 300.0
    max_z: float = 4.5
    min_entropy_symbol: float = 1.1
    def evaluate(self, symbol: str, liquidity: float, z: float):
        ent = shannon_entropy(symbol)
        if len(symbol) > self.max_symbol_len: return False, f"len {len(symbol)}>{self.max_symbol_len}"
        if liquidity < self.min_liquidity: return False, f"liq {liquidity:.1f}<{self.min_liquidity}"
        if z > self.max_z: return False, f"z {z:.2f}>{self.max_z}"
        if ent < self.min_entropy_symbol: return False, f"ent {ent:.2f}<{self.min_entropy_symbol}"
        return True, f"PASS ent={ent:.2f}"

@dataclass
class ControllerState:
    thresholds: Thresholds
    last_entropy: float = 0.0
    last_kl: float = 0.0
    integrity: float = 1.0
    mode: str = "nominal"

def init_production_architecture():
    if DB_PATH.exists(): DB_PATH.unlink()
    WORKSPACE.mkdir(exist_ok=True)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if PUBLIC_LEDGER.exists(): PUBLIC_LEDGER.unlink()
    priv, pub = load_or_create_identity()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()
    cur.execute('''CREATE TABLE birth_edge (id INTEGER PRIMARY KEY AUTOINCREMENT, token_symbol TEXT NOT NULL, contract_address TEXT NOT NULL, liquidity REAL NOT NULL, symbol_entropy REAL NOT NULL, z_score REAL NOT NULL, integrity_at_birth REAL NOT NULL, timestamp INTEGER NOT NULL, source_hash TEXT NOT NULL, content_cid TEXT NOT NULL, metadata_json TEXT NOT NULL)''')
    cur.execute('''CREATE TABLE learning (id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER NOT NULL, prev_hash TEXT NOT NULL, state_hash TEXT NOT NULL, action_taken TEXT NOT NULL, merkle_root TEXT NOT NULL, signature TEXT NOT NULL, pubkey TEXT NOT NULL, timestamp INTEGER NOT NULL)''')
    cur.execute('''CREATE TABLE cognition (id INTEGER PRIMARY KEY AUTOINCREMENT, heuristic_weights TEXT NOT NULL, mode TEXT NOT NULL, entropy REAL NOT NULL, kl REAL NOT NULL, integrity REAL NOT NULL, timestamp INTEGER NOT NULL)''')
    conn.commit(); conn.close()
    return priv, pub

@contextmanager
def acquire_atomic_lock(db_path: str):
    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE", timeout=10.0)
    try: yield conn.cursor()
    finally: conn.commit(); conn.close()

def audit_environment():
    files = list(WORKSPACE.glob("*.dat"))
    sizes = [f.stat().st_size for f in files]
    manifest = sorted([f.name for f in files])
    concat = "".join(manifest)
    env_entropy = shannon_entropy(concat) if concat else float(len(files)*0.3)
    return {"file_count": len(files), "total_size_bytes": sum(sizes), "file_manifest": manifest, "entropy_real": env_entropy, "kl_real": kl_divergence_uniform(sizes), "read_time": time.time()}

def update_homeostasis(env):
    entropy = env["entropy_real"]; kl = env["kl_real"]; file_count = env["file_count"]
    integrity = max(0.05, 1.0 - (entropy*0.12 + kl*0.25 + file_count*0.04))
    mode = "nominal"; th = Thresholds()
    if entropy > 4.4 or file_count > 8 or kl > 1.5:
        mode = "tight"; th = Thresholds(16, 800.0, 2.8, 1.6)
    elif entropy < 1.8 and file_count <= 1 and kl < 0.3:
        mode = "relaxed"; th = Thresholds(32, 150.0, 6.0, 0.7)
    elif integrity < 0.6:
        th = Thresholds(20, 500.0, 3.5, 1.3)
    state = ControllerState(th, entropy, kl, integrity, mode)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))
    return state

def compute_merkle_root_of_births():
    if not DB_PATH.exists(): return "EMPTY"
    try:
        with acquire_atomic_lock(str(DB_PATH)) as cur:
            cur.execute("SELECT source_hash FROM birth_edge ORDER BY id")
            hashes = [r[0] for r in cur.fetchall()]
            if not hashes: return "EMPTY"
            return hashlib.sha256("".join(hashes).encode()).hexdigest()
    except: return "EMPTY"

def generate_atomic_snapshot(env_state, controller_state):
    prev_hash = "GENESIS"
    if DB_PATH.exists():
        try:
            with acquire_atomic_lock(str(DB_PATH)) as cur:
                cur.execute("SELECT state_hash FROM learning ORDER BY id DESC LIMIT 1")
                row = cur.fetchone()
                if row: prev_hash = row[0]
        except: pass
    merkle_births = compute_merkle_root_of_births()
    snapshot = {"environment": env_state, "homeostasis": asdict(controller_state), "prev_hash": prev_hash, "merkle_births": merkle_births}
    with acquire_atomic_lock(str(DB_PATH)) as cur:
        cur.execute("SELECT COUNT(*) FROM birth_edge")
        snapshot["tripartite_row_count"] = cur.fetchone()[0]
    s = json.dumps(snapshot, sort_keys=True)
    atomic_hash = hashlib.sha256((prev_hash + s + merkle_births).encode()).hexdigest()
    merkle_root = hashlib.sha256((atomic_hash + prev_hash + merkle_births).encode()).hexdigest()
    snapshot["ATOMIC_HASH"] = atomic_hash; snapshot["MERKLE_ROOT"] = merkle_root; snapshot["DETERMINISTIC_SEED"] = int(atomic_hash[:16], 16)
    return snapshot

def fetch_pumpfun_births(limit=5):
    url = f"https://frontend-api.pump.fun/coins?offset=0&limit={limit}&sort=created_timestamp&order=DESC&includeNsfw=false"
    try:
        req = Request(url, headers={"User-Agent": "Aegis-Tessera-APEX/2.0"})
        with urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode())
            cands = []
            for coin in data:
                sym = coin.get("symbol","")[:24]; mint = coin.get("mint","")
                liq = float(coin.get("usd_market_cap",0) or coin.get("market_cap",0) or random.uniform(100,2000))
                z = float(coin.get("reply_count",0) % 7) + random.uniform(0,1)
                if not sym or not mint: continue
                cands.append({"token_symbol": sym, "contract_address": mint, "liquidity": liq, "z_score": z, "_raw": coin})
            if cands: print(f" [FEED] Pump.fun live: {len(cands)} births")
            return cands
    except Exception as e:
        print(f" [FEED] Live fetch failed ({e}), fallback to sim")
        return []

def simulate_birth_candidates(n=2):
    symbols = ["".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=random.randint(3,10))) for _ in range(n)]
    if random.random() < 0.3: symbols.append("AAAA"*random.randint(1,2))
    return [{"token_symbol": sym, "contract_address": f"0x{uuid.uuid4().hex[:10]}", "liquidity": random.uniform(50,1500), "z_score": random.uniform(0.5,7.0), "_raw": {"simulated": True}} for sym in symbols]

def run_production_kernel(max_cycles=12, real_feed=True):
    print("=== AEGIS-TESSERA APEX v2 LIVE ORACLE ===")
    priv, pub = init_production_architecture()
    print(f"Oracle Pubkey: {pub[:16]}... Crypto: {'Ed25519' if CRYPTO else 'HMAC-fallback'}")
    genesis_hash = None
    for cycle in range(1, max_cycles+1):
        env_state = audit_environment()
        ctrl_state = update_homeostasis(env_state)
        snapshot = generate_atomic_snapshot(env_state, ctrl_state)
        state_hash = snapshot["ATOMIC_HASH"]; merkle_root = snapshot["MERKLE_ROOT"]; prev_hash = snapshot["prev_hash"]; seed_int = snapshot["DETERMINISTIC_SEED"]
        if cycle == 1:
            genesis_hash = state_hash
            GENESIS_FILE.write_text(f"AEGIS-TESSERA APEX v2 GENESIS\nTime: {time.ctime()}\nPubkey: {pub}\nGenesis Hash: {genesis_hash}\nThesis: Homeostatic integrity + hash-chain verifiability\n")
            print(f"[GENESIS] {genesis_hash} frozen to {GENESIS_FILE}")
        candidates = fetch_pumpfun_births(limit=4) if real_feed else []
        if not candidates: candidates = simulate_birth_candidates(random.randint(1,3))
        births_accepted = 0
        for cand in candidates:
            ok, reason = ctrl_state.thresholds.evaluate(cand["token_symbol"], cand["liquidity"], cand["z_score"])
            ent = shannon_entropy(cand["token_symbol"])
            meta = {"symbol": cand["token_symbol"], "mint": cand["contract_address"], "liq": cand["liquidity"], "ent": ent, "ts": int(time.time())}
            cid = content_address(meta)
            if ok:
                births_accepted += 1
                with acquire_atomic_lock(str(DB_PATH)) as cur:
                    cur.execute("INSERT INTO birth_edge (token_symbol, contract_address, liquidity, symbol_entropy, z_score, integrity_at_birth, timestamp, source_hash, content_cid, metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (cand["token_symbol"], cand["contract_address"], cand["liquidity"], ent, cand["z_score"], ctrl_state.integrity, int(time.time()), state_hash, cid, json.dumps(meta)))
        if births_accepted > 0: final_action = f"BIRTH_ACCEPT x{births_accepted}"
        elif env_state["file_count"] == 0:
            final_action = "SPAWN_ENTROPY"; (WORKSPACE / f"node_{uuid.uuid4().hex[:6]}.dat").write_text("AEGIS_DATA_PAYLOAD"*512)
        elif ctrl_state.mode == "tight" or env_state["file_count"] > 7:
            final_action = "PURGE_ENTROPY"
            for f in WORKSPACE.glob("*.dat"): f.unlink()
        else:
            code = seed_int % 3
            if code == 0:
                final_action = "OPTIMIZE_STATE"; files = sorted(WORKSPACE.glob("*.dat"), key=os.path.getmtime)
                if files: files[0].unlink()
            elif code == 1:
                final_action = "SPAWN_ENTROPY"; (WORKSPACE / f"node_{uuid.uuid4().hex[:6]}.dat").write_text("AEGIS_DATA_PAYLOAD"*512)
            else: final_action = "STANDBY"
        signature = sign_message(priv, f"{prev_hash}{state_hash}{merkle_root}".encode())
        with acquire_atomic_lock(str(DB_PATH)) as cur:
            cur.execute("INSERT INTO learning (cycle_id, prev_hash, state_hash, action_taken, merkle_root, signature, pubkey, timestamp) VALUES (?,?,?,?,?,?,?,?)",
                        (cycle, prev_hash, state_hash, final_action, merkle_root, signature, pub, int(time.time())))
            cur.execute("INSERT INTO cognition (heuristic_weights, mode, entropy, kl, integrity, timestamp) VALUES (?,?,?,?,?,?)",
                        (json.dumps(asdict(ctrl_state.thresholds)), ctrl_state.mode, ctrl_state.last_entropy, ctrl_state.last_kl, ctrl_state.integrity, int(time.time())))
        with open(PUBLIC_LEDGER, "a") as f:
            f.write(json.dumps({"cycle": cycle, "prev": prev_hash[:12], "hash": state_hash[:12], "merkle": merkle_root[:12], "action": final_action, "sig": signature[:16]+"..", "pub": pub[:16], "int": round(ctrl_state.integrity,2)})+"\n")
        print(f"[CYCLE {cycle:02d}] {ctrl_state.mode.upper():<8} Files:{env_state['file_count']} Ent:{ctrl_state.last_entropy:.2f} Int:{ctrl_state.integrity:.2f} | {final_action}")
        print(f" {prev_hash[:8]} -> {state_hash[:8]} merkle {merkle_root[:8]} sig {signature[:8]}")
        time.sleep(1.2)
    with open(PUBLIC_LEDGER, "rb") as f: ledger_hash = hashlib.sha256(f.read()).hexdigest()
    PROOF_FILE.write_text(f"GENESIS: {genesis_hash}\nLEDGER_SHA256: {ledger_hash}\nPUBKEY: {pub}\nCYCLES: {max_cycles}\n")
    print("\n=== APEX v2 OFFLINE ==="); print(f"Genesis: {genesis_hash}"); print(f"Ledger hash: {ledger_hash}"); print(f"Files: {GENESIS_FILE}, {PROOF_FILE}, {PUBLIC_LEDGER}")

if __name__ == "__main__":
    run_production_kernel(max_cycles=12, real_feed=True)
