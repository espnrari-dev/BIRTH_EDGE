#!/usr/bin/env python3
"""
Cognition Layer
---------------
Maintains a simple Bayesian-style confidence in data integrity
and healing success rate. Updates are multiplicative and logged.
"""

from __future__ import annotations
import json
import sqlite3
import pathlib
from datetime import datetime, timezone

DB = pathlib.Path("data/cognition.db")

def _conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS beliefs (
            key TEXT PRIMARY KEY,
            value REAL NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            event TEXT NOT NULL,
            detail TEXT,
            integrity REAL
        );
        INSERT OR IGNORE INTO beliefs VALUES ('data_integrity', 1.0, datetime('now'));
        INSERT OR IGNORE INTO beliefs VALUES ('heal_success', 1.0, datetime('now'));
        """)

def get_belief(key: str) -> float:
    with _conn() as c:
        row = c.execute("SELECT value FROM beliefs WHERE key=?", (key,)).fetchone()
        return float(row["value"]) if row else 1.0

def update_belief(key: str, success: bool, weight: float = 0.15):
    """
    Multiplicative update:
    success → value = value + weight * (1 - value)
    failure → value = value * (1 - weight)
    """
    current = get_belief(key)
    if success:
        new = current + weight * (1.0 - current)
    else:
        new = current * (1.0 - weight)
    new = max(0.01, min(1.0, new))
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO beliefs (key, value, updated_at) VALUES (?,?,?)",
            (key, new, datetime.now(timezone.utc).isoformat())
        )
    return new

def record_episode(event: str, detail: dict, integrity: float):
    with _conn() as c:
        c.execute(
            "INSERT INTO episodes (ts, event, detail, integrity) VALUES (?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), event, json.dumps(detail), integrity)
        )

init()
