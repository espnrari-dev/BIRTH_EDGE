import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH

def get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS tokens (
        addr TEXT PRIMARY KEY,
        chain TEXT,
        symbol TEXT,
        discovered_at TEXT,
        liquidity_usd REAL,
        holder_score REAL,
        dev_score REAL,
        lp_lock_score REAL,
        tax_score REAL,
        overall_score REAL,
        status TEXT DEFAULT 'pending'
    );

    CREATE TABLE IF NOT EXISTS outcomes (
        addr TEXT PRIMARY KEY,
        final_price_usd REAL,
        rug_pulled INTEGER DEFAULT 0,
        pumped INTEGER DEFAULT 0,
        updated_at TEXT
    );
    """)
    conn.commit()
    conn.close()

def insert_token(token_data: dict):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO tokens (addr, chain, symbol, discovered_at,
                                      liquidity_usd, holder_score, dev_score,
                                      lp_lock_score, tax_score, overall_score,
                                      status)
        VALUES (:addr, :chain, :symbol, :discovered_at,
                :liquidity_usd, :holder_score, :dev_score,
                :lp_lock_score, :tax_score, :overall_score,
                'pending')
    """, token_data)
    conn.commit()
    conn.close()

def update_outcome(addr: str, final_price_usd: float, rug_pulled: bool, pumped: bool):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO outcomes (addr, final_price_usd, rug_pulled, pumped, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (addr, final_price_usd, int(rug_pulled), int(pumped), datetime.now().isoformat()))
    conn.commit()
    conn.close()
