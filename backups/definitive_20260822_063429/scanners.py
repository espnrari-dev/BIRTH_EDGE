import time
from datetime import datetime
from config import (
    POLL_INTERVAL_BIRTH, POLL_INTERVAL_FILTERED,
    POLL_INTERVAL_KATANA, POLL_INTERVAL_BEACON,
    BEACON_SYMBOLS, DEX_LATEST_URL, DEX_TOKEN_URL, DEX_SEARCH_URL,
    LIQ_THRESHOLD, KATANA_GAP_THRESHOLD, BEACON_MAX_GAP
)
from utils import fetch_json_sync, log_jsonl, now_str

def birth_simple():
    """Detect new tokens appearing on DexScreener latest profiles."""
    print(f"[{now_str()}] BIRTH_SIMPLE started")
    seen = set()
    while True:
        try:
            r = fetch_json_sync(DEX_LATEST_URL)
            if not r:
                time.sleep(POLL_INTERVAL_BIRTH)
                continue
            for t in r[:15]:
                addr = t.get('tokenAddress', '')
                addr_short = addr[:8]
                if addr and addr_short not in seen:
                    seen.add(addr_short)
                    chain = t.get('chainId', '?')
                    symbol = t.get('symbol', '?')
                    desc = t.get('description', '')[:40]
                    msg = f"NEW BIRTH {symbol} on {chain} - {addr_short} - {desc}"
                    print(f"[{now_str()}] {msg}")
                    log_jsonl("births.jsonl", {
                        "time": now_str(),
                        "chain": chain,
                        "addr": addr,
                        "addr_short": addr_short,
                        "symbol": symbol,
                        "description": desc,
                    })
            print(f"[{now_str()}] BIRTH_SIMPLE watching {len(seen)} births - alive")
        except Exception as e:
            print(f"[{now_str()}] BIRTH_SIMPLE error: {e}")
        time.sleep(POLL_INTERVAL_BIRTH)

def birth_filtered():
    """Filter new births by liquidity > threshold."""
    print(f"[{now_str()}] BIRTH_FILTERED started")
    seen = set()
    while True:
        try:
            r = fetch_json_sync(DEX_LATEST_URL)
            if not r:
                time.sleep(POLL_INTERVAL_FILTERED)
                continue
            for t in r[:20]:
                addr = t.get('tokenAddress')
                if not addr or addr in seen:
                    continue
                seen.add(addr)
                details = fetch_json_sync(DEX_TOKEN_URL.format(addr))
                if not details:
                    continue
                pairs = details.get('pairs', [])
                if pairs:
                    liq = float(pairs[0].get('liquidity', {}).get('usd', 0) or 0)
                    if liq > LIQ_THRESHOLD:
                        chain = t.get('chainId', '?')
                        symbol = t.get('symbol', '?')
                        msg = f"FILTERED NEW {addr[:8]} liq ${liq:,.0f} - REAL TARGET"
                        print(f"[{now_str()}] {msg}")
                        log_jsonl("filtered.jsonl", {
                            "time": now_str(),
                            "chain": chain,
                            "addr": addr,
                            "symbol": symbol,
                            "liq_usd": liq,
                        })
            print(f"[{now_str()}] BIRTH_FILTERED {len(seen)} seen, filtering > ${LIQ_THRESHOLD:,.0f}")
        except Exception as e:
            print(f"[{now_str()}] BIRTH_FILTERED error: {e}")
        time.sleep(POLL_INTERVAL_FILTERED)

def birth_to_katana():
    """Detect Solana new tokens with price gap > threshold between DEXes."""
    print(f"[{now_str()}] BIRTH_TO_KATANA started")
    while True:
        try:
            r = fetch_json_sync(DEX_LATEST_URL)
            if not r:
                time.sleep(POLL_INTERVAL_KATANA)
                continue
            for t in r[:5]:
                token_addr = t.get('tokenAddress')
                chain = t.get('chainId')
                if chain != 'solana' or not token_addr:
                    continue
                details = fetch_json_sync(DEX_TOKEN_URL.format(token_addr))
                if not details:
                    continue
                pairs = details.get('pairs', [])
                if len(pairs) >= 2:
                    p1 = float(pairs[0].get('priceUsd', 0) or 0)
                    p2 = float(pairs[1].get('priceUsd', 0) or 0)
                    if p1 and p2:
                        gap = abs(p1 - p2) / p2 * 100
                        if gap > KATANA_GAP_THRESHOLD:
                            msg = f"{token_addr[:8]}.. GAP {gap:.2f}% ${p1:.6f} vs ${p2:.6f} - KATANA TARGET"
                            print(f"[{now_str()}] {msg}")
                            log_jsonl("katana_targets.jsonl", {
                                "time": now_str(),
                                "token_addr": token_addr,
                                "gap_percent": gap,
                                "price1": p1,
                                "price2": p2,
                            })
            print(f"[{now_str()}] BIRTH_TO_KATANA alive")
        except Exception as e:
            print(f"[{now_str()}] BIRTH_TO_KATANA error: {e}")
        time.sleep(POLL_INTERVAL_KATANA)

def beacon_viable_slab():
    """Monitor fixed list of symbols for cross-DEX arbitrage gaps."""
    print(f"[{now_str()}] BEACON_VIABLE_SLAB started")
    while True:
        for tok in BEACON_SYMBOLS:
            gap_info = get_gap_for_symbol(tok)
            if gap_info:
                msg = f"{tok} {gap_info['dex1']} vs {gap_info['dex2']} GAP {gap_info['gap']:+.4f}% {gap_info['addr'][:8]}"
                print(f"[{now_str()}] {msg}")
                log_jsonl("beacon_gaps.jsonl", {"time": now_str(), **gap_info})
            else:
                print(f"[{now_str()}] {tok} GAP -- no clean pair")
            time.sleep(2)
        time.sleep(POLL_INTERVAL_BEACON)

def get_gap_for_symbol(symbol):
    """Check same-token cross-DEX gap for a given symbol."""
    try:
        r = fetch_json_sync(DEX_SEARCH_URL.format(symbol))
        if not r:
            return None
        pairs = r.get('pairs', [])
        if not pairs:
            return None
        by_addr = {}
        for p in pairs:
            addr = p.get('baseToken', {}).get('address')
            if addr:
                by_addr.setdefault(addr, []).append(p)
        for addr, lst in by_addr.items():
            if len(lst) >= 2:
                p1 = float(lst[0].get('priceUsd', 0) or 0)
                p2 = float(lst[1].get('priceUsd', 0) or 0)
                if p1 and p2:
                    gap = ((p1 - p2) / p2) * 100
                    if abs(gap) < BEACON_MAX_GAP:
                        return {
                            "symbol": symbol,
                            "addr": addr,
                            "gap": gap,
                            "dex1": lst[0].get('dexId'),
                            "dex2": lst[1].get('dexId'),
                            "price1": p1,
                            "price2": p2,
                        }
        return None
    except Exception as e:
        print(f"Beacon gap error for {symbol}: {e}")
        return None
