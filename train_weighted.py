"""
Trains ml_model.OnlineLogisticRegression with class-weighted
updates: each positive-class example's gradient is scaled up by
(negative_count / positive_count) so the minority class isn't
negligible in the loss. Standard imbalanced-data practice, not a
label trick -- reality labels are untouched.

Evaluates with sensitivity/specificity, not raw accuracy, since
raw accuracy is maximized by collapsing to the majority class on
this data (as already demonstrated).

Refuses to save if sensitivity is still 0.0 after training --
that would mean weighting alone isn't enough and the feature
separability check needs to be addressed first.
"""

import json
import sys

import ml_model


def load_pairs(path):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    rows = payload.get("reflections", payload) if isinstance(payload, dict) else payload

    pairs = []
    for row in rows:
        actual = row.get("actual_outcome", row.get("actual"))
        if actual is None:
            continue
        pairs.append((row, actual))
    return pairs


def main():
    if len(sys.argv) < 2:
        print("usage: python3 train_weighted.py <data.json> [epochs]")
        sys.exit(1)

    data_path = sys.argv[1]
    epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    pairs = load_pairs(data_path)
    positives = [(r, y) for r, y in pairs if float(y) >= 0.5]
    negatives = [(r, y) for r, y in pairs if float(y) < 0.5]

    if not positives or not negatives:
        print("ABORT: single-class data, cannot weight or discriminate.")
        sys.exit(1)

    pos_weight = len(negatives) / len(positives)
    print(f"positives={len(positives)} negatives={len(negatives)} "
          f"pos_weight={pos_weight:.4f}")

    model = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)

    for epoch in range(epochs):
        for row, target in positives:
            for _ in range(round(pos_weight)):
                model.update(row, target)
        for row, target in negatives:
            model.update(row, target)

    tp = tn = fp = fn = 0
    for row, target in pairs:
        pred = model.predict(row)
        a = 1 if float(target) >= 0.5 else 0
        if pred == 1 and a == 1: tp += 1
        elif pred == 0 and a == 0: tn += 1
        elif pred == 1 and a == 0: fp += 1
        else: fn += 1

    pos_n = tp + fn
    neg_n = tn + fp
    sensitivity = tp / pos_n if pos_n else float("nan")
    specificity = tn / neg_n if neg_n else float("nan")

    print(f"tp={tp} tn={tn} fp={fp} fn={fn}")
    print(f"sensitivity={sensitivity:.4f} specificity={specificity:.4f}")
    print(f"weights={dict(model.weights)} bias={model.bias}")

    if sensitivity == 0.0:
        print("ABORT: still collapsed to negative-only after weighting. "
              "Run check_separability.py -- features likely don't separate classes.")
        sys.exit(1)

    model.save(ml_model.MODEL_FILE)
    print(f"saved -> {ml_model.MODEL_FILE}")


if __name__ == "__main__":
    main()
