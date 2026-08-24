import sqlite3, time, os
from datetime import datetime
while True:
    conn=sqlite3.connect("data/learning.db")
    cur=conn.cursor()
    cur.execute("SELECT COUNT(*) FROM learning_results WHERE overall_score>=76 AND final_price_usd IS NOT NULL")
    n=cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM learning_results WHERE overall_score>=76 AND pumped=1")
    wins=cur.fetchone()[0]
    prec=wins/n*100 if n else 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 76+ = {wins}/{n} = {prec:.0f}% | need {30-n} more for 30", flush=True)
    if n>=30:
        print(">>> 30 REACHED — RUN PROVE.py FOR PAPER <<<", flush=True)
        break
    conn.close()
    time.sleep(300)
