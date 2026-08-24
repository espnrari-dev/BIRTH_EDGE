#!/usr/bin/env python3

import math
import os
import tempfile

from ml_model import OnlineLogisticRegression


FEATURES = [
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "liquidity_usd",
]


def assert_finite_model(model):
    assert math.isfinite(model.bias)

    for name in model.feature_names:
        assert math.isfinite(model.weights[name]), (
            f"non-finite weight: {name}"
        )


def main():
    print("=" * 72)
    print("BIRTH_EDGE — ML MODEL VALIDATION")
    print("=" * 72)

    # ------------------------------------------------------------
    # TEST 1 — Construction
    # ------------------------------------------------------------

    model = OnlineLogisticRegression()

    assert model.feature_names == FEATURES
    assert_finite_model(model)

    print("TEST 1 — CONSTRUCTION              PASS")

    # ------------------------------------------------------------
    # TEST 2 — Prediction
    # ------------------------------------------------------------

    positive = {
        "holder_score": 30,
        "dev_score": 30,
        "lp_lock_score": 30,
        "liquidity_usd": 30000,
    }

    negative = {
        "holder_score": 0,
        "dev_score": 0,
        "lp_lock_score": 0,
        "liquidity_usd": 0,
    }

    p_pos_before = model.predict_proba(positive)
    p_neg_before = model.predict_proba(negative)

    assert 0.0 <= p_pos_before <= 1.0
    assert 0.0 <= p_neg_before <= 1.0

    print(
        "TEST 2 — PREDICTION                PASS",
        f"(positive={p_pos_before:.6f}, negative={p_neg_before:.6f})"
    )

    # ------------------------------------------------------------
    # TEST 3 — SGD actually changes model
    # ------------------------------------------------------------

    old_weights = dict(model.weights)
    old_bias = model.bias

    for _ in range(25):
        model.train_one(positive, 1)

    changed = (
        model.bias != old_bias
        or any(
            model.weights[k] != old_weights[k]
            for k in model.feature_names
        )
    )

    assert changed, "SGD did not modify model parameters"

    p_pos_after = model.predict_proba(positive)

    assert p_pos_after > p_pos_before, (
        "positive training did not increase positive probability"
    )

    assert_finite_model(model)

    print(
        "TEST 3 — SGD LEARNING              PASS",
        f"(before={p_pos_before:.6f}, after={p_pos_after:.6f})"
    )

    # ------------------------------------------------------------
    # TEST 4 — Negative learning
    # ------------------------------------------------------------

    before_negative_training = model.predict_proba(negative)

    for _ in range(25):
        model.train_one(negative, 0)

    after_negative_training = model.predict_proba(negative)

    assert after_negative_training < before_negative_training, (
        "negative training did not reduce negative probability"
    )

    assert_finite_model(model)

    print(
        "TEST 4 — NEGATIVE LEARNING          PASS",
        f"(before={before_negative_training:.6f}, "
        f"after={after_negative_training:.6f})"
    )

    # ------------------------------------------------------------
    # TEST 5 — Safe feature handling
    # ------------------------------------------------------------

    hostile = {
        "holder_score": None,
        "dev_score": "",
        "lp_lock_score": "not-a-number",
        "liquidity_usd": float("nan"),
    }

    probability = model.predict_proba(hostile)

    assert math.isfinite(probability)
    assert 0.0 <= probability <= 1.0

    print("TEST 5 — SAFE FEATURES              PASS")

    # ------------------------------------------------------------
    # TEST 6 — Missing features
    # ------------------------------------------------------------

    missing = {}

    probability = model.predict_proba(missing)

    assert math.isfinite(probability)
    assert 0.0 <= probability <= 1.0

    print("TEST 6 — MISSING FEATURES            PASS")

    # ------------------------------------------------------------
    # TEST 7 — Batch training
    # ------------------------------------------------------------

    rows = [
        (
            {
                "holder_score": 25,
                "dev_score": 25,
                "lp_lock_score": 25,
                "liquidity_usd": 25000,
            },
            1,
        ),
        (
            {
                "holder_score": 2,
                "dev_score": 2,
                "lp_lock_score": 2,
                "liquidity_usd": 100,
            },
            0,
        ),
        (
            {
                "holder_score": 20,
                "dev_score": 15,
                "lp_lock_score": 20,
                "liquidity_usd": 15000,
            },
            1,
        ),
        (
            {
                "holder_score": 1,
                "dev_score": 3,
                "lp_lock_score": 1,
                "liquidity_usd": 200,
            },
            0,
        ),
    ]

    batch_model = OnlineLogisticRegression()

    metrics = batch_model.fit(
        rows,
        epochs=20,
        shuffle=False,
    )

    assert metrics["samples"] == 80.0
    assert math.isfinite(metrics["loss"])
    assert 0.0 <= metrics["accuracy"] <= 1.0

    assert_finite_model(batch_model)

    print(
        "TEST 7 — BATCH TRAINING             PASS",
        f"(loss={metrics['loss']:.6f}, "
        f"accuracy={metrics['accuracy']:.4f})"
    )

    # ------------------------------------------------------------
    # TEST 8 — Evaluation
    # ------------------------------------------------------------

    evaluation = batch_model.evaluate(rows)

    assert evaluation["samples"] == 4.0
    assert math.isfinite(evaluation["loss"])
    assert 0.0 <= evaluation["accuracy"] <= 1.0

    print(
        "TEST 8 — EVALUATION                 PASS",
        f"(accuracy={evaluation['accuracy']:.4f}, "
        f"TP={evaluation['tp']:.0f}, "
        f"TN={evaluation['tn']:.0f}, "
        f"FP={evaluation['fp']:.0f}, "
        f"FN={evaluation['fn']:.0f})"
    )

    # ------------------------------------------------------------
    # TEST 9 — Persistence
    # ------------------------------------------------------------

    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "model.json")

        batch_model.save(path)

        assert os.path.exists(path)

        loaded = OnlineLogisticRegression.load(path)

        assert loaded.feature_names == batch_model.feature_names
        assert loaded.lr == batch_model.lr
        assert loaded.l2 == batch_model.l2

        assert loaded.bias == batch_model.bias

        for name in batch_model.feature_names:
            assert loaded.weights[name] == batch_model.weights[name]

        original_probability = batch_model.predict_proba(positive)
        loaded_probability = loaded.predict_proba(positive)

        assert original_probability == loaded_probability

    print("TEST 9 — PERSISTENCE                PASS")

    # ------------------------------------------------------------
    # TEST 10 — Deterministic replay
    # ------------------------------------------------------------

    a = OnlineLogisticRegression()
    b = OnlineLogisticRegression()

    for data, target in rows:
        a.train_one(data, target)
        b.train_one(data, target)

    assert a.bias == b.bias

    for name in FEATURES:
        assert a.weights[name] == b.weights[name]

    print("TEST 10 — DETERMINISTIC REPLAY       PASS")

    # ------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------

    print("=" * 72)
    print("ALL ML MODEL TESTS PASSED")
    print("=" * 72)

    print("\nFINAL MODEL:")
    print("bias =", batch_model.bias)

    for name in batch_model.feature_names:
        print(
            f"{name:20s} = "
            f"{batch_model.weights[name]:.12f}"
        )

    print("\nSTATUS: READY FOR BIRTH_EDGE INTEGRATION")


if __name__ == "__main__":
    main()
