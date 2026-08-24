"""
Leave-one-out cross-validated verdict. Trains on all rows except one,
predicts the held-out row, repeats for every row. This is the honest
out-of-sample number -- same-set evaluation (train and test on
identical data) is optimistic and doesn't count.

Prints one bottom-line verdict: NOMINAL or NOT NOMINAL.
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

positives = [(f, y) for f, y in pairs if float(y) >= 0.5]
negatives = [(f, y) for f, y in pairs if float(y) < 0.5]
pos_weight = len(negatives) / len(positives) if positives else 0

tp = tn = fp = fn = 0

for held_out_idx in range(len(pairs)):
    train = [pairs[i] for i in range(len(pairs)) if i != held_out_idx]
    test_feats, test_actual = pairs[held_out_idx]

    train_pos = [(f, y) for f, y in train if float(y) >= 0.5]
    train_neg = [(f, y) for f, y in train if float(y) < 0.5]
    if not train_pos or not train_neg:
        continue

    model = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    for epoch in range(EPOCHS):
        for feats, target in train_pos:
            for _ in range(round(pos_weight)):
                model.update(feats, target)
        for feats, target in train_neg:
            model.update(feats, target)

    pred = model.predict(test_feats)
    a = 1 if float(test_actual) >= 0.5 else 0
    if pred == 1 and a == 1: tp += 1
    elif pred == 0 and a == 0: tn += 1
    elif pred == 1 and a == 0: fp += 1
    else: fn += 1

pos_n = tp + fn
neg_n = tn + fp
sensitivity = tp / pos_n if pos_n else 0.0
specificity = tn / neg_n if neg_n else 0.0
precision = tp / (tp + fp) if (tp + fp) else 0.0

print(f"LOOCV: tp={tp} tn={tn} fp={fp} fn={fn}")
print(f"sensitivity={sensitivity:.4f} specificity={specificity:.4f} precision={precision:.4f}")
print()

if sensitivity > 0.0 and specificity > 0.5 and precision > (pos_n / len(pairs) if pairs else 0):
    print("VERDICT: NOMINAL — model discriminates above chance on held-out data.")
else:
    print("VERDICT: NOT NOMINAL — model does not reliably discriminate out-of-sample.")
