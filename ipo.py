import asyncio, sqlite3
from datetime import datetime, timedelta
import aiohttp
from utils import now_str, log_jsonl

DB = "data/birth_edge.db"
URL = "https://api.nasdaq.com/api/ipo/calendar?date={date}"
HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json"}

def init_ipo_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS ipos (
        symbol TEXT PRIMARY KEY, company TEXT, price_range TEXT,
        shares_offered TEXT, expected_date TEXT, overall_score REAL,
        discovered_at TEXT, status TEXT)""")
    con.commit(); con.close()

def score_ipo(row):
    price=str(row.get('proposedSharePrice',''))
    s=50
    if '$' in price: s+=20
    if row.get('proposedTickerSymbol'): s+=10
    if 'M' in str(row.get('sharesOffered','')): s+=5
    return min(s,95)

async def fetch_month(session, date_str):
    url=URL.format(date=date_str)
    try:
        async with session.get(url, headers=HEADERS, timeout=15) as r:
            if r.status!=200: return []
            j=await r.json()
            if not j: return []
            data=j.get('data')
            if not data: return []
            # Nasdaq returns different keys
            rows = data.get('rows') or data.get('priced') or data.get('upcoming') or data.get('data') or []
            # some wrappers are dicts
            if isinstance(rows, dict):
                rows = rows.get('rows',[])
            return rows if isinstance(rows, list) else []
    except Exception as e:
        print(f"[{now_str()}] IPO fetch error {date_str} -> {e}")
    return []

async def ipo_loop():
    init_ipo_db()
    seen=set()
    print(f"[{now_str()}] IPO_EDGE loop starting, 6h interval")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                today=datetime.now()
                dates=[today.strftime("%Y-%m-%d"), (today+timedelta(days=30)).strftime("%Y-%m-%d")]
                new=0
                for d in dates:
                    rows=await fetch_month(session,d)
                    for row in rows:
                        if not isinstance(row, dict): continue
                        sym=row.get('proposedTickerSymbol') or row.get('symbol') or (row.get('companyName','')[:10])
                        if not sym or sym in seen: continue
                        seen.add(sym)
                        score=score_ipo(row)
                        con=sqlite3.connect(DB)
                        con.execute("INSERT OR IGNORE INTO ipos VALUES (?,?,?,?,?,?,?,?)",
                            (sym, row.get('companyName'), row.get('proposedSharePrice'), str(row.get('sharesOffered') or row.get('proposedSharesOffered')), row.get('expectedPriceDate') or d, score, now_str(), 'PASS' if score>=75 else 'pending'))
                        con.commit(); con.close()
                        log_jsonl("ipo.jsonl",{"symbol":sym,"score":score,"company":row.get('companyName'),"at":now_str()})
                        print(f"[{now_str()}] IPO {sym} {row.get('companyName')} {row.get('proposedSharePrice')} score {score}")
                        new+=1
                if new==0:
                    print(f"[{now_str()}] IPO scan {dates} - 0 new, {len(seen)} watched")
            except Exception as e:
                print(f"[{now_str()}] IPO loop error {e}")
            await asyncio.sleep(21600)

if __name__=="__main__":
    asyncio.run(ipo_loop())
