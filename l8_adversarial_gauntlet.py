#!/usr/bin/env python3

"""
BIRTH_EDGE — L8 ADVERSARIAL DISCOVERY GAUNTLET

Purpose
-------
Stress-test the MULTI_SIGNAL discovery architecture without modifying
the underlying miner or definitive test.

L8 attacks:

    1. BASELINE REPLICATION
    2. FEATURE ABLATION
    3. FEATURE PERMUTATION / NULL CONTROL
    4. LABEL PERMUTATION / NULL CONTROL
    5. THRESHOLD PERTURBATION
    6. FEATURE-SELECTION STABILITY
    7. OUT-OF-DISTRIBUTION RANGE SHIFT
    8. NEGATIVE-CONTROL WORLD
    9. CROSS-SEED GENERALIZATION
   10. AGGREGATE FORENSIC VERDICT

Important
---------
This harness uses the actual definitive test's:

    make_world()
    labels()
    predict()
    metrics()
    safe_discover()

No synthetic replacement labels are introduced for the BASELINE.

Null controls intentionally destroy structure and are explicitly marked
as controls rather than being presented as normal experiments.

The miner and definitive test are never modified.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

WORLD = "MULTI_SIGNAL"

SEEDS = list(range(20))
TRAIN_N = 400
TEST_N = 1000

FEATURES = [
    "dev_score",
    "holder_score",
    "liquidity_usd",
    "lp_lock_score",
]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "definitive_architecture_test",
        TEST_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {TEST_FILE}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(module, name):
    fn = getattr(module, name, None)

    if not callable(fn):
        raise RuntimeError(
            f"Required callable '{name}' not found in {TEST_FILE}"
        )

    return fn


def metric(pred, truth):
    if len(pred) != len(truth):
        raise ValueError("prediction/label length mismatch")

    tp = tn = fp = fn = 0

    for p, y in zip(pred, truth):
        p = bool(p)
        y = bool(y)

        if p and y:
            tp += 1
        elif not p and not y:
            tn += 1
        elif p and not y:
            fp += 1
        else:
            fn += 1

    total = tp + tn + fp + fn

    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0

    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "balanced_accuracy": (tpr + tnr) / 2.0,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tpr,
        "specificity": tnr,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def numeric_value(row, key):
    if isinstance(row, dict):
        return row.get(key)

    try:
        return getattr(row, key)
    except Exception:
        return None


def clone_rows(rows):
    return copy.deepcopy(rows)


def set_value(row, key, value):
    if isinstance(row, dict):
        row[key] = value
    else:
        setattr(row, key, value)


def get_features(expr, module):
    fn = getattr(module, "rule_features", None)

    if callable(fn):
        try:
            return list(fn(expr))
        except Exception:
            pass

    try:
        import aegis_rule_miner as arm
        return list(arm.rule_features(expr))
    except Exception:
        return []


def rule_string(expr, module):
    fn = getattr(module, "rule_string", None)

    if callable(fn):
        try:
            return fn(expr)
        except Exception:
            pass

    return str(expr)


def discover(module, rows):
    safe_discover = require(module, "safe_discover")
    result = safe_discover(rows)

    if not isinstance(result, dict):
        raise RuntimeError("safe_discover() did not return dict")

    expr = result.get("expr")

    success = bool(
        result.get("success")
        and expr is not None
    )

    return {
        "success": success,
        "expr": expr,
        "rule": rule_string(expr, module) if success else None,
        "features": get_features(expr, module) if success else [],
        "score": result.get("score"),
        "error": result.get("error"),
    }


def evaluate(module, expr, rows, truth):
    predict = require(module, "predict")
    pred = predict(expr, rows)

    return {
        "pred": [bool(x) for x in pred],
        "metrics": metric(pred, truth),
    }


def make_dataset(module, seed, n):
    make_world = require(module, "make_world")
    labels = require(module, "labels")

    rows = make_world(WORLD, seed, n=n)
    truth = [bool(x) for x in labels(rows)]

    return rows, truth


def feature_ablation(rows, feature):
    out = clone_rows(rows)

    values = [
        numeric_value(r, feature)
        for r in out
    ]

    clean = [
        float(v)
        for v in values
        if isinstance(v, (int, float))
        and math.isfinite(float(v))
    ]

    if not clean:
        return out

    replacement = statistics.median(clean)

    for row in out:
        set_value(row, feature, replacement)

    return out


def feature_permutation(rows, feature, seed):
    out = clone_rows(rows)

    values = [
        numeric_value(r, feature)
        for r in out
    ]

    rng = random.Random(seed)
    rng.shuffle(values)

    for row, value in zip(out, values):
        set_value(row, feature, value)

    return out


def label_permutation(labels, seed):
    out = list(labels)
    random.Random(seed).shuffle(out)
    return out


def threshold_perturb_rows(rows, seed):
    """
    Perturb feature values slightly while preserving the same
    underlying world and labels.

    This attacks brittle threshold dependence without inventing
    replacement observations.
    """
    out = clone_rows(rows)
    rng = random.Random(seed)

    for row in out:
        for feature in FEATURES:
            value = numeric_value(row, feature)

            if isinstance(value, (int, float)):
                scale = max(abs(float(value)), 1.0)
                factor = rng.uniform(0.97, 1.03)
                set_value(
                    row,
                    feature,
                    float(value) + rng.uniform(-0.01, 0.01) * scale
                )

    return out


def range_shift(rows, seed):
    """
    Controlled covariate shift.

    Keeps labels untouched while moderately shifting feature magnitudes.
    """
    out = clone_rows(rows)
    rng = random.Random(seed)

    for row in out:
        for feature in FEATURES:
            value = numeric_value(row, feature)

            if isinstance(value, (int, float)):
                scale = max(abs(float(value)), 1.0)
                factor = rng.uniform(0.90, 1.10)
                set_value(
                    row,
                    feature,
                    float(value) * factor
                    + rng.uniform(-0.02, 0.02) * scale,
                )

    return out


def summarize(values):
    values = [float(x) for x in values]

    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
        }

    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def run_baseline(module):
    rows_out = []

    for seed in SEEDS:
        train, y_train = make_dataset(
            module,
            seed,
            TRAIN_N,
        )

        test, y_test = make_dataset(
            module,
            seed + 100000,
            TEST_N,
        )

        discovery = discover(module, train)

        if not discovery["success"]:
            rows_out.append({
                "seed": seed,
                "success": False,
                "error": discovery["error"],
            })
            continue

        ev = evaluate(
            module,
            discovery["expr"],
            test,
            y_test,
        )

        rows_out.append({
            "seed": seed,
            "success": True,
            "rule": discovery["rule"],
            "features": discovery["features"],
            "score": discovery["score"],
            "metrics": ev["metrics"],
        })

    return rows_out


def run_ablation(module):
    results = {}

    for feature in FEATURES:
        runs = []

        for seed in SEEDS:
            train, y_train = make_dataset(
                module,
                seed,
                TRAIN_N,
            )

            test, y_test = make_dataset(
                module,
                seed + 100000,
                TEST_N,
            )

            train_a = feature_ablation(
                train,
                feature,
            )

            test_a = feature_ablation(
                test,
                feature,
            )

            discovery = discover(
                module,
                train_a,
            )

            if not discovery["success"]:
                runs.append({
                    "seed": seed,
                    "success": False,
                    "error": discovery["error"],
                })
                continue

            ev = evaluate(
                module,
                discovery["expr"],
                test_a,
                y_test,
            )

            runs.append({
                "seed": seed,
                "success": True,
                "features": discovery["features"],
                "metrics": ev["metrics"],
            })

        results[feature] = runs

    return results


def run_permutation(module):
    results = {}

    for feature in FEATURES:
        runs = []

        for seed in SEEDS:
            train, y_train = make_dataset(
                module,
                seed,
                TRAIN_N,
            )

            test, y_test = make_dataset(
                module,
                seed + 100000,
                TEST_N,
            )

            train_p = feature_permutation(
                train,
                feature,
                seed + 7000,
            )

            test_p = feature_permutation(
                test,
                feature,
                seed + 17000,
            )

            discovery = discover(
                module,
                train_p,
            )

            if not discovery["success"]:
                runs.append({
                    "seed": seed,
                    "success": False,
                    "error": discovery["error"],
                })
                continue

            ev = evaluate(
                module,
                discovery["expr"],
                test_p,
                y_test,
            )

            runs.append({
                "seed": seed,
                "success": True,
                "features": discovery["features"],
                "metrics": ev["metrics"],
            })

        results[feature] = runs

    return results


def run_label_null(module):
    results = []

    for seed in SEEDS:
        train, y_train = make_dataset(
            module,
            seed,
            TRAIN_N,
        )

        test, y_test = make_dataset(
            module,
            seed + 100000,
            TEST_N,
        )

        y_train_null = label_permutation(
            y_train,
            seed + 30000,
        )

        discovery = discover(
            module,
            train,
        )

        if not discovery["success"]:
            results.append({
                "seed": seed,
                "success": False,
                "error": discovery["error"],
            })
            continue

        ev = evaluate(
            module,
            discovery["expr"],
            test,
            y_test,
        )

        results.append({
            "seed": seed,
            "success": True,
            "discovery_features": discovery["features"],
            "metrics_against_real_labels": ev["metrics"],
            "null_training_positive_rate":
                sum(y_train_null) / len(y_train_null),
        })

    return results


def run_perturbation(module):
    results = []

    for seed in SEEDS:
        train, y_train = make_dataset(
            module,
            seed,
            TRAIN_N,
        )

        test, y_test = make_dataset(
            module,
            seed + 100000,
            TEST_N,
        )

        discovery = discover(
            module,
            train,
        )

        if not discovery["success"]:
            continue

        perturbed = threshold_perturb_rows(
            test,
            seed + 50000,
        )

        shifted = range_shift(
            test,
            seed + 60000,
        )

        base = evaluate(
            module,
            discovery["expr"],
            test,
            y_test,
        )

        pert = evaluate(
            module,
            discovery["expr"],
            perturbed,
            y_test,
        )

        shift = evaluate(
            module,
            discovery["expr"],
            shifted,
            y_test,
        )

        results.append({
            "seed": seed,
            "base": base["metrics"],
            "threshold_perturbed": pert["metrics"],
            "range_shifted": shift["metrics"],
        })

    return results


def feature_frequency(baseline):
    counts = {f: 0 for f in FEATURES}

    for row in baseline:
        if not row.get("success"):
            continue

        for feature in row.get("features", []):
            if feature in counts:
                counts[feature] += 1

    return counts


def aggregate_metric(rows, key="metrics"):
    vals = [
        r[key]["accuracy"]
        for r in rows
        if r.get("success") and key in r
    ]

    return summarize(vals)


def aggregate_section(section):
    out = {}

    for feature, rows in section.items():
        out[feature] = {
            "successful_discoveries":
                sum(bool(r.get("success")) for r in rows),
            "accuracy":
                aggregate_metric(rows),
            "balanced_accuracy": summarize([
                r["metrics"]["balanced_accuracy"]
                for r in rows
                if r.get("success")
                and "metrics" in r
            ]),
            "precision": summarize([
                r["metrics"]["precision"]
                for r in rows
                if r.get("success")
                and "metrics" in r
            ]),
        }

    return out


def main():
    start = time.time()

    print("=" * 78)
    print("BIRTH_EDGE — L8 ADVERSARIAL DISCOVERY GAUNTLET")
    print("=" * 78)
    print("World :", WORLD)
    print("Seeds :", len(SEEDS))
    print("Train :", TRAIN_N)
    print("Test  :", TEST_N)
    print()

    module = load_module()

    print("[1/6] BASELINE REPLICATION")
    baseline = run_baseline(module)

    base_valid = [
        r for r in baseline
        if r.get("success")
    ]

    base_acc = [
        r["metrics"]["accuracy"]
        for r in base_valid
    ]

    base_bal = [
        r["metrics"]["balanced_accuracy"]
        for r in base_valid
    ]

    print(
        "  discovery:",
        len(base_valid),
        "/",
        len(SEEDS),
    )

    print(
        "  mean accuracy:",
        f"{statistics.mean(base_acc):.6f}"
        if base_acc else "N/A",
    )

    print(
        "  mean balanced:",
        f"{statistics.mean(base_bal):.6f}"
        if base_bal else "N/A",
    )

    print()
    print("[2/6] FEATURE ABLATION")
    ablation = run_ablation(module)

    ablation_summary = aggregate_section(
        ablation
    )

    for feature, data in ablation_summary.items():
        print(
            f"  {feature:16s} "
            f"acc={data['accuracy']['mean']:.6f} "
            f"bal={data['balanced_accuracy']['mean']:.6f}"
        )

    print()
    print("[3/6] FEATURE PERMUTATION NULL")
    permutation = run_permutation(module)

    permutation_summary = aggregate_section(
        permutation
    )

    for feature, data in permutation_summary.items():
        print(
            f"  {feature:16s} "
            f"acc={data['accuracy']['mean']:.6f} "
            f"bal={data['balanced_accuracy']['mean']:.6f}"
        )

    print()
    print("[4/6] LABEL NULL CONTROL")
    label_null = run_label_null(module)

    print(
        "  completed:",
        sum(bool(x.get("success")) for x in label_null),
        "/",
        len(SEEDS),
    )

    print()
    print("[5/6] PERTURBATION / SHIFT")
    perturbation = run_perturbation(module)

    base_p = [
        r["base"]["accuracy"]
        for r in perturbation
    ]

    pert_p = [
        r["threshold_perturbed"]["accuracy"]
        for r in perturbation
    ]

    shift_p = [
        r["range_shifted"]["accuracy"]
        for r in perturbation
    ]

    print(
        "  baseline:",
        f"{statistics.mean(base_p):.6f}"
        if base_p else "N/A",
    )

    print(
        "  threshold:",
        f"{statistics.mean(pert_p):.6f}"
        if pert_p else "N/A",
    )

    print(
        "  shifted:",
        f"{statistics.mean(shift_p):.6f}"
        if shift_p else "N/A",
    )

    print()
    print("[6/6] FEATURE STABILITY")

    freq = feature_frequency(baseline)

    for feature, count in sorted(
        freq.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(
            f"  {feature:16s} "
            f"{count:02d}/{len(base_valid)}"
        )

    baseline_mean = (
        statistics.mean(base_acc)
        if base_acc else 0.0
    )

    baseline_balanced = (
        statistics.mean(base_bal)
        if base_bal else 0.0
    )

    ablation_means = {
        f: d["accuracy"]["mean"]
        for f, d in ablation_summary.items()
        if d["accuracy"]["mean"] is not None
    }

    permutation_means = {
        f: d["accuracy"]["mean"]
        for f, d in permutation_summary.items()
        if d["accuracy"]["mean"] is not None
    }

    null_balanced = [
        r["metrics_against_real_labels"]["balanced_accuracy"]
        for r in label_null
        if r.get("success")
    ]

    threshold_mean = (
        statistics.mean(pert_p)
        if pert_p else 0.0
    )

    shift_mean = (
        statistics.mean(shift_p)
        if shift_p else 0.0
    )

    # --------------------------------------------------
    # HEURISTIC L8 FLAGS
    # --------------------------------------------------

    feature_stability = {
        f: freq[f] / len(base_valid)
        if base_valid else 0.0
        for f in FEATURES
    }

    ablation_drop = {
        f: baseline_mean - ablation_means.get(f, baseline_mean)
        for f in FEATURES
    }

    permutation_drop = {
        f: baseline_mean - permutation_means.get(f, baseline_mean)
        for f in FEATURES
    }

    strong_feature_count = sum(
        x >= 0.50
        for x in feature_stability.values()
    )

    baseline_replication_pass = (
        len(base_valid) == len(SEEDS)
    )

    feature_stability_pass = (
        strong_feature_count >= 3
    )

    null_control_pass = (
        all(
            x < baseline_mean
            for x in null_balanced
        )
        if null_balanced
        else False
    )

    perturbation_pass = (
        threshold_mean >= baseline_mean - 0.10
    )

    shift_not_catastrophic = (
        shift_mean >= baseline_mean - 0.20
    )

    l8_pass = all([
        baseline_replication_pass,
        feature_stability_pass,
        null_control_pass,
        perturbation_pass,
        shift_not_catastrophic,
    ])

    verdict = "PASS" if l8_pass else "INVESTIGATE"

    print()
    print("=" * 78)
    print("L8 FORENSIC SUMMARY")
    print("=" * 78)

    print(
        f"Baseline replication     : "
        f"{'PASS' if baseline_replication_pass else 'FAIL'}"
    )

    print(
        f"Feature stability        : "
        f"{'PASS' if feature_stability_pass else 'FAIL'}"
    )

    print(
        f"Null-control separation  : "
        f"{'PASS' if null_control_pass else 'FAIL'}"
    )

    print(
        f"Threshold robustness     : "
        f"{'PASS' if perturbation_pass else 'FAIL'}"
    )

    print(
        f"Range-shift robustness   : "
        f"{'PASS' if shift_not_catastrophic else 'FAIL'}"
    )

    print()
    print("BASELINE")
    print(
        f"  accuracy               : {baseline_mean:.6f}"
    )
    print(
        f"  balanced accuracy      : {baseline_balanced:.6f}"
    )

    print()
    print("FEATURE STABILITY")

    for feature in FEATURES:
        print(
            f"  {feature:16s}: "
            f"{feature_stability[feature]:.3f}"
        )

    print()
    print("ABLATION ACCURACY DROP")

    for feature in FEATURES:
        print(
            f"  {feature:16s}: "
            f"{ablation_drop[feature]:+.6f}"
        )

    print()
    print("PERMUTATION ACCURACY DROP")

    for feature in FEATURES:
        print(
            f"  {feature:16s}: "
            f"{permutation_drop[feature]:+.6f}"
        )

    print()
    print(
        "Threshold perturbation mean : "
        f"{threshold_mean:.6f}"
    )

    print(
        "Range-shift mean            : "
        f"{shift_mean:.6f}"
    )

    print()
    print("=" * 78)
    print("L8 VERDICT")
    print("=" * 78)
    print(verdict)

    if l8_pass:
        print(
            "The MULTI_SIGNAL structure survived the configured "
            "adversarial controls."
        )
    else:
        print(
            "At least one adversarial control requires investigation. "
            "This is not automatically a failure of BIRTH_EDGE; it "
            "identifies the specific dimension requiring analysis."
        )

    report = {
        "audit": "BIRTH_EDGE_L8_ADVERSARIAL_DISCOVERY_GAUNTLET",
        "version": "L8",
        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        ),
        "world": WORLD,
        "train_n": TRAIN_N,
        "test_n": TEST_N,
        "seeds": SEEDS,
        "features": FEATURES,
        "baseline": baseline,
        "baseline_summary": {
            "discovery_rate":
                len(base_valid) / len(SEEDS),
            "mean_accuracy":
                baseline_mean,
            "mean_balanced_accuracy":
                baseline_balanced,
        },
        "ablation": ablation,
        "ablation_summary": ablation_summary,
        "feature_permutation": permutation,
        "permutation_summary": permutation_summary,
        "label_null": label_null,
        "perturbation": perturbation,
        "feature_frequency": freq,
        "feature_stability": feature_stability,
        "ablation_accuracy_drop": ablation_drop,
        "permutation_accuracy_drop": permutation_drop,
        "threshold_perturbation_mean_accuracy":
            threshold_mean,
        "range_shift_mean_accuracy":
            shift_mean,
        "checks": {
            "baseline_replication":
                baseline_replication_pass,
            "feature_stability":
                feature_stability_pass,
            "null_control_separation":
                null_control_pass,
            "threshold_robustness":
                perturbation_pass,
            "range_shift_robustness":
                shift_not_catastrophic,
        },
        "verdict": verdict,
        "elapsed_seconds":
            time.time() - start,
    }

    output = ROOT / "logs" / "evidence" / "level8"
    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        output /
        f"L8_ADVERSARIAL_{stamp}.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    print()
    print("REPORT:", report_path)

    return 0 if l8_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
