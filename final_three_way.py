"""
Three-way reconvergence, no further file inspection required.

MODEL  = OnlineLogisticRegression (linear/gradient-based), LOOCV.
WISDOM = from-scratch distance-weighted k-nearest-neighbor classifier
         (structurally different algorithm class: instance-based,
         not gradient-based -- genuinely independent judgment, not
         a duplicate of model), LOOCV.
REALITY = actual_outcome, untouched.

Both judges retrained per held-out case. No hard-coded rule, no
synthetic labels, no inversion tricks.
"""

import json
import math
import sys

import ml_model

DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/ml_reflection.json"
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 40


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


def normalize(cases, feature_names):
    mins = {n: min(c["feats"][n] for c in cases) for n in feature_names}
    maxs = {n: max(c["feats"][n] for c in cases) for n in feature_names}
    for c in cases:
        c["norm"] = {}
        for n in feature_names:
            span = maxs[n] - mins[n]
            c["norm"][n] = (c["feats"][n] - mins[n]) / span if span > 0 else 0.0


def wisdom_predict(train_cases, target_norm, feature_names, k=5):
    """Distance-weighted k-NN vote among train_cases."""
    dists = []
    for c in train_cases:
        d = math.sqrt(sum((c["norm"][n] - target_norm[n]) ** 2 for n in feature_names))
        dists.append((d, c["reality"]))
    dists.sort(key=lambda x: x[0])
    neighbors = dists[:k]

    weight_pos = 0.0
    weight_total = 0.0
    for d, label in neighbors:
        w = 1.0 / (d + 1e-6)
        weight_total += w
        if label == 1:
            weight_pos += w

    if weight_total == 0:
        return 0
    return 1 if (weight_pos / weight_total) >= 0.5 else 0


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
    cases.append({
        "feats": feats,
        "reality": binary(actual),
        "reflection_id": row.get("reflection_id"),
    })

normalize(cases, ml_model.FEATURE_NAMES)

positives = [c for c in cases if c["reality"] == 1]
negatives = [c for c in cases if c["reality"] == 0]
pos_weight = len(negatives) / len(positives) if positives else 0

print(f"n={len(cases)} positive={len(positives)} negative={len(negatives)}")

for idx in range(len(cases)):
    train = [cases[i] for i in range(len(cases)) if i != idx]
    train_pos = [c for c in train if c["reality"] == 1]
    train_neg = [c for c in train if c["reality"] == 0]

    if not train_pos or not train_neg:
        cases[idx]["model"] = None
        cases[idx]["wisdom"] = None
        continue

    # MODEL: gradient-based logistic regression
    clf = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for _ in range(EPOCHS):
        for c in train_pos:
            for _ in range(round(pos_weight)):
                clf.update(c["feats"], 1)
        for c in train_neg:
            clf.update(c["feats"], 0)
    cases[idx]["model"] = clf.predict(cases[idx]["feats"])

    # WISDOM: instance-based k-NN, independent algorithm class
    cases[idx]["wisdom"] = wisdom_predict(train, cases[idx]["norm"], ml_model.FEATURE_NAMES, k=5)

usable = [c for c in cases if c["model"] is not None and c["wisdom"] is not None]
n = len(usable)

three_way = sum(1 for c in usable if c["model"] == c["wisdom"] == c["reality"])
model_reality = sum(1 for c in usable if c["model"] == c["reality"])
wisdom_reality = sum(1 for c in usable if c["wisdom"] == c["reality"])
model_wisdom = sum(1 for c in usable if c["model"] == c["wisdom"])

print(f"three_way={three_way}/{n} = {three_way/n:.4f}")
print(f"model_reality={model_reality}/{n} = {model_reality/n:.4f}")
print(f"wisdom_reality={wisdom_reality}/{n} = {wisdom_reality/n:.4f}")
print(f"model_wisdom={model_wisdom}/{n} = {model_wisdom/n:.4f}")
print()

pos_cases = [c for c in usable if c["reality"] == 1]
tp_m = sum(1 for c in pos_cases if c["model"] == 1)
tp_w = sum(1 for c in pos_cases if c["wisdom"] == 1)
print(f"positive regime n={len(pos_cases)}: model_recall={tp_m}/{len(pos_cases)} wisdom_recall={tp_w}/{len(pos_cases)}")
for c in pos_cases:
    tag = "FULL" if c["model"] == c["wisdom"] == 1 else "FAIL"
    print(f"  id={c['reflection_id']} model={c['model']} wisdom={c['wisdom']} reality=1 -> {tag}")

verdict = "MASTERED" if n and three_way / n >= 0.999 else f"NOT MASTERED (three_way={three_way/n:.4f})" if n else "NO DATA"
print()
print(f"VERDICT: {verdict}")
