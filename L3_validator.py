import json, hashlib
DATA="data/ml_reflection.ml_reflection.json"
with open(DATA) as f: rows=json.load(f)["reflections"]
labeled=[r for r in rows if r.get("metadata",{}).get("test") in ("known_positive","known_negative","unexpected_positive")]
if labeled:
    acc=sum(1 for r in labeled if r.get("correct"))/len(labeled)
    pos=[r for r in labeled if r["metadata"]["test"]=="known_positive"]
    neg=[r for r in labeled if r["metadata"]["test"]=="known_negative"]
    if neg and pos:
        tn=sum(1 for r in neg if r.get("correct")); fp=sum(1 for r in pos if not r.get("correct"))
        spec=tn/(tn+fp) if (tn+fp)>0 else None
    else: spec=None
else: acc=None; spec=None
result={"layer":3,"name":"DECISION_ENGINE","valid":acc is not None and acc>=0.7 and spec is not None,"accuracy":acc,"specificity":spec,"hash":hashlib.sha256(json.dumps({"acc":acc,"spec":spec}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L3_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L3: {result}")
