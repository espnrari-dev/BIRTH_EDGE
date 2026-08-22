import sqlite3, os
from config import DATABASE_PATH
LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")

conn = sqlite3.connect(LEARNING_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("PRAGMA table_info(learning_results)")
cols = [r[1] for r in cur.fetchall()]
print("cols:", cols)

cur.execute("SELECT * FROM learning_results WHERE pumped IS NOT NULL")
rows = cur.fetchall()
print(f"total rows: {len(rows)}")

def get_liq(r):
    for k in ("initial_liquidity_usd","liquidity_usd"):
        if k in cols and r[k] is not None:
            try: return float(r[k])
            except: pass
    return 0.0

def get_holder(r):
    try: return float(r["holder_score"] or 0)
    except: return 0.0

def fires(r):
    return get_liq(r) > 12012.2 and get_holder(r) > 15.0

fired = [r for r in rows if fires(r)]
not_fired = [r for r in rows if not fires(r)]

def pct_true(rs):
    if not rs: return 0.0
    return 100.0 * sum(1 for r in rs if bool(r["pumped"])) / len(rs)

print(f"A: pumped % WHEN fires: {pct_true(fired):.1f}% ({len(fired)} fired)")
print(f"B: pumped % when NOT fires: {pct_true(not_fired):.1f}% ({len(not_fired)} not fired)")

# C
time_col = next((c for c in ("timestamp","created_at","created","date","time") if c in cols), None)
if time_col:
    cur.execute(f"SELECT * FROM learning_results WHERE pumped IS NOT NULL AND {time_col} >= datetime('now','-30 days')")
    recent = cur.fetchall()
    saved = [r for r in recent if not bool(r["pumped"]) and not fires(r)]
    print(f"C: last 30 days: {len(recent)} total, rugs blocked by rule: {len(saved)}")
else:
    saved = [r for r in rows if not bool(r["pumped"]) and not fires(r)]
    print(f"C: no time col, total rugs blocked all time: {len(saved)}")

conn.close()
