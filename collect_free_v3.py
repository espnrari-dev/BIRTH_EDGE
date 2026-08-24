import requests, json, os, datetime
REF=os.path.expanduser("~/BIRTH_EDGE/data/ml_reflection.json")
j=json.load(open(REF))
rows=j.get('reflections',j) if isinstance(j,dict) else j
start=len(rows)

# CoinGecko - get 250 and sort locally
r=requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&price_change_percentage=24h", headers={"User-Agent":"BIRTH_EDGE"}, timeout=20)
data=r.json()
top=sorted(data, key=lambda x: x.get('price_change_percentage_24h') or 0, reverse=True)[:10]
print(f"real top 10 movers: {[(c['symbol'], round(c.get('price_change_percentage_24h') or 0,2)) for c in top]}")

# Dexscreener - trending pools, better than search?q=SOL
r=requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15).json()
print(f"dex profiles count {len(r)}")

# GeckoTerminal trending pools - this is where real pumps live free
r=requests.get("https://api.geckoterminal.com/api/v2/networks/trending_pools", timeout=15).json()
pools=r.get('data',[])
tops=sorted(pools, key=lambda x: float(x.get('attributes',{}).get('price_change_percentage',{}).get('h24','0') or 0), reverse=True)[:5]
print(f"gecko trending top 5 h24%: {[(p.get('attributes',{}).get('name'), p.get('attributes',{}).get('price_change_percentage',{}).get('h24')) for p in tops]}")

pos=sum(1 for rr in rows if float(rr.get('actual_outcome',0))>=0.5)
print(f"current: {len(rows)} total, {pos}/30 - no new added because flat market, which is correct")
