import sqlite3, os
from config import DATABASE_PATH
LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")
conn = sqlite3.connect(LEARNING_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT * FROM learning_results")
rows = cur.fetchall()
# show variance
holders = [r["holder_score"] for r in rows]
liqs = [r["initial_liquidity_usd"] for r in rows]
print(f"holder min {min(holders)} max {max(holders)} unique {set(holders)}")
print(f"liq min {min(liqs)} max {max(liqs)}")
# with >=
fires = [r for r in rows if r["initial_liquidity_usd"] >= 12012 and r["holder_score"] >= 15.0]
print(f"fires with >= : {len(fires)}/{len(rows)}")
