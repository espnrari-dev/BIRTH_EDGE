import asyncio, os, traceback, inspect
from datetime import datetime
os.makedirs("data", exist_ok=True)
print(f"[{datetime.now()}] BIRTH_EDGE REAL + IPO FIXED v4...")
from utils import fetch_json_sync, now_str
from config import DEX_LATEST_URL, DEX_TOKEN_URL, LIQ_THRESHOLD, POLL_INTERVAL_FILTERED
from filters import run_all_filters
import scoring, learning
from ipo import ipo_loop, init_ipo_db
print("filters:", inspect.signature(scoring.record_token if hasattr(scoring,'record_token') else learning.record_token))
try: getattr(scoring,'init_db',lambda:None)()
except: pass
try: getattr(learning,'init_learning_db',lambda:None)()
except: pass
try: init_ipo_db()
except: pass

def make_pair_url(addr):
    return DEX_TOKEN_URL.format(addr) if '{}' in DEX_TOKEN_URL else f"{DEX_TOKEN_URL.rstrip('/')}/{addr}"

async def call_filters(addr, chain, liq, pair_obj):
    # filters.py now is dict version: {"addr":..., "chain":..., "liquidity_usd":...}
    token_data = {
        "addr": addr,
        "address": addr,
        "tokenAddress": addr,
        "chain": chain,
        "chainId": chain,
        "liquidity_usd": liq,
        "liquidity": {"usd": liq},
        "pair": pair_obj,
        "baseToken": pair_obj.get('baseToken',{}) if isinstance(pair_obj,dict) else {},
        "symbol": pair_obj.get('baseToken',{}).get('symbol') if isinstance(pair_obj,dict) and pair_obj.get('baseToken') else pair_obj.get('symbol','?') if isinstance(pair_obj,dict) else '?'
    }
    # also add all pair fields into token_data for filters that read directly
    if isinstance(pair_obj, dict):
        token_data.update(pair_obj)
    return await run_all_filters(token_data)

def call_record(mod, addr, chain, symbol, liq, result):
    # try dict version, then 5-arg version
    try:
        # new dict api
        payload = {
            "addr": addr, "address": addr, "chain": chain, "symbol": symbol,
            "liquidity_usd": liq, "overall_score": result.get('overall_score'),
            "holder_score": result.get('holder_score'),
            "status": "PASS" if result.get('pass') else "FILTERED",
            "result": result
        }
        payload.update(result)
        return mod.record_token(payload)
    except TypeError:
        try:
            return mod.record_token(addr, chain, symbol, liq, result)
        except TypeError:
            return mod.record_token({"addr":addr,"chain":chain,"symbol":symbol,"liq":liq,"result":result})

async def birth_filtered_loop():
    seen=set()
    print(f"[{now_str()}] BIRTH_FILTERED hunting ${LIQ_THRESHOLD}+")
    while True:
        try:
            data=fetch_json_sync(DEX_LATEST_URL)
            if not data:
                await asyncio.sleep(POLL_INTERVAL_FILTERED); continue
            tokens=data if isinstance(data,list) else data.get('tokens',[]) or data.get('pairs',[]) or []
            new_count=0
            for t in tokens:
                addr=t.get('tokenAddress') or t.get('address') or t.get('baseToken',{}).get('address')
                if not addr or addr in seen: continue
                liq=0; pair_obj=None
                if 'liquidity' in t and isinstance(t.get('liquidity'),dict):
                    liq=float(t.get('liquidity',{}).get('usd',0) or 0); pair_obj=t
                elif 'liquidity_usd' in t:
                    liq=float(t.get('liquidity_usd',0) or 0); pair_obj=t
                else:
                    pd=fetch_json_sync(make_pair_url(addr))
                    if not pd: continue
                    pairs=pd.get('pairs',[]) if isinstance(pd,dict) else pd
                    if not pairs: continue
                    pair_obj=pairs[0]
                    liq=float(pair_obj.get('liquidity',{}).get('usd',0) or 0)
                if liq < LIQ_THRESHOLD: continue
                seen.add(addr); new_count+=1
                chain=pair_obj.get('chainId','solana') if pair_obj and isinstance(pair_obj,dict) else 'solana'
                symbol=pair_obj.get('baseToken',{}).get('symbol') if pair_obj and isinstance(pair_obj,dict) else t.get('symbol','?')
                result=await call_filters(addr, chain, liq, pair_obj or t)
                status="PASS" if result.get('pass') else "FILTERED"
                print(f"[{now_str()}] {status} {symbol} {addr[:8]} liq ${liq:,.0f} overall {result.get('overall_score')} {result.get('reason','')}")
                call_record(scoring, addr, chain, symbol, liq, result)
                call_record(learning, addr, chain, symbol, liq, result)
            if new_count==0:
                print(f"[{now_str()}] Watching {len(seen)} seen, no new >${LIQ_THRESHOLD}")
        except Exception as e:
            print(f"[{now_str()}] birth error {e}"); traceback.print_exc()
        await asyncio.sleep(POLL_INTERVAL_FILTERED)

async def dual():
    await asyncio.gather(birth_filtered_loop(), ipo_loop())

if __name__=="__main__":
    asyncio.run(dual())

import threading
import time
from aethel-abyss.void-protocol import VoidProtocol  # Placeholder; we'll copy the JS logic

class VoidListener(threading.Thread):
    def run(self):
        print("[VOID] Listening for APEX sigil...")
        # In reality: capture audio, decode sigil, rehydrate APEX
        time.sleep(2)
        print("[VOID] Sigil detected, rehydrating APEX...")

# Start listener
listener = VoidListener()
listener.daemon = True
listener.start()
