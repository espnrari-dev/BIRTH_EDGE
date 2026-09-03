import json, hashlib
DATA="data/ml_reflection.ml_reflection.json"
with open(DATA) as f: rows=json.load(f)["reflections"]
anomalies=sum(1 for r in rows if r.get("model_confidence") and r.get("calibration_quality") and r["model_confidence"]>0.8 and r["calibration_quality"]<0.3)
result={"layer":6,"name":"SELF_MONITORING","valid":anomalies<5,"anomalies_count":anomalies,"hash":hashlib.sha256(json.dumps({"anom":anomalies}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L6_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L6: {result}")
