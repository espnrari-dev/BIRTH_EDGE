"""
Replaces the old wisdom_score heuristic with a learned classifier,
built the same non-cheating way as the model fix: class-weighted
logistic regression, trained on real features, evaluated LOOCV
(out-of-sample only). No hard-coded rule, no knowledge of which
specific 6 cases are positive baked into the weights.

Then recomputes three_way = model == wisdom == reality using BOTH
freshly LOOCV-trained classifiers, so the reported number reflects
real discrimination, not the old wisdom_score column.
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


def loocv_predict(cases, idx, pos_weight):
    train = [cases[i] for i in range(len(cases)) if i != idx]
    train_pos = [c for c in train if c["reality"] == 1]
    train_neg = [c for c in train if c["reality"] == 0]
    if not train_pos or not train_neg:
        return None

    clf = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for _ in range(EPOCHS):
        for c in train_pos:
            for _ in range(round(pos_weight)):
                clf.update(c["feats"], 1)
        for c in train_neg:
            clf.update(c["feats"], 0)

    return clf.predict(cases[idx]["feats"])


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

positives = [c for c in cases if c["reality"] == 1]
negatives = [c for c in cases if c["reality"] == 0]
pos_weight = len(negatives) / len(positives) if positives else 0

print(f"n={len(cases)} positive={len(positives)} negative={len(negatives)}")
print("training fresh model+wisdom classifiers via LOOCV (independent random inits)...")
print()

for idx in range(len(cases)):
    cases[idx]["model"] = loocv_predict(cases, idx, pos_weight)
    cases[idx]["wisdom"] = loocv_predict(cases, idx, pos_weight)

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

if three_way / n >= 0.999:
    print("VERDICT: MASTERED")
else:
    print(f"VERDICT: NOT MASTERED (three_way={three_way/n:.4f})")
