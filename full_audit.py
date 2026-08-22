import os, glob, sqlite3, sys, json, subprocess
BASE = os.path.expanduser("~/BIRTH_EDGE")
print(f"=== BASE {BASE} ===")
# 1. Files
files = glob.glob(os.path.join(BASE, "*.py"))
print(f"py files: {files}")
for must in ["config.py", "learning.db" not in str(files) and "shogun.py" or "shogun.py", "cognition.py"]:
    path = os.path.join(BASE, must)
    print(f"{must}: {'FOUND' if os.path.exists(path) else 'MISSING'}")

# 2. Config
try:
    sys.path.insert(0, BASE)
    from config import DATABASE_PATH
    print(f"DATABASE_PATH = {DATABASE_PATH}")
    print(f"DATABASE_PATH exists: {os.path.exists(DATABASE_PATH)}")
    LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")
    print(f"LEARNING_DB = {LEARNING_DB} exists: {os.path.exists(LEARNING_DB)}")
except Exception as e:
    print(f"config import FAIL: {e}")
    LEARNING_DB = None

# 3. DB tables
if LEARNING_DB and os.path.exists(LEARNING_DB):
    conn = sqlite3.connect(LEARNING_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"tables in learning.db: {tables}")
    if "learning_results" in tables:
        cur.execute("SELECT COUNT(*) FROM learning_results")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM learning_results WHERE pumped IS NOT NULL")
        labeled = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM learning_results WHERE pumped=1")
        pumped = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM learning_results WHERE rug_pulled=1")
        rugs = cur.fetchone()[0]
        print(f"learning_results total={total} labeled={labeled} pumped={pumped} rugs={rugs}")
        cur.execute("SELECT initial_liquidity_usd, holder_score, overall_score, dev_score, lp_lock_score, tax_score FROM learning_results LIMIT 20")
        rows = cur.fetchall()
        for col in ["initial_liquidity_usd","holder_score","overall_score","dev_score","lp_lock_score","tax_score"]:
            vals = [r[col] for r in rows if r[col] is not None]
            uniq = len(set(vals))
            print(f"{col}: count {len(vals)} unique {uniq} min {min(vals) if vals else None} max {max(vals) if vals else None} {'STUCK - NOT REAL' if uniq<=1 else 'OK'}")
        # check discovered_at
        cur.execute("SELECT MAX(discovered_at) as last FROM learning_results")
        print(f"last discovered_at: {cur.fetchone()['last']}")
    conn.close()

# 4. discovered_rules
for p in [os.path.join(BASE, "discovered_rules.jsonl"), os.path.join(BASE, "logs/discovered_rules.jsonl")]:
    if os.path.exists(p):
        lines = open(p).read().strip().splitlines()
        print(f"{p}: {len(lines)} rules, last: {lines[-1][:200] if lines else 'empty'}")
    else:
        print(f"{p}: MISSING")

# 5. scoring code - find where holder_score is set
print("\n=== GREP holder_score ===")
try:
    out = subprocess.check_output(["grep", "-rn", "holder_score", BASE, "--include=*.py"], text=True)
    print(out[:5000])
except Exception as e:
    print(f"grep fail: {e}")

# 6. processes
print("\n=== PROCESSES ===")
try:
    ps = subprocess.check_output(["ps", "aux"], text=True)
    for line in ps.splitlines():
        if "shogun" in line.lower() or "birth" in line.lower() or "scan" in line.lower() or "python" in line.lower():
            print(line)
except Exception as e:
    print(f"ps fail {e}")

# 7. auto-fix attempt for stuck holder_score - look for scoring file
print("\n=== AUTO-FIX CHECK ===")
for fp in files:
    try:
        txt = open(fp, encoding="utf-8", errors="ignore").read()
        if "holder_score = 15" in txt or "holder_score=15" in txt:
            print(f"FOUND hardcoded 15 in {fp} - THIS IS FAKE")
        if "def holder" in txt.lower() or "def calc_holder" in txt.lower():
            print(f"Possible holder calc in {fp}")
    except: pass

print("\n=== DONE ===")
print("If holder_score unique=1, your scorer is fake/defaulting. Fix that file from grep above.")
