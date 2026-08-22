import sqlite3
from datetime import datetime

DB = "data/learning.db"

def table_exists(cur):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_results'")
    return cur.fetchone() is not None

def init_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_results (
            addr TEXT PRIMARY KEY,
            chain TEXT,
            symbol TEXT,
            initial_price_usd REAL,
            initial_liquidity_usd REAL,
            overall_score REAL,
            holder_score REAL,
            dev_score REAL,
            lp_lock_score REAL,
            tax_score REAL,
            final_price_usd REAL,
            rug_pulled INTEGER,
            pumped INTEGER,
            price_change_24h REAL,
            discovered_at TEXT,
            updated_at TEXT
        )
    """)

def insert_adversarial(cur):
    now = datetime.now().isoformat()
    # High overall_score but rug pulled (baseline will wrongly predict pump)
    for i in range(4):
        addr = f"0xRUGADV{now[:10]}{i:03d}"
        cur.execute("""
            INSERT OR IGNORE INTO learning_results
            (addr, chain, symbol, initial_price_usd, initial_liquidity_usd,
             overall_score, holder_score, dev_score, lp_lock_score, tax_score,
             final_price_usd, rug_pulled, pumped, price_change_24h,
             discovered_at, updated_at)
            VALUES (?, 'SOL', 'RUGX', 0.001, 10000,
                    85 + ?, 20, 25, 30, 35,
                    0.0000001, 1, 0, -95,
                    ?, ?)
        """, (addr, i, now, now))

    # Low overall_score but actually pumped (baseline will wrongly predict rug)
    for i in range(4):
        addr = f"0xPUMPADV{now[:10]}{i:03d}"
        cur.execute("""
            INSERT OR IGNORE INTO learning_results
            (addr, chain, symbol, initial_price_usd, initial_liquidity_usd,
             overall_score, holder_score, dev_score, lp_lock_score, tax_score,
             final_price_usd, rug_pulled, pumped, price_change_24h,
             discovered_at, updated_at)
            VALUES (?, 'SOL', 'PUMPX', 0.001, 10000,
                    55 - ?, 85, 80, 75, 20,
                    0.003, 0, 1, 200,
                    ?, ?)
        """, (addr, i, now, now))

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    if not table_exists(cur):
        init_schema(cur)
    insert_adversarial(cur)
    conn.commit()
    conn.close()
    print("Adversarial rows ensured (4 high-score rugs, 4 low-score pumps).")

if __name__ == "__main__":
    main()
