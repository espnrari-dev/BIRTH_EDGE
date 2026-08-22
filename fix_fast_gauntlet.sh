#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/BIRTH_EDGE"

cp aegis_rule_miner.py aegis_rule_miner.py.pre_fix_fast 2>/dev/null || true
cp full_novelty_gauntlet.py full_novelty_gauntlet.py.pre_fix_fast 2>/dev/null || true

python - <<'PY'
from pathlib import Path

p = Path("aegis_rule_miner.py")
s = p.read_text()

old = '    candidates = [(a,b,c,d) for a,b,c,d in top]\n'
new = '    candidates = list(top)\n'

if old not in s:
    raise SystemExit("ERROR: expected broken candidates line not found")

s = s.replace(old, new, 1)

old = '''            pred = tuple(x and y for x,y in zip(top[i][3] and top[i][4], top[j][4]))
            rule = Rule((r1.predicates[0], r2.predicates[0]))
'''

new = '''            pred1 = top[i][4]
            pred2 = top[j][4]
            pred = tuple(x and y for x, y in zip(pred1, pred2))
            rule = Rule((r1.predicates[0], r2.predicates[0]))
'''

if old not in s:
    raise SystemExit("ERROR: expected broken pair logic not found")

s = s.replace(old, new, 1)
p.write_text(s)

p = Path("full_novelty_gauntlet.py")
s = p.read_text()

old = '''    _, bal, acc, best, _ = candidates[0]
'''
# This is actually already correct, so just verify it exists.
if old not in Path("aegis_rule_miner.py").read_text():
    raise SystemExit("ERROR: candidate tuple structure verification failed")

print("AEGIS Rule Miner repaired successfully.")
PY

python -m py_compile aegis_rule_miner.py full_novelty_gauntlet.py

echo
echo "REPAIR COMPLETE"
echo "Running smoke test..."

python - <<'PY'
import aegis_rule_miner as arm

rows = []
for i in range(100):
    liquidity = i * 300
    holder = i % 30
    rows.append({
        "initial_liquidity_usd": liquidity,
        "holder_score": holder,
        "dev_score": 0,
        "lp_lock_score": 0,
        "tax_score": 0,
        "overall_score": 0,
        "pumped": liquidity > 12000 and holder > 15
    })

expr, acc = arm.evolve_rule(rows)
print("RULE:", expr.to_string() if expr else None)
print("ACCURACY:", round(acc, 4))

if expr is None:
    raise SystemExit("SMOKE TEST FAILED: no rule discovered")

print("SMOKE TEST PASSED")
PY

echo
echo "NOW RUN:"
echo "cd ~/BIRTH_EDGE && python -u full_novelty_gauntlet.py 2>&1 | tee fast_gauntlet.log"
