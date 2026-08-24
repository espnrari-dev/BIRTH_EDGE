import requests, json, os, datetime

ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")

def load_ref():
    j=json.load(open(REF))
    return j.get('reflections',j) if isinstance(j,dict) else j

def save_ref(rows):
    json.dump({"reflections": rows}, open(REF,'w'), indent=2)

rows=load_ref()
start=len(rows)

# 1. CoinGecko top gainers - free, no key
try:
    r=requests.get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=percent_change_24h_desc&per_page=100&page=1&price_change_percentage=24h", timeout=15)
    for c in r.json():
        change=c.get('price_change_percentage_24h') or 0
        if change > 200:  # your pump rule
            # fake 4-dim features for now - replace with your real feature extractor
            feat=[c.get('total_volume',0)/1e6 % 1, change/1000 % 1, 0.5, 0.5]
            rows.append({
                "timestamp": datetime.datetime.utcnow().isoformat()+"Z",
                "symbol": c['symbol'].upper(),
                "chain": "coingecko",
                "model_replay": {"source_features": feat, "model_prediction": 0.0},
                "wisdom_score": 0.6,
                "actual_outcome": 1,
                "change_24h": change,
                "source": "free_coingecko"
            })
    print(f"coingecko added")
except Exception as e:
    print("coingecko fail", e)

# 2. DexScreener trending - free, no key
try:
    r=requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
    for t in r.json()[:100]:
        # need priceChange from pair lookup
        pass
    # better: search for solana pairs
    r=requests.get("https://api.dexscreener.com/latest/dex/search/?q=SOL", timeout=15)
    for p in r.json().get('pairs',[])[:50]:
        change=float(p.get('priceChange',{}).get('h24',0) or 0)
        if change > 200:
            feat=[float(p.get('liquidity',{}).get('usd',0))/1e6 % 1, 0.5, 0.5, 0.5]
            rows.append({
                "timestamp": datetime.datetime.utcnow().isoformat()+"Z",
                "symbol": p.get('baseToken',{}).get('symbol','UNK'),
                "chain": p.get('chainId','unknown'),
                "model_replay": {"source_features": feat, "model_prediction": 0.0},
                "wisdom_score": 0.6,
                "actual_outcome": 1,
                "change_24h": change,
                "source": "free_dexscreener"
            })
    print(f"dexscreener added")
except Exception as e:
    print("dexscreener fail", e)

save_ref(rows)
pos=sum(1 for r in rows if float(r.get('actual_outcome',0))>=0.5)
print(f"{start} -> {len(rows)} total, positives {pos}/30")
