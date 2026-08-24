import sqlite3
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()
cur.execute("SELECT overall_score, holder_score, dev_score, lp_lock_score, tax_score, pumped FROM learning_results WHERE final_price_usd IS NOT NULL AND overall_score IS NOT NULL")
rows=cur.fetchall()
print(f"Total labeled: {len(rows)} pumped={sum(r[5] for r in rows)} base={sum(r[5] for r in rows)/len(rows)*100:.2f}%")

for name, idx in [("holder",1),("dev",2),("lp_lock",3),("tax",4)]:
    hi = [r for r in rows if r[0]>=76]
    if not rows: continue
    avg_pump = sum(r[idx] for r in rows if r[5]==1)/max(1,len([r for r in rows if r[5]==1]))
    avg_all = sum(r[idx] for r in rows)/len(rows)
    avg_hi = sum(r[idx] for r in hi)/max(1,len(hi))
    print(f"{name}: all={avg_all:.1f} | pumped avg={avg_pump:.1f} | 76+ avg={avg_hi:.1f}")

print("\nFALSE POSITIVES at 76+ (leaks):")
for r in cur.execute("SELECT symbol, overall_score, holder_score, dev_score, lp_lock_score, tax_score FROM learning_results WHERE overall_score>=76 AND pumped=0 AND final_price_usd IS NOT NULL ORDER BY discovered_at DESC LIMIT 10"):
    print(r)

print("\nTRUE WINS at 76+:")
for r in cur.execute("SELECT symbol, overall_score, holder_score, dev_score, lp_lock_score, tax_score FROM learning_results WHERE overall_score>=76 AND pumped=1 ORDER BY discovered_at DESC"):
    print(r)
