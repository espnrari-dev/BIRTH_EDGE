import json, hashlib
reports=[]
for i in range(1,9):
    with open(f"L1_L9_EVIDENCE/L{i}_evidence.json") as f: reports.append(json.load(f))
all_valid=all(r.get("valid",False) for r in reports)
result={"layer":9,"name":"SOVEREIGNTY","valid":all_valid,"all_layers_valid":all_valid,"hash":hashlib.sha256(json.dumps({"all_valid":all_valid}).encode()).hexdigest()}
open("L1_L9_EVIDENCE/L9_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L9: {result}")
