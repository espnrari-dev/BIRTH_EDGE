#!/usr/bin/env python3
import json, os, sys, math
def b(v):
    try:
        x=float(v); return 1 if x>=0.5 else 0
    except: return None
path=sys.argv[1] if len(sys.argv)>1 else os.path.expanduser("~/BIRTH_EDGE/data/ml_reflection.json")
with open(path) as h:
    p=json.load(h)
rows=p.get("reflections",[]) if isinstance(p,dict) else p
usable=[]
for r in rows:
    m=b(r.get("predicted_outcome")); w=b(r.get("wisdom_score")); re=b(r.get("actual_outcome"))
    if None in (m,w,re): continue
    usable.append((m,w,re))
from collections import Counter
cnt=Counter((m,w,re) for m,w,re in usable)
for k,v in cnt.most_common(): print(f"{k} COUNT={v} FULL={k[0]==k[1]==k[2]}")
print(f"three_way={sum(1 for m,w,re in usable if m==w==re)/len(usable):.4f} n={len(usable)}")
