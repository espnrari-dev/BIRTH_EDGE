import asyncio
import json
import websockets
from datetime import datetime
from utils import now_str, log_jsonl

PUMP_WS_URL = "wss://pumpportal.fun/ws"

async def realtime_pumpfun(queue):
    """
    Connect to PumpPortal WebSocket and listen for new token mints.
    Pushes token mint address into the async queue for processing.
    """
    print(f"[{now_str()}] PumpPortal realtime listener starting...")
    while True:
        try:
            async with websockets.connect(PUMP_WS_URL) as ws:
                # Subscribe to new token events
                subscribe_msg = {"method": "subscribeNewToken"}
                await ws.send(json.dumps(subscribe_msg))
                print(f"[{now_str()}] Subscribed to PumpPortal newToken stream.")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    # PumpPortal sends events like {"type":"newToken","data":{"mint":"..."}}
                    if data.get("type") == "newToken":
                        mint = data.get("data", {}).get("mint")
                        if mint:
                            log_jsonl("realtime_births.jsonl", {
                                "time": now_str(),
                                "chain": "solana",
                                "addr": mint,
                                "source": "pumpportal"
                            })
                            await queue.put({
                                "chain": "solana",
                                "addr": mint,
                                "symbol": "?",
                                "liquidity_usd": 0,
                                "creator": None,
                                "discovered_at": now_str()
                            })
                            print(f"[{now_str()}] ⚡ REALTIME BIRTH: {mint[:8]}.. (Pump.fun)")
        except Exception as e:
            print(f"[{now_str()}] PumpPortal WS error: {e}")
            await asyncio.sleep(5)  # retry
