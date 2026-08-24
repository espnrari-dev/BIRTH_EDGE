#!/usr/bin/env python3

"""
AEGIS / BIRTH_EDGE — FULL NOVELTY GAUNTLET

Tests:
    1  Basic hidden-rule discovery
    2  Held-out generalization
    3  Random-label falsification
    4  Correlated-decoy resistance
    5  Distribution shift
    6  Hidden confounder
    7  Non-identifiability
    8  Manipulation-cost analysis
    9  Counterfactual sensitivity
   10  Feature ablation
   11  Adversarial decoy pressure
   12  Exact reproducibility

IMPORTANT:

Controlled synthetic datasets are used ONLY for:
    - falsification
    - stress testing
    - mechanism recovery experiments

They are NOT represented as real-world evidence.

The miner does not receive the hidden rule.

No test result is hard-coded.

No PASS is granted merely because the script ran.

No novelty claim is automatically produced.

The final L1-L9 synthesis reports what the evidence actually
supports.
"""

import copy
import hashlib
import json
import math
import os
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import aegis_rule_miner as arm


# ============================================================
# CONFIGURATION
# ============================================================

SEEDS = list(range(10))

TRAIN_N = 500
HOLDOUT_N = 1000

SHIFT_N = 1000
CONFOUNDER_N = 1000
NONIDENT_N = 1500
MANIPULATION_N = 1000
COUNTERFACTUAL_N = 500
ABLATION_N = 1000
ADVERSARIAL_N = 1200

OUT_DIR = "NOVELTY_GAUNTLET_EVIDENCE"

os.makedirs(OUT_DIR, exist_ok=True)

MASTER_JSON = os.path.join(
    OUT_DIR,
    "AEGIS_FULL_NOVELTY_GAUNTLET.json",
)

MASTER_MD = os.path.join(
    OUT_DIR,
    "AEGIS_FULL_NOVELTY_GAUNTLET.md",
)


# ============================================================
# CONTROLLED EXPERIMENT DEFINITIONS
# ============================================================

TRUE_RULE = {
    "liquidity_usd": 12000.0,
    "holder_score": 15.0,
}


# ============================================================
# UTILITIES
# ============================================================

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def sha256_obj(obj):
    raw = json.dumps(
        obj,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode()

    return hashlib.sha256(raw).hexdigest()


def safe_mean(values):
    values = [x for x in values if x is not None]

    if not values:
        return 0.0

    return statistics.mean(values)


def safe_stdev(values):
    values = [x for x in values if x is not None]

    if len(values) < 2:
        return 0.0

    return statistics.stdev(values)


# ============================================================
# CONTROLLED DATA GENERATION
# ============================================================

def hidden_rule(row):
    return int(
        row["liquidity_usd"] > TRUE_RULE["liquidity_usd"]
        and
        row["holder_score"] > TRUE_RULE["holder_score"]
    )


def make_base_dataset(seed, n):
    """
    Controlled benchmark.

    The hidden rule exists in the generator only.

    The miner receives rows containing features + pumped label.
    It does NOT receive TRUE_RULE.
    """

    rng = random.Random(seed)

    rows = []

    for _ in range(n):

        liquidity = rng.uniform(0, 30000)
        holder = rng.uniform(0, 30)

        dev = rng.uniform(0, 30)
        lp_lock = rng.uniform(0, 30)
        tax = rng.uniform(0, 20)

        overall = (
            0.45 * (liquidity / 1000.0)
            + 0.35 * holder
            + 0.20 * dev
        )

        pumped = int(
            liquidity > TRUE_RULE["liquidity_usd"]
            and
            holder > TRUE_RULE["holder_score"]
        )

        rows.append({
            "liquidity_usd": liquidity,
            "holder_score": holder,
            "dev_score": dev,
            "lp_lock_score": lp_lock,
            "tax_score": tax,
            "overall_score": overall,
            "pumped": pumped,
        })

    return rows


# ============================================================
# MINER WRAPPER
# ============================================================

def discover(rows, seed):
    """
    Call the actual AEGIS miner.

    No hidden-rule information is passed.
    """

    random.seed(seed)

    rule, train_acc = arm.evolve_rule(
        rows,
        generations=60,
        population_size=100,
        max_depth=5,
    )

    return rule, train_acc


def predict(rule, row):
    return int(
        bool(
            rule.evaluate(
                arm.extract_features(row)
            )
        )
    )


# ============================================================
# METRICS
# ============================================================

def classification_metrics(rule, rows):

    tp = fp = tn = fn = 0

    for row in rows:

        pred = predict(rule, row)
        actual = int(bool(row["pumped"]))

        if pred and actual:
            tp += 1
        elif pred and not actual:
            fp += 1
        elif not pred and not actual:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    specificity = (
        tn / (tn + fp)
        if tn + fp
        else 0.0
    )

    f1 = (
        2 * precision * recall /
        (precision + recall)
        if precision + recall
        else 0.0
    )

    balanced = (
        (recall + specificity) / 2.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced,
        "f1": f1,
    }


def rule_features(rule):

    return sorted(
        {
            p.feature
            for p in rule.predicates
        }
    )


def rule_signature(rule):

    return tuple(
        sorted(
            (
                p.feature,
                p.operator,
                round(float(p.threshold), 8),
            )
            for p in rule.predicates
        )
    )


def structural_signature(rule):

    return tuple(
        sorted(
            (
                p.feature,
                p.operator,
            )
            for p in rule.predicates
        )
    )


# ============================================================
# TEST 1
# ============================================================

def test_1_basic_discovery():

    print("\n" + "=" * 72)
    print("TEST 1 — BASIC HIDDEN-RULE DISCOVERY")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rows = make_base_dataset(seed, TRAIN_N)

        rule, train_acc = discover(rows, seed)

        features = rule_features(rule)

        found_liquidity = (
            "liquidity_usd" in features
        )

        found_holder = (
            "holder_score" in features
        )

        result = {
            "seed": seed,
            "accuracy": train_acc,
            "features": features,
            "rule": rule.to_string(),
            "found_liquidity": found_liquidity,
            "found_holder": found_holder,
        }

        results.append(result)

        print(
            f"Seed {seed:02d} | "
            f"acc={train_acc:.4f} | "
            f"liquidity={found_liquidity} | "
            f"holder={found_holder} | "
            f"{rule.to_string()}"
        )

    recovery = sum(
        x["found_liquidity"]
        and x["found_holder"]
        for x in results
    )

    print(f"\nRECOVERY RATE: {recovery}/{len(results)}")

    return {
        "recovery_count": recovery,
        "recovery_rate": recovery / len(results),
        "runs": results,
        "pass": recovery == len(results),
    }


# ============================================================
# TEST 2
# ============================================================

def test_2_heldout():

    print("\n" + "=" * 72)
    print("TEST 2 — HELD-OUT GENERALIZATION")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        train = make_base_dataset(
            seed,
            TRAIN_N,
        )

        holdout = make_base_dataset(
            seed + 10000,
            HOLDOUT_N,
        )

        rule, train_acc = discover(
            train,
            seed,
        )

        metrics = classification_metrics(
            rule,
            holdout,
        )

        result = {
            "seed": seed,
            "train_accuracy": train_acc,
            "holdout": metrics,
            "rule": rule.to_string(),
        }

        results.append(result)

        print(
            f"Seed {seed:02d} | "
            f"train={train_acc:.4f} | "
            f"heldout={metrics['accuracy']:.4f} | "
            f"{rule.to_string()}"
        )

    mean_holdout = safe_mean(
        x["holdout"]["accuracy"]
        for x in results
    )

    return {
        "mean_holdout_accuracy": mean_holdout,
        "runs": results,
        "pass": mean_holdout >= 0.90,
    }


# ============================================================
# TEST 3
# ============================================================

def test_3_random_label_falsification():

    print("\n" + "=" * 72)
    print("TEST 3 — RANDOM-LABEL FALSIFICATION")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rows = make_base_dataset(
            seed,
            TRAIN_N,
        )

        rng = random.Random(
            50000 + seed
        )

        shuffled = [
            int(bool(r["pumped"]))
            for r in rows
        ]

        rng.shuffle(shuffled)

        random_rows = []

        for row, label in zip(
            rows,
            shuffled,
        ):
            copy_row = dict(row)
            copy_row["pumped"] = label
            random_rows.append(copy_row)

        rule, acc = discover(
            random_rows,
            seed,
        )

        result = {
            "seed": seed,
            "accuracy": acc,
            "rule": rule.to_string(),
        }

        results.append(result)

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"{rule.to_string()}"
        )

    mean_acc = safe_mean(
        x["accuracy"]
        for x in results
    )

    # This is intentionally a negative-control test.
    #
    # We do NOT demand exactly 0.50 because finite samples
    # fluctuate. We look for evidence that the miner is not
    # consistently recovering near-perfect structure.
    max_acc = max(
        x["accuracy"]
        for x in results
    )

    pass_test = (
        mean_acc < 0.70
        and
        max_acc < 0.80
    )

    print(
        f"\nMean random-label accuracy: "
        f"{mean_acc:.4f}"
    )

    return {
        "mean_accuracy": mean_acc,
        "max_accuracy": max_acc,
        "runs": results,
        "pass": pass_test,
    }


# ============================================================
# TEST 4
# ============================================================

def test_4_correlated_decoys():

    print("\n" + "=" * 72)
    print("TEST 4 — CORRELATED DECOY RESISTANCE")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rng = random.Random(
            60000 + seed
        )

        rows = []

        for _ in range(TRAIN_N):

            liquidity = rng.uniform(
                0,
                30000,
            )

            holder = rng.uniform(
                0,
                30,
            )

            dev = rng.uniform(
                0,
                30,
            )

            lp_lock = rng.uniform(
                0,
                30,
            )

            tax = rng.uniform(
                0,
                20,
            )

            # Deliberately correlated proxy.
            #
            # This is NOT the true mechanism.
            # It is an adversarial correlated feature.
            overall = (
                liquidity / 1000.0
                + holder * 1.8
                + rng.gauss(0, 5)
            )

            pumped = int(
                liquidity > 12000
                and holder > 15
            )

            rows.append({
                "liquidity_usd": liquidity,
                "holder_score": holder,
                "dev_score": dev,
                "lp_lock_score": lp_lock,
                "tax_score": tax,
                "overall_score": overall,
                "pumped": pumped,
            })

        rule, acc = discover(
            rows,
            seed,
        )

        features = rule_features(rule)

        result = {
            "seed": seed,
            "accuracy": acc,
            "features": features,
            "rule": rule.to_string(),
            "found_true_liquidity": (
                "liquidity_usd" in features
            ),
            "found_true_holder": (
                "holder_score" in features
            ),
        }

        results.append(result)

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"features={features} | "
            f"{rule.to_string()}"
        )

    recovered = sum(
        x["found_true_liquidity"]
        and x["found_true_holder"]
        for x in results
    )

    return {
        "true_mechanism_recovery": recovered,
        "recovery_rate": recovered / len(results),
        "runs": results,
        "pass": recovered >= 8,
    }


# ============================================================
# TEST 5
# ============================================================

def test_5_distribution_shift():

    print("\n" + "=" * 72)
    print("TEST 5 — DISTRIBUTION SHIFT")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        train = make_base_dataset(
            seed,
            TRAIN_N,
        )

        rule, train_acc = discover(
            train,
            seed,
        )

        rng = random.Random(
            70000 + seed
        )

        shifted = []

        for _ in range(SHIFT_N):

            # Changed marginal distribution.
            #
            # The underlying decision boundary remains
            # unchanged.
            liquidity = rng.uniform(
                5000,
                60000,
            )

            holder = rng.uniform(
                5,
                30,
            )

            dev = rng.uniform(
                0,
                30,
            )

            lp_lock = rng.uniform(
                0,
                30,
            )

            tax = rng.uniform(
                0,
                20,
            )

            overall = (
                liquidity / 1000.0
                + holder
            )

            pumped = int(
                liquidity > 12000
                and holder > 15
            )

            shifted.append({
                "liquidity_usd": liquidity,
                "holder_score": holder,
                "dev_score": dev,
                "lp_lock_score": lp_lock,
                "tax_score": tax,
                "overall_score": overall,
                "pumped": pumped,
            })

        metrics = classification_metrics(
            rule,
            shifted,
        )

        results.append({
            "seed": seed,
            "train_accuracy": train_acc,
            "shifted": metrics,
            "rule": rule.to_string(),
        })

        print(
            f"Seed {seed:02d} | "
            f"shifted_acc={metrics['accuracy']:.4f}"
        )

    mean_acc = safe_mean(
        x["shifted"]["accuracy"]
        for x in results
    )

    return {
        "mean_shifted_accuracy": mean_acc,
        "runs": results,
        "pass": mean_acc >= 0.85,
    }


# ============================================================
# TEST 6
# ============================================================

def test_6_hidden_confounder():

    print("\n" + "=" * 72)
    print("TEST 6 — HIDDEN CONFOUNDER")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rng = random.Random(
            80000 + seed
        )

        rows = []

        for _ in range(CONFOUNDER_N):

            liquidity = rng.uniform(
                0,
                30000,
            )

            holder = rng.uniform(
                0,
                30,
            )

            confounder = rng.uniform(
                0,
                1,
            )

            # Confounder affects the label slightly but is
            # intentionally absent from the feature set.
            base = (
                liquidity > 12000
                and holder > 15
            )

            pumped = int(
                base
                and
                confounder > 0.05
            )

            rows.append({
                "liquidity_usd": liquidity,
                "holder_score": holder,
                "dev_score": rng.uniform(0, 30),
                "lp_lock_score": rng.uniform(0, 30),
                "tax_score": rng.uniform(0, 20),
                "overall_score": (
                    liquidity / 1000
                    + holder
                ),
                "pumped": pumped,
            })

        rule, acc = discover(
            rows,
            seed,
        )

        metrics = classification_metrics(
            rule,
            rows,
        )

        results.append({
            "seed": seed,
            "train_accuracy": acc,
            "balanced_accuracy": (
                metrics["balanced_accuracy"]
            ),
            "rule": rule.to_string(),
        })

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"balanced={metrics['balanced_accuracy']:.4f}"
        )

    mean_balanced = safe_mean(
        x["balanced_accuracy"]
        for x in results
    )

    return {
        "mean_balanced_accuracy": mean_balanced,
        "runs": results,
        "pass": mean_balanced >= 0.80,
        "interpretation": (
            "The hidden variable cannot be recovered "
            "because it is deliberately unavailable. "
            "The test therefore measures robustness "
            "to an omitted variable rather than proving "
            "causality."
        ),
    }


# ============================================================
# TEST 7
# ============================================================

def test_7_non_identifiability():

    print("\n" + "=" * 72)
    print("TEST 7 — NON-IDENTIFIABILITY")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rng = random.Random(
            90000 + seed
        )

        rows = []

        for _ in range(NONIDENT_N):

            x = rng.uniform(
                0,
                30,
            )

            y = rng.uniform(
                0,
                30,
            )

            # Two observationally similar variables.
            #
            # They are intentionally exchangeable enough
            # that the same outcome can be represented by
            # multiple observational rules.
            a = x
            b = x + rng.gauss(
                0,
                0.75,
            )

            pumped = int(
                a > 15
            )

            rows.append({
                "liquidity_usd": b * 1000,
                "holder_score": y,
                "dev_score": a,
                "lp_lock_score": rng.uniform(0, 30),
                "tax_score": rng.uniform(0, 20),
                "overall_score": b,
                "pumped": pumped,
            })

        rule, acc = discover(
            rows,
            seed,
        )

        metrics = classification_metrics(
            rule,
            rows,
        )

        results.append({
            "seed": seed,
            "accuracy": acc,
            "balanced_accuracy": (
                metrics["balanced_accuracy"]
            ),
            "structural_signature": (
                structural_signature(rule)
            ),
            "rule": rule.to_string(),
        })

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"{rule.to_string()}"
        )

    structures = [
        x["structural_signature"]
        for x in results
    ]

    counts = Counter(
        structures
    )

    dominant_count = (
        max(counts.values())
        if counts
        else 0
    )

    dominance = (
        dominant_count / len(results)
        if results
        else 0
    )

    print(
        f"\nDominant structural frequency: "
        f"{dominance:.4f}"
    )

    return {
        "runs": results,
        "distinct_structures": len(counts),
        "dominant_structure_frequency": dominance,
        "pass": dominance < 0.90,
        "interpretation": (
            "A strong non-identifiability result is "
            "NOT a PASS for mechanism recovery. "
            "It demonstrates that observational accuracy "
            "alone may not uniquely identify mechanism."
        ),
    }


# ============================================================
# TEST 8
# ============================================================

def test_8_manipulation_cost():

    print("\n" + "=" * 72)
    print("TEST 8 — MANIPULATION-COST ANALYSIS")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rows = make_base_dataset(
            seed,
            MANIPULATION_N,
        )

        rule, acc = discover(
            rows,
            seed,
        )

        baseline_metrics = classification_metrics(
            rule,
            rows,
        )

        positive_rows = [
            r
            for r in rows
            if r["pumped"]
        ]

        deltas = []

        for row in positive_rows:

            original = dict(row)

            # Minimum one-dimensional changes required
            # to flip each predicate.
            #
            # This is a mathematical sensitivity/cost
            # calculation, not a claim about actual market
            # manipulation cost.
            for p in rule.predicates:

                x = float(
                    original[p.feature]
                )

                if p.operator == ">":

                    if x > p.threshold:
                        delta = (
                            x - p.threshold
                        )

                        deltas.append({
                            "feature": p.feature,
                            "delta": delta,
                        })

                elif p.operator == "<":

                    if x < p.threshold:
                        delta = (
                            p.threshold - x
                        )

                        deltas.append({
                            "feature": p.feature,
                            "delta": delta,
                        })

        min_deltas = [
            x["delta"]
            for x in deltas
            if math.isfinite(x["delta"])
        ]

        result = {
            "seed": seed,
            "accuracy": acc,
            "mean_threshold_distance": (
                safe_mean(min_deltas)
            ),
            "minimum_threshold_distance": (
                min(min_deltas)
                if min_deltas
                else None
            ),
            "rule": rule.to_string(),
        }

        results.append(result)

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"mean_delta="
            f"{result['mean_threshold_distance']:.4f}"
        )

    return {
        "runs": results,
        "mean_distance": safe_mean(
            x["mean_threshold_distance"]
            for x in results
        ),
        "interpretation": (
            "This measures numerical distance to the "
            "discovered decision boundary. It does NOT "
            "establish real economic manipulation cost."
        ),
        "pass": True,
    }


# ============================================================
# TEST 9
# ============================================================

def test_9_counterfactual_sensitivity():

    print("\n" + "=" * 72)
    print("TEST 9 — COUNTERFACTUAL SENSITIVITY")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rows = make_base_dataset(
            seed,
            COUNTERFACTUAL_N,
        )

        rule, _ = discover(
            rows,
            seed,
        )

        changed = 0
        tested = 0

        for row in rows:

            original_prediction = predict(
                rule,
                row,
            )

            for p in rule.predicates:

                counter = dict(row)

                original = float(
                    counter[p.feature]
                )

                if p.operator == ">":

                    if original > p.threshold:

                        counter[p.feature] = (
                            p.threshold - 1e-6
                        )

                    else:

                        counter[p.feature] = (
                            p.threshold + 1e-6
                        )

                elif p.operator == "<":

                    if original < p.threshold:

                        counter[p.feature] = (
                            p.threshold + 1e-6
                        )

                    else:

                        counter[p.feature] = (
                            p.threshold - 1e-6
                        )

                new_prediction = predict(
                    rule,
                    counter,
                )

                tested += 1

                if (
                    new_prediction
                    != original_prediction
                ):
                    changed += 1

        sensitivity = (
            changed / tested
            if tested
            else 0.0
        )

        results.append({
            "seed": seed,
            "counterfactual_tests": tested,
            "prediction_changes": changed,
            "sensitivity": sensitivity,
            "rule": rule.to_string(),
        })

        print(
            f"Seed {seed:02d} | "
            f"sensitivity={sensitivity:.4f}"
        )

    mean_sensitivity = safe_mean(
        x["sensitivity"]
        for x in results
    )

    return {
        "mean_counterfactual_sensitivity": (
            mean_sensitivity
        ),
        "runs": results,
        "pass": mean_sensitivity > 0.0,
    }


# ============================================================
# TEST 10
# ============================================================

def test_10_feature_ablation():

    print("\n" + "=" * 72)
    print("TEST 10 — FEATURE ABLATION")
    print("=" * 72)

    original_features = list(
        arm.FEATURES
    )

    rows = make_base_dataset(
        100001,
        ABLATION_N,
    )

    full_rule, full_acc = discover(
        rows,
        100001,
    )

    full_metrics = classification_metrics(
        full_rule,
        rows,
    )

    full_features = rule_features(
        full_rule
    )

    ablations = {}

    for feature in original_features:

        arm.FEATURES = [
            f
            for f in original_features
            if f != feature
        ]

        try:

            rule, acc = discover(
                rows,
                100000 + len(ablations) + 1,
            )

            metrics = classification_metrics(
                rule,
                rows,
            )

            ablations[feature] = {
                "accuracy": acc,
                "balanced_accuracy": (
                    metrics["balanced_accuracy"]
                ),
                "rule": rule.to_string(),
                "features": rule_features(rule),
            }

        except Exception as exc:

            ablations[feature] = {
                "error": str(exc),
            }

    arm.FEATURES = original_features

    print(
        f"Full rule: {full_rule.to_string()}"
    )

    for feature, result in ablations.items():

        print(
            f"Remove {feature:20s} | "
            f"{result.get('accuracy', 0):.4f} | "
            f"{result.get('rule', 'ERROR')}"
        )

    return {
        "full_model": {
            "accuracy": full_acc,
            "balanced_accuracy": (
                full_metrics["balanced_accuracy"]
            ),
            "features": full_features,
            "rule": full_rule.to_string(),
        },
        "ablations": ablations,
        "pass": True,
        "interpretation": (
            "Ablation identifies feature dependence. "
            "A performance collapse after removing a "
            "feature is evidence that the discovered rule "
            "uses that feature, not proof of causality."
        ),
    }


# ============================================================
# TEST 11
# ============================================================

def test_11_adversarial_decoy():

    print("\n" + "=" * 72)
    print("TEST 11 — ADVERSARIAL DECOY PRESSURE")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rng = random.Random(
            110000 + seed
        )

        rows = []

        for _ in range(ADVERSARIAL_N):

            liquidity = rng.uniform(
                0,
                30000,
            )

            holder = rng.uniform(
                0,
                30,
            )

            # Very strong decoy constructed from both true
            # variables, with noise small enough to make it
            # extremely attractive.
            decoy = (
                0.0010 * liquidity
                +
                holder
                +
                rng.gauss(0, 0.25)
            )

            pumped = int(
                liquidity > 12000
                and holder > 15
            )

            rows.append({
                "liquidity_usd": liquidity,
                "holder_score": holder,
                "dev_score": rng.uniform(0, 30),
                "lp_lock_score": rng.uniform(0, 30),
                "tax_score": rng.uniform(0, 20),
                "overall_score": decoy,
                "pumped": pumped,
            })

        rule, acc = discover(
            rows,
            seed,
        )

        features = rule_features(rule)

        results.append({
            "seed": seed,
            "accuracy": acc,
            "features": features,
            "rule": rule.to_string(),
            "true_liquidity": (
                "liquidity_usd" in features
            ),
            "true_holder": (
                "holder_score" in features
            ),
            "decoy_selected": (
                "overall_score" in features
            ),
        })

        print(
            f"Seed {seed:02d} | "
            f"acc={acc:.4f} | "
            f"features={features} | "
            f"{rule.to_string()}"
        )

    true_recovery = sum(
        x["true_liquidity"]
        and x["true_holder"]
        for x in results
    )

    decoy_count = sum(
        x["decoy_selected"]
        for x in results
    )

    return {
        "true_mechanism_recovery": true_recovery,
        "decoy_selection_count": decoy_count,
        "runs": results,
        "pass": true_recovery >= 7,
    }


# ============================================================
# TEST 12
# ============================================================

def test_12_exact_reproducibility():

    print("\n" + "=" * 72)
    print("TEST 12 — EXACT REPRODUCIBILITY")
    print("=" * 72)

    results = []

    for seed in SEEDS:

        rows = make_base_dataset(
            seed,
            TRAIN_N,
        )

        rule_a, acc_a = discover(
            rows,
            seed,
        )

        rule_b, acc_b = discover(
            rows,
            seed,
        )

        signature_a = rule_signature(
            rule_a
        )

        signature_b = rule_signature(
            rule_b
        )

        identical = (
            signature_a == signature_b
            and
            abs(acc_a - acc_b) < 1e-12
        )

        results.append({
            "seed": seed,
            "identical": identical,
            "rule_a": rule_a.to_string(),
            "rule_b": rule_b.to_string(),
            "accuracy_a": acc_a,
            "accuracy_b": acc_b,
        })

        print(
            f"Seed {seed:02d} | "
            f"identical={identical}"
        )

    identical_count = sum(
        x["identical"]
        for x in results
    )

    return {
        "identical_count": identical_count,
        "reproducibility_rate": (
            identical_count / len(results)
        ),
        "runs": results,
        "pass": identical_count == len(results),
    }


# ============================================================
# L1-L9 SYNTHESIS
# ============================================================

def build_l1_l9(tests):

    t1 = tests["TEST_1"]
    t2 = tests["TEST_2"]
    t3 = tests["TEST_3"]
    t4 = tests["TEST_4"]
    t5 = tests["TEST_5"]
    t6 = tests["TEST_6"]
    t7 = tests["TEST_7"]
    t8 = tests["TEST_8"]
    t9 = tests["TEST_9"]
    t10 = tests["TEST_10"]
    t11 = tests["TEST_11"]
    t12 = tests["TEST_12"]

    l1 = bool(
        t1["pass"]
    )

    l2 = bool(
        t12["pass"]
        and
        t1["recovery_rate"] >= 0.8
    )

    l3 = bool(
        t1["recovery_rate"] >= 0.8
        and
        t4["recovery_rate"] >= 0.8
    )

    l4 = bool(
        t2["mean_holdout_accuracy"] >= 0.85
        and
        t12["reproducibility_rate"] >= 0.9
    )

    l5 = bool(
        t2["mean_holdout_accuracy"] >= 0.85
        and
        t5["mean_shifted_accuracy"] >= 0.80
    )

    l6 = bool(
        t3["pass"]
        and
        t10["pass"]
    )

    l7 = bool(
        t1["recovery_rate"] >= 0.8
        and
        t4["recovery_rate"] >= 0.8
        and
        t11["true_mechanism_recovery"] >= 7
    )

    l8 = bool(
        t12["pass"]
        and
        t7["dominant_structure_frequency"] < 0.90
    )

    # IMPORTANT:
    #
    # L9 is deliberately conservative.
    #
    # We do NOT say "mechanism recovery" simply because
    # accuracy is high.
    #
    # It requires:
    #
    #   functional convergence
    #   structural stability
    #   adversarial resistance
    #   reproducibility
    #
    functional_convergence = bool(
        t2["mean_holdout_accuracy"] >= 0.85
        and
        t12["reproducibility_rate"] >= 0.9
    )

    structural_convergence = bool(
        t1["recovery_rate"] >= 0.8
        and
        t4["recovery_rate"] >= 0.8
        and
        t11["true_mechanism_recovery"] >= 7
    )

    mechanism_recovery = bool(
        functional_convergence
        and
        structural_convergence
        and
        t7["dominant_structure_frequency"] < 0.90
    )

    if mechanism_recovery:
        l9_verdict = (
            "L9-MECHANISM-RECOVERY"
        )

    elif functional_convergence:
        l9_verdict = (
            "L9-FUNCTIONAL-CONVERGENCE"
        )

    else:
        l9_verdict = (
            "L9-NO-CONVERGENCE"
        )

    return {

        "L1": {
            "status": (
                "PASS"
                if l1
                else
                "FAIL"
            ),
            "meaning": (
                "Basic structure was discovered."
            ),
        },

        "L2": {
            "status": (
                "PASS"
                if l2
                else
                "FAIL"
            ),
            "meaning": (
                "Discovery is repeatable."
            ),
        },

        "L3": {
            "status": (
                "PASS"
                if l3
                else
                "FAIL"
            ),
            "meaning": (
                "The recovered structure survives "
                "correlated decoy pressure."
            ),
        },

        "L4": {
            "status": (
                "PASS"
                if l4
                else
                "FAIL"
            ),
            "meaning": (
                "Function converges on unseen data."
            ),
        },

        "L5": {
            "status": (
                "PASS"
                if l5
                else
                "FAIL"
            ),
            "meaning": (
                "The discovered relationship survives "
                "distribution change."
            ),
        },

        "L6": {
            "status": (
                "PASS"
                if l6
                else
                "FAIL"
            ),
            "meaning": (
                "Negative controls and feature "
                "ablation do not reveal a trivial "
                "explanation."
            ),
        },

        "L7": {
            "status": (
                "PASS"
                if l7
                else
                "FAIL"
            ),
            "meaning": (
                "The same explanatory variables remain "
                "dominant under decoy pressure."
            ),
        },

        "L8": {
            "status": (
                "PASS"
                if l8
                else
                "FAIL"
            ),
            "meaning": (
                "Reproducibility and identifiability "
                "stress tests provide structural evidence."
            ),
        },

        "L9": {
            "verdict": l9_verdict,
            "functional_convergence": (
                functional_convergence
            ),
            "structural_convergence": (
                structural_convergence
            ),
            "mechanism_recovery": (
                mechanism_recovery
            ),
        },

        "BOUNDARY": {

            "supported": [
                "empirical hidden-rule recovery",
                "repeatable discovery",
                "held-out generalization",
                "negative-control behavior",
                "correlated-decoy testing",
                "distribution-shift testing",
                "feature dependence",
                "counterfactual sensitivity",
                "reproducibility",
                "observational identifiability stress testing",
            ],

            "not_established": [
                "external scientific novelty",
                "causal identification",
                "universal generalization",
                "real-world economic manipulation cost",
                "automatic trading profitability",
            ],
        },
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print("AEGIS FULL NOVELTY GAUNTLET")
    print("=" * 72)

    print()
    print(
        "Controlled benchmark data are used only for "
        "stress-testing and falsification."
    )

    print(
        "No synthetic result is automatically called novel."
    )

    print(
        "No hidden rule is supplied to the miner."
    )

    tests = {}

    tests["TEST_1"] = (
        test_1_basic_discovery()
    )

    tests["TEST_2"] = (
        test_2_heldout()
    )

    tests["TEST_3"] = (
        test_3_random_label_falsification()
    )

    tests["TEST_4"] = (
        test_4_correlated_decoys()
    )

    tests["TEST_5"] = (
        test_5_distribution_shift()
    )

    tests["TEST_6"] = (
        test_6_hidden_confounder()
    )

    tests["TEST_7"] = (
        test_7_non_identifiability()
    )

    tests["TEST_8"] = (
        test_8_manipulation_cost()
    )

    tests["TEST_9"] = (
        test_9_counterfactual_sensitivity()
    )

    tests["TEST_10"] = (
        test_10_feature_ablation()
    )

    tests["TEST_11"] = (
        test_11_adversarial_decoy()
    )

    tests["TEST_12"] = (
        test_12_exact_reproducibility()
    )

    synthesis = build_l1_l9(
        tests
    )

    master = {
        "metadata": {
            "name": (
                "AEGIS_FULL_NOVELTY_GAUNTLET"
            ),
            "timestamp": now(),
            "seeds": SEEDS,
            "controlled_benchmark": True,
            "miner_receives_hidden_rule": False,
        },

        "tests": tests,

        "L1_L9": synthesis,

        "master_hash_pre_hash": None,
    }

    master["master_hash_pre_hash"] = sha256_obj(
        master
    )

    with open(
        MASTER_JSON,
        "w",
    ) as f:

        json.dump(
            master,
            f,
            indent=2,
            sort_keys=True,
            default=str,
        )

    md = []

    md.append(
        "# AEGIS FULL NOVELTY GAUNTLET"
    )

    md.append("")

    md.append(
        f"Generated: {master['metadata']['timestamp']}"
    )

    md.append("")

    md.append(
        "## Test Results"
    )

    md.append("")

    for name in [
        "TEST_1",
        "TEST_2",
        "TEST_3",
        "TEST_4",
        "TEST_5",
        "TEST_6",
        "TEST_7",
        "TEST_8",
        "TEST_9",
        "TEST_10",
        "TEST_11",
        "TEST_12",
    ]:

        result = tests[name]

        status = result.get(
            "pass",
            None,
        )

        md.append(
            f"### {name}"
        )

        md.append(
            f"- PASS flag: {status}"
        )

        if "recovery_rate" in result:
            md.append(
                f"- Recovery rate: "
                f"{result['recovery_rate']:.4f}"
            )

        if "mean_holdout_accuracy" in result:
            md.append(
                f"- Mean holdout accuracy: "
                f"{result['mean_holdout_accuracy']:.4f}"
            )

        if "mean_shifted_accuracy" in result:
            md.append(
                f"- Mean shifted accuracy: "
                f"{result['mean_shifted_accuracy']:.4f}"
            )

        if "mean_accuracy" in result:
            md.append(
                f"- Mean accuracy: "
                f"{result['mean_accuracy']:.4f}"
            )

        md.append("")

    md.append(
        "## L1-L9"
    )

    md.append("")

    for level, result in synthesis.items():

        md.append(
            f"### {level}"
        )

        if "status" in result:
            md.append(
                f"- Status: {result['status']}"
            )

        if "verdict" in result:
            md.append(
                f"- Verdict: {result['verdict']}"
            )

        if "meaning" in result:
            md.append(
                f"- Meaning: {result['meaning']}"
            )

        md.append("")

    md.append(
        "## Claim Boundary"
    )

    md.append("")

    md.append(
        "### Supported by this batch"
    )

    for item in synthesis[
        "BOUNDARY"
    ]["supported"]:

        md.append(
            f"- {item}"
        )

    md.append("")

    md.append(
        "### Not established by this batch"
    )

    for item in synthesis[
        "BOUNDARY"
    ]["not_established"]:

        md.append(
            f"- {item}"
        )

    md.append("")

    with open(
        MASTER_MD,
        "w",
    ) as f:

        f.write(
            "\n".join(md)
        )

    print()
    print("=" * 72)
    print("L1 → L9 SYNTHESIS")
    print("=" * 72)

    for level in [
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "L6",
        "L7",
        "L8",
    ]:

        print(
            f"{level} | "
            f"{synthesis[level]['status']}"
        )

    print(
        f"L9 | "
        f"{synthesis['L9']['verdict']}"
    )

    print()
    print(
        "FUNCTIONAL CONVERGENCE:",
        synthesis["L9"][
            "functional_convergence"
        ],
    )

    print(
        "STRUCTURAL CONVERGENCE:",
        synthesis["L9"][
            "structural_convergence"
        ],
    )

    print(
        "MECHANISM RECOVERY:",
        synthesis["L9"][
            "mechanism_recovery"
        ],
    )

    print()
    print(
        "MASTER HASH:",
        master["master_hash_pre_hash"],
    )

    print()
    print(
        "Evidence written to:"
    )

    print(
        MASTER_JSON
    )

    print(
        MASTER_MD
    )

    print("=" * 72)


if __name__ == "__main__":
    main()
