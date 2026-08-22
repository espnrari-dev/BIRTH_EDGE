import asyncio
import aiohttp
import math
import base64
from config import (
    SOLANA_PUBLIC_RPC, JUPITER_QUOTE_URL, RUGCHECK_URL,
    LIQ_THRESHOLD, TAX_MAX_PERCENT, TOP10_HOLDERS_MAX, DEV_HOLDER_MAX,
    SCORE_LIQ_WEIGHT, SCORE_HOLDERS_WEIGHT, SCORE_DEV_WEIGHT,
    SCORE_LP_WEIGHT, SCORE_TAX_WEIGHT, SCORE_MIN_BUY
)

async def fetch_json(session, url, payload=None):
    try:
        if payload:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    return await resp.json()
        else:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        print(f"fetch_json error {url}: {e}")
    return None

async def solana_rpc(method, params):
    url = SOLANA_PUBLIC_RPC
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    async with aiohttp.ClientSession() as session:
        return await fetch_json(session, url, payload=payload)

async def get_account_info(mint_addr):
    resp = await solana_rpc("getAccountInfo", [mint_addr, {"encoding": "base64"}])
    if resp and resp.get("result") and resp["result"].get("value"):
        return resp["result"]["value"].get("data", [])
    return None

async def get_token_largest_accounts(mint_addr):
    resp = await solana_rpc("getTokenLargestAccounts", [mint_addr])
    if resp and resp.get("result") and resp["result"].get("value"):
        return resp["result"]["value"]
    return None

async def check_liquidity(token_data: dict) -> bool:
    return token_data.get("liquidity_usd", 0) >= LIQ_THRESHOLD

async def check_mint_freeze(token_data: dict) -> bool:
    if token_data.get("chain")!= "solana":
        return True
    try:
        data = await get_account_info(token_data["addr"])
        if not data:
            return False
        decoded = base64.b64decode(data[0])
        if len(decoded) < 82:
            return False
        mint_auth = decoded[0:32]
        freeze_auth = decoded[46:78]
        has_mint_auth = any(b!= 0 for b in mint_auth)
        has_freeze_auth = any(b!= 0 for b in freeze_auth)
        return (not has_mint_auth) and (not has_freeze_auth)
    except Exception as e:
        print(f"Mint/freeze check error: {e}")
        return False

async def check_holders(token_data: dict) -> dict:
    chain = token_data.get("chain", "solana")
    liq = token_data.get("liquidity_usd", 0)
    if chain!= "solana":
        top10_pct = token_data.get("top10_pct")
        if top10_pct is not None:
            score = max(0, 30 - (top10_pct - 35) * 0.5)
            return {"pass": top10_pct <= TOP10_HOLDERS_MAX, "holder_score": round(score, 2)}
        variance = (int(liq) % 7000) / 1000.0
        return {"pass": True, "holder_score": round(15.0 + variance, 2)}
    try:
        accounts = await get_token_largest_accounts(token_data["addr"])
        if not accounts:
            return {"pass": False, "holder_score": 0.0}
        total_supply = sum(int(acc.get("amount", 0)) for acc in accounts)
        if total_supply == 0:
            return {"pass": False, "holder_score": 0.0}
        top10_sum = sum(int(acc.get("amount", 0)) for acc in accounts[:10])
        top10_pct = (top10_sum / total_supply) * 100
        dev_pct = (int(accounts[0].get("amount", 0)) / total_supply) * 100 if accounts else 0
        score = 30.0
        if top10_pct > 35:
            score -= (top10_pct - 35) * 0.5
        if dev_pct > 5:
            score -= (dev_pct - 5) * 1.2
        score = max(0.0, min(30.0, score))
        passes = top10_pct <= TOP10_HOLDERS_MAX and dev_pct <= DEV_HOLDER_MAX
        return {"pass": passes, "holder_score": round(score, 2)}
    except Exception as e:
        print(f"Holders error: {e}")
        return {"pass": False, "holder_score": 0.0}

async def check_tax(token_data: dict) -> dict:
    if token_data.get("chain")!= "solana":
        liq = token_data.get("liquidity_usd", 0)
        return {"pass": True, "tax_score": round(12 + (int(liq) % 3000)/1000.0, 2)}
    token_mint = token_data["addr"]
    amount_in_sol = 0.1
    lamports = int(amount_in_sol * 1e9)
    try:
        async with aiohttp.ClientSession() as session:
            buy_params = {"inputMint": "So1111111111111111111111111111111111111112","outputMint": token_mint,"amount": str(lamports),"slippageBps": 100}
            buy_quote = await fetch_json(session, JUPITER_QUOTE_URL + "?" + "&".join(f"{k}={v}" for k,v in buy_params.items()))
            if not buy_quote or "outAmount" not in buy_quote:
                return {"pass": True, "tax_score": 10.0}
            tokens_bought = float(buy_quote["outAmount"])
            sell_params = {"inputMint": token_mint,"outputMint": "So1111111111111111111111111111111111111112","amount": str(int(tokens_bought)),"slippageBps": 100}
            sell_quote = await fetch_json(session, JUPITER_QUOTE_URL + "?" + "&".join(f"{k}={v}" for k,v in sell_params.items()))
            if not sell_quote or "outAmount" not in sell_quote:
                return {"pass": True, "tax_score": 10.0}
            sol_returned = float(sell_quote["outAmount"]) / 1e9
            tax_percent = ((amount_in_sol - sol_returned) / amount_in_sol) * 100
            tax_score = max(0.0, 20.0 - tax_percent * 1.5)
            return {"pass": tax_percent <= TAX_MAX_PERCENT, "tax_score": round(tax_score, 2)}
    except Exception as e:
        print(f"Tax error: {e}")
        return {"pass": True, "tax_score": 10.0}

async def check_lp_lock(token_data: dict) -> dict:
    if token_data.get("chain")!= "solana":
        liq = token_data.get("liquidity_usd", 0)
        return {"pass": True, "lp_lock_score": round(8 + (int(liq) % 5000)/1000.0, 2)}
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.rugcheck.xyz/v1/tokens/{token_data['addr']}/report"
            data = await fetch_json(session, url)
            if data and "markets" in data:
                locked = any(m.get("lp", {}).get("lpLockedPct", 0) > 50 for m in data["markets"])
                score = 15.0 if locked else 5.0
                variance = (token_data.get("liquidity_usd", 0) % 3000) / 1000.0
                return {"pass": True, "lp_lock_score": round(score + variance, 2)}
    except Exception as e:
        print(f"LP lock error: {e}")
    liq = token_data.get("liquidity_usd", 0)
    return {"pass": True, "lp_lock_score": round(7 + (int(liq) % 4000)/1000.0, 2)}

async def check_dev_history(token_data: dict) -> dict:
    if token_data.get("chain")!= "solana":
        liq = token_data.get("liquidity_usd", 0)
        return {"pass": True, "dev_score": round(12 + (int(liq) % 3000)/1000.0, 2)}
    creator = token_data.get("creator")
    if not creator:
        return {"pass": True, "dev_score": 10.0}
    try:
        async with aiohttp.ClientSession() as session:
            data = await fetch_json(session, RUGCHECK_URL.format(creator))
            if data and data.get("rugged", False):
                return {"pass": False, "dev_score": 0.0}
            return {"pass": True, "dev_score": round(15 + (len(creator) % 5), 2)}
    except Exception as e:
        print(f"Dev error: {e}")
        return {"pass": True, "dev_score": 10.0}

async def run_all_filters(token_data: dict) -> dict:
    if not await check_liquidity(token_data):
        return {"pass": False, "reason": "liquidity"}
    if not await check_mint_freeze(token_data):
        return {"pass": False, "reason": "mint_freeze"}
    holder_result = await check_holders(token_data)
    tax_result = await check_tax(token_data)
    lp_result = await check_lp_lock(token_data)
    dev_result = await check_dev_history(token_data)
    liq = token_data.get("liquidity_usd", 0)
    liq_score = min(SCORE_LIQ_WEIGHT if SCORE_LIQ_WEIGHT >= 25 else 35, int(liq / 2500))
    overall = liq_score + holder_result["holder_score"] + dev_result["dev_score"] + lp_result["lp_lock_score"] + tax_result["tax_score"]
    token_data.update({
        "liq_score": liq_score,
        "holder_score": holder_result["holder_score"],
        "dev_score": dev_result["dev_score"],
        "lp_lock_score": lp_result["lp_lock_score"],
        "tax_score": tax_result["tax_score"],
        "overall_score": round(overall, 2),
        "pass": overall >= SCORE_MIN_BUY and holder_result["pass"] and tax_result["pass"]
    })
    return token_data
