import json, hashlib
DATA="data/ml_reflection.ml_reflection.json"
with open(DATA) as f: rows=json.load(f)["reflections"]
out_of_range=0
for r in rows:
    for fld in ["calibration_quality","confidence_alignment","discernment_quality","evidence_agreement","evidence_strength","model_confidence"]:
        v=r.get(fld)
        if v is not None and not (0 <= v <= 1): out_of_range+=1
result={"layer":2,"name":"FEATURE_EXTRACT","valid":out_of_range==0,"out_of_range_count":out_of_range,"hash":hashlib.sha256(json.dumps({"oor":out_of_range}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L2_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L2: {result}")
