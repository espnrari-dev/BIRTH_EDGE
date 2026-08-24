#!/usr/bin/env python3
"""
BIRTH_EDGE: Core Execution Engine & Pipeline Runner
Zero-Footprint Concurrency / Edge-Primitive Engineering
"""

import os
import sys
import time
import json
import urllib.request
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.expanduser("~/BIRTH_EDGE")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

LOG = os.path.join(DATA_DIR, "event_log.jsonl")
TREAS = os.path.join(DATA_DIR, "treasury.jsonl")

def append_event(ev):
    try:
        with open(LOG, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(ev, sort_keys=True) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(f"[LEDGER ERR] {e}", flush=True)

def fetch_pump_coins(offset):
    url = f"https://frontend-api-v3.pump.fun/coins?offset={offset}&limit=30&sort=created_timestamp&order=DESC"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    events = []
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
            for c in data:
                sym = str(c.get("symbol", ""))[:20]
                mint = c.get("mint")
                mcap = int(float(c.get("usd_market_cap", 0)) * 100)
                if mint and mcap >= 1000:
                    events.append({
                        "type": "birth_seen",
                        "symbol": sym,
                        "mint": mint,
                        "mcap_cents": mcap,
                        "t": int(time.time()),
                        "source": "pump.fun"
                    })
    except Exception as e:
        print(f"[CAPTURE ERR] offset {offset}: {e}", flush=True)
    return events

def get_market_cap(mint):
    urls = [
        f"https://frontend-api-v3.pump.fun/coins/{mint}",
        f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                j = json.loads(r.read().decode())
                if "usd_market_cap" in j:
                    return int(float(j["usd_market_cap"]) * 100)
                if "pairs" in j and j["pairs"]:
                    p = j["pairs"][0]
                    fdv = p.get("fdv") or p.get("marketCap") or 0
                    if fdv:
                        return int(float(fdv) * 100)
        except Exception:
            continue
    return None

def load_known_mints():
    mints = {}
    if os.path.exists(LOG):
        try:
            with open(LOG, "r") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                        if ev.get("mint") and ev.get("symbol"):
                            mints[ev["symbol"]] = ev["mint"]
                    except:
                        pass
        except:
            pass
    return mints

def load_open_positions():
    opens = {}
    if os.path.exists(TREAS):
        try:
            with open(TREAS, "r") as f:
                for line in f:
                    try:
                        ev = json.loads(line)
                        sym = ev.get("symbol")
                        if not sym:
                            continue
                        if ev["type"] == "trade_open":
                            opens[sym] = ev
                        elif ev["type"] in ("profit", "loss"):
                            opens.pop(sym, None)
                    except:
                        pass
        except:
            pass
    return opens

def execution_cycle():
    start_time = time.time()
    
    offsets = [0, 20, 40, 60, 80]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_pump_coins, off) for off in offsets]
        for future in as_completed(futures):
            for ev in future.result():
                append_event(ev)

    mints = load_known_mints()
    opens = load_open_positions()
    
    updated_count = 0
    for sym, pos in list(opens.items()):
        mint = mints.get(sym)
        if not mint:
            continue
        mcap = get_market_cap(mint)
        if mcap:
            ev = {
                "type": "price_update",
                "symbol": sym,
                "mint": mint,
                "mcap_cents": mcap,
                "t": int(time.time()),
                "source": "refresh"
            }
            append_event(ev)
            updated_count += 1

    elapsed = time.time() - start_time
    print(f"[EXEC ENGINE] Cycle completed in {elapsed:.2f}s | {len(opens)} opens | {len(mints)} mints known", flush=True)

if __name__ == "__main__":
    print(f"[BOOT] BIRTH_EDGE Engine live in {BASE_DIR}", flush=True)
    while True:
        try:
            execution_cycle()
        except Exception as e:
            print(f"[CRITICAL ERR] {e}", flush=True)
        time.sleep(5)
