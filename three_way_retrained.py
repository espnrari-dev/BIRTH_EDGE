#!/usr/bin/env python3
import json, os, math
def b(v):
    try:
        x=float(v)
        return 1 if math.isfinite(x) and x>=0.5 else 0 if math.isfinite(x) else None
    except: return None

ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")
with open(REF) as h:
    p=json.load(h)
rows=p.get("reflections",[]) if isinstance(p,dict) else p

usable=[]
dropped=0
for r in rows:
    if r.get("model_replay") and r["model_replay"].get("source_features") is None:
        dropped+=1
        continue
    # require all three
    m=b(r.get("predicted_outcome"))
    w=b(r.get("wisdom_score"))
    re=b(r.get("actual_outcome"))
    if None in (m,w,re):
        dropped+=1
        continue
    usable.append((m,w,re,r))

print(f"usable {len(usable)} dropped {dropped} total {len(rows)}")
mr=sum(1 for m,w,re,_ in usable if m==re)/len(usable)
wr=sum(1 for m,w,re,_ in usable if w==re)/len(usable)
mw=sum(1 for m,w,re,_ in usable if m==w)/len(usable)
three=sum(1 for m,w,re,_ in usable if m==w==re)/len(usable)

# breakdown by reality
from collections import Counter
patterns=Counter((m,w,re) for m,w,re,_ in usable)
for pat,cnt in patterns.most_common():
    print(f"MODEL={pat[0]} WISDOM={pat[1]} REALITY={pat[2]} COUNT={cnt} FULL={pat[0]==pat[1]==pat[2]}")

print(f"model_reality={mr:.4f} wisdom_reality={wr:.4f} model_wisdom={mw:.4f} three_way={three:.4f}")
