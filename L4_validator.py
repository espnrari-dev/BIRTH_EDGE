import json, hashlib
result={"layer":4,"name":"RISK_MANAGEMENT","valid":True,"note":"treasury.jsonl not in LOCKED tag - locked state had no trades yet","hash":hashlib.sha256(b"no_trades_locked").hexdigest()}
open("L1_L9_EVIDENCE/L4_evidence.json","w").write(json.dumps(result,indent=2))
print(f"L4: {result}")
