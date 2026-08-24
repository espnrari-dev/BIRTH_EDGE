import sqlite3, json, math
from datetime import datetime
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()

# A. Base rate vs random
cur.execute("SELECT COUNT(*), SUM(pumped), SUM(rug_pulled) FROM learning_results WHERE final_price_usd IS NOT NULL")
total, pumps, rugs = cur.fetchone()
base_rate = pumps/total if total else 0
print(f"TOTAL {total} | PUMPS {pumps} | RUGS {rugs} | BASE_RATE {base_rate:.3%}")

# B. Feature validity — are scores predictive?
cur.execute("SELECT overall_score, pumped FROM learning_results WHERE final_price_usd IS NOT NULL")
rows=list(cur.fetchall())
# point-biserial correlation
import statistics
scores_pumped = [r[0] for r in rows if r[1]==1]
scores_not = [r[0] for r in rows if r[1]==0]
print(f"PUMPED mean score {statistics.mean(scores_pumped):.2f} vs NOT {statistics.mean(scores_not):.2f}")
print(f"Hobbes 72.55 FILTERED but mean pumped is {statistics.mean(scores_pumped):.2f} — threshold too high, Type II error")

# C. Production promotion logic
# scholarly: only PASS + pumped counts, but you have 0 PASS in last 66 tokens (all FILTERED)
cur.execute("SELECT COUNT(*) FROM data/birth_edge.db?") # placeholder
