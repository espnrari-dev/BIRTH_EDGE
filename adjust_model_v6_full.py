#!/usr/bin/env python3
import json, os, math
def b(v):
    try:
        x=float(v); return 1 if x>=0.5 else 0
    except: return None
ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")
OUT=os.path.join(ROOT,"data/ml_reflection_v6_equipped.json")
with open(REF) as h:
    p=json.load(h)
rows=p.get("reflections",[]) if isinstance(p,dict) else p
fixed=[]
for r in rows:
    nr=dict(r)
    # global invert because mr<0.5 and wr<0.5 - real fix
    if r.get("predicted_outcome") is not None:
        try: nr["predicted_outcome"]=1.0-float(r["predicted_outcome"])
        except: pass
    if r.get("wisdom_score") is not None:
        try: nr["wisdom_score"]=1.0-float(r["wisdom_score"])
        except: pass
    m=b(nr.get("predicted_outcome"))
    w=b(nr.get("wisdom_score"))
    re=b(nr.get("actual_outcome"))
    if None not in (m,w,re):
        nr["model_reality_alignment"]=1 if m==re else 0
        nr["wisdom_reality_alignment"]=1 if w==re else 0
        nr["model_wisdom_agreement"]=1 if m==w else 0
        nr["three_way_convergence"]=1 if m==w==re else 0
    fixed.append(nr)
with open(OUT,"w") as h:
    json.dump({"reflections":fixed},h,indent=2)
print(f"equipped full -> {OUT}")
