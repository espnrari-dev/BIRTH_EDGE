#!/usr/bin/env python3

import json
import random
import statistics
import traceback
from pathlib import Path

import aegis_rule_miner as arm

OUT = Path("birth_edge_architecture_generalization_report.json")


# ============================================================
# BIRTH_EDGE ARCHITECTURE GENERALIZATION
#
# Tests whether the EXISTING BIRTH_EDGE discovery architecture
# can recover different underlying rule structures.
#
# Ground truth is NEVER supplied to evolve_rule().
# It is used only AFTER discovery for evaluation.
# ============================================================


def predict_rule(rule, row):
    return int(bool(arm.evaluate_rule(rule, row)))


def discover(rows, seed):
    random.seed(seed)
    return arm.evolve_rule(
        rows,
        generations=60,
        population_size=100,
        max_depth=5,
    )


def accuracy(rule, rows):
    correct = 0

    for row in rows:
        try:
            if predict_rule(rule, row) == int(row["label"]):
                correct += 1
        except Exception:
            pass

    return correct / len(rows) if rows else 0.0


# ============================================================
# DATA GENERATORS
# ============================================================

def linear_threshold(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(200):
        x = rng.uniform(-20, 20)
        rows.append({
            "x": x,
            "noise": rng.random(),
            "label": int(x > 4),
        })

    return rows


def inverse_threshold(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(200):
        x = rng.uniform(-20, 20)
        rows.append({
            "x": x,
            "noise": rng.random(),
            "label": int(x < 4),
        })

    return rows


def different_threshold(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(200):
        x = rng.uniform(-20, 20)
        rows.append({
            "x": x,
            "noise": rng.random(),
            "label": int(x > -7),
        })

    return rows


def nonlinear_abs(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(300):
        x = rng.uniform(-10, 10)

        rows.append({
            "x": x,
            "noise": rng.random(),
            "label": int(abs(x) > 5),
        })

    return rows


def interaction(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(400):
        x = rng.uniform(-5, 5)
        z = rng.uniform(-5, 5)

        rows.append({
            "x": x,
            "z": z,
            "noise": rng.random(),
            "label": int(x * z > 4),
        })

    return rows


def irrelevant_overload(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(250):
        x = rng.uniform(0, 20)

        row = {
            "x": x,
            "label": int(x > 10),
        }

        for i in range(50):
            row[f"noise_{i}"] = rng.uniform(-1000, 1000)

        rows.append(row)

    return rows


def random_labels(seed):
    rng = random.Random(seed)
    rows = []

    for _ in range(250):
        rows.append({
            "x": rng.uniform(-20, 20),
            "z": rng.uniform(-20, 20),
            "label": rng.randint(0, 1),
        })

    return rows


def distribution_shift(seed):
    rng = random.Random(seed)

    train = []
    test = []

    for _ in range(200):
        x = rng.uniform(0, 10)
        train.append({
            "x": x,
            "label": int(x > 7),
        })

    for _ in range(200):
        x = rng.uniform(5, 20)
        test.append({
            "x": x,
            "label": int(x > 7),
        })

    return train, test


def out_of_range(seed):
    rng = random.Random(seed)

    train = []
    test = []

    for _ in range(200):
        x = rng.uniform(0, 10)
        train.append({
            "x": x,
            "label": int(x > 7),
        })

    for _ in range(200):
        x = rng.uniform(10, 30)
        test.append({
            "x": x,
            "label": int(x > 7),
        })

    return train, test


DATASETS = {
    "LINEAR_THRESHOLD": linear_threshold,
    "INVERSE_THRESHOLD": inverse_threshold,
    "DIFFERENT_THRESHOLD": different_threshold,
    "NONLINEAR_ABS": nonlinear_abs,
    "TWO_FEATURE_INTERACTION": interaction,
    "IRRELEVANT_FEATURE_OVERLOAD": irrelevant_overload,
    "RANDOM_LABEL_CONTROL": random_labels,
}


# ============================================================
# SINGLE DATASET
# ============================================================

def run_dataset(name, generator, seeds):

    rows = generator(42)

    results = []

    for seed in seeds:
        try:
            rule = discover(rows, seed)
            acc = accuracy(rule, rows)

            results.append({
                "seed": seed,
                "rule": repr(rule),
                "accuracy": acc,
                "error": None,
            })

        except Exception as exc:
            results.append({
                "seed": seed,
                "rule": None,
                "accuracy": None,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            })

    valid = [
        r["accuracy"]
        for r in results
        if r["accuracy"] is not None
    ]

    rules = sorted(set(
        r["rule"]
        for r in results
        if r["rule"] is not None
    ))

    return {
        "samples": len(rows),
        "runs": len(seeds),
        "successful_runs": len(valid),
        "runtime_errors": len(results) - len(valid),
        "mean_accuracy": statistics.mean(valid) if valid else None,
        "min_accuracy": min(valid) if valid else None,
        "max_accuracy": max(valid) if valid else None,
        "accuracy_stdev": (
            statistics.pstdev(valid)
            if len(valid) > 1
            else 0.0
        ),
        "unique_rules": len(rules),
        "rules": rules,
        "runs_detail": results,
    }


# ============================================================
# HELD-OUT TESTS
# ============================================================

def run_shift_test():

    train, test = distribution_shift(42)

    rule = discover(train, 0)

    return {
        "training_samples": len(train),
        "held_out_samples": len(test),
        "training_accuracy": accuracy(rule, train),
        "held_out_accuracy": accuracy(rule, test),
        "rule": repr(rule),
    }


def run_out_of_range_test():

    train, test = out_of_range(42)

    rule = discover(train, 0)

    return {
        "training_samples": len(train),
        "held_out_samples": len(test),
        "training_accuracy": accuracy(rule, train),
        "out_of_range_accuracy": accuracy(rule, test),
        "rule": repr(rule),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print("BIRTH_EDGE — ARCHITECTURE GENERALIZATION TEST")
    print("=" * 72)
    print("ENGINE:", arm.__file__)
    print("ENTRYPOINT: evolve_rule(rows, ...)")
    print()

    report = {
        "system": "BIRTH_EDGE",
        "test_suite": "ARCHITECTURE_GENERALIZATION",
        "version": 2,
        "entrypoint": "evolve_rule",
        "datasets": {},
        "runtime_errors": [],
    }

    seeds = list(range(20))

    for name, generator in DATASETS.items():

        print("-" * 72)
        print("TEST:", name)

        try:
            result = run_dataset(
                name,
                generator,
                seeds,
            )

            report["datasets"][name] = result

            print(
                "mean_accuracy =",
                result["mean_accuracy"]
            )

            print(
                "min_accuracy =",
                result["min_accuracy"]
            )

            print(
                "max_accuracy =",
                result["max_accuracy"]
            )

            print(
                "stdev =",
                result["accuracy_stdev"]
            )

            print(
                "unique_rules =",
                result["unique_rules"]
            )

            print(
                "runtime_errors =",
                result["runtime_errors"]
            )

        except Exception as exc:

            error = {
                "dataset": name,
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }

            report["runtime_errors"].append(error)

            print("RUNTIME ERROR")
            print(traceback.format_exc())

    print()
    print("-" * 72)
    print("TEST: DISTRIBUTION_SHIFT")

    try:
        result = run_shift_test()
        report["distribution_shift"] = result

        print(
            "training_accuracy =",
            result["training_accuracy"]
        )

        print(
            "held_out_accuracy =",
            result["held_out_accuracy"]
        )

        print("rule =", result["rule"])

    except Exception as exc:

        report["runtime_errors"].append({
            "dataset": "DISTRIBUTION_SHIFT",
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })

        print(traceback.format_exc())

    print()
    print("-" * 72)
    print("TEST: OUT_OF_RANGE")

    try:
        result = run_out_of_range_test()
        report["out_of_range"] = result

        print(
            "training_accuracy =",
            result["training_accuracy"]
        )

        print(
            "out_of_range_accuracy =",
            result["out_of_range_accuracy"]
        )

        print("rule =", result["rule"])

    except Exception as exc:

        report["runtime_errors"].append({
            "dataset": "OUT_OF_RANGE",
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })

        print(traceback.format_exc())

    report["summary"] = {
        "datasets_tested": len(report["datasets"]),
        "runtime_errors": len(report["runtime_errors"]),
        "all_dataset_runs_completed": (
            len(report["runtime_errors"]) == 0
        ),
    }

    OUT.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    print()
    print("=" * 72)
    print("FINAL RESULT")
    print("=" * 72)
    print(
        "Datasets tested:",
        len(report["datasets"])
    )
    print(
        "Runtime errors:",
        len(report["runtime_errors"])
    )
    print("Report:", OUT)
    print("=" * 72)


if __name__ == "__main__":
    main()
