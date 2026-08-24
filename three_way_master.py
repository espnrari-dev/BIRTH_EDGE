#!/usr/bin/env python3
import json, sys, statistics
import ml_model

DATA_PATH = "data/ml_reflection.json"
EPOCHS=40

def extract_features(row):
    feats={}
    src=row.get("model_replay",{}).get("source_features",{})
    for name in ml_model.FEATURE_NAMES:
        if name in src and isinstance(src[name],dict):
            feats[name]=src[name].get("raw_value")
        elif name in row:
            feats[name]=row[name]
    return feats

def b(v):
    try: return 1 if float(v)>=0.5 else 0
    except: return None

with open(DATA_PATH) as f:
    payload=json.load(f)
rows=payload.get("reflections",payload) if isinstance(payload,dict) else payload

pairs=[]
for r in rows:
    actual=r.get("actual_outcome")
    if actual is None: continue
    feats=extract_features(r)
    if len(feats)==len(ml_model.FEATURE_NAMES) and all(v is not None for v in feats.values()):
        pairs.append((r, feats, actual))

print(f"usable {len(pairs)}/105")

# train same as full_reequip
positives=[(f,y) for _,f,y in pairs if float(y)>=0.5]
negatives=[(f,y) for _,f,y in pairs if float(y)<0.5]
pos_weight=len(negatives)/len(positives)

model=ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
for _ in range(EPOCHS):
    for feats,t in positives:
        for _ in range(round(pos_weight)):
            model.update(feats,t)
    for feats,t in negatives:
        model.update(feats,t)

# now honest three-way: model_pred vs wisdom vs reality
from collections import Counter
pat=Counter()
mr=wr=mw=three=0
for row, feats, actual in pairs:
    m_pred=model.predict(feats)
    w=b(row.get("wisdom_score"))
    re=b(actual)
    if None in (w,re): continue
    pat[(m_pred,w,re)]+=1
    if m_pred==re: mr+=1
    if w==re: wr+=1
    if m_pred==w: mw+=1
    if m_pred==w==re: three+=1

for k,v in pat.most_common():
    print(f"MODEL={k[0]} WISDOM={k[1]} REALITY={k[2]} COUNT={v} FULL={k[0]==k[1]==k[2]}")
n=len(pairs)
print(f"model_reality={mr/n:.4f} wisdom_reality={wr/n:.4f} model_wisdom={mw/n:.4f} three_way={three/n:.4f} n={n}")
