#!/usr/bin/env python3

import importlib
import json
import math
import random
import statistics
import traceback
from collections import Counter

from oracle import oracle_label


# =====================================================================
# BIRTH_EDGE — COMPREHENSIVE ADVERSARIAL / NOVELTY VALIDATION
# =====================================================================

M = importlib.import_module("aegis_rule_miner")

REPORT_FILE = "birth_edge_adversarial_report.json"


# =====================================================================
# DATA GENERATION
# =====================================================================

def make_rows(holder_values, liquidity_values, extra=False):
    rows = []

    for h in holder_values:
        for l in liquidity_values:
            row = {
                "holder_score": float(h),
                "liquidity": float(l),
            }

            if extra:
                row.update({
                    "volume": float((h * 137 + l / 73) % 50000),
                    "age": float((h * 19 + int(l / 1000)) % 100),
                    "holders": float((h * 311 + int(l / 100)) % 10000),
                    "fees": float((l % 997) / 997),
                    "noise_a": float((h * 17 + l * 0.003) % 913),
                    "noise_b": float((h * 29 + l * 0.007) % 701),
                    "noise_c": float((h * 41 + l * 0.011) % 503),
                    "noise_d": float((h * 53 + l * 0.017) % 307),
                })

            row["pumped"] = oracle_label(row)
            rows.append(row)

    return rows


TRAIN = make_rows(
    range(0, 13, 2),
    [0, 5000, 10000, 20000, 30000],
)

TEST = make_rows(
    range(1, 14, 2),
    [2500, 7500, 15000, 25000, 35000],
)


# =====================================================================
# MINER WRAPPERS
# =====================================================================

def evolve(rows, seed=None):
    if seed is not None:
        random.seed(seed)

    try:
        result = M.evolve_rule(rows)

        if isinstance(result, tuple):
            rule = result[0]
            score = result[1] if len(result) > 1 else None
        else:
            rule = result
            score = None

        return rule, score, None

    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def features(rule):
    if rule is None:
        return []

    try:
        return list(M.rule_features(rule))
    except Exception:
        return []


def predict(rule, row):
    if rule is None:
        return None

    try:
        values = M.extract_features(row)
        return int(bool(rule.evaluate(values)))
    except Exception:
        return None


def accuracy(rule, rows):
    if rule is None or not rows:
        return 0.0

    evaluated = 0
    correct = 0

    for row in rows:
        prediction = predict(rule, row)

        if prediction is None:
            continue

        evaluated += 1

        if prediction == oracle_label(row):
            correct += 1

    return correct / evaluated if evaluated else 0.0


def evaluated_count(rule, rows):
    if rule is None:
        return 0

    return sum(predict(rule, row) is not None for row in rows)


def confusion(rule, rows):
    tp = tn = fp = fn = 0

    for row in rows:
        prediction = predict(rule, row)

        if prediction is None:
            continue

        truth = oracle_label(row)

        if truth == 1 and prediction == 1:
            tp += 1
        elif truth == 0 and prediction == 0:
            tn += 1
        elif truth == 0 and prediction == 1:
            fp += 1
        elif truth == 1 and prediction == 0:
            fn += 1

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def rule_text(rule):
    return str(rule) if rule is not None else None


def result(rule, score, rows=None, error=None):
    out = {
        "rule": rule_text(rule),
        "features": features(rule),
        "discovery_score": (
            float(score)
            if isinstance(score, (int, float))
            and math.isfinite(float(score))
            else None
        ),
    }

    if rows is not None:
        out["accuracy"] = round(accuracy(rule, rows), 6)
        out["evaluated"] = evaluated_count(rule, rows)
        out["samples"] = len(rows)

    if error:
        out["error"] = error

    return out


# =====================================================================
# TEST EXECUTION FRAMEWORK
# =====================================================================

RESULTS = {}
FAILURES = []


def run_test(number, name, function):
    print()
    print("=" * 72)
    print(f"[{number}] {name}")
    print("=" * 72)

    try:
        value = function()
        RESULTS[name] = value
        print(json.dumps(value, indent=2, default=str))
        return value

    except Exception as exc:
        error = {
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }

        RESULTS[name] = error
        FAILURES.append(name)

        print("TEST ERROR — CONTINUING")
        print(error["error"])

        return error


# =====================================================================
# 1. BASE DISCOVERY
# =====================================================================

def test_base():
    rule, score, error = evolve(TRAIN)

    return result(
        rule,
        score,
        TRAIN,
        error,
    ) | {
        "held_out_accuracy": round(accuracy(rule, TEST), 6),
        "held_out_evaluated": evaluated_count(rule, TEST),
        "confusion": confusion(rule, TEST),
    }


run_test(1, "BASE_DISCOVERY", test_base)


# =====================================================================
# 2. MULTI-SPLIT IDENTIFIABILITY
# =====================================================================

def test_multisplit():
    splits = [
        (
            "A",
            range(0, 13, 2),
            [0, 5000, 10000, 20000, 30000],
        ),
        (
            "B",
            range(1, 14, 2),
            [2500, 7500, 15000, 25000, 35000],
        ),
        (
            "C",
            [0, 1, 3, 5, 7, 9, 11, 13],
            [1000, 6000, 12000, 18000, 26000, 34000],
        ),
        (
            "D",
            [2, 4, 6, 8, 10, 12],
            [3000, 9000, 14000, 22000, 32000],
        ),
    ]

    output = {}

    for label, hs, ls in splits:
        rows = make_rows(hs, ls)
        rule, score, error = evolve(rows)

        output[label] = result(
            rule,
            score,
            rows,
            error,
        )

    return output


run_test(2, "MULTI_SPLIT_IDENTIFIABILITY", test_multisplit)


# =====================================================================
# 3. NOISE RESISTANCE
# =====================================================================

def test_noise():
    rows = make_rows(
        range(0, 13, 2),
        [0, 5000, 10000, 20000, 30000],
        extra=True,
    )

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error) | {
        "expected_core_feature": "holder_score",
        "ignored_noise": set(features(rule)) == {"holder_score"},
    }


run_test(3, "NOISE_RESISTANCE", test_noise)


# =====================================================================
# 4. TRUE-FEATURE PERMUTATION
# =====================================================================

def test_feature_permutation():
    rows = make_rows(
        range(0, 13, 2),
        [0, 5000, 10000, 20000, 30000],
    )

    rng = random.Random(9917)

    values = [r["holder_score"] for r in rows]
    rng.shuffle(values)

    for row, value in zip(rows, values):
        row["holder_score"] = value

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error) | {
        "post_permutation_accuracy": round(accuracy(rule, rows), 6),
        "post_permutation_features": features(rule),
    }


run_test(4, "TRUE_FEATURE_PERMUTATION", test_feature_permutation)


# =====================================================================
# 5. LIQUIDITY-ONLY ABLATION
# =====================================================================

def test_liquidity_only():
    rows = []

    for row in TRAIN:
        rows.append({
            "holder_score": 0.0,
            "liquidity": row["liquidity"],
            "pumped": row["pumped"],
        })

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(5, "LIQUIDITY_ONLY_ABLATION", test_liquidity_only)


# =====================================================================
# 6. HOLDER-ONLY ABLATION
# =====================================================================

def test_holder_only():
    rows = []

    for row in TRAIN:
        rows.append({
            "holder_score": row["holder_score"],
            "liquidity": 0.0,
            "pumped": row["pumped"],
        })

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(6, "HOLDER_ONLY_ABLATION", test_holder_only)


# =====================================================================
# 7. BOUNDARY RECOVERY
# =====================================================================

def test_boundary():
    rule, score, error = evolve(TRAIN)

    points = [
        6.9999,
        7.0,
        7.0001,
        9.9999,
        10.0,
        10.0001,
    ]

    observations = []

    for h in points:
        row = {
            "holder_score": h,
            "liquidity": 0.0,
        }

        observations.append({
            "holder_score": h,
            "oracle": oracle_label(row),
            "prediction": predict(rule, row),
            "correct": predict(rule, row) == oracle_label(row),
        })

    return {
        "rule": rule_text(rule),
        "observations": observations,
        "all_correct": all(x["correct"] for x in observations),
    }


run_test(7, "BOUNDARY_RECOVERY", test_boundary)


# =====================================================================
# 8. FEATURE SWAP
# =====================================================================

def test_feature_swap():
    rows = []

    for row in TRAIN:
        rows.append({
            "holder_score": row["liquidity"] / 5000.0,
            "liquidity": row["holder_score"] * 5000.0,
            "pumped": row["pumped"],
        })

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(8, "FEATURE_SWAP", test_feature_swap)


# =====================================================================
# 9. LABEL SHUFFLE
# =====================================================================

def test_label_shuffle():
    rows = [dict(row) for row in TRAIN]

    rng = random.Random(44121)

    labels = [row["pumped"] for row in rows]
    rng.shuffle(labels)

    for row, label in zip(rows, labels):
        row["pumped"] = label

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(9, "LABEL_SHUFFLE", test_label_shuffle)


# =====================================================================
# 10. MULTI-SEED STABILITY
# =====================================================================

def test_multiseed():
    entries = []

    for seed in range(20):
        random.seed(seed)

        rows = make_rows(
            range(0, 13, 2),
            [0, 5000, 10000, 20000, 30000],
        )

        rule, score, error = evolve(rows)

        entries.append({
            "seed": seed,
            "rule": rule_text(rule),
            "features": features(rule),
            "score": score,
            "accuracy": round(accuracy(rule, rows), 6),
            "error": error,
        })

    unique_rules = sorted({
        x["rule"]
        for x in entries
        if x["rule"] is not None
    })

    return {
        "runs": len(entries),
        "unique_rules": len(unique_rules),
        "rules": unique_rules,
        "results": entries,
    }


run_test(10, "MULTI_SEED_STABILITY", test_multiseed)


# =====================================================================
# 11. LARGE GRID
# =====================================================================

def test_large_grid():
    rows = make_rows(
        [x / 2 for x in range(0, 31)],
        [
            0,
            1000,
            2500,
            5000,
            7500,
            10000,
            15000,
            20000,
            30000,
            40000,
        ],
    )

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(11, "LARGE_GRID", test_large_grid)


# =====================================================================
# 12. OUT-OF-RANGE GENERALIZATION
# =====================================================================

def test_out_of_range():
    rows = make_rows(
        [-10, -5, -1, 14, 16, 20, 25],
        [500, 5000, 12500, 22500, 45000, 60000],
    )

    rule, score, error = evolve(TRAIN)

    return {
        "training_rule": rule_text(rule),
        "training_score": score,
        "training_samples": len(TRAIN),
        "out_of_range_samples": len(rows),
        "out_of_range_accuracy": round(accuracy(rule, rows), 6),
        "evaluated": evaluated_count(rule, rows),
        "error": error,
    }


run_test(12, "OUT_OF_RANGE_GENERALIZATION", test_out_of_range)


# =====================================================================
# 13. DENSE HOLDER GRID
# =====================================================================

def test_dense():
    rows = make_rows(
        [x / 10 for x in range(0, 201)],
        [0, 10000, 25000, 50000],
    )

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(13, "DENSE_HOLDER_GRID", test_dense)


# =====================================================================
# 14. LIQUIDITY RANGE STRESS
# =====================================================================

def test_liquidity_stress():
    rows = make_rows(
        [0, 3, 5, 7, 8, 10, 12, 15],
        [
            -10000,
            -1,
            0,
            1,
            1000,
            10000,
            50000,
            100000,
            1000000,
        ],
    )

    rule, score, error = evolve(TRAIN)

    return {
        "training_rule": rule_text(rule),
        "training_score": score,
        "stress_samples": len(rows),
        "stress_accuracy": round(accuracy(rule, rows), 6),
        "evaluated": evaluated_count(rule, rows),
        "error": error,
    }


run_test(14, "LIQUIDITY_RANGE_STRESS", test_liquidity_stress)


# =====================================================================
# 15. REPEATED DISCOVERY CONSISTENCY
# =====================================================================

def test_repeated():
    rules = []
    scores = []

    for i in range(50):
        random.seed(i + 1000)

        rule, score, error = evolve(TRAIN)

        rules.append(rule_text(rule))

        if isinstance(score, (int, float)):
            scores.append(float(score))

    unique_rules = sorted(set(rules))

    return {
        "runs": len(rules),
        "unique_rules": len(unique_rules),
        "rules": unique_rules,
        "mean_score": (
            round(statistics.mean(scores), 6)
            if scores else None
        ),
        "score_stdev": (
            round(statistics.pstdev(scores), 6)
            if len(scores) > 1
            else 0.0
        ),
    }


run_test(15, "REPEATED_DISCOVERY_CONSISTENCY", test_repeated)


# =====================================================================
# 16. BOOTSTRAP RESAMPLING
# =====================================================================

def test_bootstrap():
    rng = random.Random(73191)

    entries = []

    for i in range(50):
        sample = [
            dict(rng.choice(TRAIN))
            for _ in range(len(TRAIN))
        ]

        rule, score, error = evolve(sample)

        entries.append({
            "run": i,
            "rule": rule_text(rule),
            "features": features(rule),
            "score": score,
            "accuracy_on_original": round(
                accuracy(rule, TRAIN), 6
            ),
            "error": error,
        })

    valid = [
        x for x in entries
        if x["rule"] is not None
    ]

    return {
        "runs": len(entries),
        "successful_discoveries": len(valid),
        "success_rate": round(
            len(valid) / len(entries),
            6,
        ),
        "unique_rules": len({
            x["rule"] for x in valid
        }),
        "rules": sorted({
            x["rule"] for x in valid
        }),
        "results": entries,
    }


run_test(16, "BOOTSTRAP_RESAMPLING", test_bootstrap)


# =====================================================================
# 17. MANY IRRELEVANT FEATURES
# =====================================================================

def test_many_noise():
    rows = []

    for row in TRAIN:
        x = dict(row)

        for i in range(50):
            x[f"irrelevant_{i:02d}"] = float(
                (row["holder_score"] * (i + 3)
                 + row["liquidity"] * (i + 1) / 997)
                % (1000 + i)
            )

        rows.append(x)

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error) | {
        "core_feature_only": set(features(rule)) == {"holder_score"},
        "noise_feature_count": 50,
    }


run_test(17, "MANY_IRRELEVANT_FEATURES", test_many_noise)


# =====================================================================
# 18. DUPLICATE / CORRELATED FEATURES
# =====================================================================

def test_duplicate_features():
    rows = []

    for row in TRAIN:
        x = dict(row)

        x["holder_copy_1"] = row["holder_score"]
        x["holder_copy_2"] = row["holder_score"] * 1.0
        x["holder_copy_3"] = row["holder_score"] + 0.0

        rows.append(x)

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(18, "DUPLICATE_CORRELATED_FEATURES", test_duplicate_features)


# =====================================================================
# 19. MONOTONIC TRANSFORMATION
# =====================================================================

def test_monotonic_transform():
    rows = []

    for row in TRAIN:
        x = {
            "holder_score": row["holder_score"] ** 2,
            "liquidity": row["liquidity"],
            "pumped": row["pumped"],
        }

        rows.append(x)

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(19, "MONOTONIC_TRANSFORMATION", test_monotonic_transform)


# =====================================================================
# 20. NON-MONOTONIC TRANSFORMATION
# =====================================================================

def test_nonmonotonic_transform():
    rows = []

    for row in TRAIN:
        x = {
            "holder_score": (
                math.sin(row["holder_score"])
            ),
            "liquidity": row["liquidity"],
            "pumped": row["pumped"],
        }

        rows.append(x)

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(20, "NON_MONOTONIC_TRANSFORMATION", test_nonmonotonic_transform)


# =====================================================================
# 21. THRESHOLD PERTURBATION
# =====================================================================

def test_threshold_perturbation():
    values = [
        6.90,
        6.95,
        6.99,
        6.999,
        6.9999,
        7.0001,
        7.001,
        7.01,
        7.05,
        7.10,
    ]

    rows = []

    for h in values:
        for l in [0, 10000, 30000]:
            rows.append({
                "holder_score": h,
                "liquidity": l,
                "pumped": oracle_label({
                    "holder_score": h,
                    "liquidity": l,
                }),
            })

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(21, "THRESHOLD_PERTURBATION", test_threshold_perturbation)


# =====================================================================
# 22. TRAIN/TEST DISTRIBUTION SHIFT
# =====================================================================

def test_distribution_shift():
    train = make_rows(
        [0, 2, 4, 6, 8, 10, 12],
        [100, 200, 300, 500, 1000],
    )

    shifted = make_rows(
        [
            0.1,
            1.1,
            2.9,
            4.1,
            5.9,
            7.1,
            8.9,
            10.1,
            11.9,
            13.1,
        ],
        [
            7500,
            12500,
            17500,
            27500,
            45000,
        ],
    )

    rule, score, error = evolve(train)

    return {
        "rule": rule_text(rule),
        "features": features(rule),
        "training_score": score,
        "training_accuracy": round(
            accuracy(rule, train), 6
        ),
        "shifted_accuracy": round(
            accuracy(rule, shifted), 6
        ),
        "shifted_samples": len(shifted),
        "error": error,
    }


run_test(22, "DISTRIBUTION_SHIFT", test_distribution_shift)


# =====================================================================
# 23. EXTREME OUTLIERS
# =====================================================================

def test_outliers():
    rows = [dict(r) for r in TRAIN]

    rows.extend([
        {
            "holder_score": 1000000.0,
            "liquidity": 1.0,
            "pumped": 1,
        },
        {
            "holder_score": -1000000.0,
            "liquidity": 1.0,
            "pumped": 0,
        },
        {
            "holder_score": 7.0000001,
            "liquidity": 1e12,
            "pumped": 1,
        },
        {
            "holder_score": 6.9999999,
            "liquidity": -1e12,
            "pumped": 0,
        },
    ])

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(23, "EXTREME_OUTLIERS", test_outliers)


# =====================================================================
# 24. DUPLICATE ROW CONTAMINATION
# =====================================================================

def test_duplicate_contamination():
    rows = []

    for row in TRAIN:
        rows.extend([
            dict(row),
            dict(row),
            dict(row),
            dict(row),
            dict(row),
        ])

    rule, score, error = evolve(rows)

    return result(rule, score, rows, error)


run_test(24, "DUPLICATE_ROW_CONTAMINATION", test_duplicate_contamination)


# =====================================================================
# 25. CLASS IMBALANCE
# =====================================================================

def test_imbalance():
    positive = [
        dict(r)
        for r in TRAIN
        if oracle_label(r) == 1
    ]

    negative = [
        dict(r)
        for r in TRAIN
        if oracle_label(r) == 0
    ]

    rows = []

    for row in negative:
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))
        rows.append(dict(row))

    rows.extend(positive)

    rule, score, error = evolve(rows)

    return {
        "rule": rule_text(rule),
        "features": features(rule),
        "discovery_score": score,
        "training_accuracy": round(
            accuracy(rule, rows), 6
        ),
        "original_accuracy": round(
            accuracy(rule, TRAIN), 6
        ),
        "samples": len(rows),
        "positive_count": sum(
            oracle_label(r) for r in rows
        ),
        "negative_count": sum(
            1 - oracle_label(r) for r in rows
        ),
        "error": error,
    }


run_test(25, "CLASS_IMBALANCE", test_imbalance)


# =====================================================================
# 26. SAMPLE-SIZE SCALING
# =====================================================================

def test_sample_scaling():
    grids = [
        (
            "small",
            [0, 2, 4, 6, 8, 10, 12],
            [0, 30000],
        ),
        (
            "medium",
            [x / 2 for x in range(0, 25)],
            [0, 5000, 15000, 30000],
        ),
        (
            "large",
            [x / 10 for x in range(0, 131)],
            [0, 2500, 5000, 10000, 20000, 40000],
        ),
    ]

    output = {}

    for name, hs, ls in grids:
        rows = make_rows(hs, ls)
        rule, score, error = evolve(rows)

        output[name] = result(
            rule,
            score,
            rows,
            error,
        )

    return output


run_test(26, "SAMPLE_SIZE_SCALING", test_sample_scaling)


# =====================================================================
# 27. NULL DATA DISCOVERY
# =====================================================================

def test_null_data():
    rows = []

    for i in range(100):
        rows.append({
            "holder_score": float(i),
            "liquidity": float(i * 1000),
            "pumped": 0,
        })

    rule, score, error = evolve(rows)

    return {
        "rule": rule_text(rule),
        "features": features(rule),
        "discovery_score": score,
        "accuracy": round(accuracy(rule, rows), 6),
        "samples": len(rows),
        "error": error,
    }


run_test(27, "NULL_DATA_DISCOVERY", test_null_data)


# =====================================================================
# 28. RANDOM-LABEL NULL DISTRIBUTION
# =====================================================================

def test_random_label_distribution():
    rng = random.Random(821771)

    scores = []
    rules = []

    for i in range(30):
        rows = []

        for row in TRAIN:
            x = dict(row)
            rows.append(x)

        labels = [
            rng.randint(0, 1)
            for _ in rows
        ]

        for row, label in zip(rows, labels):
            row["pumped"] = label

        rule, score, error = evolve(rows)

        rules.append(rule_text(rule))

        if isinstance(score, (int, float)):
            scores.append(float(score))

    return {
        "runs": 30,
        "successful_scores": len(scores),
        "mean_discovery_score": (
            round(statistics.mean(scores), 6)
            if scores else None
        ),
        "max_discovery_score": (
            round(max(scores), 6)
            if scores else None
        ),
        "min_discovery_score": (
            round(min(scores), 6)
            if scores else None
        ),
        "unique_rules": len(set(rules)),
        "rules": sorted(set(rules)),
    }


run_test(28, "RANDOM_LABEL_NULL_DISTRIBUTION", test_random_label_distribution)


# =====================================================================
# 29. BASELINE COMPARISON
# =====================================================================

def test_baselines():
    truth = [oracle_label(r) for r in TEST]

    majority = Counter(truth).most_common(1)[0][0]

    majority_accuracy = sum(
        x == majority
        for x in truth
    ) / len(truth)

    always_zero = sum(x == 0 for x in truth) / len(truth)
    always_one = sum(x == 1 for x in truth) / len(truth)

    rule, score, error = evolve(TRAIN)

    return {
        "majority_class": majority,
        "majority_accuracy": round(
            majority_accuracy, 6
        ),
        "always_zero_accuracy": round(
            always_zero, 6
        ),
        "always_one_accuracy": round(
            always_one, 6
        ),
        "birth_edge_rule": rule_text(rule),
        "birth_edge_accuracy": round(
            accuracy(rule, TEST), 6
        ),
        "birth_edge_evaluated": evaluated_count(
            rule,
            TEST,
        ),
        "error": error,
    }


run_test(29, "BASELINE_COMPARISON", test_baselines)


# =====================================================================
# 30. RULE COMPLEXITY / PARSIMONY
# =====================================================================

def test_complexity():
    rule, score, error = evolve(TRAIN)

    predicate_count = (
        len(getattr(rule, "predicates", ()))
        if rule is not None
        else 0
    )

    return {
        "rule": rule_text(rule),
        "features": features(rule),
        "predicate_count": predicate_count,
        "feature_count": len(features(rule)),
        "training_accuracy": round(
            accuracy(rule, TRAIN), 6
        ),
        "held_out_accuracy": round(
            accuracy(rule, TEST), 6
        ),
        "error": error,
    }


run_test(30, "RULE_COMPLEXITY_PARSIMONY", test_complexity)


# =====================================================================
# FINAL SYNTHESIS
# =====================================================================

def safe_result(name):
    return RESULTS.get(name, {})


base = safe_result("BASE_DISCOVERY")
multi = safe_result("MULTI_SPLIT_IDENTIFIABILITY")
noise = safe_result("NOISE_RESISTANCE")
perm = safe_result("TRUE_FEATURE_PERMUTATION")
liq = safe_result("LIQUIDITY_ONLY_ABLATION")
holder = safe_result("HOLDER_ONLY_ABLATION")
boundary = safe_result("BOUNDARY_RECOVERY")
multiseed = safe_result("MULTI_SEED_STABILITY")
repeated = safe_result("REPEATED_DISCOVERY_CONSISTENCY")
large = safe_result("LARGE_GRID")
dense = safe_result("DENSE_HOLDER_GRID")
oor = safe_result("OUT_OF_RANGE_GENERALIZATION")
null_data = safe_result("NULL_DATA_DISCOVERY")
random_null = safe_result("RANDOM_LABEL_NULL_DISTRIBUTION")
baseline = safe_result("BASELINE_COMPARISON")


unique_seed_rules = multiseed.get(
    "unique_rules",
    None,
)

unique_repeated_rules = repeated.get(
    "unique_rules",
    None,
)

summary = {
    "base_held_out_accuracy": base.get(
        "held_out_accuracy"
    ),
    "base_training_accuracy": base.get(
        "accuracy"
    ),
    "base_rule": base.get(
        "rule"
    ),
    "base_features": base.get(
        "features"
    ),

    "noise_resistance": noise.get(
        "ignored_noise"
    ),

    "liquidity_only_rule": liq.get(
        "rule"
    ),

    "holder_only_accuracy": holder.get(
        "accuracy"
    ),

    "boundary_all_correct": boundary.get(
        "all_correct"
    ),

    "multi_seed_unique_rules": unique_seed_rules,

    "repeated_discovery_unique_rules":
        unique_repeated_rules,

    "large_grid_accuracy": large.get(
        "accuracy"
    ),

    "dense_grid_accuracy": dense.get(
        "accuracy"
    ),

    "out_of_range_accuracy": oor.get(
        "out_of_range_accuracy"
    ),

    "null_data_accuracy": null_data.get(
        "accuracy"
    ),

    "random_label_mean_score":
        random_null.get(
            "mean_discovery_score"
        ),

    "random_label_max_score":
        random_null.get(
            "max_discovery_score"
        ),

    "baseline_test_accuracy":
        baseline.get(
            "birth_edge_accuracy"
        ),

    "baseline_majority_accuracy":
        baseline.get(
            "majority_accuracy"
        ),

    "feature_permutation_accuracy":
        perm.get(
            "post_permutation_accuracy"
        ),
}


# =====================================================================
# AUTOMATIC INTERPRETATION
# =====================================================================

checks = {}

checks["base_recovery"] = (
    isinstance(
        summary["base_held_out_accuracy"],
        (int, float),
    )
    and summary["base_held_out_accuracy"] >= 0.80
)

checks["noise_resistance"] = (
    summary["noise_resistance"] is True
)

checks["holder_is_sufficient"] = (
    isinstance(
        summary["holder_only_accuracy"],
        (int, float),
    )
    and summary["holder_only_accuracy"] >= 0.95
)

checks["liquidity_not_sufficient"] = (
    summary["liquidity_only_rule"] is None
    or safe_result(
        "LIQUIDITY_ONLY_ABLATION"
    ).get("accuracy", 0) < 0.80
)

checks["boundary_recovery"] = (
    summary["boundary_all_correct"] is True
)

checks["multi_seed_stability"] = (
    summary["multi_seed_unique_rules"] == 1
)

checks["repeated_stability"] = (
    summary["repeated_discovery_unique_rules"] == 1
)

checks["large_grid_recovery"] = (
    isinstance(
        summary["large_grid_accuracy"],
        (int, float),
    )
    and summary["large_grid_accuracy"] >= 0.90
)

checks["dense_grid_recovery"] = (
    isinstance(
        summary["dense_grid_accuracy"],
        (int, float),
    )
    and summary["dense_grid_accuracy"] >= 0.90
)

checks["out_of_range_recovery"] = (
    isinstance(
        summary["out_of_range_accuracy"],
        (int, float),
    )
    and summary["out_of_range_accuracy"] >= 0.90
)

checks["null_data_not_perfect"] = (
    summary["null_data_accuracy"] is None
    or summary["null_data_accuracy"] < 0.95
)


# =====================================================================
# WRITE MACHINE-READABLE REPORT
# =====================================================================

report = {
    "system": "BIRTH_EDGE",
    "test_suite": "COMPREHENSIVE_ADVERSARIAL_VALIDATION",
    "version": 1,
    "base_training_samples": len(TRAIN),
    "base_test_samples": len(TEST),
    "tests_run": 30,
    "tests_with_runtime_errors": len(FAILURES),
    "runtime_error_tests": FAILURES,
    "results": RESULTS,
    "summary": summary,
    "checks": checks,
}


with open(REPORT_FILE, "w", encoding="utf-8") as fh:
    json.dump(
        report,
        fh,
        indent=2,
        sort_keys=True,
        default=str,
    )


# =====================================================================
# FINAL CONSOLE REPORT
# =====================================================================

print()
print("=" * 72)
print("BIRTH_EDGE ADVERSARIAL VALIDATION — FINAL REPORT")
print("=" * 72)

print()
print("BASE RULE:")
print(summary["base_rule"])

print()
print("BASE FEATURES:")
print(summary["base_features"])

print()
print(
    "BASE TRAIN ACCURACY:",
    summary["base_training_accuracy"],
)

print(
    "BASE HELD-OUT ACCURACY:",
    summary["base_held_out_accuracy"],
)

print()
print("KEY FINDINGS")
print("-" * 72)

for key, value in checks.items():
    print(
        f"{key:32s}: "
        f"{'PASS' if value else 'FAIL'}"
    )

print()
print("MULTI-SEED UNIQUE RULES:",
      summary["multi_seed_unique_rules"])

print("20/50-RUN REPEAT UNIQUE RULES:",
      summary["repeated_discovery_unique_rules"])

print("LARGE GRID ACCURACY:",
      summary["large_grid_accuracy"])

print("DENSE GRID ACCURACY:",
      summary["dense_grid_accuracy"])

print("OUT-OF-RANGE ACCURACY:",
      summary["out_of_range_accuracy"])

print("FEATURE-PERMUTATION ACCURACY:",
      summary["feature_permutation_accuracy"])

print("NULL-DATA ACCURACY:",
      summary["null_data_accuracy"])

print("RANDOM-LABEL MEAN SCORE:",
      summary["random_label_mean_score"])

print("RANDOM-LABEL MAX SCORE:",
      summary["random_label_max_score"])

print()
print("RUNTIME ERRORS:",
      len(FAILURES))

if FAILURES:
    for name in FAILURES:
        print("  -", name)

print()
print("JSON REPORT:")
print(REPORT_FILE)

print()
print("=" * 72)
print("BATCH COMPLETE")
print("=" * 72)
