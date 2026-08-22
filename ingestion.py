import asyncio
import json
import os
from datetime import datetime
import websockets
from utils import now_str, log_jsonl

async def ingest_solana():
    """Helius WebSocket logsSubscribe for new token mints."""
    from config import HELIUS_WS_URL
    if not HELIUS_WS_URL or "YOUR_KEY" in HELIUS_WS_URL:
        print(f"[{now_str()}] Helius WS not configured, skipping Solana real-time ingestion.")
        return
    try:
        async with websockets.connect(HELIUS_WS_URL) as ws:
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": ["11111111111111111111111111111111"]},
                    {"commitment": "processed"}
                ]
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"[{now_str()}] Solana real-time listener started.")
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if "params" in data:
                    value = data["params"]["result"]["value"]
                    token_addr = value.get("signature", "")  # will be replaced with actual extraction
                    # Simple placeholder: we just log the event; actual parsing needed.
                    log_jsonl("solana_raw.jsonl", {"time": now_str(), "data": value})
                    # In a full implementation we'd extract token mint from logs and call process_token
        except Exception as e:
            print(f"[{now_str()}] Solana WS error: {e}")

async def ingest_evm():
    """QuickNode WebSocket for new pool creation (PairCreated) events."""
    from config import QUICKNODE_WS_URL
    if not QUICKNODE_WS_URL or "your-quicknode" in QUICKNODE_WS_URL:
        print(f"[{now_str()}] QuickNode WS not configured, skipping EVM real-time ingestion.")
        return
    try:
        async with websockets.connect(QUICKNODE_WS_URL) as ws:
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "eth_subscribe",
                "params": ["logs", {"address": None, "topics": []}]
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"[{now_str()}] EVM real-time listener started.")
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if "params" in data:
                    log_jsonl("evm_raw.jsonl", {"time": now_str(), "data": data["params"]["result"]})
        except Exception as e:
            print(f"[{now_str()}] EVM WS error: {e}")

async def ingest_sui():
    """Sui event subscription for template::TEMPLATE creation."""
    from config import SUI_RPC_WS
    try:
        async with websockets.connect(SUI_RPC_WS) as ws:
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "suix_subscribeEvent",
                "params": [{"MoveModule": {"package": None, "module": "template"}}]
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"[{now_str()}] Sui real-time listener started.")
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if "params" in data:
                    log_jsonl("sui_raw.jsonl", {"time": now_str(), "data": data["params"]["result"]})
    except Exception as e:
        print(f"[{now_str()}] Sui WS error: {e}")

async def ingest_xrpl():
    """XRPL OfferCreate subscription."""
    from config import XRPL_WSS
    try:
        async with websockets.connect(XRPL_WSS) as ws:
            subscribe_msg = {
                "id": 4,
                "command": "subscribe",
                "streams": ["transactions"]
            }
            await ws.send(json.dumps(subscribe_msg))
            print(f"[{now_str()}] XRPL real-time listener started.")
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("transaction", {}).get("TransactionType") == "OfferCreate":
                    log_jsonl("xrpl_raw.jsonl", {"time": now_str(), "data": data["transaction"]})
    except Exception as e:
        print(f"[{now_str()}] XRPL WS error: {e}")

async def ingest_robinhood():
    """Robinhood polling (1 sec)."""
    import requests
    from config import POLL_INTERVAL_FILTERED
    url = "https://robinhood.com/api/crypto"
    print(f"[{now_str()}] Robinhood polling started.")
    while True:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                for item in resp.json().get("results", []):
                    log_jsonl("robinhood_raw.jsonl", {"time": now_str(), "data": item})
        except Exception as e:
            print(f"[{now_str()}] Robinhood error: {e}")
        await asyncio.sleep(1)
