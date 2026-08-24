"""
Finds the L2 regularization strength that maximizes out-of-sample
(LOOCV) balanced accuracy -- i.e. the point where the model ignores
noise in the 4 features without losing real signal.

Sweeps a range of l2 values. For each value, retrains fresh per
held-out case (no leakage) and measures sensitivity/specificity on
the held-out point. Reports the l2 with best balanced accuracy, and
refuses to recommend a setting that collapses to a single class.
"""

import json
import sys

import ml_model

DATA_PATH = "data/ml_reflection.json"
EPOCHS = 40
L2_CANDIDATES = [0.0, 0.0005, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]


def extract_features(row):
    feats = {}
    source = row.get("model_replay", {}).get("source_features", {})
    for name in ml_model.FEATURE_NAMES:
        if name in source and isinstance(source[name], dict):
            feats[name] = source[name].get("raw_value")
        elif name in row:
            feats[name] = row[name]
    return feats


def binary(value):
    if value is None:
        return None
    return 1 if float(value) >= 0.5 else 0


with open(DATA_PATH) as f:
    payload = json.load(f)
rows = payload.get("reflections", payload) if isinstance(payload, dict) else payload

cases = []
for row in rows:
    actual = row.get("actual_outcome", row.get("actual"))
    if actual is None:
        continue
    feats = extract_features(row)
    if not (all(v is not None for v in feats.values()) and len(feats) == len(ml_model.FEATURE_NAMES)):
        continue
    cases.append({"feats": feats, "reality": binary(actual)})

positives = [c for c in cases if c["reality"] == 1]
negatives = [c for c in cases if c["reality"] == 0]
pos_weight = len(negatives) / len(positives) if positives else 0
print(f"n={len(cases)} positive={len(positives)} negative={len(negatives)}")
print()

results = []
for l2 in L2_CANDIDATES:
    tp = tn = fp = fn = 0
    for idx in range(len(cases)):
        train = [cases[i] for i in range(len(cases)) if i != idx]
        train_pos = [c for c in train if c["reality"] == 1]
        train_neg = [c for c in train if c["reality"] == 0]
        if not train_pos or not train_neg:
            continue

        clf = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES, l2=l2)
        for _ in range(EPOCHS):
            for c in train_pos:
                for _ in range(round(pos_weight)):
                    clf.update(c["feats"], 1)
            for c in train_neg:
                clf.update(c["feats"], 0)

        pred = clf.predict(cases[idx]["feats"])
        a = cases[idx]["reality"]
        if pred == 1 and a == 1: tp += 1
        elif pred == 0 and a == 0: tn += 1
        elif pred == 1 and a == 0: fp += 1
        else: fn += 1

    pos_n = tp + fn
    neg_n = tn + fp
    sens = tp / pos_n if pos_n else 0.0
    spec = tn / neg_n if neg_n else 0.0
    bal = 0.5 * sens + 0.5 * spec
    collapsed = (sens == 0.0 or spec == 0.0)

    results.append((l2, sens, spec, bal, collapsed, tp, tn, fp, fn))
    flag = " [COLLAPSED]" if collapsed else ""
    print(f"l2={l2:<8} sensitivity={sens:.4f} specificity={spec:.4f} balanced={bal:.4f} "
          f"tp={tp} tn={tn} fp={fp} fn={fn}{flag}")

valid = [r for r in results if not r[4]]
if not valid:
    print("\nABORT: every l2 candidate collapsed to a single class. "
          "Regularization alone can't fix this -- data/feature issue, not a blinders issue.")
    sys.exit(1)

best = max(valid, key=lambda r: r[3])
print(f"\nBEST L2 (blinders setting): l2={best[0]} "
      f"sensitivity={best[1]:.4f} specificity={best[2]:.4f} balanced_accuracy={best[3]:.4f}")
print("Use this l2 value in production: ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES, l2=<value above>)")
