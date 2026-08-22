#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import itertools
import json
import math
import random
import statistics
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_FILE = ROOT / "definitive_architecture_test.py"

WORLD = "MULTI_SIGNAL"

DISCOVERY_SEEDS = list(range(50))

TRAIN_SIZES = [
    100,
    200,
    400,
    800,
]

COMMON_TEST_SEED = 987654
COMMON_TEST_N = 5000

SHIFTED_TEST_SEEDS = [
    111111,
    222222,
    333333,
]

SHIFTED_TEST_N = 3000

FEATURES = [
    "dev_score",
    "holder_score",
    "liquidity_usd",
    "lp_lock_score",
]


# ============================================================
# MODULE
# ============================================================

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


# ============================================================
# DATA
# ============================================================

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


# ============================================================
# DISCOVERY
# ============================================================

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

    if not success:
        return {
            "success": False,
            "expr": None,
            "rule": None,
            "score": result.get("score"),
            "error": result.get("error"),
            "seconds": elapsed,
        }

    return {
        "success": True,
        "expr": expr,
        "rule": rule_string(expr, module),
        "score": result.get("score"),
        "error": result.get("error"),
        "seconds": elapsed,
    }


# ============================================================
# RULE REPRESENTATION
# ============================================================

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


def fingerprint(value):
    return hashlib.sha256(
        str(value).encode(
            "utf-8",
            errors="replace",
        )
    ).hexdigest()[:16]


# ============================================================
# GENERIC EXPRESSION FORENSICS
# ============================================================

def node_children(node):
    if node is None:
        return []

    if isinstance(node, dict):
        for key in (
            "children",
            "args",
            "operands",
        ):
            value = node.get(key)

            if isinstance(value, (list, tuple)):
                return list(value)

        children = []

        for key in (
            "left",
            "right",
        ):
            if key in node:
                children.append(node[key])

        return children

    if isinstance(node, (list, tuple)):
        if len(node) >= 2:
            return list(node[1:])

    for attr in (
        "children",
        "args",
        "operands",
    ):
        try:
            value = getattr(node, attr)

            if isinstance(value, (list, tuple)):
                return list(value)
        except Exception:
            pass

    children = []

    for attr in (
        "left",
        "right",
    ):
        try:
            children.append(getattr(node, attr))
        except Exception:
            pass

    return children


def node_operator(node):
    if node is None:
        return None

    if isinstance(node, dict):
        for key in (
            "op",
            "operator",
            "kind",
            "type",
        ):
            if key in node:
                return str(node[key]).upper()

    if isinstance(node, (list, tuple)) and node:
        if isinstance(node[0], str):
            return node[0].upper()

    for attr in (
        "op",
        "operator",
        "kind",
        "type",
    ):
        try:
            value = getattr(node, attr)

            if isinstance(value, str):
                return value.upper()
        except Exception:
            pass

    return None


def walk_tree(node, depth=0, seen=None):
    if seen is None:
        seen = set()

    ident = id(node)

    if ident in seen:
        return []

    seen.add(ident)

    result = [
        {
            "depth": depth,
            "type": type(node).__name__,
            "operator": node_operator(node),
            "text": str(node),
        }
    ]

    for child in node_children(node):
        result.extend(
            walk_tree(
                child,
                depth + 1,
                seen,
            )
        )

    return result


def extract_text_predicates(expr):
    text = rule_string(expr, None)

    predicates = []

    for feature in FEATURES:
        marker = feature

        if marker not in text:
            continue

        predicates.append(feature)

    return sorted(set(predicates))


# ============================================================
# PREDICTION
# ============================================================

def predict(module, expr, rows):
    fn = require(module, "predict")

    result = fn(
        expr,
        rows,
    )

    return [
        bool(x)
        for x in result
    ]


# ============================================================
# METRICS
# ============================================================

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
            if total else 0.0,

        "balanced_accuracy":
            (tpr + tnr) / 2.0,

        "precision":
            tp / (tp + fp)
            if tp + fp else 0.0,

        "recall":
            tpr,

        "specificity":
            tnr,

        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def agreement(a, b):
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


def positive_rate(pred):
    if not pred:
        return 0.0

    return sum(bool(x) for x in pred) / len(pred)


# ============================================================
# FEATURE STABILITY
# ============================================================

def feature_set(expr, module):
    result = set()

    for feature in rule_features(expr, module):
        result.add(str(feature))

    for feature in extract_text_predicates(expr):
        result.add(feature)

    return sorted(
        x for x in result
        if x in FEATURES
    )


# ============================================================
# THRESHOLD TEXT FORENSICS
# ============================================================

def threshold_texts(expr):
    text = rule_string(expr, None)

    results = []

    for feature in FEATURES:

        marker = feature

        if marker not in text:
            continue

        pieces = text.split(marker)

        for piece in pieces[1:]:
            fragment = piece[:80]

            for op in (
                ">=",
                "<=",
                ">",
                "<",
                "==",
            ):
                if op not in fragment:
                    continue

                try:
                    right = fragment.split(op, 1)[1]
                    token = ""

                    for char in right:
                        if (
                            char.isdigit()
                            or char in ".-+eE"
                        ):
                            token += char
                        else:
                            break

                    if token:
                        value = float(token)

                        if math.isfinite(value):
                            results.append({
                                "feature": feature,
                                "operator": op,
                                "threshold": value,
                            })
                except Exception:
                    pass

    return results


# ============================================================
# RULE COMPLEXITY
# ============================================================

def rule_complexity(expr, module):
    text = rule_string(expr, module)

    return {
        "length": len(text),
        "and_count": text.upper().count("AND"),
        "or_count": text.upper().count("OR"),
        "predicate_text_count":
            sum(
                text.count(feature)
                for feature in FEATURES
            ),
    }


# ============================================================
# SHUFFLED LABEL NULL
# ============================================================

def shuffled_labels(truth, seed):
    rng = random.Random(seed)

    output = list(truth)
    rng.shuffle(output)

    return output


# ============================================================
# MAIN EXPERIMENT
# ============================================================

def run():
    started = time.time()

    print("=" * 78)
    print("BIRTH_EDGE — L9 MECHANISM RECOVERY")
    print("=" * 78)
    print("QUESTION:")
    print(
        "Does repeated discovery recover a common underlying "
        "decision mechanism?"
    )
    print()
    print("Miner              : UNMODIFIED")
    print("Definitive test    : UNMODIFIED")
    print("Discovery seeds    :", len(DISCOVERY_SEEDS))
    print("Train sizes        :", TRAIN_SIZES)
    print("Common test N      :", COMMON_TEST_N)
    print("Shifted tests      :", len(SHIFTED_TEST_SEEDS))
    print()

    module = load_module()

    discoveries = []

    # ========================================================
    # PHASE 1 — 50-SEED CONVERGENCE
    # ========================================================

    print("=" * 78)
    print("PHASE 1 — 50-SEED DISCOVERY CONVERGENCE")
    print("=" * 78)

    for seed in DISCOVERY_SEEDS:

        train, truth = make_dataset(
            module,
            seed,
            400,
        )

        print(
            f"[{seed:02d}] discovering...",
            end=" ",
            flush=True,
        )

        d = discover(
            module,
            train,
        )

        if not d["success"]:
            print("FAILED")
            discoveries.append({
                "seed": seed,
                "success": False,
                "error": d["error"],
            })
            continue

        expr = d["expr"]

        item = {
            "seed": seed,
            "success": True,
            "expr": expr,
            "rule": d["rule"],
            "raw_fingerprint":
                fingerprint(d["rule"]),
            "features":
                feature_set(expr, module),
            "thresholds":
                threshold_texts(expr),
            "complexity":
                rule_complexity(expr, module),
            "score":
                d["score"],
            "seconds":
                d["seconds"],
        }

        discoveries.append(item)

        print(
            f"{d['seconds']:.2f}s | "
            f"score={d['score']} | "
            f"features={item['features']}"
        )

    valid = [
        x for x in discoveries
        if x.get("success")
    ]

    print()
    print(
        f"Successful discoveries: "
        f"{len(valid)}/{len(DISCOVERY_SEEDS)}"
    )

    # ========================================================
    # PHASE 2 — COMMON POPULATION
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 2 — COMMON HELD-OUT POPULATION")
    print("=" * 78)

    common_rows, common_truth = make_dataset(
        module,
        COMMON_TEST_SEED,
        COMMON_TEST_N,
    )

    predictions = {}

    for d in valid:

        pred = predict(
            module,
            d["expr"],
            common_rows,
        )

        predictions[d["seed"]] = pred

        d["common_metrics"] = classification_metrics(
            pred,
            common_truth,
        )

        print(
            f"Seed {d['seed']:02d} | "
            f"acc={d['common_metrics']['accuracy']:.5f} | "
            f"bal={d['common_metrics']['balanced_accuracy']:.5f}"
        )

    # ========================================================
    # PHASE 3 — ALL PAIRWISE FUNCTIONAL AGREEMENT
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 3 — PAIRWISE FUNCTIONAL EQUIVALENCE")
    print("=" * 78)

    pairwise = []

    for a, b in itertools.combinations(
        valid,
        2,
    ):

        sa = a["seed"]
        sb = b["seed"]

        value = agreement(
            predictions[sa],
            predictions[sb],
        )

        pairwise.append(value)

    pairwise_mean = (
        statistics.mean(pairwise)
        if pairwise else None
    )

    pairwise_min = (
        min(pairwise)
        if pairwise else None
    )

    print(
        f"Pairs evaluated : {len(pairwise)}"
    )

    print(
        f"Mean agreement  : "
        f"{pairwise_mean:.6f}"
        if pairwise_mean is not None
        else "Mean agreement  : N/A"
    )

    print(
        f"Minimum         : "
        f"{pairwise_min:.6f}"
        if pairwise_min is not None
        else "Minimum         : N/A"
    )

    # ========================================================
    # PHASE 4 — FEATURE CONVERGENCE
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 4 — FEATURE CONVERGENCE")
    print("=" * 78)

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
            if valid else 0.0
        for feature in FEATURES
    }

    for feature in FEATURES:
        print(
            f"{feature:18s} "
            f"{feature_frequency[feature]:2d}/"
            f"{len(valid):2d} "
            f"({feature_stability[feature]:.3f})"
        )

    # ========================================================
    # PHASE 5 — THRESHOLD DISTRIBUTION
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 5 — THRESHOLD CONVERGENCE")
    print("=" * 78)

    threshold_summary = {}

    for feature in FEATURES:

        values = []

        for d in valid:
            for item in d["thresholds"]:
                if item["feature"] == feature:
                    values.append(
                        item["threshold"]
                    )

        if values:

            threshold_summary[feature] = {
                "n": len(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "range":
                    max(values) - min(values),
                "stdev":
                    statistics.stdev(values)
                    if len(values) > 1
                    else 0.0,
            }

            s = threshold_summary[feature]

            print(
                f"{feature:18s} "
                f"n={s['n']} "
                f"median={s['median']:.4f} "
                f"range={s['range']:.4f} "
                f"stdev={s['stdev']:.4f}"
            )

        else:

            threshold_summary[feature] = {
                "n": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "range": None,
                "stdev": None,
            }

            print(
                f"{feature:18s} N/A"
            )

    # ========================================================
    # PHASE 6 — TRAINING-SIZE SCALING
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 6 — SAMPLE-SIZE SCALING")
    print("=" * 78)

    scaling = []

    for n in TRAIN_SIZES:

        print()
        print(
            f"TRAIN N={n}"
        )

        local = []

        for seed in range(10):

            train, _ = make_dataset(
                module,
                700000 + seed,
                n,
            )

            d = discover(
                module,
                train,
            )

            if not d["success"]:
                print(
                    f"  seed={seed:02d} FAILED"
                )
                continue

            pred = predict(
                module,
                d["expr"],
                common_rows,
            )

            metrics = classification_metrics(
                pred,
                common_truth,
            )

            local.append({
                "seed": seed,
                "accuracy":
                    metrics["accuracy"],
                "balanced":
                    metrics["balanced_accuracy"],
                "features":
                    feature_set(
                        d["expr"],
                        module,
                    ),
                "rule":
                    d["rule"],
            })

            print(
                f"  seed={seed:02d} "
                f"acc={metrics['accuracy']:.5f} "
                f"bal={metrics['balanced_accuracy']:.5f}"
            )

        if local:

            scaling.append({
                "train_n": n,
                "runs": local,
                "accuracy_mean":
                    statistics.mean(
                        x["accuracy"]
                        for x in local
                    ),
                "accuracy_min":
                    min(
                        x["accuracy"]
                        for x in local
                    ),
                "balanced_mean":
                    statistics.mean(
                        x["balanced"]
                        for x in local
                    ),
            })

    # ========================================================
    # PHASE 7 — DISTRIBUTION SHIFT
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 7 — DISTRIBUTION-SHIFT GENERALIZATION")
    print("=" * 78)

    shifted = []

    for seed in SHIFTED_TEST_SEEDS:

        rows, truth = make_dataset(
            module,
            seed,
            SHIFTED_TEST_N,
        )

        values = []

        for d in valid:

            pred = predict(
                module,
                d["expr"],
                rows,
            )

            metrics = classification_metrics(
                pred,
                truth,
            )

            values.append(
                metrics["balanced_accuracy"]
            )

        if values:

            shifted.append({
                "seed": seed,
                "mean_balanced":
                    statistics.mean(values),
                "min_balanced":
                    min(values),
                "max_balanced":
                    max(values),
            })

            print(
                f"shift={seed} "
                f"mean_bal={statistics.mean(values):.5f} "
                f"min={min(values):.5f}"
            )

    # ========================================================
    # PHASE 8 — FEATURE ABLATION
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 8 — DISCOVERY FEATURE ABLATION")
    print("=" * 78)

    ablation = {}

    labels_fn = require(
        module,
        "labels",
    )

    base_rows = common_rows

    for feature in FEATURES:

        modified = []

        for row in base_rows:

            if not isinstance(row, dict):
                modified.append(row)
                continue

            copy = dict(row)

            if feature in copy:
                copy[feature] = 0.0

            modified.append(copy)

        ablation_predictions = []

        for d in valid:

            pred = predict(
                module,
                d["expr"],
                modified,
            )

            ablation_predictions.append(
                pred
            )

        rates = [
            positive_rate(x)
            for x in ablation_predictions
        ]

        ablation[feature] = {
            "mean_positive_rate":
                statistics.mean(rates)
                if rates else None,
            "min_positive_rate":
                min(rates)
                if rates else None,
            "max_positive_rate":
                max(rates)
                if rates else None,
        }

        print(
            f"{feature:18s} "
            f"positive-rate mean="
            f"{statistics.mean(rates):.5f}"
            if rates
            else f"{feature:18s} N/A"
        )

    # ========================================================
    # PHASE 9 — PERMUTATION DISRUPTION
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 9 — FEATURE PERMUTATION DISRUPTION")
    print("=" * 78)

    permutation = {}

    for feature in FEATURES:

        rng = random.Random(
            910000 + FEATURES.index(feature)
        )

        shuffled = list(base_rows)

        values = []

        for row in shuffled:

            if isinstance(row, dict):
                values.append(
                    row.get(feature)
                )
            else:
                values.append(None)

        rng.shuffle(values)

        modified = []

        for i, row in enumerate(shuffled):

            if not isinstance(row, dict):
                modified.append(row)
                continue

            copy = dict(row)

            if feature in copy:
                copy[feature] = values[i]

            modified.append(copy)

        scores = []

        for d in valid:

            pred = predict(
                module,
                d["expr"],
                modified,
            )

            metrics = classification_metrics(
                pred,
                common_truth,
            )

            scores.append(
                metrics["balanced_accuracy"]
            )

        permutation[feature] = {
            "mean_balanced":
                statistics.mean(scores)
                if scores else None,
            "min_balanced":
                min(scores)
                if scores else None,
            "max_balanced":
                max(scores)
                if scores else None,
        }

        print(
            f"{feature:18s} "
            f"balanced mean="
            f"{statistics.mean(scores):.5f}"
            if scores
            else f"{feature:18s} N/A"
        )

    # ========================================================
    # PHASE 10 — LABEL-SHUFFLE NULL
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 10 — LABEL-SHUFFLE NULL")
    print("=" * 78)

    null_rows = []

    for seed in range(10):

        shuffled_truth = shuffled_labels(
            common_truth,
            880000 + seed,
        )

        values = []

        for d in valid:

            pred = predictions[d["seed"]]

            metrics = classification_metrics(
                pred,
                shuffled_truth,
            )

            values.append(
                metrics["balanced_accuracy"]
            )

        null_rows.append({
            "seed": seed,
            "mean_balanced":
                statistics.mean(values),
        })

        print(
            f"null={seed:02d} "
            f"balanced="
            f"{statistics.mean(values):.5f}"
        )

    null_mean = statistics.mean(
        x["mean_balanced"]
        for x in null_rows
    )

    # ========================================================
    # PHASE 11 — FUNCTIONAL CLUSTERING
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 11 — FUNCTIONAL CLUSTERING")
    print("=" * 78)

    threshold = 0.95

    clusters = []

    for d in valid:

        assigned = False

        for cluster in clusters:

            representative = cluster[0]

            if agreement(
                predictions[
                    representative["seed"]
                ],
                predictions[
                    d["seed"]
                ],
            ) >= threshold:

                cluster.append(d)
                assigned = True
                break

        if not assigned:
            clusters.append([d])

    cluster_sizes = [
        len(x)
        for x in clusters
    ]

    print(
        f"Agreement threshold : {threshold}"
    )

    print(
        f"Functional clusters : {len(clusters)}"
    )

    print(
        f"Cluster sizes       : "
        f"{cluster_sizes}"
    )

    # ========================================================
    # PHASE 12 — BOUNDARY CONCENTRATION
    # ========================================================

    print()
    print("=" * 78)
    print("PHASE 12 — DISAGREEMENT CONCENTRATION")
    print("=" * 78)

    disagreement_counts = []

    if len(valid) >= 2:

        for i in range(COMMON_TEST_N):

            votes = [
                predictions[
                    d["seed"]
                ][i]
                for d in valid
            ]

            positives = sum(votes)
            negatives = len(votes) - positives

            disagreement_counts.append(
                min(
                    positives,
                    negatives,
                )
            )

    boundary_disagreement = (
        statistics.mean(
            disagreement_counts
        )
        if disagreement_counts
        else 0.0
    )

    print(
        f"Mean disagreement mass: "
        f"{boundary_disagreement:.6f}"
    )

    # ========================================================
    # PHASE 13 — OVERALL SCORE
    # ========================================================

    accuracy_values = [
        d["common_metrics"]["accuracy"]
        for d in valid
    ]

    balanced_values = [
        d["common_metrics"]["balanced_accuracy"]
        for d in valid
    ]

    mean_accuracy = (
        statistics.mean(accuracy_values)
        if accuracy_values else 0.0
    )

    mean_balanced = (
        statistics.mean(balanced_values)
        if balanced_values else 0.0
    )

    full_feature_stability = (
        all(
            feature_stability[x] >= 0.80
            for x in FEATURES
        )
    )

    strong_functional_convergence = (
        pairwise_mean is not None
        and pairwise_mean >= 0.95
    )

    functional_floor = (
        pairwise_min is not None
        and pairwise_min >= 0.90
    )

    discovery_replication = (
        len(valid) == len(DISCOVERY_SEEDS)
    )

    strong_generalization = (
        mean_balanced >= 0.75
    )

    null_separation = (
        mean_balanced - null_mean
    )

    # This is intentionally NOT called structural
    # identifiability. It asks whether the entire
    # discovery process converges functionally on a
    # common mechanism.
    mechanism_recovery = (
        discovery_replication
        and full_feature_stability
        and strong_functional_convergence
        and functional_floor
        and strong_generalization
        and null_separation >= 0.20
    )

    if mechanism_recovery:
        verdict = (
            "L9-MECHANISM-RECOVERY-SUPPORTED"
        )
    elif (
        discovery_replication
        and strong_functional_convergence
        and strong_generalization
    ):
        verdict = (
            "L9-FUNCTIONAL-CONVERGENCE-SUPPORTED"
        )
    else:
        verdict = (
            "L9-MECHANISM-RECOVERY-NOT-ESTABLISHED"
        )

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 78)
    print("L9 FINAL FORENSIC SUMMARY")
    print("=" * 78)

    print(
        f"Successful discoveries : "
        f"{len(valid)}/{len(DISCOVERY_SEEDS)}"
    )

    print(
        f"Mean common accuracy   : "
        f"{mean_accuracy:.6f}"
    )

    print(
        f"Mean balanced accuracy : "
        f"{mean_balanced:.6f}"
    )

    print(
        f"Pairwise mean agreement: "
        f"{pairwise_mean:.6f}"
        if pairwise_mean is not None
        else
        "Pairwise mean agreement: N/A"
    )

    print(
        f"Pairwise minimum       : "
        f"{pairwise_min:.6f}"
        if pairwise_min is not None
        else
        "Pairwise minimum       : N/A"
    )

    print(
        f"Label-null mean        : "
        f"{null_mean:.6f}"
    )

    print(
        f"Null separation        : "
        f"{null_separation:.6f}"
    )

    print(
        f"Functional clusters    : "
        f"{len(clusters)}"
    )

    print()
    print("=" * 78)
    print("L9 VERDICT")
    print("=" * 78)
    print(verdict)

    # ========================================================
    # JSON
    # ========================================================

    output = (
        ROOT /
        "logs" /
        "evidence" /
        "level9"
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
        f"L9_MECHANISM_RECOVERY_{stamp}.json"
    )

    report = {
        "audit":
            "BIRTH_EDGE_L9_MECHANISM_RECOVERY",

        "version":
            "L9",

        "timestamp":
            time.strftime(
                "%Y-%m-%dT%H:%M:%S%z"
            ),

        "world":
            WORLD,

        "miner_modified":
            False,

        "definitive_test_modified":
            False,

        "discovery_seeds":
            DISCOVERY_SEEDS,

        "train_sizes":
            TRAIN_SIZES,

        "common_test_seed":
            COMMON_TEST_SEED,

        "common_test_n":
            COMMON_TEST_N,

        "shifted_test_seeds":
            SHIFTED_TEST_SEEDS,

        "discoveries":
            [
                {
                    k: v
                    for k, v in d.items()
                    if k != "expr"
                }
                for d in discoveries
            ],

        "feature_frequency":
            feature_frequency,

        "feature_stability":
            feature_stability,

        "threshold_summary":
            threshold_summary,

        "pairwise_functional":
            {
                "n":
                    len(pairwise),
                "mean":
                    pairwise_mean,
                "min":
                    pairwise_min,
            },

        "common_test":
            {
                "n":
                    len(accuracy_values),
                "accuracy_mean":
                    mean_accuracy,
                "balanced_mean":
                    mean_balanced,
                "accuracy_min":
                    min(accuracy_values)
                    if accuracy_values else None,
                "accuracy_max":
                    max(accuracy_values)
                    if accuracy_values else None,
            },

        "sample_size_scaling":
            scaling,

        "distribution_shift":
            shifted,

        "feature_ablation":
            ablation,

        "feature_permutation":
            permutation,

        "label_shuffle_null":
            {
                "runs":
                    null_rows,
                "mean_balanced":
                    null_mean,
            },

        "functional_clusters":
            {
                "threshold":
                    threshold,
                "count":
                    len(clusters),
                "sizes":
                    cluster_sizes,
            },

        "boundary_disagreement":
            boundary_disagreement,

        "checks":
            {
                "discovery_replication":
                    discovery_replication,

                "full_feature_stability":
                    full_feature_stability,

                "functional_convergence":
                    strong_functional_convergence,

                "functional_floor":
                    functional_floor,

                "generalization":
                    strong_generalization,

                "null_separation":
                    null_separation >= 0.20,

                "mechanism_recovery":
                    mechanism_recovery,
            },

        "verdict":
            verdict,

        "elapsed_seconds":
            time.time() - started,
    }

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

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
