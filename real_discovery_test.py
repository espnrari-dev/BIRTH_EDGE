#!/usr/bin/env python3
"""
REAL DISCOVERY TEST
Uses actual learning_results from learning.db.
No synthetic generator. No TRUE_RULE.
Chronological split: train on earlier tokens, evaluate on later tokens.
"""
import sqlite3, json, time, math, statistics, hashlib
from datetime import datetime

DB = "data/learning.db"
OUT_JSON = "real_discovery_evidence.json"
OUT_MD = "real_discovery_evidence.md"

FEATURES = [
    "initial_liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]

def load_data():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT addr, initial_liquidity_usd, holder_score, dev_score,
               lp_lock_score, tax_score, overall_score, pumped, rug_pulled,
               discovered_at, updated_at
        FROM learning_results
        WHERE final_price_usd IS NOT NULL
          AND discovered_at IS NOT NULL
        ORDER BY discovered_at, rowid
    """)
    rows = cur.fetchall()
    conn.close()
    data = []
    for r in rows:
        record = {f: (r[f] or 0.0) for f in FEATURES}
        record["target"] = int(r["pumped"] or 0)
        record["addr"] = r["addr"]
        record["discovered_at"] = r["discovered_at"]
        data.append(record)
    return data

def train_rule_from_real(rows):
    """
    Simple, transparent decision rule: choose threshold for one feature
    that maximizes training accuracy. Not a planted rule.
    """
    if not rows:
        return None, 0.0, ""
    best_acc = -1
    best_feature = None
    best_threshold = None
    best_op = ">"
    for feature in FEATURES:
        values = [r[feature] for r in rows]
        unique = sorted(set(values))
        # Try midpoints between unique values
        for i in range(len(unique)-1):
            thr = (unique[i] + unique[i+1]) / 2
            tp = fp = tn = fn = 0
            for r in rows:
                pred = int(r[feature] > thr)
                actual = r["target"]
                if pred and actual: tp += 1
                elif pred and not actual: fp += 1
                elif not pred and not actual: tn += 1
                else: fn += 1
            acc = (tp + tn) / len(rows)
            if acc > best_acc:
                best_acc = acc
                best_feature = feature
                best_threshold = thr
                best_op = ">"
    if best_feature is None:
        return None, 0.0, ""
    rule = {"feature": best_feature, "threshold": best_threshold, "operator": best_op}
    rule_text = f"{best_feature} {best_op} {best_threshold:.4f}"
    return rule, best_acc, rule_text

def predict(rule, row):
    if rule is None:
        return 0
    x = row.get(rule["feature"], 0.0)
    op = rule.get("operator", ">")
    thr = rule.get("threshold", 0)
    if op == ">": return int(x > thr)
    if op == ">=": return int(x >= thr)
    if op == "<": return int(x < thr)
    if op == "<=": return int(x <= thr)
    return 0

def evaluate(rows, rule):
    tp = fp = tn = fn = 0
    for r in rows:
        pred = predict(rule, r)
        actual = r["target"]
        if pred and actual: tp += 1
        elif pred and not actual: fp += 1
        elif not pred and not actual: tn += 1
        else: fn += 1
    total = tp + fp + tn + fn
    acc = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if tp+fp else 0
    recall = tp / (tp + fn) if tp+fn else 0
    f1 = 2*tp/(2*tp+fp+fn) if (2*tp+fp+fn) else 0
    return {"tp":tp,"fp":fp,"tn":tn,"fn":fn,"accuracy":acc,
            "precision":precision,"recall":recall,"f1":f1}

def baseline_75(rows):
    tp = fp = tn = fn = 0
    for r in rows:
        pred = int(r.get("overall_score", 0) >= 75)
        actual = r["target"]
        if pred and actual: tp += 1
        elif pred and not actual: fp += 1
        elif not pred and not actual: tn += 1
        else: fn += 1
    total = tp + fp + tn + fn
    return {"accuracy": (tp+tn)/total if total else 0, "tp":tp,"fp":fp,"tn":tn,"fn":fn}

def main():
    data = load_data()
    if len(data) < 30:
        print("Not enough real labeled data yet:", len(data))
        return
    # Chronological split 70/30
    split = int(len(data) * 0.7)
    train = data[:split]
    test = data[split:]
    rule, train_acc, rule_text = train_rule_from_real(train)
    if rule is None:
        print("Could not learn any rule from real data.")
        return
    test_metrics = evaluate(test, rule)
    baseline_metrics = baseline_75(test)
    improvement = test_metrics["accuracy"] - baseline_metrics["accuracy"]

    report = {
        "timestamp": datetime.now().isoformat(),
        "train_n": len(train),
        "test_n": len(test),
        "learned_rule": rule_text,
        "train_accuracy": train_acc,
        "test_metrics": test_metrics,
        "baseline_75": baseline_metrics,
        "improvement_over_baseline": improvement,
        "verdict": "PASS" if improvement > 0 else "FAIL",
        "data_source": DB,
        "note": "Real outcome data; no synthetic generator, no planted rule."
    }

    with open(OUT_JSON, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    md = f"""# Real Discovery Evidence

- Timestamp: {report['timestamp']}
- Training rows: {len(train)}
- Test rows: {len(test)}
- Learned rule: `{rule_text}`
- Train accuracy: {train_acc:.4f}
- Test accuracy: {test_metrics['accuracy']:.4f}
- Baseline (overall_score >= 75) accuracy: {baseline_metrics['accuracy']:.4f}
- Improvement: {improvement:+.4f}
- Verdict: **{report['verdict']}**

This test uses only real token outcomes. No synthetic TRUE_RULE.
"""
    with open(OUT_MD, "w") as f:
        f.write(md)

    print("=" * 72)
    print("REAL DISCOVERY TEST")
    print("=" * 72)
    print(f"Training rows: {len(train)}")
    print(f"Test rows: {len(test)}")
    print(f"Learned rule: {rule_text}")
    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_metrics['accuracy']:.4f}")
    print(f"Baseline accuracy: {baseline_metrics['accuracy']:.4f}")
    print(f"Improvement: {improvement:+.4f}")
    print(f"Verdict: {report['verdict']}")
    print("=" * 72)

if __name__ == "__main__":
    main()
