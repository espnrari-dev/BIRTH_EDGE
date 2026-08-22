#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backups/L8_FAST_$STAMP"
EVIDENCE="$ROOT/logs/evidence/level8/L8_FAST_$STAMP"

mkdir -p "$BACKUP" "$EVIDENCE"

echo "======================================================================"
echo "BIRTH_EDGE — L8 FAST ADVERSARIAL DIAGNOSTIC"
echo "======================================================================"
echo "STAMP    : $STAMP"
echo "EVIDENCE : $EVIDENCE"
echo

for f in \
    aegis_rule_miner.py \
    definitive_architecture_test.py \
    forensic_multisignal_audit.py
do
    if [ -f "$ROOT/$f" ]; then
        cp -p "$ROOT/$f" "$BACKUP/"
        echo "BACKUP   : $f"
    fi
done

(
    cd "$ROOT"
    sha256sum \
        aegis_rule_miner.py \
        definitive_architecture_test.py \
        forensic_multisignal_audit.py \
        2>/dev/null || true
) > "$EVIDENCE/SOURCE_HASHES.sha256"

cat > "$ROOT/l8_fast_adversarial.py" <<'PY'
#!/usr/bin/env python3

"""
BIRTH_EDGE — L8 FAST ADVERSARIAL DIAGNOSTIC

Purpose
-------
A fast forensic stress test of the existing MULTI_SIGNAL architecture.

IMPORTANT:
    - aegis_rule_miner.py is NOT modified.
    - definitive_architecture_test.py is NOT modified.
    - No synthetic replacement world is introduced.
    - The existing make_world(), labels(), safe_discover(), predict()
      and MULTI_SIGNAL generator are used directly.
    - Discovery is performed ONCE per seed.
    - Adversarial attacks are then applied to the held-out data and
      evaluated against the SAME discovered rule.

Tests
-----
1. BASELINE DISCOVERY REPLICATION
2. RULE IDENTITY STABILITY
3. FEATURE ABLATION
4. FEATURE PERMUTATION
5. LABEL NULL CONTROL
6. THRESHOLD PERTURBATION
7. RANGE SHIFT
8. SIGNAL-DESTRUCTION CONTRAST
9. CROSS-SEED GENERALIZATION
10. FORENSIC VERDICT

This version is deliberately instrumented so a slow discovery cannot
look like a frozen process.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import random
import statistics
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

WORLD = "MULTI_SIGNAL"

# Fast diagnostic run.
SEEDS = list(range(5))

TRAIN_N = 400
TEST_N = 1000

FEATURES = [
    "dev_score",
    "holder_score",
    "liquidity_usd",
    "lp_lock_score",
]


# ---------------------------------------------------------------------
# MODULE LOADING
# ---------------------------------------------------------------------

def load_module():
    spec = importlib.util.spec_from_file_location(
        "definitive_architecture_test",
        TEST_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to load {TEST_FILE}"
        )

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


# ---------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------

def metric(pred, truth):
    if len(pred) != len(truth):
        raise ValueError(
            "prediction/label length mismatch"
        )

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


# ---------------------------------------------------------------------
# ROW OPERATIONS
# ---------------------------------------------------------------------

def numeric_value(row, key):
    if isinstance(row, dict):
        return row.get(key)

    try:
        return getattr(row, key)
    except Exception:
        return None


def set_value(row, key, value):
    if isinstance(row, dict):
        row[key] = value
    else:
        setattr(row, key, value)


def clone_rows(rows):
    return copy.deepcopy(rows)


# ---------------------------------------------------------------------
# RULE DESCRIPTION
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# DISCOVERY
# ---------------------------------------------------------------------

def discover(module, rows):
    safe_discover = require(module, "safe_discover")

    started = time.time()

    result = safe_discover(rows)

    elapsed = time.time() - started

    if not isinstance(result, dict):
        raise RuntimeError(
            "safe_discover() did not return dict"
        )

    expr = result.get("expr")

    success = bool(
        result.get("success")
        and expr is not None
    )

    return {
        "success": success,
        "expr": expr,
        "rule": (
            rule_string(expr, module)
            if success
            else None
        ),
        "features": (
            get_features(expr, module)
            if success
            else []
        ),
        "score": result.get("score"),
        "error": result.get("error"),
        "elapsed_seconds": elapsed,
    }


# ---------------------------------------------------------------------
# DATASET
# ---------------------------------------------------------------------

def make_dataset(module, seed, n):
    make_world = require(module, "make_world")
    labels = require(module, "labels")

    rows = make_world(
        WORLD,
        seed,
        n=n,
    )

    truth = [
        bool(x)
        for x in labels(rows)
    ]

    return rows, truth


# ---------------------------------------------------------------------
# PREDICTION
# ---------------------------------------------------------------------

def evaluate(module, expr, rows, truth):
    predict = require(module, "predict")

    pred = predict(
        expr,
        rows,
    )

    pred = [
        bool(x)
        for x in pred
    ]

    return {
        "pred": pred,
        "metrics": metric(
            pred,
            truth,
        ),
    }


# ---------------------------------------------------------------------
# ADVERSARIAL TRANSFORMS
# ---------------------------------------------------------------------

def feature_ablation(rows, feature):
    """
    Destroy one feature while preserving all other observations.
    """

    out = clone_rows(rows)

    values = [
        numeric_value(row, feature)
        for row in out
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
        set_value(
            row,
            feature,
            replacement,
        )

    return out


def feature_permutation(rows, feature, seed):
    """
    Destroy row-wise correspondence for one feature.
    """

    out = clone_rows(rows)

    values = [
        numeric_value(row, feature)
        for row in out
    ]

    random.Random(seed).shuffle(values)

    for row, value in zip(out, values):
        set_value(
            row,
            feature,
            value,
        )

    return out


def label_permutation(labels, seed):
    """
    Proper label-null control.

    The labels are genuinely shuffled rather than merely generated
    and then ignored.
    """

    out = list(labels)

    random.Random(seed).shuffle(out)

    return out


def threshold_perturb_rows(rows, seed):
    """
    Small numerical perturbation.

    Does not replace the world or labels.
    """

    out = clone_rows(rows)
    rng = random.Random(seed)

    for row in out:

        for feature in FEATURES:

            value = numeric_value(
                row,
                feature,
            )

            if isinstance(value, (int, float)):

                value = float(value)

                scale = max(
                    abs(value),
                    1.0,
                )

                factor = rng.uniform(
                    0.97,
                    1.03,
                )

                noise = rng.uniform(
                    -0.01,
                    0.01,
                ) * scale

                set_value(
                    row,
                    feature,
                    value * factor + noise,
                )

    return out


def range_shift(rows, seed):
    """
    Moderate covariate shift.

    Labels remain untouched.
    """

    out = clone_rows(rows)
    rng = random.Random(seed)

    for row in out:

        for feature in FEATURES:

            value = numeric_value(
                row,
                feature,
            )

            if isinstance(value, (int, float)):

                value = float(value)

                scale = max(
                    abs(value),
                    1.0,
                )

                factor = rng.uniform(
                    0.90,
                    1.10,
                )

                offset = rng.uniform(
                    -0.02,
                    0.02,
                ) * scale

                set_value(
                    row,
                    feature,
                    value * factor + offset,
                )

    return out


# ---------------------------------------------------------------------
# RULE FINGERPRINT
# ---------------------------------------------------------------------

def fingerprint(rule):
    if rule is None:
        return None

    raw = str(rule).encode(
        "utf-8",
        errors="replace",
    )

    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------
# SINGLE-SEED FORENSIC RUN
# ---------------------------------------------------------------------

def run_seed(module, seed):
    started = time.time()

    print(
        f"\n[SEED {seed:02d}] generating data...",
        flush=True,
    )

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

    print(
        f"[SEED {seed:02d}] discovering...",
        flush=True,
    )

    discovery = discover(
        module,
        train,
    )

    if not discovery["success"]:

        print(
            f"[SEED {seed:02d}] DISCOVERY FAILED "
            f"after {discovery['elapsed_seconds']:.3f}s",
            flush=True,
        )

        return {
            "seed": seed,
            "success": False,
            "error": discovery["error"],
            "discovery_seconds":
                discovery["elapsed_seconds"],
        }

    print(
        f"[SEED {seed:02d}] discovered in "
        f"{discovery['elapsed_seconds']:.3f}s",
        flush=True,
    )

    print(
        f"[SEED {seed:02d}] rule: "
        f"{discovery['rule']}",
        flush=True,
    )

    print(
        f"[SEED {seed:02d}] features: "
        f"{discovery['features']}",
        flush=True,
    )

    # --------------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------------

    base = evaluate(
        module,
        discovery["expr"],
        test,
        y_test,
    )

    print(
        f"[SEED {seed:02d}] baseline accuracy="
        f"{base['metrics']['accuracy']:.6f} "
        f"balanced="
        f"{base['metrics']['balanced_accuracy']:.6f}",
        flush=True,
    )

    # --------------------------------------------------------------
    # FEATURE ABLATION
    # --------------------------------------------------------------

    ablation = {}

    for feature in FEATURES:

        attacked = feature_ablation(
            test,
            feature,
        )

        ev = evaluate(
            module,
            discovery["expr"],
            attacked,
            y_test,
        )

        ablation[feature] = ev["metrics"]

    # --------------------------------------------------------------
    # FEATURE PERMUTATION
    # --------------------------------------------------------------

    permutation = {}

    for feature in FEATURES:

        attacked = feature_permutation(
            test,
            feature,
            seed + 7000,
        )

        ev = evaluate(
            module,
            discovery["expr"],
            attacked,
            y_test,
        )

        permutation[feature] = ev["metrics"]

    # --------------------------------------------------------------
    # LABEL NULL CONTROL
    # --------------------------------------------------------------

    null_labels = label_permutation(
        y_test,
        seed + 30000,
    )

    null_eval = evaluate(
        module,
        discovery["expr"],
        test,
        null_labels,
    )

    # --------------------------------------------------------------
    # THRESHOLD PERTURBATION
    # --------------------------------------------------------------

    threshold_test = threshold_perturb_rows(
        test,
        seed + 50000,
    )

    threshold_eval = evaluate(
        module,
        discovery["expr"],
        threshold_test,
        y_test,
    )

    # --------------------------------------------------------------
    # RANGE SHIFT
    # --------------------------------------------------------------

    shifted_test = range_shift(
        test,
        seed + 60000,
    )

    shift_eval = evaluate(
        module,
        discovery["expr"],
        shifted_test,
        y_test,
    )

    # --------------------------------------------------------------
    # SIGNAL DESTRUCTION CONTRAST
    # --------------------------------------------------------------

    signal_contrast = {}

    for feature in FEATURES:

        perm = permutation[feature]["balanced_accuracy"]

        signal_contrast[feature] = {
            "baseline_balanced_accuracy":
                base["metrics"]["balanced_accuracy"],

            "permuted_balanced_accuracy":
                perm,

            "drop":
                base["metrics"]["balanced_accuracy"] - perm,
        }

    elapsed = time.time() - started

    print(
        f"[SEED {seed:02d}] COMPLETE "
        f"total={elapsed:.3f}s",
        flush=True,
    )

    return {
        "seed": seed,
        "success": True,

        "discovery": {
            "rule": discovery["rule"],
            "fingerprint":
                fingerprint(discovery["rule"]),
            "features":
                discovery["features"],
            "score":
                discovery["score"],
            "seconds":
                discovery["elapsed_seconds"],
        },

        "baseline": base["metrics"],

        "ablation": ablation,

        "permutation": permutation,

        "label_null": null_eval["metrics"],

        "threshold_perturbation":
            threshold_eval["metrics"],

        "range_shift":
            shift_eval["metrics"],

        "signal_contrast":
            signal_contrast,

        "elapsed_seconds": elapsed,
    }


# ---------------------------------------------------------------------
# FORENSIC AGGREGATION
# ---------------------------------------------------------------------

def mean(values):
    values = [
        float(x)
        for x in values
        if x is not None
    ]

    return (
        statistics.mean(values)
        if values
        else None
    )


def summarize(values):
    values = [
        float(x)
        for x in values
        if x is not None
    ]

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


def aggregate(results):

    valid = [
        r
        for r in results
        if r.get("success")
    ]

    baseline_acc = [
        r["baseline"]["accuracy"]
        for r in valid
    ]

    baseline_bal = [
        r["baseline"]["balanced_accuracy"]
        for r in valid
    ]

    null_bal = [
        r["label_null"]["balanced_accuracy"]
        for r in valid
    ]

    threshold_acc = [
        r["threshold_perturbation"]["accuracy"]
        for r in valid
    ]

    shift_acc = [
        r["range_shift"]["accuracy"]
        for r in valid
    ]

    discovery_seconds = [
        r["discovery"]["seconds"]
        for r in valid
    ]

    total_seconds = [
        r["elapsed_seconds"]
        for r in valid
    ]

    fingerprints = [
        r["discovery"]["fingerprint"]
        for r in valid
    ]

    # --------------------------------------------------------------
    # FEATURE STABILITY
    # --------------------------------------------------------------

    frequency = {
        feature: 0
        for feature in FEATURES
    }

    for r in valid:

        for feature in r["discovery"]["features"]:

            if feature in frequency:
                frequency[feature] += 1

    stability = {
        feature:
            frequency[feature] / len(valid)
            if valid
            else 0.0
        for feature in FEATURES
    }

    # --------------------------------------------------------------
    # FEATURE SIGNAL DROPS
    # --------------------------------------------------------------

    permutation_drop = {}

    for feature in FEATURES:

        drops = []

        for r in valid:

            drops.append(
                r["signal_contrast"][feature]["drop"]
            )

        permutation_drop[feature] = summarize(
            drops
        )

    # --------------------------------------------------------------
    # CHECKS
    # --------------------------------------------------------------

    baseline_replication = (
        len(valid) == len(SEEDS)
    )

    identity_stability = (
        len(set(fingerprints)) <=
        max(1, len(fingerprints) // 2)
        if fingerprints
        else False
    )

    # Null control should be materially worse than
    # the actual baseline.
    baseline_mean = mean(
        baseline_bal
    )

    null_mean = mean(
        null_bal
    )

    null_separation = (
        null_mean < baseline_mean
        if baseline_mean is not None
        and null_mean is not None
        else False
    )

    threshold_mean = mean(
        threshold_acc
    )

    shift_mean = mean(
        shift_acc
    )

    threshold_robust = (
        threshold_mean >=
        mean(baseline_acc) - 0.10
        if threshold_mean is not None
        and baseline_acc
        else False
    )

    shift_robust = (
        shift_mean >=
        mean(baseline_acc) - 0.20
        if shift_mean is not None
        and baseline_acc
        else False
    )

    strong_features = sum(
        x >= 0.50
        for x in stability.values()
    )

    feature_stability = (
        strong_features >= 3
    )

    # At least one feature should show
    # meaningful destruction under permutation.
    causal_signal_present = any(
        (
            d["mean"] is not None
            and d["mean"] >= 0.05
        )
        for d in permutation_drop.values()
    )

    checks = {
        "baseline_replication":
            baseline_replication,

        "rule_identity_stability":
            identity_stability,

        "feature_stability":
            feature_stability,

        "null_control_separation":
            null_separation,

        "threshold_robustness":
            threshold_robust,

        "range_shift_robustness":
            shift_robust,

        "signal_destruction_detected":
            causal_signal_present,
    }

    # This is deliberately NOT a simplistic
    # "everything must pass" gate.
    #
    # A discovery can be highly stable while a
    # robustness dimension fails. The report preserves
    # those distinctions.

    verdict = (
        "L8-PASS"
        if all(checks.values())
        else "L8-INVESTIGATE"
    )

    return {
        "successful_seeds":
            len(valid),

        "requested_seeds":
            len(SEEDS),

        "baseline_accuracy":
            summarize(baseline_acc),

        "baseline_balanced_accuracy":
            summarize(baseline_bal),

        "label_null_balanced_accuracy":
            summarize(null_bal),

        "threshold_accuracy":
            summarize(threshold_acc),

        "range_shift_accuracy":
            summarize(shift_acc),

        "discovery_seconds":
            summarize(discovery_seconds),

        "total_seconds":
            summarize(total_seconds),

        "rule_fingerprints":
            fingerprints,

        "feature_frequency":
            frequency,

        "feature_stability":
            stability,

        "permutation_signal_drop":
            permutation_drop,

        "checks":
            checks,

        "verdict":
            verdict,
    }


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

def main():

    started = time.time()

    print("=" * 70)
    print("BIRTH_EDGE — L8 FAST ADVERSARIAL DIAGNOSTIC")
    print("=" * 70)
    print(f"World       : {WORLD}")
    print(f"Seeds       : {len(SEEDS)}")
    print(f"Train       : {TRAIN_N}")
    print(f"Test        : {TEST_N}")
    print("Discovery   : ONCE PER SEED")
    print("Miner       : UNMODIFIED")
    print("Definitive  : UNMODIFIED")
    print()

    module = load_module()

    results = []

    for seed in SEEDS:

        result = run_seed(
            module,
            seed,
        )

        results.append(result)

    print()
    print("=" * 70)
    print("L8 FORENSIC AGGREGATION")
    print("=" * 70)

    summary = aggregate(
        results
    )

    print(
        f"Successful seeds : "
        f"{summary['successful_seeds']}/"
        f"{summary['requested_seeds']}"
    )

    print(
        f"Discovery time   : "
        f"{summary['discovery_seconds']['mean']:.4f}s mean"
        if summary["discovery_seconds"]["mean"] is not None
        else "Discovery time   : N/A"
    )

    print(
        f"Baseline acc     : "
        f"{summary['baseline_accuracy']['mean']:.6f}"
        if summary["baseline_accuracy"]["mean"] is not None
        else "Baseline acc     : N/A"
    )

    print(
        f"Baseline balanced: "
        f"{summary['baseline_balanced_accuracy']['mean']:.6f}"
        if summary["baseline_balanced_accuracy"]["mean"] is not None
        else "Baseline balanced: N/A"
    )

    print()
    print("FEATURE STABILITY")

    for feature in FEATURES:

        print(
            f"  {feature:16s} "
            f"{summary['feature_stability'][feature]:.3f}"
        )

    print()
    print("PERMUTATION SIGNAL DROP")

    for feature in FEATURES:

        value = (
            summary["permutation_signal_drop"]
            [feature]["mean"]
        )

        print(
            f"  {feature:16s} "
            f"{value:+.6f}"
            if value is not None
            else
            f"  {feature:16s} N/A"
        )

    print()
    print("ADVERSARIAL RESULTS")

    print(
        f"  Label null balanced : "
        f"{summary['label_null_balanced_accuracy']['mean']:.6f}"
        if summary["label_null_balanced_accuracy"]["mean"] is not None
        else "  Label null balanced : N/A"
    )

    print(
        f"  Threshold accuracy  : "
        f"{summary['threshold_accuracy']['mean']:.6f}"
        if summary["threshold_accuracy"]["mean"] is not None
        else "  Threshold accuracy  : N/A"
    )

    print(
        f"  Range-shift accuracy: "
        f"{summary['range_shift_accuracy']['mean']:.6f}"
        if summary["range_shift_accuracy"]["mean"] is not None
        else "  Range-shift accuracy: N/A"
    )

    print()
    print("CHECKS")

    for name, passed in summary["checks"].items():

        print(
            f"  {name:30s}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print("=" * 70)
    print("L8 VERDICT")
    print("=" * 70)
    print(summary["verdict"])

    report = {
        "audit":
            "BIRTH_EDGE_L8_FAST_ADVERSARIAL_DIAGNOSTIC",

        "version":
            "L8-FAST",

        "timestamp":
            time.strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            ),

        "world":
            WORLD,

        "train_n":
            TRAIN_N,

        "test_n":
            TEST_N,

        "seeds":
            SEEDS,

        "features":
            FEATURES,

        "source_test":
            str(TEST_FILE),

        "miner_modified":
            False,

        "definitive_test_modified":
            False,

        "results":
            results,

        "summary":
            summary,

        "elapsed_seconds":
            time.time() - started,

        "method_note":
            (
                "Discovery occurs once per seed. "
                "Adversarial transforms operate on "
                "held-out observations using the same "
                "discovered rule. Label null genuinely "
                "shuffles labels for evaluation."
            ),
    }

    output = (
        ROOT /
        "logs" /
        "evidence" /
        "level8"
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    stamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        output /
        f"L8_FAST_{stamp}.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    print()
    print(
        f"REPORT: {report_path}"
    )

    return 0 if summary["verdict"] == "L8-PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/l8_fast_adversarial.py"

echo
echo "======================================================================"
echo "L8 FAST INSTALLED"
echo "======================================================================"
echo "Miner modified : NO"
echo "Definitive test: NO"
echo "Discovery/seed : 1"
echo "Seeds          : 5"
echo "Evidence       : $EVIDENCE"
echo
echo "RUNNING..."
echo

cd "$ROOT"

python -u l8_fast_adversarial.py \
    | tee "$EVIDENCE/L8_FAST_CONSOLE.log"

STATUS=${PIPESTATUS[0]}

echo
echo "======================================================================"
echo "L8 FAST EXIT STATUS: $STATUS"
echo "======================================================================"

exit "$STATUS"
