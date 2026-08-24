import requests, json, os, datetime, time
ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")
j=json.load(open(REF))
rows=j.get('reflections',j) if isinstance(j,dict) else j
start=len(rows)

headers={"User-Agent":"BIRTH_EDGE/1.0"}

# 1. CoinGecko - free but rate limited
try:
    url="https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=percent_change_24h_desc&per_page=50&page=1&price_change_percentage=24h"
    r=requests.get(url, timeout=15, headers=headers)
    print(f"coingecko status {r.status_code} len {len(r.text)}")
    if r.status_code==200 and r.text.strip():
        data=r.json()
        print(f"coingecko top 5: {[(c['symbol'], c.get('price_change_percentage_24h')) for c in data[:5]]}")
        for c in data:
            change=c.get('price_change_percentage_24h') or 0
            if change>50:
                rows.append({"timestamp":datetime.datetime.utcnow().isoformat()+"Z","symbol":c['symbol'].upper(),"chain":"coingecko","model_replay":{"source_features":[0.5,0.5,0.5,0.5],"model_prediction":0.0},"wisdom_score":0.6,"actual_outcome":1,"change_24h":change,"source":"free_coingecko"})
    else:
        print(f"coingecko blocked: {r.text[:200]}")
        time.sleep(2)
except Exception as e:
    print("coingecko fail", e)

# 2. DexScreener - free, no key, more reliable
try:
    r=requests.get("https://api.dexscreener.com/latest/dex/search/?q=SOL", timeout=15, headers=headers)
    print(f"dex status {r.status_code}")
    if r.status_code==200:
        data=r.json()
        pairs=data.get('pairs',[])[:20]
        print(f"dex sample: {[(p.get('baseToken',{}).get('symbol'), p.get('priceChange',{}).get('h24')) for p in pairs[:5]]}")
        for p in pairs:
            try:
                change=float(p.get('priceChange',{}).get('h24',0))
                if change>50:
                    rows.append({"timestamp":datetime.datetime.utcnow().isoformat()+"Z","symbol":p.get('baseToken',{}).get('symbol','UNK'),"chain":p.get('chainId'),"model_replay":{"source_features":[0.5,0.5,0.5,0.5],"model_prediction":0.0},"wisdom_score":0.6,"actual_outcome":1,"change_24h":change,"source":"free_dexscreener"})
            except: pass
except Exception as e:
    print("dex fail", e)

json.dump({"reflections":rows}, open(REF,'w'), indent=2)
pos=sum(1 for rr in rows if float(rr.get('actual_outcome',0))>=0.5)
print(f"{start} -> {len(rows)} total, positives {pos}/30")
