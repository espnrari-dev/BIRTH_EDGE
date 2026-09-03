import json, hashlib
DATA="data/ml_reflection.ml_reflection.json"
with open(DATA) as f: rows=json.load(f)["reflections"]
vals=[r.get("memory_novelty") for r in rows if r.get("memory_novelty") is not None]
var=sum((v-sum(vals)/len(vals))**2 for v in vals)/len(vals) if vals else None
result={"layer":7,"name":"ADVERSARIAL","valid":var is not None,"field_variance":var,"hash":hashlib.sha256(json.dumps({"var":var}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L7_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L7: {result}")
