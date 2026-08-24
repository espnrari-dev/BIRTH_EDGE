import sqlite3
conn=sqlite3.connect("data/learning.db")
cur=conn.cursor()

print("=== PROOF 1: Identical birth price for 8 different coins at different times ===")
cur.execute("SELECT symbol, discovered_at, initial_price_usd, final_price_usd FROM learning_results WHERE overall_score>=76 ORDER BY discovered_at")
rows=cur.fetchall()
for r in rows:
    print(r)
print("\nAll 8 wins have initial=1e-05 exactly. Real market: 8 coins born hours apart never have identical price to 8 decimals.")

print("\n=== PROOF 2: Code that fakes it ===")
with open("learning.py") as f:
    txt=f.read()
    # Find fallback line
    for i,line in enumerate(txt.splitlines(),1):
        if "1e-05" in line or "iprice" in line.lower():
            if i>10:
                print(f"Line {i}: {line}")

print("\n=== PROOF 3: Real price would vary ===")
cur.execute("SELECT COUNT(DISTINCT initial_price_usd) as distinct_initial, COUNT(*) as total FROM learning_results WHERE overall_score>=76")
d,t=cur.fetchone()
print(f"Distinct initial prices: {d} out of {t} rows = fake. Real market would be {t} distinct.")

