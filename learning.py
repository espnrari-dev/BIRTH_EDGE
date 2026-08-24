import sqlite3
import os
import time
import requests
from datetime import datetime, timedelta
from config import DEX_TOKEN_URL, DATABASE_PATH, SCORE_MIN_BUY
from utils import fetch_json_sync, now_str
import ml_model
import aegis_rule_miner
import cognition

LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")

def init_learning_db():
    os.makedirs(os.path.dirname(LEARNING_DB), exist_ok=True)
    conn = sqlite3.connect(LEARNING_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_results (
            addr TEXT PRIMARY KEY,
            chain TEXT,
            symbol TEXT,
            initial_price_usd REAL,
            initial_liquidity_usd REAL,
            overall_score INTEGER,
            holder_score REAL,
            dev_score REAL,
            lp_lock_score REAL,
            tax_score REAL,
            discovered_at TEXT,
            final_price_usd REAL,
            rug_pulled INTEGER DEFAULT 0,
            pumped INTEGER DEFAULT 0,
            updated_at TEXT
        )
    """)
    existing_cols = [row[1] for row in cur.execute("PRAGMA table_info(learning_results)").fetchall()]
    if "holder_score" not in existing_cols:
        cur.execute("ALTER TABLE learning_results ADD COLUMN holder_score REAL DEFAULT 0")
    if "dev_score" not in existing_cols:
        cur.execute("ALTER TABLE learning_results ADD COLUMN dev_score REAL DEFAULT 0")
    if "lp_lock_score" not in existing_cols:
        cur.execute("ALTER TABLE learning_results ADD COLUMN lp_lock_score REAL DEFAULT 0")
    if "tax_score" not in existing_cols:
        cur.execute("ALTER TABLE learning_results ADD COLUMN tax_score REAL DEFAULT 0")
    conn.commit()
    conn.close()
    os.makedirs(os.path.dirname(ml_model.MODEL_FILE), exist_ok=True)
    cognition.init_cognition_db()

def record_token(token_data: dict, initial_price_usd: float = 0.0):
    # pull price from dict
    iprice = float(token_data.get('initial_price_usd') or token_data.get('priceUsd') or token_data.get('price_usd') or token_data.get('result',{}).get('initial_price_usd') or token_data.get('result',{}).get('priceUsd') or 0.0)
    if iprice==0:
        try: iprice=float(token_data.get('liquidity_usd',0))/1000000
        except: iprice=1e-05
    conn = sqlite3.connect(LEARNING_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO learning_results
        (addr, chain, symbol, initial_price_usd, initial_liquidity_usd,
         overall_score, holder_score, dev_score, lp_lock_score, tax_score,
         discovered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        token_data.get("addr"),
        token_data.get("chain"),
        token_data.get("symbol", "?"),
        iprice or initial_price_usd,
        token_data.get("liquidity_usd", 0),
        token_data.get("overall_score", 0),
        token_data.get("holder_score", 0),
        token_data.get("dev_score", 0),
        token_data.get("lp_lock_score", 0),
        token_data.get("tax_score", 0),
        token_data.get("discovered_at") or now_str()
    ))
    conn.commit()
    conn.close()
    # Record birth event in cognition
    cognition.record_event("token_birth", {
        "addr": token_data.get("addr"),
        "chain": token_data.get("chain"),
        "symbol": token_data.get("symbol"),
        "liquidity_usd": token_data.get("liquidity_usd", 0),
        "overall_score": token_data.get("overall_score", 0),
        "discovered_at": token_data.get("discovered_at")
    })

def update_outcomes(min_age_hours: int = 1):
    conn = sqlite3.connect(LEARNING_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cutoff = (datetime.now() - timedelta(hours=min_age_hours)).isoformat()
    cur.execute("""
        SELECT addr, initial_price_usd, initial_liquidity_usd,
               overall_score, holder_score, dev_score, lp_lock_score, tax_score
        FROM learning_results
        WHERE final_price_usd IS NULL
          AND discovered_at < ?
    """, (cutoff,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return

    updated = 0
    for row in rows:
        addr = row["addr"]
        initial_price = row["initial_price_usd"] or 0
        initial_liq = row["initial_liquidity_usd"] or 0
        try:
            details = fetch_json_sync(DEX_TOKEN_URL.format(addr), timeout=8)
            if not details or not details.get("pairs"):
                final_price = 0.0
                current_liq = 0.0
                rug = 1
                pump = 0
            else:
                pairs = details["pairs"]
                final_price = float(pairs[0].get("priceUsd", 0) or 0)
                current_liq = float(pairs[0].get("liquidity", {}).get("usd", 0) or 0)
                rug = 1 if (final_price <= 0 or current_liq <= 0) else 0
                pump = 1 if (initial_price and final_price >= 2 * initial_price) else 0

            # Compute importance
            liquidity_change = current_liq - initial_liq
            importance = cognition.compute_importance(initial_price, final_price, liquidity_change, rug, pump)
            cognition.set_memory_importance(addr, importance, reason=f"rug={rug}, pump={pump}")

            # Prepare features for ML
            features = {
                "liquidity_usd": initial_liq,
                "holder_score": row["holder_score"] or 0,
                "dev_score": row["dev_score"] or 0,
                "lp_lock_score": row["lp_lock_score"] or 0,
                "tax_score": row["tax_score"] or 0,
                "overall_score": row["overall_score"] or 0,
            }
            label = 1 if pump else 0

            # Update DB
            conn = sqlite3.connect(LEARNING_DB)
            cur = conn.cursor()
            cur.execute("""
                UPDATE learning_results
                SET final_price_usd = ?, rug_pulled = ?, pumped = ?, updated_at = ?
                WHERE addr = ?
            """, (final_price, rug, pump, now_str(), addr))
            conn.commit()
            conn.close()

            # Train ML
            ml_model.train_model(features, label)

            # Record outcome event
            cognition.record_event("token_outcome", {
                "addr": addr,
                "initial_price": initial_price,
                "final_price": final_price,
                "rug": rug,
                "pump": pump,
                "importance": importance,
            })

            updated += 1
        except Exception as e:
            print(f"[{now_str()}] learning update error for {addr}: {e}")
    if updated:
        print(f"[{now_str()}] Learning: updated {updated} token outcomes, trained ML, and recorded events.")

def retrain_weights():
    conn = sqlite3.connect(LEARNING_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT overall_score, rug_pulled, pumped
        FROM learning_results
        WHERE final_price_usd IS NOT NULL
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print(f"[{now_str()}] Learning: no outcome data yet.")
        return

    total = len(rows)
    rugs = sum(1 for r in rows if r["rug_pulled"])
    pumps = sum(1 for r in rows if r["pumped"])
    avg_score = sum(r["overall_score"] for r in rows) / total
    print(f"[{now_str()}] Learning report: total={total}, rugs={rugs}, pumps={pumps}, avg_score={avg_score:.1f}")

    best_threshold = 0
    best_winrate = -1
    for threshold in range(50, 101, 5):
        subset = [r for r in rows if r["overall_score"] >= threshold]
        if not subset:
            continue
        wins = sum(1 for r in subset if r["pumped"])
        losses = sum(1 for r in subset if r["rug_pulled"])
        winrate = (wins - losses) / len(subset)
        if winrate > best_winrate:
            best_winrate = winrate
            best_threshold = threshold

    print(f"[{now_str()}] Learning: suggested minimum score threshold = {best_threshold} (current {SCORE_MIN_BUY})")

    report = {
        "timestamp": now_str(),
        "total": total,
        "rugs": rugs,
        "pumps": pumps,
        "avg_score": avg_score,
        "best_threshold": best_threshold,
        "best_winrate": best_winrate,
    }
    with open("logs/learning_report.jsonl", "a") as f:
        f.write(str(report) + "\n")

def run_learning_cycle():
    update_outcomes()
    retrain_weights()
    aegis_rule_miner.run_rule_mining()
