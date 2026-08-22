import asyncio
import os
import time
import traceback
from datetime import datetime

os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

print(f"[{datetime.now()}] BIRTH_EDGE starting REAL...")

from utils import fetch_json_sync, log_jsonl, now_str
from config import DEX_LATEST_URL, DEX_TOKEN_URL, LIQ_THRESHOLD, POLL_INTERVAL_FILTERED
from filters import run_all_filters
from scoring import record_token as record_to_birth
from learning import record_token as record_to_learning

try:
    from database import init_db
    from learning import init_learning_db
    init_db()
    init_learning_db()
    print("DBs initialized")
except Exception as e:
    print(f"DB init error: {e}")
    traceback.print_exc()

def fetch_filtered_tokens():
    try:
        r = fetch_json_sync(DEX_LATEST_URL)
        if not r:
            return []
        tokens = []
        for t in r[:20]:
            addr = t.get('tokenAddress')
            if not addr:
                continue
            details = fetch_json_sync(DEX_TOKEN_URL.format(addr))
            if not details:
                continue
            pairs = details.get('pairs', [])
            if not pairs:
                continue
            liq = float(pairs[0].get('liquidity', {}).get('usd', 0) or 0)
            if liq > LIQ_THRESHOLD:
                chain = t.get('chainId', 'solana')
                symbol = t.get('symbol', '?')
                creator = None
                try:
                    creator = pairs[0].get('baseToken', {}).get('address')
                except:
                    pass
                tokens.append({
                    "addr": addr,
                    "chain": chain,
                    "symbol": symbol,
                    "liquidity_usd": liq,
                    "creator": creator,
                    "discovered_at": now_str(),
                })
        return tokens
    except Exception as e:
        print(f"fetch_filtered error: {e}")
        traceback.print_exc()
        return []

async def process_token(token):
    try:
        print(f"[{now_str()}] Processing {token.get('symbol')} {token.get('addr')[:8]} liq ${token.get('liquidity_usd'):,.0f}")
        filtered = await run_all_filters(token)
        final_data = filtered if "overall_score" in filtered else {**token, **filtered}
        if filtered.get("pass"):
            print(f"[{now_str()}] PASS {token.get('symbol')} overall {final_data.get('overall_score')} holder {final_data.get('holder_score')}")
        else:
            print(f"[{now_str()}] FILTERED {token.get('symbol')} reason {filtered.get('reason','score')} overall {final_data.get('overall_score','?')}")
        try:
            record_to_birth(final_data)
            record_to_learning(final_data)
            print(f"[{now_str()}] RECORDED to both DBs")
        except Exception as e:
            print(f"record_token error: {e}")
            traceback.print_exc()
    except Exception as e:
        print(f"process_token error: {e}")
        traceback.print_exc()

async def main_loop():
    print(f"[{now_str()}] REAL BIRTH_FILTERED loop starting, threshold ${LIQ_THRESHOLD}")
    seen = set()
    while True:
        try:
            tokens = fetch_filtered_tokens()
            new_tokens = [t for t in tokens if t['addr'] not in seen]
            if new_tokens:
                print(f"[{now_str()}] Found {len(new_tokens)} NEW filtered tokens")
                for t in new_tokens:
                    seen.add(t['addr'])
                    await process_token(t)
                    await asyncio.sleep(2)
            else:
                print(f"[{now_str()}] Watching {len(seen)} seen, no new, alive")
            await asyncio.sleep(POLL_INTERVAL_FILTERED)
        except Exception as e:
            print(f"main loop error: {e}")
            traceback.print_exc()
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main_loop())
