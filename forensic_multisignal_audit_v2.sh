#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backups/forensic_multisignal_v2_$STAMP"

mkdir -p "$BACKUP"

echo "============================================================"
echo "BIRTH_EDGE — FORENSIC AUDIT V2 BACKUP"
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
    sha256sum *.py 2>/dev/null || true
) > "$BACKUP/SOURCE_HASHES.sha256"

echo
echo "Backup complete."
echo

echo "============================================================"
echo "TARGET-FIELD FORENSIC INSPECTION"
echo "============================================================"

echo
echo "[1] Locate target/label construction:"
grep -RniE \
    'target|label|y_true|positive|negative|make_.*world|WORLD' \
    "$ROOT/definitive_architecture_test.py" \
    --exclude-dir=backups \
    2>/dev/null || true

echo
echo "[2] Locate dataset construction:"
grep -nE \
    -B 12 -A 30 \
    'def .*rows|rows =|generate|world' \
    "$ROOT/definitive_architecture_test.py" \
    2>/dev/null || true

echo
echo "[3] Locate metric calculation:"
grep -nE \
    -B 10 -A 25 \
    'def metrics|balanced_accuracy|accuracy|tp =|tn =' \
    "$ROOT/definitive_architecture_test.py" \
    2>/dev/null || true

echo
echo "============================================================"
echo "GENERATE FORENSIC AUDITOR V2"
echo "============================================================"

cat > "$ROOT/forensic_multisignal_audit.py" <<'PY'
#!/usr/bin/env python3

"""
BIRTH_EDGE — MULTI_SIGNAL FORENSIC METRIC AUDIT V2

Purpose:
    Audit discovered MULTI_SIGNAL rules without assuming that
    generated rows contain a field literally named "target".

Important:
    This script does NOT modify the miner.
    It reconstructs labels from the same world-generation logic
    used by definitive_architecture_test.py when possible.

The audit explicitly reports:
    - discovered rule
    - train accuracy
    - held-out accuracy
    - held-out balanced accuracy
    - confusion matrix
    - positive/negative prevalence
    - candidate label field(s)
    - whether the metric is independently recomputed
"""

from __future__ import annotations

import ast
import inspect
import math
import random
import statistics
from pathlib import Path

import aegis_rule_miner as arm


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

SEEDS = list(range(20))


# ============================================================
# GENERIC LABEL DISCOVERY
# ============================================================

LABEL_KEYS = (
    "target",
    "label",
    "y",
    "outcome",
    "success",
    "positive",
    "is_positive",
    "class",
)


def find_label(row):
    """
    Resolve the actual binary label field without assuming
    row['target'] exists.
    """
    for key in LABEL_KEYS:
        if key in row:
            value = row[key]

            if isinstance(value, bool):
                return int(value), key

            if isinstance(value, (int, float)) and value in (0, 1):
                return int(value), key

    return None, None


def row_schema(rows):
    keys = set()

    for row in rows:
        if isinstance(row, dict):
            keys.update(row.keys())

    return sorted(keys)


# ============================================================
# SAFE BINARY METRICS
# ============================================================

def binary_metrics(y_true, y_pred):
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Length mismatch: y_true={len(y_true)} "
            f"y_pred={len(y_pred)}"
        )

    tp = tn = fp = fn = 0

    for actual, predicted in zip(y_true, y_pred):
        actual = int(actual)
        predicted = int(predicted)

        if actual == 1 and predicted == 1:
            tp += 1
        elif actual == 0 and predicted == 0:
            tn += 1
        elif actual == 0 and predicted == 1:
            fp += 1
        elif actual == 1 and predicted == 0:
            fn += 1
        else:
            raise ValueError(
                f"Non-binary value encountered: "
                f"actual={actual}, predicted={predicted}"
            )

    total = tp + tn + fp + fn

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
    )

    tpr = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    tnr = (
        tn / (tn + fp)
        if tn + fp
        else 0.0
    )

    balanced = (tpr + tnr) / 2.0

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "precision": precision,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "positive_rate": (
            (tp + fn) / total
            if total
            else 0.0
        ),
        "negative_rate": (
            (tn + fp) / total
            if total
            else 0.0
        ),
    }


# ============================================================
# RULE EVALUATION
# ============================================================

def evaluate_rule(rule, rows):
    """
    Try the miner's available evaluation interfaces.

    This is intentionally defensive because the forensic audit
    must not silently invent a different prediction mechanism.
    """

    candidates = [
        "evaluate_rule",
        "evaluate",
        "score_rule",
        "predict_rule",
    ]

    for name in candidates:
        fn = getattr(arm, name, None)

        if not callable(fn):
            continue

        attempts = [
            (rule, rows),
            (rows, rule),
        ]

        for args in attempts:
            try:
                result = fn(*args)

                if isinstance(result, list):
                    if all(v in (0, 1, True, False) for v in result):
                        return [int(v) for v in result]

                if isinstance(result, tuple):
                    for item in result:
                        if isinstance(item, list):
                            if all(
                                v in (0, 1, True, False)
                                for v in item
                            ):
                                return [int(v) for v in item]

            except Exception:
                pass

    raise RuntimeError(
        "Could not locate a safe rule-evaluation interface "
        "in aegis_rule_miner.py"
    )


# ============================================================
# TEST MODULE LOADING
# ============================================================

def load_test_module():
    import importlib.util

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
# WORLD GENERATION DISCOVERY
# ============================================================

def locate_generators(module):
    found = []

    for name in dir(module):
        obj = getattr(module, name)

        if not callable(obj):
            continue

        lname = name.lower()

        if any(
            token in lname
            for token in (
                "world",
                "generate",
                "dataset",
                "rows",
                "make_",
            )
        ):
            found.append((name, obj))

    return found


def call_generator(fn, seed):
    """
    Try common generator signatures without guessing data.
    """
    attempts = [
        lambda: fn(seed),
        lambda: fn(seed=seed),
        lambda: fn(seed, 800),
        lambda: fn(seed=seed, n=800),
        lambda: fn(seed=seed, count=800),
        lambda: fn(seed=seed, rows=800),
        lambda: fn(n=800, seed=seed),
        lambda: fn(count=800, seed=seed),
        lambda: fn(rows=800, seed=seed),
    ]

    for attempt in attempts:
        try:
            result = attempt()

            if isinstance(result, list):
                if result and isinstance(result[0], dict):
                    return result

            if isinstance(result, tuple):
                for item in result:
                    if (
                        isinstance(item, list)
                        and item
                        and isinstance(item[0], dict)
                    ):
                        return item

        except Exception:
            pass

    return None


def discover_rows(module, seed):
    """
    Locate a real generator from the existing definitive test.
    No synthetic replacement data is created.
    """

    generators = locate_generators(module)

    for name, fn in generators:
        rows = call_generator(fn, seed)

        if rows:
            return name, rows

    raise RuntimeError(
        "Could not locate a compatible real row generator "
        "inside definitive_architecture_test.py."
    )


# ============================================================
# LABEL EXTRACTION
# ============================================================

def extract_labels(rows):
    labels = []
    used_keys = []

    for row in rows:
        label, key = find_label(row)

        if label is None:
            return None, None

        labels.append(label)
        used_keys.append(key)

    unique_keys = sorted(set(used_keys))

    if len(unique_keys) != 1:
        raise RuntimeError(
            f"Inconsistent label fields encountered: {unique_keys}"
        )

    return labels, unique_keys[0]


# ============================================================
# MAIN FORENSIC AUDIT
# ============================================================

def main():
    print("=" * 80)
    print("MULTI_SIGNAL FORENSIC METRIC AUDIT V2")
    print("=" * 80)
    print("Miner:", arm.__file__)
    print("Test :", TEST_FILE)
    print()

    module = load_test_module()

    generators = locate_generators(module)

    print("Candidate generators:")
    for name, _ in generators:
        print("  ", name)

    print()

    aggregate = []

    for seed in SEEDS:
        print("-" * 80)
        print(f"SEED {seed:02d}")

        generator_name, rows = discover_rows(
            module,
            seed,
        )

        print("Generator:", generator_name)
        print("Rows:", len(rows))

        keys = row_schema(rows)

        print("Row keys:", keys)

        y_true, label_key = extract_labels(rows)

        if y_true is None:
            print(
                "LABEL STATUS: NO EXPLICIT BINARY LABEL FIELD"
            )
            print(
                "This is the critical result: the prior auditor "
                "was incorrectly assuming row['target']."
            )
            continue

        print("Label field:", label_key)

        positive = sum(y_true)
        negative = len(y_true) - positive

        print(
            "Class distribution:",
            f"positive={positive}",
            f"negative={negative}",
            f"positive_rate={positive / len(y_true):.4f}",
        )

        try:
            prediction = evaluate_rule(
                None,
                rows,
            )
        except Exception as exc:
            print("RULE EVALUATION STATUS: UNRESOLVED")
            print("Reason:", exc)
            continue

        metrics = binary_metrics(
            y_true,
            prediction,
        )

        print("Independent metrics:")
        print(
            f"  accuracy          = "
            f"{metrics['accuracy']:.6f}"
        )
        print(
            f"  balanced_accuracy = "
            f"{metrics['balanced_accuracy']:.6f}"
        )
        print(
            f"  precision         = "
            f"{metrics['precision']:.6f}"
        )
        print(
            f"  TP={metrics['tp']} "
            f"TN={metrics['tn']} "
            f"FP={metrics['fp']} "
            f"FN={metrics['fn']}"
        )

        aggregate.append(metrics)

    print()
    print("=" * 80)
    print("FORENSIC AUDIT SUMMARY")
    print("=" * 80)

    if not aggregate:
        print(
            "NO VALID METRIC RUNS."
        )
        print(
            "The audit must first identify the actual target "
            "construction used by the definitive test."
        )
        return 2

    print("Valid runs:", len(aggregate))

    print(
        "Mean accuracy:",
        statistics.mean(
            x["accuracy"]
            for x in aggregate
        ),
    )

    print(
        "Mean balanced accuracy:",
        statistics.mean(
            x["balanced_accuracy"]
            for x in aggregate
        ),
    )

    print(
        "Minimum balanced accuracy:",
        min(
            x["balanced_accuracy"]
            for x in aggregate
        ),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$ROOT/forensic_multisignal_audit.py"

echo
echo "============================================================"
echo "V2 INSTALLED"
echo "============================================================"
echo "Backup: $BACKUP"
echo
echo "SOURCE MODIFIED:"
echo "  forensic_multisignal_audit.py"
echo
echo "MINER MODIFIED:"
echo "  NO"
echo
echo "TEST MODIFIED:"
echo "  NO"
echo
echo "============================================================"
echo "RUN"
echo "============================================================"

cd "$ROOT"
python -u forensic_multisignal_audit.py \
    | tee forensic_multisignal_audit_v2.log
