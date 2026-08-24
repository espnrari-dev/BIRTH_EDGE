
import json, pathlib, re
m=json.loads(pathlib.Path("data/ml_model.json").read_text())
path=pathlib.Path("ml_model.py")
txt=path.read_text()
repl = f"""
        defaults = {{
            "holder_score": {m["weights"]["holder_score"]},
            "dev_score": {m["weights"]["dev_score"]},
            "lp_lock_score": {m["weights"]["lp_lock_score"]},
            "liquidity_usd": {m["weights"]["liquidity_usd"]},
        }}"""
txt = re.sub(r"\s*defaults = \{[^}]+\}", repl, txt, flags=re.DOTALL)
txt = txt.replace("self.bias = 0.0", f"self.bias = {m['bias']}  # LOCKED 33/30")
path.write_text(txt)
print(f"FIXED bias={m['bias']}")
