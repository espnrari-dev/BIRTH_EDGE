import requests, json, os, datetime, math
REF=os.path.expanduser("~/BIRTH_EDGE/data/ml_reflection.json")
j=json.load(open(REF))
rows=j.get('reflections',j) if isinstance(j,dict) else j
before=len(rows)
rows=[r for r in rows if not (r.get('source')=='free_geckoterminal' and r.get('model_replay',{}).get('source_features')==[0.5,0.5,0.5,0.5])]
print(f"removed {before-len(rows)} dummy")
r=requests.get("https://api.geckoterminal.com/api/v2/networks/trending_pools?page=1", timeout=15).json()
added=0
for pool in r.get('data',[]):
    a=pool.get('attributes',{})
    try:
        ch=float(a.get('price_change_percentage',{}).get('h24','0') or 0)
        if ch<50: continue
        vol=float(a.get('volume_usd',{}).get('h24','0') or 0)
        liq=float(a.get('reserve_in_usd','0') or 0)
        txns=a.get('transactions',{}).get('h24',{})
        buys=int(txns.get('buys',0) or 0); sells=int(txns.get('sells',0) or 0)
        feat=[round(math.log10(vol+1)/6,4), round(min(ch/1000,1),4), round(math.log10(liq+1)/6,4), round(buys/(buys+sells+1),4)]
        rows.append({"timestamp":datetime.datetime.now(datetime.timezone.utc).isoformat(),"symbol":a.get('name','')[:30],"chain":pool.get('relationships',{}).get('network',{}).get('data',{}).get('id',''),"model_replay":{"source_features":feat,"model_prediction":0.0},"wisdom_score":0.6,"actual_outcome":1,"change_24h":ch,"source":"free_geckoterminal_real"})
        added+=1
    except: pass
json.dump({"reflections":rows}, open(REF,'w'), indent=2)
pos=sum(1 for rr in rows if float(rr.get('actual_outcome',0))>=0.5)
print(f"{before}->{len(rows)} total, {pos}/30 (+{added} REAL)")
