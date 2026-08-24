"""
Computes real three_way convergence (model == wisdom == reality) using
LOOCV model predictions (honest, out-of-sample) against wisdom_score
and actual_outcome, both pulled directly from the row data (not
recomputed, not inverted). Also lists the 8 positive-regime cases
(reality==1) individually so wisdom disagreement can be audited.
"""

import json
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


with open(DATA_PATH) as f:
    payload = json.load(f)
rows = payload.get("reflections", payload) if isinstance(payload, dict) else payload

cases = []
for row in rows:
    actual = row.get("actual_outcome", row.get("actual"))
    wisdom_raw = row.get("wisdom_score")
    if actual is None or wisdom_raw is None:
        continue
    feats = extract_features(row)
    if not (all(v is not None for v in feats.values()) and len(feats) == len(ml_model.FEATURE_NAMES)):
        continue
    cases.append({
        "feats": feats,
        "reality": binary(actual),
        "wisdom": binary(wisdom_raw),
        "reflection_id": row.get("reflection_id"),
    })

positives = [c for c in cases if c["reality"] == 1]
negatives = [c for c in cases if c["reality"] == 0]
pos_weight = len(negatives) / len(positives) if positives else 0

# LOOCV model predictions (honest, out-of-sample)
for held_out_idx in range(len(cases)):
    train = [cases[i] for i in range(len(cases)) if i != held_out_idx]
    train_pos = [c for c in train if c["reality"] == 1]
    train_neg = [c for c in train if c["reality"] == 0]
    if not train_pos or not train_neg:
        cases[held_out_idx]["model"] = None
        continue

    model = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for epoch in range(EPOCHS):
        for c in train_pos:
            for _ in range(round(pos_weight)):
                model.update(c["feats"], 1)
        for c in train_neg:
            model.update(c["feats"], 0)

    cases[held_out_idx]["model"] = model.predict(cases[held_out_idx]["feats"])

three_way = sum(1 for c in cases if c["model"] == c["wisdom"] == c["reality"])
model_reality = sum(1 for c in cases if c["model"] == c["reality"])
wisdom_reality = sum(1 for c in cases if c["wisdom"] == c["reality"])
model_wisdom = sum(1 for c in cases if c["model"] == c["wisdom"])
n = len(cases)

print(f"n={n}")
print(f"three_way={three_way}/{n} = {three_way/n:.4f}")
print(f"model_reality={model_reality}/{n} = {model_reality/n:.4f}")
print(f"wisdom_reality={wisdom_reality}/{n} = {wisdom_reality/n:.4f}")
print(f"model_wisdom={model_wisdom}/{n} = {model_wisdom/n:.4f}")
print()

print(f"=== POSITIVE REGIME (reality=1, n={len(positives)}) ===")
for c in cases:
    if c["reality"] == 1:
        agree = "FULL" if c["model"] == c["wisdom"] == 1 else "FAIL"
        print(f"id={c['reflection_id']} model={c['model']} wisdom={c['wisdom']} reality=1 -> {agree}")
