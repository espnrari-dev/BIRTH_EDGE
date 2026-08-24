import sqlite3
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()
for row in cur.execute("""
SELECT symbol, overall_score, holder_score, dev_score, lp_lock_score, tax_score, initial_liquidity_usd, price_change_24h, pumped, discovered_at
FROM learning_results WHERE overall_score>=76 AND final_price_usd IS NOT NULL ORDER BY pumped DESC, overall_score DESC
"""):
    print(row)
