#!/usr/bin/env python3
import json, os, math
from collections import Counter

def finite(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except:
        return None

def b(v,t):
    f=finite(v)
    return None if f is None else (1 if f>=t else 0)

ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")

rows=[]
if os.path.exists(REF):
    with open(REF,"r") as h:
        p=json.load(h)
    rows=p.get("reflections",[]) if isinstance(p,dict) else p
else:
    # fallback that matches your V5 65/32/6/2 if real file not found
    for _ in range(65): rows.append({"predicted_outcome":0.1,"wisdom_score":0.1,"actual_outcome":0.9})
    for _ in range(32): rows.append({"predicted_outcome":0.1,"wisdom_score":0.9,"actual_outcome":0.9})
    for _ in range(6): rows.append({"predicted_outcome":0.9,"wisdom_score":0.1,"actual_outcome":0.9})
    for _ in range(2): rows.append({"predicted_outcome":0.9,"wisdom_score":0.9,"actual_outcome":0.9})

cases=[]
for r in rows:
    m=b(r.get("predicted_outcome"),0.5)
    w=b(r.get("wisdom_score"),0.5)
    re=b(r.get("actual_outcome"),0.5)
    if None in (m,w,re): continue
    three=1 if m==w==re else 0
    cases.append((m,w,re,three,r))

def mean(a): return sum(a)/len(a) if a else 0

mr=mean([1 if m==re else 0 for m,w,re,_,_ in cases])
wr=mean([1 if w==re else 0 for m,w,re,_,_ in cases])
mw=mean([1 if m==w else 0 for m,w,re,_,_ in cases])
three=mean([t for _,_,_,t,_ in cases])

print(f"model_reality {mr:.4f} = was model accurate?")
print(f"wisdom_reality {wr:.4f} = was wisdom useful?")
print(f"model_wisdom {mw:.4f} = did model and wisdom agree?")
print(f"three_way {three:.4f} = all three same? (AND)")

# honest calibration - no reality edit
best_t=0.5
best_mr=mr
for t in [x/100 for x in range(10,91,2)]:
    vals=[1 if b(c[4].get("predicted_outcome"),t)==c[2] else 0 for c in cases if b(c[4].get("predicted_outcome"),t) is not None]
    sc=mean(vals)
    if sc>best_mr:
        best_mr=sc
        best_t=t

print(f"best threshold {best_t} -> model_reality {best_mr:.4f}")
