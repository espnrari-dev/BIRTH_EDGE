"""
One-shot: extract real features from wherever they actually live in
data/ml_reflection.json (model_replay.source_features.<name>.raw_value,
falling back to top-level keys if present), check class separability,
train with class-weighted updates, evaluate with sensitivity/specificity,
and save only if the model actually discriminates. No synthetic labels,
no inversion tricks, reality untouched.
"""

import json
import statistics
import sys

import ml_model

DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/ml_reflection.json"
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 40


def extract_features(row):
    feats = {}
    replay = row.get("model_replay", {})
    source = replay.get("source_features", {})

    for name in ml_model.FEATURE_NAMES:
        if name in source and isinstance(source[name], dict):
            feats[name] = source[name].get("raw_value")
        elif name in row:
            feats[name] = row[name]
        elif name in row.get("raw", {}):
            feats[name] = row["raw"][name]

    return feats


with open(DATA_PATH) as f:
    payload = json.load(f)
rows = payload.get("reflections", payload) if isinstance(payload, dict) else payload

pairs = []
for row in rows:
    actual = row.get("actual_outcome", row.get("actual"))
    if actual is None:
        continue
    feats = extract_features(row)
    if all(v is not None for v in feats.values()) and len(feats) == len(ml_model.FEATURE_NAMES):
        pairs.append((feats, actual))

print(f"=== EXTRACTION ===")
print(f"total_rows={len(rows)} usable_rows_with_full_features={len(pairs)}")

if not pairs:
    print("ABORT: no rows have complete feature data at any known path.")
    sys.exit(1)

positives = [(f, y) for f, y in pairs if float(y) >= 0.5]
negatives = [(f, y) for f, y in pairs if float(y) < 0.5]
print(f"positive={len(positives)} negative={len(negatives)}")

if not positives or not negatives:
    print("ABORT: single-class data, cannot discriminate.")
    sys.exit(1)

print()
print("=== SEPARABILITY ===")
for name in ml_model.FEATURE_NAMES:
    p = [float(f[name]) for f, _ in positives]
    n = [float(f[name]) for f, _ in negatives]
    p_mean, p_min, p_max = statistics.mean(p), min(p), max(p)
    n_mean, n_min, n_max = statistics.mean(n), min(n), max(n)
    overlap = not (p_max < n_min or n_max < p_min)
    print(f"{name}: pos_mean={p_mean:.4f} neg_mean={n_mean:.4f} "
          f"pos_range=[{p_min:.4f},{p_max:.4f}] neg_range=[{n_min:.4f},{n_max:.4f}] "
          f"overlap={overlap}")

print()
print("=== TRAINING (class-weighted) ===")
pos_weight = len(negatives) / len(positives)
print(f"pos_weight={pos_weight:.4f} epochs={EPOCHS}")

model = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)

for epoch in range(EPOCHS):
    for feats, target in positives:
        for _ in range(round(pos_weight)):
            model.update(feats, target)
    for feats, target in negatives:
        model.update(feats, target)

tp = tn = fp = fn = 0
for feats, target in pairs:
    pred = model.predict(feats)
    a = 1 if float(target) >= 0.5 else 0
    if pred == 1 and a == 1: tp += 1
    elif pred == 0 and a == 0: tn += 1
    elif pred == 1 and a == 0: fp += 1
    else: fn += 1

pos_n = tp + fn
neg_n = tn + fp
sensitivity = tp / pos_n if pos_n else float("nan")
specificity = tn / neg_n if neg_n else float("nan")

print()
print("=== RESULT ===")
print(f"tp={tp} tn={tn} fp={fp} fn={fn}")
print(f"sensitivity={sensitivity:.4f} specificity={specificity:.4f}")
print(f"weights={dict(model.weights)} bias={model.bias}")

if sensitivity == 0.0 or specificity == 0.0:
    print("ABORT: model still collapsed to a single class. Not saved.")
    print("If separability above shows heavy overlap on all features, "
          "the current feature set cannot linearly separate this data — "
          "need more/better features or more positive examples, not more training.")
    sys.exit(1)

model.save(ml_model.MODEL_FILE)
print(f"saved -> {ml_model.MODEL_FILE}")
