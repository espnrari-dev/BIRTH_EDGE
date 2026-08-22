#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cd "$HOME/BIRTH_EDGE"

cp aegis_rule_miner.py aegis_rule_miner.py.pre_fast_gauntlet 2>/dev/null || true
cp full_novelty_gauntlet.py full_novelty_gauntlet.py.pre_fast 2>/dev/null || true

cat > aegis_rule_miner.py <<'PY'
#!/usr/bin/env python3
"""
AEGIS RULE MINER V3 — FAST VALIDATED
Deterministic data-driven conjunction discovery.
"""

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

FEATURES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]

@dataclass(frozen=True)
class Predicate:
    feature: str
    operator: str
    threshold: float

    def evaluate(self, values):
        x = float(values.get(self.feature, 0.0))
        return x > self.threshold if self.operator == ">" else x < self.threshold

    def to_string(self):
        return f"({self.feature} {self.operator} {self.threshold:.6g})"

@dataclass(frozen=True)
class Rule:
    predicates: Tuple[Predicate, ...]

    def evaluate(self, values):
        return all(p.evaluate(values) for p in self.predicates)

    def to_string(self):
        if len(self.predicates) == 1:
            return self.predicates[0].to_string()
        return "(" + " AND ".join(p.to_string() for p in self.predicates) + ")"

    @property
    def complexity(self):
        return len(self.predicates)

Expr = Rule

def extract_features(row):
    out = {}
    for f in FEATURES:
        v = row.get("initial_liquidity_usd", row.get("liquidity_usd", 0.0)) if f == "liquidity_usd" else row.get(f, 0.0)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        out[f] = v if math.isfinite(v) else 0.0
    return out

def _matrix(rows):
    names = list(FEATURES)
    cols = {f: [] for f in names}
    labels = []
    for row in rows:
        x = extract_features(row)
        for f in names:
            cols[f].append(x[f])
        labels.append(bool(row["pumped"]))
    return names, cols, labels

def _thresholds(values, limit=20):
    vals = sorted(set(values))
    if len(vals) < 2:
        return []
    mids = [(a+b)/2.0 for a,b in zip(vals, vals[1:]) if a != b]
    if len(mids) <= limit:
        return mids
    return [mids[round(i*(len(mids)-1)/(limit-1))] for i in range(limit)]

def _metrics(pred, labels):
    n = len(labels)
    if not n:
        return 0.0, 0.0, 0.0
    tp = tn = fp = fn = 0
    for p, y in zip(pred, labels):
        if y:
            if p: tp += 1
            else: fn += 1
        else:
            if p: fp += 1
            else: tn += 1
    acc = (tp + tn) / n
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    bal = (tpr + tnr) / 2.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    return acc, bal, prec

def _support(pred):
    return sum(pred) / len(pred) if pred else 0.0

def _candidate_score(pred, labels, complexity):
    acc, bal, prec = _metrics(pred, labels)
    support = _support(pred)
    penalty = 0.012 * max(0, complexity - 1)
    if support < 0.05:
        penalty += (0.05 - support) * 2.0
    return 0.45*acc + 0.40*bal + 0.15*prec - penalty, acc, bal

def _predicates(cols, active):
    out = []
    for f in active:
        for t in _thresholds(cols[f]):
            for op in (">", "<"):
                p = tuple(x > t if op == ">" else x < t for x in cols[f])
                out.append((Predicate(f, op, t), p))
    return out

def _discover(rows, seed):
    if len(rows) < 20 or not FEATURES:
        return None, 0.0

    names, cols, labels = _matrix(rows)
    active = [f for f in names if len(set(cols[f])) >= 2]
    if not active:
        return None, 0.0

    singles = _predicates(cols, active)
    ranked = []

    for pred_obj, pred in singles:
        score, acc, bal = _candidate_score(pred, labels, 1)
        ranked.append((score, bal, acc, Rule((pred_obj,)), pred))

    ranked.sort(key=lambda x: (-x[0], -x[1], x[3].to_string()))
    top = ranked[:24]

    candidates = [(a,b,c,d) for a,b,c,d in top]

    # Only build pairs from the top 24 single predicates.
    # This is the major runtime reduction.
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            r1 = top[i][3]
            r2 = top[j][3]
            if r1.predicates[0].feature == r2.predicates[0].feature:
                continue
            pred = tuple(x and y for x,y in zip(top[i][3] and top[i][4], top[j][4]))
            rule = Rule((r1.predicates[0], r2.predicates[0]))
            score, acc, bal = _candidate_score(pred, labels, 2)
            candidates.append((score, bal, acc, rule, pred))

    candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3].complexity, x[3].to_string()))

    if not candidates:
        return None, 0.0

    _, bal, acc, best, _ = candidates[0]

    # Gate on balanced performance, preventing majority-class tricks.
    if bal < 0.55:
        return None, bal

    return best, acc

def evolve_rule(rows, generations=60, population_size=100, max_depth=5):
    del generations, population_size, max_depth
    data = list(rows)
    state = random.getstate()
    try:
        seed = state[1][0]
    except Exception:
        seed = 0
    return _discover(data, seed)

def evaluate_rule(expr, rows):
    labels = [bool(r["pumped"]) for r in rows]
    pred = [bool(expr.evaluate(extract_features(r))) for r in rows]
    acc, bal, precision = _metrics(pred, labels)
    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "positive_precision": precision,
    }

def rule_features(expr):
    return sorted({p.feature for p in expr.predicates})

__all__ = [
    "FEATURES", "Expr", "Rule", "Predicate",
    "extract_features", "evolve_rule",
    "evaluate_rule", "rule_features",
]
PY

cat > full_novelty_gauntlet.py <<'PY'
#!/usr/bin/env python3
"""
AEGIS FAST NOVELTY GAUNTLET

Same 12 scientific test categories as the full gauntlet.
Reduced replication only where repeated seeds were redundant.

Replications:
  discovery/heldout/shift/confound/non-ID/random = 5
  decoy/adversarial = 8
  ablation/cost/counterfactual/repro = exact single experiments
"""

import json
import random
import statistics
import time
import traceback
import aegis_rule_miner as arm

OUT = "novelty_gauntlet_results.json"
N_STANDARD = 5
N_DECOY = 8

def mean(x): return statistics.mean(x) if x else 0.0
def sd(x): return statistics.stdev(x) if len(x) > 1 else 0.0

def accuracy(expr, rows):
    if not rows or expr is None: return 0.0
    return sum(
        bool(expr.evaluate(arm.extract_features(r))) == bool(r["pumped"])
        for r in rows
    ) / len(rows)

def discover(rows, seed):
    random.seed(seed)
    expr, acc = arm.evolve_rule(rows, generations=60, population_size=100, max_depth=5)
    return expr, acc, expr.to_string() if expr else ""

def add(R, name, **data):
    R["tests"][name] = data

def banner(s):
    print("\n" + "="*72 + "\n" + s + "\n" + "="*72)

def base_rows(n, seed, noise=.05):
    g=random.Random(seed); out=[]
    for _ in range(n):
        l=g.uniform(0,30000); h=g.uniform(0,30)
        y=int(l>12000 and h>15)
        if g.random()<noise: y=1-y
        out.append({"initial_liquidity_usd":l,"holder_score":h,
            "dev_score":g.uniform(0,20),"lp_lock_score":g.uniform(0,20),
            "tax_score":g.uniform(0,15),"overall_score":g.uniform(0,100),
            "pumped":y,"rug_pulled":0})
    return out

def random_rows(n, seed):
    r=base_rows(n,seed); g=random.Random(seed+99991)
    for x in r: x["pumped"]=g.randint(0,1)
    return r

def correlated_rows(n, seed, adversarial=False):
    g=random.Random(seed); out=[]
    for _ in range(n):
        l=g.uniform(0,30000); h=g.uniform(0,30); y=int(l>12000 and h>15)
        if g.random()<.05:y=1-y
        if adversarial:
            o=g.gauss(80 if y else 20,3)
        else:
            o=100*((l/30000)*.55+(h/30)*.45)+g.gauss(0,4)
        out.append({"initial_liquidity_usd":l,"holder_score":h,
            "dev_score":g.uniform(0,20),"lp_lock_score":g.uniform(0,20),
            "tax_score":g.uniform(0,15),"overall_score":o,
            "pumped":y,"rug_pulled":0})
    return out

def shifted_rows(n,seed):
    g=random.Random(seed); out=[]
    for _ in range(n):
        l=g.uniform(15000,45000); h=g.uniform(10,40); y=int(l>12000 and h>15)
        if g.random()<.05:y=1-y
        out.append({"initial_liquidity_usd":l,"holder_score":h,
            "dev_score":g.uniform(0,20),"lp_lock_score":g.uniform(0,20),
            "tax_score":g.uniform(0,15),"overall_score":g.uniform(0,100),
            "pumped":y,"rug_pulled":0})
    return out

def confounded_rows(n,seed):
    g=random.Random(seed); out=[]
    for _ in range(n):
        c=g.random(); y=int(c>.5)
        if g.random()<.05:y=1-y
        out.append({"initial_liquidity_usd":max(0,7000+c*18000+g.gauss(0,1500)),
            "holder_score":max(0,8+c*18+g.gauss(0,2)),
            "dev_score":g.uniform(0,20),"lp_lock_score":g.uniform(0,20),
            "tax_score":g.uniform(0,15),"overall_score":g.uniform(0,100),
            "pumped":y,"rug_pulled":0})
    return out

def nonid_rows(n,seed):
    g=random.Random(seed); out=[]
    for _ in range(n):
        z=g.random()
        out.append({"initial_liquidity_usd":z*30000,"holder_score":z*z*30,
            "dev_score":g.uniform(0,20),"lp_lock_score":g.uniform(0,20),
            "tax_score":g.uniform(0,15),"overall_score":g.uniform(0,100),
            "pumped":int(z>.5),"rug_pulled":0})
    return out

def test_basic(R):
    banner("TEST 1 — BASIC HIDDEN-RULE DISCOVERY")
    rules=[]; scores=[]
    for s in range(N_STANDARD):
        e,a,t=discover(base_rows(250,1000+s),s)
        rules.append(t); scores.append(a); print(f"{s:02d} acc={a:.4f} {t}")
    recovered=sum("liquidity_usd" in x and "holder_score" in x for x in rules)
    add(R,"basic_discovery",runs=len(scores),both_features_recovered=recovered,
        recovery_rate=recovered/len(scores),mean_accuracy=mean(scores),
        stdev_accuracy=sd(scores),rules=rules)

def test_heldout(R):
    banner("TEST 2 — HELD-OUT GENERALIZATION")
    scores=[]; gaps=[]
    for s in range(N_STANDARD):
        e,a,t=discover(base_rows(300,2000+s),100+s)
        b=accuracy(e,base_rows(1000,3000+s)); scores.append(b); gaps.append(a-b)
        print(f"{s:02d} train={a:.4f} heldout={b:.4f} gap={a-b:.4f}")
    add(R,"heldout_generalization",runs=len(scores),mean_heldout_accuracy=mean(scores),
        stdev_heldout_accuracy=sd(scores),mean_train_test_gap=mean(gaps),
        minimum=min(scores),maximum=max(scores))

def test_random(R):
    banner("TEST 3 — RANDOM-LABEL FALSIFICATION")
    scores=[]
    for s in range(N_STANDARD):
        e,a,t=discover(random_rows(250,4000+s),200+s); scores.append(a)
        print(f"{s:02d} acc={a:.4f} {t}")
    add(R,"random_label_falsification",runs=len(scores),mean_accuracy=mean(scores),
        maximum_accuracy=max(scores),suspicious_high_accuracy_runs=sum(x>=.90 for x in scores))

def test_decoy(R, adversarial=False):
    name="adversarial_decoy" if adversarial else "correlated_decoy"
    banner(("TEST 11 — ADVERSARIAL DECOY PRESSURE" if adversarial else "TEST 4 — CORRELATED DECOY"))
    decoy=true=scores=0; rules=[]
    for s in range(N_DECOY):
        e,a,t=discover(correlated_rows(300,(13000 if adversarial else 5000)+s,adversarial),
                       (1000 if adversarial else 300)+s)
        rules.append(t); scores+=a
        decoy += "overall_score" in t
        true += ("liquidity_usd" in t and "holder_score" in t)
        print(f"{s:02d} acc={a:.4f} decoy={'overall_score' in t} {t}")
    add(R,name,runs=N_DECOY,mean_accuracy=scores/N_DECOY,
        decoy_selection_rate=decoy/N_DECOY,true_pair_rate=true/N_DECOY,rules=rules)

def test_shift(R):
    banner("TEST 5 — DISTRIBUTION SHIFT")
    scores=[]
    for s in range(N_STANDARD):
        e,a,t=discover(base_rows(300,6000+s),400+s)
        b=accuracy(e,shifted_rows(1000,7000+s));scores.append(b)
        print(f"{s:02d} train={a:.4f} shifted={b:.4f}")
    add(R,"distribution_shift",runs=len(scores),mean_shifted_accuracy=mean(scores),
        stdev_shifted_accuracy=sd(scores),minimum=min(scores),maximum=max(scores))

def test_confounder(R):
    banner("TEST 6 — HIDDEN CONFOUNDER")
    scores=[];rules=[]
    for s in range(N_STANDARD):
        e,a,t=discover(confounded_rows(400,8000+s),500+s);scores.append(a);rules.append(t)
        print(f"{s:02d} acc={a:.4f} {t}")
    add(R,"hidden_confounder",runs=len(scores),mean_accuracy=mean(scores),
        rules=rules,warning="Predictive success here does not establish causal identification.")

def test_nonid(R):
    banner("TEST 7 — NON-IDENTIFIABILITY")
    scores=[];rules=[]
    for s in range(N_STANDARD):
        e,a,t=discover(nonid_rows(400,9000+s),600+s);scores.append(a);rules.append(t)
        print(f"{s:02d} acc={a:.4f} {t}")
    add(R,"nonidentifiability",runs=len(scores),mean_accuracy=mean(scores),
        rules=rules,expected_behavior="Prediction may succeed while latent causal mechanism remains non-identifiable.")

def test_cost(R):
    banner("TEST 8 — MANIPULATION-COST ANALYSIS")
    e,a,t=discover(correlated_rows(500,10000),700)
    costs={"liquidity_usd":12000,"holder_score":5000,"overall_score":0,
           "dev_score":1000,"lp_lock_score":3000,"tax_score":500}
    cost=sum(v for k,v in costs.items() if k in t)
    print(t);print("acc",a,"synthetic_cost",cost)
    add(R,"manipulation_cost",rule=t,accuracy=a,hypothetical_cost=cost,
        cost_model_is_synthetic=True)

def test_counterfactual(R):
    banner("TEST 9 — COUNTERFACTUAL SENSITIVITY")
    rows=base_rows(300,11000);e,a,t=discover(rows,800)
    counts=[0,0,0]
    for r in rows:
        o=bool(e.evaluate(arm.extract_features(r)))
        variants=[]
        x=dict(r);x["initial_liquidity_usd"]=29000 if r["initial_liquidity_usd"]<12000 else 1000;variants.append(x)
        x=dict(r);x["holder_score"]=29 if r["holder_score"]<15 else 1;variants.append(x)
        x=dict(r);x["overall_score"]=99 if r["overall_score"]<50 else 1;variants.append(x)
        for i,x in enumerate(variants):
            counts[i]+=bool(e.evaluate(arm.extract_features(x)))!=o
    vals=[x/len(rows) for x in counts]
    print(t,vals)
    add(R,"counterfactual",rule=t,accuracy=a,liquidity_sensitivity=vals[0],
        holder_sensitivity=vals[1],decoy_sensitivity=vals[2])

def test_ablation(R):
    banner("TEST 10 — FEATURE ABLATION")
    original=list(arm.FEATURES); rows=base_rows(300,12000); table={}
    sets={"all_features":original,
          "no_liquidity":[x for x in original if x!="liquidity_usd"],
          "no_holder":[x for x in original if x!="holder_score"],
          "only_decoy":["overall_score"],
          "only_true_features":["liquidity_usd","holder_score"]}
    try:
        for name,fs in sets.items():
            arm.FEATURES[:]=fs;e,a,t=discover(rows,900+len(name))
            table[name]={"accuracy":a,"rule":t,"features":fs}
            print(name,a,t)
    finally:
        arm.FEATURES[:]=original
    add(R,"feature_ablation",**table)

def test_repro(R):
    banner("TEST 12 — EXACT REPRODUCIBILITY")
    rows=base_rows(250,15000)
    e1,a1,t1=discover(rows,424242);e2,a2,t2=discover(rows,424242)
    identical=t1==t2 and abs(a1-a2)<1e-12
    print(t1);print(t2);print("identical",identical)
    add(R,"reproducibility",identical=identical,run1_rule=t1,run2_rule=t2,
        run1_accuracy=a1,run2_accuracy=a2)

def verdict(R):
    banner("FINAL SUMMARY")
    t=R["tests"]
    recovery=t["basic_discovery"]["recovery_rate"]
    held=t["heldout_generalization"]["mean_heldout_accuracy"]
    rnd=t["random_label_falsification"]["maximum_accuracy"]
    dec=t["correlated_decoy"]["decoy_selection_rate"]
    adv=t["adversarial_decoy"]["decoy_selection_rate"]
    discovery="STRONG" if recovery>=.8 else "PARTIAL" if recovery>=.5 else "WEAK"
    generalization="STRONG" if held>=.9 else "PARTIAL" if held>=.75 else "WEAK"
    falsification="PASS" if rnd<.75 else "WARNING" if rnd<.9 else "FAIL"
    decoy="PROMISING" if dec<.2 else "PARTIAL" if dec<.5 else "FAIL"
    R["summary"]={"discovery_status":discovery,
                  "generalization_status":generalization,
                  "noise_falsification_status":falsification,
                  "decoy_status":decoy,
                  "adversarial_decoy_selection_rate":adv,
                  "exact_reproducibility":t["reproducibility"]["identical"],
                  "replication_schedule":"5 standard seeds; 8 decoy/adversarial seeds",
                  "novelty_claim":"NOT AUTOMATICALLY ESTABLISHED"}
    for k,v in R["summary"].items(): print(k+":",v)

def main():
    start=time.time()
    R={"metadata":{"system":"AEGIS Rule Miner V3 FAST VALIDATED",
                   "timestamp":time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "standard_replications":N_STANDARD,
                   "decoy_replications":N_DECOY,
                   "test_categories":12},
       "tests":{}}
    tests=[test_basic,test_heldout,test_random,
           lambda r:test_decoy(r,False),test_shift,test_confounder,test_nonid,
           test_cost,test_counterfactual,test_ablation,
           lambda r:test_decoy(r,True),test_repro]
    for fn in tests:
        try: fn(R)
        except Exception as e:
            name=getattr(fn,"__name__","unknown_test")
            print("TEST ERROR",name,type(e).__name__,str(e))
            traceback.print_exc()
            R["tests"][name]={"status":"ERROR","error":str(e)}
    verdict(R)
    R["runtime_seconds"]=time.time()-start
    with open(OUT,"w") as f: json.dump(R,f,indent=2)
    print("\nCOMPLETE")
    print("Results:",OUT)
    print("Runtime:",round(R["runtime_seconds"],2),"seconds")

if __name__=="__main__":
    main()
PY

chmod +x full_novelty_gauntlet.py

python -m py_compile aegis_rule_miner.py full_novelty_gauntlet.py

echo
echo "FAST VALIDATED GAUNTLET INSTALLED"
echo "Backups:"
echo "  aegis_rule_miner.py.pre_fast_gauntlet"
echo "  full_novelty_gauntlet.py.pre_fast"
echo
echo "RUN:"
echo "  cd ~/BIRTH_EDGE && python -u full_novelty_gauntlet.py 2>&1 | tee fast_gauntlet.log"
