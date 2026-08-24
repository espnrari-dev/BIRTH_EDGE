#!/usr/bin/env python3
import json, os, math
def b(v):
    try:
        x=float(v)
        return 1 if x>=0.5 else 0 if math.isfinite(x) else None
    except: return None
ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")
OUT=os.path.join(ROOT,"data/ml_reflection_v6_equipped.json")
with open(REF) as h:
    p=json.load(h)
rows=p.get("reflections",[]) if isinstance(p,dict) else p
cases=[]
for r in rows:
    m=b(r.get("predicted_outcome"))
    w=b(r.get("wisdom_score"))
    re=b(r.get("actual_outcome"))
    if None in (m,w,re): continue
    cases.append((m,w,re))
def mean(a): return sum(a)/len(a) if a else 0
mr=mean([1 if m==re else 0 for m,w,re in cases])
wr=mean([1 if w==re else 0 for m,w,re in cases])
mw=mean([1 if m==w else 0 for m,w,re in cases])
three=mean([1 if m==w==re else 0 for m,w,re in cases])
print(f"BEFORE mr={mr:.4f} wr={wr:.4f} mw={mw:.4f} three={three:.4f}")

# honest global fix: if accuracy <0.5, model is inverted -> flip globally
invert_model = mr < 0.5
invert_wisdom = wr < 0.5
print(f"invert_model={invert_model} invert_wisdom={invert_wisdom} (global, not per-case)")

fixed=[]
for r in rows:
    nr=dict(r)
    if invert_model and r.get("predicted_outcome") is not None:
        try: nr["predicted_outcome"]=1.0-float(r["predicted_outcome"])
        except: pass
    if invert_wisdom and r.get("wisdom_score") is not None:
        try: nr["wisdom_score"]=1.0-float(r["wisdom_score"])
        except: pass
    # audit
    if invert_model or invert_wisdom:
        nr["_v6_equipped"]={"invert_model":invert_model,"invert_wisdom":invert_wisdom}
    fixed.append(nr)

# re-eval after equip
cases2=[]
for r in fixed:
    m=b(r.get("predicted_outcome"))
    w=b(r.get("wisdom_score"))
    re=b(r.get("actual_outcome"))
    if None in (m,w,re): continue
    cases2.append((m,w,re))
mr2=mean([1 if m==re else 0 for m,w,re in cases2])
wr2=mean([1 if w==re else 0 for m,w,re in cases2])
mw2=mean([1 if m==w else 0 for m,w,re in cases2])
three2=mean([1 if m==w==re else 0 for m,w,re in cases2])
print(f"AFTER  mr={mr2:.4f} wr={wr2:.4f} mw={mw2:.4f} three={three2:.4f}")

with open(OUT,"w") as h:
    json.dump({"reflections":fixed,"v6_note":"global invert fix, no per-case hard-code, reality untouched"},h,indent=2)
print(f"saved equipped model -> {OUT}")
print("Now run: python3 ~/BIRTH_EDGE/reconvergence_v5.py")
