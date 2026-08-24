#!/usr/bin/env python3
"""
AEGIS Audit Log
---------------
Append-only, hash-chained audit trail.

Each entry contains:
- timestamp
- event
- detail
- previous hash
- current hash = SHA-256 of (previous_hash + canonical_payload)

This provides tamper-evident logging suitable for later verification.
"""

from __future__ import annotations
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any

LOG_PATH = pathlib.Path("data/aegis_chain.log")
GENESIS = "0" * 64

def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)

def _load_last_hash() -> str:
    if not LOG_PATH.exists():
        return GENESIS
    with open(LOG_PATH, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size == 0:
            return GENESIS
        # read last line
        f.seek(max(0, size - 4096), 0)
        lines = f.read().decode("utf-8", errors="ignore").strip().splitlines()
        if not lines:
            return GENESIS
        last = lines[-1]
        if "| HASH=" in last:
            return last.split("| HASH=")[-1].strip()
        return GENESIS

def audit(event: str, detail: dict | None = None) -> str:
    prev = _load_last_hash()
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "detail": detail or {},
        "prev": prev,
    }
    canonical = _canonical(payload)
    current = hashlib.sha256((prev + canonical).encode("utf-8")).hexdigest()
    line = f"{canonical} | HASH={current}\n"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    return current
