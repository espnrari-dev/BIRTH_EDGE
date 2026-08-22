#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backups/forensic_multisignal_v3_$STAMP"

mkdir -p "$BACKUP"

echo "============================================================"
echo "BIRTH_EDGE — MULTI_SIGNAL FORENSIC AUDIT V3"
echo "============================================================"
echo "Backup: $BACKUP"
echo

for f in \
    aegis_rule_miner.py \
    definitive_architecture_test.py \
    forensic_multisignal_audit.py
do
    if [ -f "$ROOT/$f" ]; then
        cp -p "$ROOT/$f" "$BACKUP/"
        echo "BACKUP  $f"
    fi
done

(
    cd "$ROOT"
    sha256sum aegis_rule_miner.py definitive_architecture_test.py \
        2>/dev/null || true
) > "$BACKUP/SOURCE_HASHES.sha256"

echo
echo "Backup complete."
echo

cat > "$ROOT/forensic_multisignal_audit.py" <<'PY'
#!/usr/bin/env python3

"""
BIRTH_EDGE — MULTI_SIGNAL FORENSIC METRIC AUDIT V3

Purpose
-------
Independently audit the MULTI_SIGNAL experiment from
definitive_architecture_test.py.

This version deliberately reuses ONLY the definitive test's
real-world generator, label construction, and prediction semantics.

It independently recomputes:

    accuracy
    balanced accuracy
    precision
    TP / TN / FP / FN
    positive prevalence
    negative prevalence

It does NOT modify:

    aegis_rule_miner.py
    definitive_architecture_test.py

Critical forensic guarantees
----------------------------
1. Explicitly selects MULTI_SIGNAL.
2. Uses the definitive test's make_world().
3. Uses the definitive test's labels().
4. Uses the definitive test's predict().
5. Independently recomputes all metrics.
6. Discovers a fresh rule from TRAIN ONLY.
7. Applies that rule unchanged to HELD-OUT data.
8. Compares independent metrics against the definitive test's
   own metric implementation.
"""

from __future__ import annotations

import importlib.util
import json
import math
import statistics
from pathlib import Path

import aegis_rule_miner as arm


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

SEEDS = list(range(20))

WORLD = "MULTI_SIGNAL"

TRAIN_N = 400
TEST_N = 1000


# ============================================================
# MODULE LOADING
# ============================================================

def load_test_module():
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


# ============================================================
# REQUIRED DEFINITIVE-TEST INTERFACES
# ============================================================

def require_callable(module, name):
    fn = getattr(module, name, None)

    if not callable(fn):
        raise RuntimeError(
            f"Required callable '{name}' was not found in "
            f"{TEST_FILE}"
        )

    return fn


# ============================================================
# INDEPENDENT METRICS
# ============================================================

def independent_metrics(pred, truth):
    if len(pred) != len(truth):
        raise ValueError(
            f"Length mismatch: predictions={len(pred)} "
            f"truth={len(truth)}"
        )

    tp = tn = fp = fn = 0

    for p, y in zip(pred, truth):
        p = bool(p)
        y = bool(y)

        if y and p:
            tp += 1
        elif (not y) and (not p):
            tn += 1
        elif (not y) and p:
            fp += 1
        elif y and (not p):
            fn += 1

    total = tp + tn + fp + fn

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
    )

    tpr = (
        tp / (tp + fn)
        if (tp + fn)
        else 0.0
    )

    tnr = (
        tn / (tn + fp)
        if (tn + fp)
        else 0.0
    )

    balanced_accuracy = (tpr + tnr) / 2.0

    precision = (
        tp / (tp + fp)
        if (tp + fp)
        else 0.0
    )

    positive = tp + fn
    negative = tn + fp

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "precision": precision,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "positive_count": positive,
        "negative_count": negative,
        "positive_rate": (
            positive / total
            if total
            else 0.0
        ),
        "negative_rate": (
            negative / total
            if total
            else 0.0
        ),
    }


# ============================================================
# METRIC CONSISTENCY CHECK
# ============================================================

def compare_metrics(definitive, independent):
    """
    Compare metric values from the definitive implementation
    against the independently recomputed values.
    """

    fields = (
        "accuracy",
        "balanced_accuracy",
        "precision",
        "tp",
        "tn",
        "fp",
        "fn",
    )

    mismatches = []

    for field in fields:
        a = definitive.get(field)
        b = independent.get(field)

        if isinstance(a, float) or isinstance(b, float):
            if not math.isclose(
                float(a),
                float(b),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                mismatches.append(
                    {
                        "field": field,
                        "definitive": a,
                        "independent": b,
                    }
                )
        else:
            if a != b:
                mismatches.append(
                    {
                        "field": field,
                        "definitive": a,
                        "independent": b,
                    }
                )

    return mismatches


# ============================================================
# RULE DISCOVERY
# ============================================================

def discover_rule(rows, module):
    """
    Reuse the definitive test's exact discovery pathway.
    """

    safe_discover = require_callable(
        module,
        "safe_discover",
    )

    result = safe_discover(rows)

    if not isinstance(result, dict):
        raise RuntimeError(
            "safe_discover() did not return the expected dict."
        )

    return result


# ============================================================
# RULE DESCRIPTION
# ============================================================

def describe_rule(expr, module):
    fn = getattr(module, "rule_string", None)

    if callable(fn):
        try:
            return fn(expr)
        except Exception:
            pass

    if expr is None:
        return None

    return str(expr)


# ============================================================
# RULE FEATURES
# ============================================================

def extract_rule_features(expr, module):
    fn = getattr(module, "rule_features", None)

    if callable(fn):
        try:
            return fn(expr)
        except Exception:
            return []

    try:
        return arm.rule_features(expr)
    except Exception:
        return []


# ============================================================
# MAIN FORENSIC RUN
# ============================================================

def main():
    print("=" * 80)
    print("MULTI_SIGNAL FORENSIC METRIC AUDIT V3")
    print("=" * 80)
    print("Miner :", arm.__file__)
    print("Test  :", TEST_FILE)
    print("World :", WORLD)
    print("Seeds :", len(SEEDS))
    print()

    module = load_test_module()

    make_world = require_callable(
        module,
        "make_world",
    )

    labels = require_callable(
        module,
        "labels",
    )

    predict = require_callable(
        module,
        "predict",
    )

    definitive_metrics = require_callable(
        module,
        "metrics",
    )

    print("REAL TEST INTERFACES FOUND:")
    print("  make_world()")
    print("  labels()")
    print("  predict()")
    print("  metrics()")
    print("  safe_discover()")
    print()

    results = []

    # ========================================================
    # SEED LOOP
    # ========================================================

    for seed in SEEDS:

        print("-" * 80)
        print(f"SEED {seed:02d}")
        print("-" * 80)

        # ----------------------------------------------------
        # REAL DEFINITIVE DATA GENERATION
        # ----------------------------------------------------

        train = make_world(
            WORLD,
            seed,
            n=TRAIN_N,
        )

        test = make_world(
            WORLD,
            seed + 100000,
            n=TEST_N,
        )

        print(
            f"TRAIN rows     : {len(train)}"
        )

        print(
            f"HELD-OUT rows  : {len(test)}"
        )

        # ----------------------------------------------------
        # REAL LABEL CONSTRUCTION
        # ----------------------------------------------------

        y_train = labels(train)
        y_test = labels(test)

        print(
            f"TRAIN positives : {sum(bool(x) for x in y_train)}"
        )

        print(
            f"TRAIN negatives : "
            f"{len(y_train) - sum(bool(x) for x in y_train)}"
        )

        print(
            f"TEST positives  : {sum(bool(x) for x in y_test)}"
        )

        print(
            f"TEST negatives  : "
            f"{len(y_test) - sum(bool(x) for x in y_test)}"
        )

        # ----------------------------------------------------
        # DISCOVER FROM TRAIN ONLY
        # ----------------------------------------------------

        discovery = discover_rule(
            train,
            module,
        )

        expr = discovery.get("expr")

        discovered = bool(
            discovery.get("success")
            and expr is not None
        )

        rule = describe_rule(
            expr,
            module,
        )

        print(
            f"DISCOVERED      : {discovered}"
        )

        print(
            f"DISCOVERY SCORE : {discovery.get('score')}"
        )

        print(
            f"RULE            : {rule}"
        )

        if not discovered:
            print(
                "STATUS          : DISCOVERY FAILED"
            )

            results.append(
                {
                    "seed": seed,
                    "discovered": False,
                    "rule": None,
                    "error": discovery.get("error"),
                }
            )

            continue

        features = extract_rule_features(
            expr,
            module,
        )

        print(
            f"RULE FEATURES   : {features}"
        )

        # ----------------------------------------------------
        # PREDICTIONS USING DEFINITIVE PATH
        # ----------------------------------------------------

        train_pred = predict(
            expr,
            train,
        )

        test_pred = predict(
            expr,
            test,
        )

        # ----------------------------------------------------
        # DEFINITIVE METRICS
        # ----------------------------------------------------

        definitive_train = definitive_metrics(
            train_pred,
            y_train,
        )

        definitive_test = definitive_metrics(
            test_pred,
            y_test,
        )

        # ----------------------------------------------------
        # INDEPENDENT METRICS
        # ----------------------------------------------------

        independent_train = independent_metrics(
            train_pred,
            y_train,
        )

        independent_test = independent_metrics(
            test_pred,
            y_test,
        )

        # ----------------------------------------------------
        # CONSISTENCY AUDIT
        # ----------------------------------------------------

        train_mismatches = compare_metrics(
            definitive_train,
            independent_train,
        )

        test_mismatches = compare_metrics(
            definitive_test,
            independent_test,
        )

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        print()
        print("TRAIN METRICS")
        print(
            f"  accuracy          : "
            f"{independent_train['accuracy']:.6f}"
        )

        print(
            f"  balanced_accuracy : "
            f"{independent_train['balanced_accuracy']:.6f}"
        )

        print(
            f"  precision         : "
            f"{independent_train['precision']:.6f}"
        )

        print(
            f"  TP={independent_train['tp']} "
            f"TN={independent_train['tn']} "
            f"FP={independent_train['fp']} "
            f"FN={independent_train['fn']}"
        )

        print(
            f"  positive_rate     : "
            f"{independent_train['positive_rate']:.6f}"
        )

        print(
            f"  negative_rate     : "
            f"{independent_train['negative_rate']:.6f}"
        )

        print()
        print("HELD-OUT METRICS")

        print(
            f"  accuracy          : "
            f"{independent_test['accuracy']:.6f}"
        )

        print(
            f"  balanced_accuracy : "
            f"{independent_test['balanced_accuracy']:.6f}"
        )

        print(
            f"  precision         : "
            f"{independent_test['precision']:.6f}"
        )

        print(
            f"  TP={independent_test['tp']} "
            f"TN={independent_test['tn']} "
            f"FP={independent_test['fp']} "
            f"FN={independent_test['fn']}"
        )

        print(
            f"  positive_rate     : "
            f"{independent_test['positive_rate']:.6f}"
        )

        print(
            f"  negative_rate     : "
            f"{independent_test['negative_rate']:.6f}"
        )

        print()
        print(
            "METRIC RECOMPUTATION:"
        )

        print(
            "  TRAIN : "
            + (
                "MATCH"
                if not train_mismatches
                else f"MISMATCH ({train_mismatches})"
            )
        )

        print(
            "  TEST  : "
            + (
                "MATCH"
                if not test_mismatches
                else f"MISMATCH ({test_mismatches})"
            )
        )

        results.append(
            {
                "seed": seed,
                "discovered": True,
                "rule": rule,
                "features": features,
                "discovery_score": discovery.get("score"),
                "train": independent_train,
                "held_out": independent_test,
                "definitive_train": definitive_train,
                "definitive_held_out": definitive_test,
                "train_metric_mismatches": train_mismatches,
                "held_out_metric_mismatches": test_mismatches,
            }
        )

    # ========================================================
    # AGGREGATE
    # ========================================================

    print()
    print("=" * 80)
    print("FORENSIC MULTI_SIGNAL SUMMARY")
    print("=" * 80)

    valid = [
        r for r in results
        if r.get("discovered")
        and r.get("held_out") is not None
    ]

    if not valid:
        print("NO VALID DISCOVERY RUNS.")
        return 2

    discovery_rate = (
        sum(bool(r["discovered"]) for r in results)
        / len(results)
    )

    train_acc = [
        r["train"]["accuracy"]
        for r in valid
    ]

    test_acc = [
        r["held_out"]["accuracy"]
        for r in valid
    ]

    test_balanced = [
        r["held_out"]["balanced_accuracy"]
        for r in valid
    ]

    test_positive = [
        r["held_out"]["positive_rate"]
        for r in valid
    ]

    test_negative = [
        r["held_out"]["negative_rate"]
        for r in valid
    ]

    metric_clean = all(
        not r["train_metric_mismatches"]
        and not r["held_out_metric_mismatches"]
        for r in valid
    )

    print(
        f"World                     : {WORLD}"
    )

    print(
        f"Runs                      : {len(results)}"
    )

    print(
        f"Valid discovered runs     : {len(valid)}"
    )

    print(
        f"Discovery rate            : "
        f"{discovery_rate:.6f}"
    )

    print(
        f"Mean train accuracy       : "
        f"{statistics.mean(train_acc):.6f}"
    )

    print(
        f"Mean held-out accuracy    : "
        f"{statistics.mean(test_acc):.6f}"
    )

    print(
        f"Min held-out accuracy     : "
        f"{min(test_acc):.6f}"
    )

    print(
        f"Mean held-out balanced acc: "
        f"{statistics.mean(test_balanced):.6f}"
    )

    print(
        f"Mean held-out positive %   : "
        f"{statistics.mean(test_positive):.6f}"
    )

    print(
        f"Mean held-out negative %   : "
        f"{statistics.mean(test_negative):.6f}"
    )

    print(
        f"Independent metric audit  : "
        f"{'PASS' if metric_clean else 'FAIL'}"
    )

    # --------------------------------------------------------
    # RULE FREQUENCY
    # --------------------------------------------------------

    rule_counts = {}

    for r in valid:
        rule = r["rule"]
        rule_counts[rule] = rule_counts.get(rule, 0) + 1

    print()
    print("RULE STABILITY")
    print("-" * 80)

    for rule, count in sorted(
        rule_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(
            f"{count:02d} / {len(valid):02d} | {rule}"
        )

    # --------------------------------------------------------
    # CONFUSION MATRIX TOTALS
    # --------------------------------------------------------

    totals = {
        "tp": sum(r["held_out"]["tp"] for r in valid),
        "tn": sum(r["held_out"]["tn"] for r in valid),
        "fp": sum(r["held_out"]["fp"] for r in valid),
        "fn": sum(r["held_out"]["fn"] for r in valid),
    }

    print()
    print("HELD-OUT CONFUSION TOTALS")
    print("-" * 80)

    print(
        f"TP={totals['tp']} "
        f"TN={totals['tn']} "
        f"FP={totals['fp']} "
        f"FN={totals['fn']}"
    )

    # --------------------------------------------------------
    # FINAL FORENSIC VERDICT
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("FORENSIC VERDICT")
    print("=" * 80)

    if metric_clean:
        print(
            "PASS — independently recomputed metrics exactly "
            "match the definitive test's metric implementation."
        )
    else:
        print(
            "FAIL — independent metric recomputation disagrees "
            "with the definitive test."
        )

    print(
        "The audit used the actual MULTI_SIGNAL generator and "
        "the actual pumped-label construction."
    )

    print(
        "No synthetic replacement labels or synthetic datasets "
        "were introduced."
    )

    # --------------------------------------------------------
    # SAVE MACHINE-READABLE REPORT
    # --------------------------------------------------------

    report = {
        "audit": "MULTI_SIGNAL_FORENSIC_METRIC_AUDIT_V3",
        "world": WORLD,
        "train_n": TRAIN_N,
        "test_n": TEST_N,
        "seeds": SEEDS,
        "discovery_rate": discovery_rate,
        "valid_runs": len(valid),
        "mean_train_accuracy": statistics.mean(train_acc),
        "mean_held_out_accuracy": statistics.mean(test_acc),
        "min_held_out_accuracy": min(test_acc),
        "mean_held_out_balanced_accuracy":
            statistics.mean(test_balanced),
        "mean_held_out_positive_rate":
            statistics.mean(test_positive),
        "mean_held_out_negative_rate":
            statistics.mean(test_negative),
        "independent_metric_audit":
            "PASS" if metric_clean else "FAIL",
        "confusion_totals": totals,
        "rule_counts": rule_counts,
        "results": results,
    }

    out = ROOT / "forensic_multisignal_audit_v3.json"

    out.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    print()
    print("REPORT:", out)
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/forensic_multisignal_audit.py"

echo
echo "============================================================"
echo "V3 INSTALLED"
echo "============================================================"
echo "Miner modified: NO"
echo "Test modified : NO"
echo "Auditor only   : YES"
echo
echo "Running..."
echo

cd "$ROOT"

python -u forensic_multisignal_audit.py \
    | tee forensic_multisignal_audit_v3.log
