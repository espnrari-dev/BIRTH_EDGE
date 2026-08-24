"""
Real three_way: model = LOOCV-trained OnlineLogisticRegression (fixed),
wisdom = the actual wisdom_score column already computed by ml_model.py's
wisdom() at reflection time (not a substitute), reality = actual_outcome.
Uses the pre-inversion backup so wisdom_score is untouched by adjust_model_v6.
"""

import json
import sys

import ml_model

DATA_PATH = "backups/ml_reflection_20260823_191955.json"
EPOCHS = 40


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

print(f"n={len(cases)}")
if not cases:
    print("ABORT: no usable rows in backup file (check feature/wisdom_score presence).")
    sys.exit(1)

positives = [c for c in cases if c["reality"] == 1]
negatives = [c for c in cases if c["reality"] == 0]
pos_weight = len(negatives) / len(positives) if positives else 0
print(f"positive={len(positives)} negative={len(negatives)}")

for idx in range(len(cases)):
    train = [cases[i] for i in range(len(cases)) if i != idx]
    train_pos = [c for c in train if c["reality"] == 1]
    train_neg = [c for c in train if c["reality"] == 0]
    if not train_pos or not train_neg:
        cases[idx]["model"] = None
        continue
    clf = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for _ in range(EPOCHS):
        for c in train_pos:
            for _ in range(round(pos_weight)):
                clf.update(c["feats"], 1)
        for c in train_neg:
            clf.update(c["feats"], 0)
    cases[idx]["model"] = clf.predict(cases[idx]["feats"])

usable = [c for c in cases if c["model"] is not None]
n = len(usable)
three_way = sum(1 for c in usable if c["model"] == c["wisdom"] == c["reality"])
model_reality = sum(1 for c in usable if c["model"] == c["reality"])
wisdom_reality = sum(1 for c in usable if c["wisdom"] == c["reality"])
model_wisdom = sum(1 for c in usable if c["model"] == c["wisdom"])

print(f"three_way={three_way}/{n} = {three_way/n:.4f}")
print(f"model_reality={model_reality}/{n} = {model_reality/n:.4f}")
print(f"wisdom_reality={wisdom_reality}/{n} = {wisdom_reality/n:.4f}")
print(f"model_wisdom={model_wisdom}/{n} = {model_wisdom/n:.4f}")

pos_cases = [c for c in usable if c["reality"] == 1]
tp_m = sum(1 for c in pos_cases if c["model"] == 1)
tp_w = sum(1 for c in pos_cases if c["wisdom"] == 1)
print(f"\npositive regime n={len(pos_cases)}: model_recall={tp_m}/{len(pos_cases)} wisdom_recall={tp_w}/{len(pos_cases)}")
for c in pos_cases:
    print(f"  id={c['reflection_id']} model={c['model']} wisdom={c['wisdom']} reality=1")

verdict = "MASTERED" if n and three_way/n >= 0.999 else f"NOT MASTERED (three_way={three_way/n:.4f})"
print(f"\nVERDICT: {verdict}")
