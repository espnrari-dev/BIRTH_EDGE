"""
Calibrates wisdom's decision threshold instead of using a fixed 0.5.
wisdom_score is a continuous historical-similarity score; 0.5 was never
derived from this data, it's just binary()'s default. This finds, per
held-out case (LOOCV, no leakage), the threshold over the OTHER 102
raw wisdom_scores that maximizes balanced accuracy against reality,
then applies it to the held-out case's own raw wisdom_score.

Un-inverts wisdom_score per-row using each row's _v6_equipped flag,
same as true_three_way_final.py. Reality and raw scores untouched.
Recomputes full three_way with calibrated wisdom + already-fixed model.
"""

import json
import sys

import ml_model

DATA_PATH = "data/ml_reflection.json"
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


def binary_fixed(value):
    if value is None:
        return None
    return 1 if float(value) >= 0.5 else 0


def real_wisdom_raw(row):
    raw = row.get("wisdom_score")
    if raw is None:
        return None
    equipped = row.get("_v6_equipped", {})
    if equipped.get("invert_wisdom"):
        return 1.0 - float(raw)
    return float(raw)


def best_threshold(scores_and_labels):
    """Sweep candidate thresholds (midpoints between sorted unique scores),
    return the one maximizing balanced accuracy."""
    scores = sorted(set(s for s, _ in scores_and_labels))
    if len(scores) < 2:
        return 0.5

    candidates = [(a + b) / 2.0 for a, b in zip(scores, scores[1:])]

    best_t, best_bal = 0.5, -1.0
    for t in candidates:
        pos = sum(1 for _, l in scores_and_labels if l == 1)
        neg = sum(1 for _, l in scores_and_labels if l == 0)
        tp = sum(1 for s, l in scores_and_labels if s >= t and l == 1)
        tn = sum(1 for s, l in scores_and_labels if s < t and l == 0)
        if pos == 0 or neg == 0:
            continue
        bal = 0.5 * (tp / pos) + 0.5 * (tn / neg)
        if bal > best_bal:
            best_bal, best_t = bal, t

    return best_t


with open(DATA_PATH) as f:
    payload = json.load(f)
rows = payload.get("reflections", payload) if isinstance(payload, dict) else payload

cases = []
for row in rows:
    actual = row.get("actual_outcome", row.get("actual"))
    wisdom_raw = real_wisdom_raw(row)
    if actual is None or wisdom_raw is None:
        continue
    feats = extract_features(row)
    if not (all(v is not None for v in feats.values()) and len(feats) == len(ml_model.FEATURE_NAMES)):
        continue
    cases.append({
        "feats": feats,
        "reality": binary_fixed(actual),
        "wisdom_raw": wisdom_raw,
        "reflection_id": row.get("reflection_id"),
    })

print(f"n={len(cases)}")
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
        cases[idx]["wisdom"] = None
        continue

    # MODEL (unchanged, already fixed)
    clf = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for _ in range(EPOCHS):
        for c in train_pos:
            for _ in range(round(pos_weight)):
                clf.update(c["feats"], 1)
        for c in train_neg:
            clf.update(c["feats"], 0)
    cases[idx]["model"] = clf.predict(cases[idx]["feats"])

    # WISDOM: calibrate threshold on the other 102 rows only, apply here
    train_scores = [(c["wisdom_raw"], c["reality"]) for c in train]
    t = best_threshold(train_scores)
    cases[idx]["wisdom"] = 1 if cases[idx]["wisdom_raw"] >= t else 0
    cases[idx]["threshold_used"] = t

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
neg_cases = [c for c in usable if c["reality"] == 0]
tp_w = sum(1 for c in pos_cases if c["wisdom"] == 1)
fp_w = sum(1 for c in neg_cases if c["wisdom"] == 1)
print(f"\nwisdom on positives: {tp_w}/{len(pos_cases)}")
print(f"wisdom false positives on negatives: {fp_w}/{len(neg_cases)}")
print(f"avg calibrated threshold: {sum(c['threshold_used'] for c in usable)/n:.4f}")

verdict = "MASTERED" if n and three_way/n >= 0.999 else f"NOT MASTERED (three_way={three_way/n:.4f})"
print(f"\nVERDICT: {verdict}")
