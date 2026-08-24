import sqlite3, statistics
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()
cur.execute("SELECT overall_score, pumped FROM learning_results WHERE final_price_usd IS NOT NULL AND overall_score IS NOT NULL")
rows=[(float(s),p) for s,p in cur.fetchall() if s is not None]
# Scholarly model = threshold only
TH=76
tp=sum(1 for s,p in rows if s>=TH and p==1)
fp=sum(1 for s,p in rows if s>=TH and p==0)
precision=tp/(tp+fp) if tp+fp else 0
base=len([p for _,p in rows if p==1])/len(rows)
print(f"TH={TH} Precision {precision:.1%} vs Base {base:.2%} = Lift {precision/base:.1f}x")
print(f"Use this as production until 30 positives, then retrain logistic regression on holder/dev/lp/tax scores")
