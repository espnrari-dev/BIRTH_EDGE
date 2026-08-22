import json
import os
import time
from datetime import datetime
import requests
import aiohttp

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch_json_sync(url, timeout=10):
    """Synchronous JSON fetch (for legacy scanners)."""
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[{now_str()}] fetch failed {url} -> {resp.status_code}")
            return None
    except Exception as e:
        print(f"[{now_str()}] fetch error {url} -> {e}")
        return None

async def fetch_json(url, timeout=10):
    """Asynchronous JSON fetch."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"[{now_str()}] fetch failed {url} -> {resp.status}")
                    return None
    except Exception as e:
        print(f"[{now_str()}] fetch error {url} -> {e}")
        return None

def log_jsonl(filename, data):
    """Append a dictionary as a JSON line to logs/filename."""
    filepath = os.path.join("logs", filename)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def send_telegram(message):
    """Send Telegram message if token and chat_id are configured."""
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"[{now_str()}] telegram error: {e}")
