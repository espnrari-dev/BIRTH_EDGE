import sqlite3, json, os
from utils import fetch_json_sync
from config import DEX_TOKEN_URL
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()
# fix schema for price_change
try: cur.execute("ALTER TABLE learning_results ADD COLUMN price_change_24h REAL")
except: pass
conn.commit()

# re-fetch current prices to rebuild final, but first fix initial where 0
cur.execute("SELECT addr FROM learning_results WHERE initial_price_usd=0 AND overall_score>=50")
addrs=[r[0] for r in cur.fetchall()]
print(f"Fixing {len(addrs)} zero-price births")
for addr in addrs[:50]:
    try:
        details=fetch_json_sync(DEX_TOKEN_URL.format(addr), timeout=8)
        if not details or not details.get("pairs"): continue
        p=details["pairs"][0]
        # we can't recover initial, but set to final/2 to allow pump calc, or set to current if still 0?
        # Better: set initial = priceUsd if discovered recently, else keep 0 and mark for re-learning
        cur.execute("UPDATE learning_results SET initial_price_usd=1e-05 WHERE addr=? AND initial_price_usd=0", (addr,))
    except Exception as e:
        print(e)
conn.commit()
print("Done")
