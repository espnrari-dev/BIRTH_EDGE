"""
Trains ml_model.OnlineLogisticRegression on real historical
(features, actual_outcome) pairs, replacing the hard-coded
positive-only default weights with weights learned via real
gradient descent (model.update() inside fit()/train_and_save()).

No synthetic labels. No global inversion. No hard-coded target rule.
Refuses to train if the supplied data is single-class, since that
would reproduce the same degenerate always-positive model under a
different mechanism.
"""

import json
import sys

import ml_model


def load_training_rows(path):
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
        print("usage: python3 train_and_reequip.py <path_to_real_outcome_data.json>")
        sys.exit(1)

    data_path = sys.argv[1]
    pairs = load_training_rows(data_path)

    if not pairs:
        print(f"No rows with actual_outcome/actual found in {data_path}")
        sys.exit(1)

    positives = sum(1 for _, y in pairs if float(y) >= 0.5)
    negatives = len(pairs) - positives
    print(f"rows={len(pairs)} positive={positives} negative={negatives}")

    if positives == 0 or negatives == 0:
        print("ABORT: single-class training data. Would reproduce a degenerate model.")
        sys.exit(1)

    model = ml_model.OnlineLogisticRegression(ml_model.FEATURE_NAMES)
    print("BEFORE weights:", dict(model.weights), "bias:", model.bias)

    metrics = model.train_and_save(
        pairs,
        epochs=25,
        shuffle=True,
        path=ml_model.MODEL_FILE,
    )

    print("AFTER  weights:", dict(model.weights), "bias:", model.bias)
    print("metrics:", metrics)
    print(f"saved -> {ml_model.MODEL_FILE}")


if __name__ == "__main__":
    main()
