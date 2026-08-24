import requests, json, os, datetime
REF=os.path.expanduser("~/BIRTH_EDGE/data/ml_reflection.json")
j=json.load(open(REF))
rows=j.get('reflections',j) if isinstance(j,dict) else j
start=len(rows)

r=requests.get("https://api.geckoterminal.com/api/v2/networks/trending_pools", timeout=15).json()
for pool in r.get('data',[]):
    attrs=pool.get('attributes',{})
    ch_str=attrs.get('price_change_percentage',{}).get('h24','0')
    try:
        ch=float(ch_str)
    except:
        continue
    if ch > 50:  # your pump rule
        name=attrs.get('name','')[:30]
        network=pool.get('relationships',{}).get('network',{}).get('data',{}).get('id','')
        # TODO: replace dummy features with your real extractor
        feat=[0.5,0.5,0.5,0.5]
        rows.append({
            "timestamp": datetime.datetime.utcnow().isoformat()+"Z",
            "symbol": name,
            "chain": network,
            "model_replay": {"source_features": feat, "model_prediction": 0.0},
            "wisdom_score": 0.6,
            "actual_outcome": 1,
            "change_24h": ch,
            "source": "free_geckoterminal"
        })

json.dump({"reflections":rows}, open(REF,'w'), indent=2)
pos=sum(1 for rr in rows if float(rr.get('actual_outcome',0))>=0.5)
print(f"{start} -> {len(rows)} total, positives {pos}/30  (+{len(rows)-start} new)")
for rr in rows[start:]:
    print(f"  + {rr['symbol']} {rr['change_24h']}%")
