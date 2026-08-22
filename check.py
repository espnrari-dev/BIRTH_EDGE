import sqlite3, os
from config import DATABASE_PATH
LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")
conn = sqlite3.connect(LEARNING_DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT initial_liquidity_usd, holder_score, overall_score, pumped, rug_pulled, discovered_at FROM learning_results")
for r in cur.fetchall():
    print(dict(r))
