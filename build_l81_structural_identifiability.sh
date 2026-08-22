#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backups/L81_STRUCTURAL_$STAMP"
EVIDENCE="$ROOT/logs/evidence/level8/L81_STRUCTURAL_$STAMP"

mkdir -p "$BACKUP" "$EVIDENCE"

echo "======================================================================"
echo "BIRTH_EDGE — L8.1 STRUCTURAL IDENTIFIABILITY DIAGNOSTIC"
echo "======================================================================"
echo "STAMP    : $STAMP"
echo "EVIDENCE : $EVIDENCE"
echo

for f in \
    aegis_rule_miner.py \
    definitive_architecture_test.py \
    forensic_multisignal_audit.py \
    l8_fast_adversarial.py
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
        l8_fast_adversarial.py \
        2>/dev/null || true
) > "$EVIDENCE/SOURCE_HASHES.sha256"

cat > "$ROOT/l81_structural_identifiability.py" <<'PY'
#!/usr/bin/env python3

"""
BIRTH_EDGE — L8.1 STRUCTURAL IDENTIFIABILITY DIAGNOSTIC

Purpose
-------
Resolve the L8 finding:

    RAW RULE FINGERPRINT INSTABILITY

versus:

    UNDERLYING STRUCTURAL / FUNCTIONAL STABILITY

This test does NOT modify the miner or definitive architecture.

It uses:
    - existing make_world()
    - existing labels()
    - existing safe_discover()
    - existing predict()

Discovery occurs ONCE PER SEED.

The discovered expressions are then analyzed through several
independent representations.

Tests
-----
1. RAW STRING IDENTITY
2. CANONICAL PREDICATE IDENTITY
3. DUPLICATE-PREDICATE REMOVAL
4. FEATURE-SET STABILITY
5. THRESHOLD STABILITY
6. COMMON-DATASET PREDICTION AGREEMENT
7. PAIRWISE STRUCTURAL JACCARD
8. PAIRWISE FUNCTIONAL AGREEMENT
9. CROSS-SEED PERFORMANCE
10. STRUCTURAL IDENTIFIABILITY VERDICT

Important
---------
This test does not declare two rules identical merely because
their accuracy is similar.

It separates:

    syntactic identity
    predicate identity
    feature identity
    threshold proximity
    functional equivalence

The goal is to determine WHICH level of identity is stable.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import statistics
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

WORLD = "MULTI_SIGNAL"

SEEDS = list(range(5))

TRAIN_N = 400
TEST_N = 1000

COMMON_TEST_SEED = 987654

FEATURES = [
    "dev_score",
    "holder_score",
    "liquidity_usd",
    "lp_lock_score",
]


# ======================================================================
# MODULE
# ======================================================================

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


# ======================================================================
# RULE HELPERS
# ======================================================================

def rule_string(expr, module):
    fn = getattr(module, "rule_string", None)

    if callable(fn):
        try:
            return str(fn(expr))
        except Exception:
            pass

    return str(expr)


def rule_features(expr, module):
    fn = getattr(module, "rule_features", None)

    if callable(fn):
        try:
            return list(fn(expr))
        except Exception:
            pass

    try:
        import aegis_rule_miner as arm

        fn = getattr(arm, "rule_features", None)

        if callable(fn):
            return list(fn(expr))
    except Exception:
        pass

    return []


# ======================================================================
# GENERIC TREE INTROSPECTION
# ======================================================================

def node_children(node):
    """
    Attempt to extract logical children from common expression forms.

    Supports:
        dict
        tuples
        lists
        objects with left/right
        objects with children
        objects with args
    """

    if node is None:
        return []

    if isinstance(node, dict):
        for key in ("children", "args"):
            value = node.get(key)
            if isinstance(value, (list, tuple)):
                return list(value)

        children = []

        for key in ("left", "right"):
            if key in node:
                children.append(node[key])

        if children:
            return children

    if isinstance(node, (list, tuple)):
        if len(node) >= 2:
            return list(node[1:])

    for attr in ("children", "args"):
        try:
            value = getattr(node, attr)
            if isinstance(value, (list, tuple)):
                return list(value)
        except Exception:
            pass

    children = []

    for attr in ("left", "right"):
        try:
            children.append(getattr(node, attr))
        except Exception:
            pass

    return children


def node_operator(node):
    """
    Attempt to identify a logical operator.
    """

    if node is None:
        return None

    if isinstance(node, dict):
        for key in ("op", "operator", "kind", "type"):
            if key in node:
                return str(node[key]).upper()

    if isinstance(node, (list, tuple)) and node:
        first = node[0]

        if isinstance(first, str):
            return first.upper()

    for attr in ("op", "operator", "kind", "type"):
        try:
            value = getattr(node, attr)
            if isinstance(value, str):
                return value.upper()
        except Exception:
            pass

    return None


def flatten_and(expr):
    """
    Flatten nested AND structures when the expression representation
    exposes its tree.

    If tree introspection is unavailable, the expression is preserved
    as a single atomic predicate representation.
    """

    op = node_operator(expr)
    children = node_children(expr)

    if op in ("AND", "&&") and children:
        out = []

        for child in children:
            out.extend(flatten_and(child))

        return out

    return [expr]


# ======================================================================
# PREDICATE NORMALIZATION
# ======================================================================

def normalize_number(value):
    try:
        value = float(value)

        if not math.isfinite(value):
            return str(value)

        return f"{value:.8g}"
    except Exception:
        return str(value)


def predicate_signature(expr, module):
    """
    Produce the strongest available predicate representation.

    Priority:
        explicit attributes
        expression string
        feature association
    """

    # Try dictionary representation.
    if isinstance(expr, dict):
        feature = None
        threshold = None
        operator = None

        for key in ("feature", "field", "column", "name"):
            if key in expr:
                feature = expr[key]
                break

        for key in ("threshold", "value", "cutoff"):
            if key in expr:
                threshold = expr[key]
                break

        for key in ("op", "operator", "comparison"):
            if key in expr:
                operator = expr[key]
                break

        if feature is not None:
            return (
                str(feature),
                str(operator) if operator is not None else ">",
                normalize_number(threshold)
                if threshold is not None
                else None,
            )

    # Try object attributes.
    feature = None
    threshold = None
    operator = None

    for attr in ("feature", "field", "column", "name"):
        try:
            feature = getattr(expr, attr)
            break
        except Exception:
            pass

    for attr in ("threshold", "value", "cutoff"):
        try:
            threshold = getattr(expr, attr)
            break
        except Exception:
            pass

    for attr in ("op", "operator", "comparison"):
        try:
            operator = getattr(expr, attr)
            break
        except Exception:
            pass

    if feature is not None:
        return (
            str(feature),
            str(operator) if operator is not None else ">",
            normalize_number(threshold)
            if threshold is not None
            else None,
        )

    # Fall back to deterministic textual representation.
    text = rule_string(expr, module)

    return (
        text.strip(),
        None,
        None,
    )


def canonical_predicates(expr, module):
    """
    Canonicalize AND predicates.

    Duplicate predicates are removed.

    Predicates are sorted deterministically.
    """

    flattened = flatten_and(expr)

    signatures = []

    for predicate in flattened:
        sig = predicate_signature(
            predicate,
            module,
        )

        signatures.append(sig)

    unique = sorted(
        set(signatures),
        key=lambda x: str(x),
    )

    return unique


def canonical_feature_set(expr, module):
    predicates = canonical_predicates(
        expr,
        module,
    )

    result = set()

    for predicate in predicates:
        if predicate[1] is not None:
            result.add(str(predicate[0]))

    if not result:
        result.update(
            str(x)
            for x in rule_features(expr, module)
        )

    return sorted(result)


def canonical_string(expr, module):
    predicates = canonical_predicates(
        expr,
        module,
    )

    return json.dumps(
        predicates,
        sort_keys=True,
        separators=(",", ":"),
    )


def fingerprint(value):
    raw = str(value).encode(
        "utf-8",
        errors="replace",
    )

    return hashlib.sha256(raw).hexdigest()[:16]


# ======================================================================
# DATA
# ======================================================================

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


# ======================================================================
# DISCOVERY
# ======================================================================

def discover(module, rows):
    safe_discover = require(
        module,
        "safe_discover",
    )

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

    if not success:
        return {
            "success": False,
            "expr": None,
            "rule": None,
            "features": [],
            "score": result.get("score"),
            "error": result.get("error"),
            "seconds": elapsed,
        }

    return {
        "success": True,
        "expr": expr,
        "rule": rule_string(expr, module),
        "features": rule_features(expr, module),
        "score": result.get("score"),
        "error": result.get("error"),
        "seconds": elapsed,
    }


# ======================================================================
# PREDICTION
# ======================================================================

def predict(module, expr, rows):
    fn = require(
        module,
        "predict",
    )

    result = fn(
        expr,
        rows,
    )

    return [
        bool(x)
        for x in result
    ]


def classification_metrics(pred, truth):
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

    return {
        "accuracy":
            (tp + tn) / total
            if total
            else 0.0,

        "balanced_accuracy":
            (tpr + tnr) / 2.0,

        "precision":
            tp / (tp + fp)
            if tp + fp
            else 0.0,

        "recall":
            tpr,

        "specificity":
            tnr,

        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


# ======================================================================
# PAIRWISE COMPARISON
# ======================================================================

def jaccard(a, b):
    a = set(a)
    b = set(b)

    union = a | b

    if not union:
        return 1.0

    return len(a & b) / len(union)


def prediction_agreement(a, b):
    if len(a) != len(b):
        raise ValueError(
            "prediction length mismatch"
        )

    if not a:
        return 1.0

    return sum(
        x == y
        for x, y in zip(a, b)
    ) / len(a)


def prediction_positive_rate(pred):
    if not pred:
        return 0.0

    return sum(bool(x) for x in pred) / len(pred)


# ======================================================================
# THRESHOLD EXTRACTION
# ======================================================================

def extract_thresholds(expr, module):
    predicates = canonical_predicates(
        expr,
        module,
    )

    result = {}

    for feature, operator, threshold in predicates:

        if (
            feature in FEATURES
            and threshold is not None
        ):
            try:
                value = float(threshold)
            except Exception:
                continue

            result.setdefault(
                feature,
                [],
            ).append(value)

    return result


def threshold_statistics(discoveries):
    values = {
        feature: []
        for feature in FEATURES
    }

    for d in discoveries:

        for feature, thresholds in d["thresholds"].items():

            values[feature].extend(
                thresholds
            )

    output = {}

    for feature in FEATURES:

        current = values[feature]

        if not current:
            output[feature] = {
                "n": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "range": None,
            }

            continue

        output[feature] = {
            "n": len(current),
            "mean": statistics.mean(current),
            "median": statistics.median(current),
            "min": min(current),
            "max": max(current),
            "range":
                max(current) - min(current),
        }

    return output


# ======================================================================
# RUN
# ======================================================================

def run():
    started = time.time()

    print("=" * 70)
    print("BIRTH_EDGE — L8.1 STRUCTURAL IDENTIFIABILITY")
    print("=" * 70)
    print(f"World              : {WORLD}")
    print(f"Seeds              : {len(SEEDS)}")
    print(f"Train              : {TRAIN_N}")
    print(f"Common test        : {COMMON_TEST_SEED}")
    print("Miner              : UNMODIFIED")
    print("Definitive test     : UNMODIFIED")
    print("Discovery           : ONCE PER SEED")
    print()

    module = load_module()

    discoveries = []

    # --------------------------------------------------------------
    # DISCOVERY
    # --------------------------------------------------------------

    for seed in SEEDS:

        print(
            f"[SEED {seed:02d}] generating...",
            flush=True,
        )

        train, _ = make_dataset(
            module,
            seed,
            TRAIN_N,
        )

        print(
            f"[SEED {seed:02d}] discovering...",
            flush=True,
        )

        d = discover(
            module,
            train,
        )

        if not d["success"]:

            print(
                f"[SEED {seed:02d}] FAILED "
                f"after {d['seconds']:.3f}s",
                flush=True,
            )

            discoveries.append({
                "seed": seed,
                "success": False,
                "error": d["error"],
            })

            continue

        canonical = canonical_predicates(
            d["expr"],
            module,
        )

        features = canonical_feature_set(
            d["expr"],
            module,
        )

        canonical_repr = canonical_string(
            d["expr"],
            module,
        )

        thresholds = extract_thresholds(
            d["expr"],
            module,
        )

        item = {
            "seed": seed,
            "success": True,
            "rule": d["rule"],
            "raw_fingerprint":
                fingerprint(d["rule"]),
            "canonical":
                canonical,
            "canonical_fingerprint":
                fingerprint(canonical_repr),
            "features":
                features,
            "thresholds":
                thresholds,
            "score":
                d["score"],
            "discovery_seconds":
                d["seconds"],
        }

        discoveries.append(item)

        print(
            f"[SEED {seed:02d}] discovered in "
            f"{d['seconds']:.3f}s",
            flush=True,
        )

        print(
            f"[SEED {seed:02d}] RAW: "
            f"{d['rule']}",
            flush=True,
        )

        print(
            f"[SEED {seed:02d}] CANONICAL: "
            f"{canonical}",
            flush=True,
        )

        print(
            f"[SEED {seed:02d}] FEATURES: "
            f"{features}",
            flush=True,
        )

    valid = [
        d
        for d in discoveries
        if d.get("success")
    ]

    # --------------------------------------------------------------
    # COMMON DATASET
    # --------------------------------------------------------------

    print()
    print(
        f"Generating COMMON TEST SET "
        f"seed={COMMON_TEST_SEED}...",
        flush=True,
    )

    common_rows, common_truth = make_dataset(
        module,
        COMMON_TEST_SEED,
        2000,
    )

    predictions = {}

    for d in valid:

        pred = predict(
            module,
            next(
                x["expr"]
                for x in discoveries
                if x["seed"] == d["seed"]
            ),
            common_rows,
        )

        predictions[d["seed"]] = pred

        metrics = classification_metrics(
            pred,
            common_truth,
        )

        d["common_test"] = metrics
        d["positive_rate"] = prediction_positive_rate(
            pred
        )

        print(
            f"[SEED {d['seed']:02d}] common-test "
            f"accuracy={metrics['accuracy']:.6f} "
            f"balanced={metrics['balanced_accuracy']:.6f}",
            flush=True,
        )

    # --------------------------------------------------------------
    # RAW IDENTITY
    # --------------------------------------------------------------

    raw_fingerprints = [
        d["raw_fingerprint"]
        for d in valid
    ]

    canonical_fingerprints = [
        d["canonical_fingerprint"]
        for d in valid
    ]

    raw_unique = len(set(raw_fingerprints))
    canonical_unique = len(
        set(canonical_fingerprints)
    )

    raw_identity = (
        raw_unique == 1
        if valid
        else False
    )

    canonical_identity = (
        canonical_unique == 1
        if valid
        else False
    )

    # --------------------------------------------------------------
    # FEATURE STABILITY
    # --------------------------------------------------------------

    feature_frequency = {
        feature: 0
        for feature in FEATURES
    }

    for d in valid:

        for feature in d["features"]:

            if feature in feature_frequency:
                feature_frequency[feature] += 1

    feature_stability = {
        feature:
            feature_frequency[feature] / len(valid)
            if valid
            else 0.0
        for feature in FEATURES
    }

    # --------------------------------------------------------------
    # STRUCTURAL JACCARD
    # --------------------------------------------------------------

    pairwise_structure = []

    for i in range(len(valid)):

        for j in range(i + 1, len(valid)):

            a = valid[i]
            b = valid[j]

            ja = jaccard(
                a["canonical"],
                b["canonical"],
            )

            pairwise_structure.append({
                "seed_a": a["seed"],
                "seed_b": b["seed"],
                "jaccard": ja,
            })

    structural_jaccards = [
        x["jaccard"]
        for x in pairwise_structure
    ]

    structural_jaccard_mean = (
        statistics.mean(structural_jaccards)
        if structural_jaccards
        else None
    )

    structural_jaccard_min = (
        min(structural_jaccards)
        if structural_jaccards
        else None
    )

    # --------------------------------------------------------------
    # FUNCTIONAL AGREEMENT
    # --------------------------------------------------------------

    pairwise_functional = []

    for i in range(len(valid)):

        for j in range(i + 1, len(valid)):

            a = valid[i]["seed"]
            b = valid[j]["seed"]

            agreement = prediction_agreement(
                predictions[a],
                predictions[b],
            )

            pairwise_functional.append({
                "seed_a": a,
                "seed_b": b,
                "agreement": agreement,
            })

    functional_values = [
        x["agreement"]
        for x in pairwise_functional
    ]

    functional_mean = (
        statistics.mean(functional_values)
        if functional_values
        else None
    )

    functional_min = (
        min(functional_values)
        if functional_values
        else None
    )

    # --------------------------------------------------------------
    # CROSS-SEED PERFORMANCE
    # --------------------------------------------------------------

    common_accuracy = [
        d["common_test"]["accuracy"]
        for d in valid
    ]

    common_balanced = [
        d["common_test"]["balanced_accuracy"]
        for d in valid
    ]

    # --------------------------------------------------------------
    # THRESHOLDS
    # --------------------------------------------------------------

    threshold_stats = threshold_statistics(
        valid
    )

    # --------------------------------------------------------------
    # IDENTIFIABILITY CHECKS
    # --------------------------------------------------------------

    full_feature_stability = all(
        feature_stability[f] >= 0.80
        for f in FEATURES
    )

    structural_stability = (
        structural_jaccard_mean is not None
        and structural_jaccard_mean >= 0.75
    )

    structural_floor = (
        structural_jaccard_min is not None
        and structural_jaccard_min >= 0.50
    )

    functional_stability = (
        functional_mean is not None
        and functional_mean >= 0.95
    )

    functional_floor = (
        functional_min is not None
        and functional_min >= 0.90
    )

    cross_seed_performance = (
        bool(common_balanced)
        and statistics.mean(common_balanced) >= 0.75
    )

    discovery_replication = (
        len(valid) == len(SEEDS)
    )

    # This is intentionally separated from exact identity.
    #
    # Exact canonical identity can fail while structural and
    # functional stability pass.

    structural_identifiability = (
        discovery_replication
        and full_feature_stability
        and structural_stability
        and structural_floor
        and functional_stability
        and functional_floor
        and cross_seed_performance
    )

    if structural_identifiability:

        verdict = (
            "L8.1-STRUCTURALLY-IDENTIFIABLE"
        )

    elif (
        discovery_replication
        and functional_stability
        and functional_floor
        and full_feature_stability
    ):

        verdict = (
            "L8.1-FUNCTIONALLY-STABLE"
        )

    else:

        verdict = (
            "L8.1-INVESTIGATE"
        )

    checks = {
        "discovery_replication":
            discovery_replication,

        "raw_string_identity":
            raw_identity,

        "canonical_identity":
            canonical_identity,

        "feature_stability":
            full_feature_stability,

        "structural_jaccard":
            structural_stability,

        "structural_jaccard_floor":
            structural_floor,

        "functional_agreement":
            functional_stability,

        "functional_agreement_floor":
            functional_floor,

        "cross_seed_performance":
            cross_seed_performance,

        "structural_identifiability":
            structural_identifiability,
    }

    # --------------------------------------------------------------
    # CONSOLE REPORT
    # --------------------------------------------------------------

    print()
    print("=" * 70)
    print("L8.1 STRUCTURAL FORENSICS")
    print("=" * 70)

    print(
        f"Successful discoveries : "
        f"{len(valid)}/{len(SEEDS)}"
    )

    print(
        f"Raw unique rules      : "
        f"{raw_unique}"
    )

    print(
        f"Canonical unique rules: "
        f"{canonical_unique}"
    )

    print()
    print("FEATURE STABILITY")

    for feature in FEATURES:

        print(
            f"  {feature:18s} "
            f"{feature_stability[feature]:.3f}"
        )

    print()
    print("STRUCTURAL AGREEMENT")

    print(
        f"  Mean Jaccard         : "
        f"{structural_jaccard_mean:.6f}"
        if structural_jaccard_mean is not None
        else
        "  Mean Jaccard         : N/A"
    )

    print(
        f"  Minimum Jaccard      : "
        f"{structural_jaccard_min:.6f}"
        if structural_jaccard_min is not None
        else
        "  Minimum Jaccard      : N/A"
    )

    print()
    print("FUNCTIONAL AGREEMENT")

    print(
        f"  Mean prediction agreement: "
        f"{functional_mean:.6f}"
        if functional_mean is not None
        else
        "  Mean prediction agreement: N/A"
    )

    print(
        f"  Minimum prediction agreement: "
        f"{functional_min:.6f}"
        if functional_min is not None
        else
        "  Minimum prediction agreement: N/A"
    )

    print()
    print("COMMON TEST PERFORMANCE")

    if common_accuracy:

        print(
            f"  Accuracy mean       : "
            f"{statistics.mean(common_accuracy):.6f}"
        )

    if common_balanced:

        print(
            f"  Balanced mean       : "
            f"{statistics.mean(common_balanced):.6f}"
        )

    print()
    print("THRESHOLD STABILITY")

    for feature, stats in threshold_stats.items():

        if stats["n"]:

            print(
                f"  {feature:18s} "
                f"median={stats['median']:.6f} "
                f"range={stats['range']:.6f}"
            )

        else:

            print(
                f"  {feature:18s} N/A"
            )

    print()
    print("CHECKS")

    for name, passed in checks.items():

        print(
            f"  {name:32s}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()
    print("=" * 70)
    print("L8.1 VERDICT")
    print("=" * 70)
    print(verdict)

    # --------------------------------------------------------------
    # REPORT
    # --------------------------------------------------------------

    report = {
        "audit":
            "BIRTH_EDGE_L8_1_STRUCTURAL_IDENTIFIABILITY",

        "version":
            "L8.1",

        "timestamp":
            time.strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            ),

        "world":
            WORLD,

        "train_n":
            TRAIN_N,

        "common_test_seed":
            COMMON_TEST_SEED,

        "common_test_n":
            2000,

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

        "discoveries":
            discoveries,

        "raw_identity":
            {
                "unique_rules":
                    raw_unique,

                "exact_identity":
                    raw_identity,

                "fingerprints":
                    raw_fingerprints,
            },

        "canonical_identity":
            {
                "unique_rules":
                    canonical_unique,

                "exact_identity":
                    canonical_identity,

                "fingerprints":
                    canonical_fingerprints,
            },

        "feature_frequency":
            feature_frequency,

        "feature_stability":
            feature_stability,

        "threshold_statistics":
            threshold_stats,

        "pairwise_structural":
            pairwise_structure,

        "pairwise_functional":
            pairwise_functional,

        "common_test_accuracy":
            {
                "n": len(common_accuracy),
                "mean":
                    statistics.mean(common_accuracy)
                    if common_accuracy
                    else None,
                "min":
                    min(common_accuracy)
                    if common_accuracy
                    else None,
                "max":
                    max(common_accuracy)
                    if common_accuracy
                    else None,
            },

        "common_test_balanced_accuracy":
            {
                "n": len(common_balanced),
                "mean":
                    statistics.mean(common_balanced)
                    if common_balanced
                    else None,
                "min":
                    min(common_balanced)
                    if common_balanced
                    else None,
                "max":
                    max(common_balanced)
                    if common_balanced
                    else None,
            },

        "checks":
            checks,

        "verdict":
            verdict,

        "method_note":
            (
                "L8.1 separates raw syntactic identity from "
                "canonical predicate identity, feature stability, "
                "structural Jaccard similarity, and functional "
                "prediction agreement. Discovery occurs once per "
                "seed and all discovered rules are evaluated on "
                "one common held-out dataset."
            ),

        "elapsed_seconds":
            time.time() - started,
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
        f"L81_STRUCTURAL_{stamp}.json"
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

    return 0 if verdict != "L8.1-INVESTIGATE" else 1


if __name__ == "__main__":
    raise SystemExit(run())
PY

chmod +x "$ROOT/l81_structural_identifiability.py"

echo
echo "======================================================================"
echo "L8.1 INSTALLED"
echo "======================================================================"
echo "Miner modified      : NO"
echo "Definitive test     : NO"
echo "Discovery/seed      : 1"
echo "Seeds               : 5"
echo "Common test         : 2000 rows"
echo "Evidence            : $EVIDENCE"
echo
echo "RUNNING..."
echo

cd "$ROOT"

python -u l81_structural_identifiability.py \
    | tee "$EVIDENCE/L81_STRUCTURAL_CONSOLE.log"

STATUS=${PIPESTATUS[0]}

echo
echo "======================================================================"
echo "L8.1 EXIT STATUS: $STATUS"
echo "======================================================================"

exit "$STATUS"
