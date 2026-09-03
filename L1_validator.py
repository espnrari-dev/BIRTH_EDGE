import json, hashlib
DATA="data/ml_reflection.ml_reflection.json"
with open(DATA) as f: rows=json.load(f)["reflections"]
required=["actual_outcome","calibration_quality","confidence_alignment","correct","decision","discernment_quality","evidence_agreement","evidence_strength","memory_id","memory_novelty","metadata","model_confidence","outcome_class","outcome_magnitude","predicted_outcome"]
missing=sum(1 for r in rows if any(k not in r for k in required))
result={"layer":1,"name":"PERCEPTION","valid":missing==0,"missing_rows":missing,"hash":hashlib.sha256(json.dumps({"missing":missing}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L1_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L1: {result}")
