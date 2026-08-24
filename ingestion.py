import asyncio
import requests
from utils import now_str, log_jsonl

def fetch_json(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[{now_str()}] fetch error {url}: {e}")
    return None

async def ingest_robinhood():
    print(f"[{now_str()}] Robinhood polling started.")
    while True:
        data = fetch_json("https://robinhood.com/api/crypto")
        if data:
            results = data.get("results", [])
            for item in results:
                log_jsonl("robinhood_raw.jsonl", {"time": now_str(), "data": item})
            print(f"[{now_str()}] Robinhood poll: {len(results)} items")
        await asyncio.sleep(30)

async def ingest_stock_platforms():
    print(f"[{now_str()}] Stock platforms poller started.")
    while True:
        await asyncio.sleep(60)

async def labelbase_logger():
    print(f"[{now_str()}] Labelbase heartbeat started.")
    while True:
        log_jsonl("labelbase.jsonl", {"time": now_str(), "status": "alive"})
        await asyncio.sleep(60)
