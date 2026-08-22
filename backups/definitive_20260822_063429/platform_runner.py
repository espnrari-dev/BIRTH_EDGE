import asyncio
from utils import now_str
import ingestion

async def safe(name, coro):
    try:
        await coro()
    except Exception as e:
        print(f"[{now_str()}] {name} error: {e}")

async def main():
    tasks = []
    for fn_name in ['ingest_robinhood', 'ingest_stock_platforms', 'labelbase_logger']:
        if hasattr(ingestion, fn_name):
            tasks.append(safe(fn_name, getattr(ingestion, fn_name)))
    if not tasks:
        print("No ingestion functions found; check ingestion.py")
        return
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
