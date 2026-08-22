import sqlite3
import os
import time
import json
from datetime import datetime, timedelta
from collections import OrderedDict

COG_DB = os.path.join("data", "cognition.db")

# ---------------- Inherent Knowledge (static facts) ----------------
INHERENT_KNOWLEDGE = {
    "solana_mint_layout": {
        "mint_authority_offset": 0,
        "mint_authority_length": 32,
        "freeze_authority_offset": 46,
        "freeze_authority_length": 32,
    },
    "jupiter_quote_url": "https://lite-api.jup.ag/swap/v1/quote",
    "dexscreener_latest_url": "https://api.dexscreener.com/token-profiles/latest/v1",
    "rugcheck_url": "https://api.rugcheck.xyz/v1/check/{}",
    "common_scam_patterns": [
        "high_tax_above_10_percent",
        "mint_authority_not_revoked",
        "freeze_authority_not_revoked",
        "top10_holders_above_35_percent",
        "dev_holds_above_5_percent",
    ],
}

# ---------------- Database management ----------------
def init_cognition_db():
    """Create cognition database tables if they don't exist."""
    os.makedirs(os.path.dirname(COG_DB), exist_ok=True)
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        data_json TEXT
    );
    CREATE TABLE IF NOT EXISTS agents (
        address TEXT PRIMARY KEY,
        role TEXT,
        confidence REAL DEFAULT 0.5,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        first_seen TEXT,
        last_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS wisdom_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_text TEXT,
        confidence REAL,
        source TEXT DEFAULT 'manual',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS memory_importance (
        addr TEXT PRIMARY KEY,
        importance REAL,
        reason TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS inherent_knowledge (
        key TEXT PRIMARY KEY,
        value_json TEXT
    );
    """)
    # Seed inherent knowledge
    for key, value in INHERENT_KNOWLEDGE.items():
        cur.execute("""
            INSERT OR REPLACE INTO inherent_knowledge (key, value_json)
            VALUES (?, ?)
        """, (key, json.dumps(value)))
    # Seed a few wisdom rules
    seed_rules = [
        ("Tokens with mint authority not revoked are usually rugs", 0.9),
        ("Tokens with top10 holders > 35% are dangerous", 0.85),
        ("Tax > 10% almost always leads to loss", 0.95),
        ("High liquidity (> $50k) on new token is often a trap", 0.7),
    ]
    for rule_text, confidence in seed_rules:
        cur.execute("""
            INSERT OR IGNORE INTO wisdom_rules (rule_text, confidence, source, created_at)
            VALUES (?, ?, 'seed', ?)
        """, (rule_text, confidence, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ---------------- World Map (Events) ----------------
def record_event(event_type: str, data: dict):
    """Record an event in the world map."""
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (timestamp, event_type, data_json)
        VALUES (?, ?, ?)
    """, (datetime.now().isoformat(), event_type, json.dumps(data)))
    conn.commit()
    conn.close()

def get_recent_events(event_type=None, limit=100):
    """Return recent events of given type (or all types if None)."""
    conn = sqlite3.connect(COG_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if event_type:
        cur.execute("""
            SELECT timestamp, event_type, data_json FROM events
            WHERE event_type = ?
            ORDER BY id DESC LIMIT ?
        """, (event_type, limit))
    else:
        cur.execute("""
            SELECT timestamp, event_type, data_json FROM events
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"timestamp": r["timestamp"], "event_type": r["event_type"], "data": json.loads(r["data_json"])} for r in rows]

# ---------------- Agent Map ----------------
def register_agent(address: str, role: str, success_count=0, fail_count=0):
    """Add or update an agent (developer, whale, sniper)."""
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO agents (address, role, success_count, fail_count, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(address) DO UPDATE SET
            role=excluded.role,
            success_count=agents.success_count + excluded.success_count,
            fail_count=agents.fail_count + excluded.fail_count,
            last_seen=excluded.last_seen,
            confidence = CASE WHEN (agents.success_count + agents.fail_count) > 0
                        THEN CAST(agents.success_count AS REAL) / (agents.success_count + agents.fail_count)
                        ELSE 0.5 END
    """, (address, role, success_count, fail_count, now, now))
    conn.commit()
    conn.close()

def get_agent(address: str):
    """Return agent info if exists."""
    conn = sqlite3.connect(COG_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents WHERE address = ?", (address,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

# ---------------- Memory Importance ----------------
def compute_importance(initial_price: float, final_price: float, liquidity_change: float, rug: bool, pump: bool) -> float:
    """
    Compute importance score 0.0-1.0 based on outcome magnitude.
    More dramatic changes => higher importance.
    """
    if rug:
        return 0.9  # rugs are critical to remember
    if pump:
        return 0.8  # pumps are important
    # Otherwise based on percentage change and liquidity change
    pct_change = abs(final_price - initial_price) / (initial_price + 1e-12)
    importance = min(1.0, pct_change * 10 + abs(liquidity_change) / 100000)
    return importance

def set_memory_importance(addr: str, importance: float, reason: str = ""):
    """Store importance for a token address."""
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO memory_importance (addr, importance, reason, updated_at)
        VALUES (?, ?, ?, ?)
    """, (addr, importance, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_memory_importance(addr: str) -> float:
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("SELECT importance FROM memory_importance WHERE addr = ?", (addr,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0.0

# ---------------- Wisdom Rules ----------------
def add_wisdom_rule(rule_text: str, confidence: float, source: str = "manual"):
    """Add a new wisdom rule."""
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wisdom_rules (rule_text, confidence, source, created_at)
        VALUES (?, ?, ?, ?)
    """, (rule_text, confidence, source, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_wisdom_rules(min_confidence: float = 0.0, limit: int = 20):
    """Return wisdom rules with confidence >= min_confidence."""
    conn = sqlite3.connect(COG_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT rule_text, confidence, source FROM wisdom_rules
        WHERE confidence >= ?
        ORDER BY confidence DESC LIMIT ?
    """, (min_confidence, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"rule": r["rule_text"], "confidence": r["confidence"], "source": r["source"]} for r in rows]

# ---------------- Inherent Knowledge ----------------
def get_inherent_knowledge(key: str):
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("SELECT value_json FROM inherent_knowledge WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def set_inherent_knowledge(key: str, value):
    conn = sqlite3.connect(COG_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO inherent_knowledge (key, value_json)
        VALUES (?, ?)
    """, (key, json.dumps(value)))
    conn.commit()
    conn.close()
