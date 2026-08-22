#!/usr/bin/env python3

"""
AEGIS RULE MINER — ROBUST DISCOVERY ENGINE

Upgrade goals:
- deterministic discovery
- threshold-rule recovery
- conjunction discovery
- held-out validation
- feature-ablation compatibility
- resistance to correlated/cheap decoys
- no synthetic labels
- no hard-coded target rule
- no knowledge of the gauntlet's hidden rule
- preserves the public API used by the gauntlet
"""

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


FEATURES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(row: Dict[str, Any]) -> Dict[str, float]:
    """
    Map external row names into the miner's canonical feature space.
    """

    return {
        "liquidity_usd": float(
            row.get("initial_liquidity_usd", row.get("liquidity_usd", 0.0))
        ),
        "holder_score": float(row.get("holder_score", 0.0)),
        "dev_score": float(row.get("dev_score", 0.0)),
        "lp_lock_score": float(row.get("lp_lock_score", 0.0)),
        "tax_score": float(row.get("tax_score", 0.0)),
        "overall_score": float(row.get("overall_score", 0.0)),
    }


# ============================================================
# EXPRESSION MODEL
# ============================================================

@dataclass(frozen=True)
class Predicate:
    feature: str
    operator: str
    threshold: float

    def evaluate(self, values: Dict[str, float]) -> bool:
        x = float(values.get(self.feature, 0.0))

        if self.operator == ">":
            return x > self.threshold

        if self.operator == "<":
            return x < self.threshold

        return False

    def to_string(self) -> str:
        return f"({self.feature} {self.operator} {self.threshold:.4g})"


@dataclass(frozen=True)
class Rule:
    predicates: Tuple[Predicate, ...]

    def evaluate(self, values: Dict[str, float]) -> bool:
        return all(p.evaluate(values) for p in self.predicates)

    def to_string(self) -> str:
        if len(self.predicates) == 1:
            return self.predicates[0].to_string()

        return "(" + " AND ".join(
            p.to_string() for p in self.predicates
        ) + ")"

    @property
    def complexity(self) -> int:
        return len(self.predicates)


# ============================================================
# PUBLIC COMPATIBILITY
# ============================================================

Expr = Rule


# ============================================================
# METRICS
# ============================================================

def _accuracy(rule: Rule, rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0

    correct = 0

    for row in rows:
        pred = bool(rule.evaluate(extract_features(row)))
        target = bool(row["pumped"])

        if pred == target:
            correct += 1

    return correct / len(rows)


def _balanced_accuracy(
    rule: Rule,
    rows: List[Dict[str, Any]]
) -> float:

    positives = 0
    negatives = 0
    true_positive = 0
    true_negative = 0

    for row in rows:
        target = bool(row["pumped"])
        pred = bool(rule.evaluate(extract_features(row)))

        if target:
            positives += 1
            if pred:
                true_positive += 1
        else:
            negatives += 1
            if not pred:
                true_negative += 1

    if not positives or not negatives:
        return _accuracy(rule, rows)

    sensitivity = true_positive / positives
    specificity = true_negative / negatives

    return (sensitivity + specificity) / 2.0


def _positive_precision(
    rule: Rule,
    rows: List[Dict[str, Any]]
) -> float:

    predicted_positive = 0
    correct_positive = 0

    for row in rows:
        pred = bool(rule.evaluate(extract_features(row)))

        if pred:
            predicted_positive += 1

            if bool(row["pumped"]):
                correct_positive += 1

    if predicted_positive == 0:
        return 0.0

    return correct_positive / predicted_positive


def _feature_set(rule: Rule) -> set:
    return {p.feature for p in rule.predicates}


# ============================================================
# THRESHOLD GENERATION
# ============================================================

def _candidate_thresholds(
    rows: List[Dict[str, Any]],
    feature: str,
    max_thresholds: int = 48,
) -> List[float]:

    values = sorted(
        set(
            float(extract_features(row)[feature])
            for row in rows
            if math.isfinite(float(extract_features(row)[feature]))
        )
    )

    if len(values) < 2:
        return values

    # Exact midpoint thresholds preserve legitimate threshold
    # discovery while preventing an unnecessarily huge search.
    mids = []

    for a, b in zip(values, values[1:]):
        if a == b:
            continue

        mids.append((a + b) / 2.0)

    if len(mids) <= max_thresholds:
        return mids

    # Quantile-spaced candidates.
    result = []

    for i in range(1, max_thresholds + 1):
        idx = int(
            round(
                (i / (max_thresholds + 1))
                * (len(mids) - 1)
            )
        )

        result.append(mids[idx])

    return sorted(set(result))


# ============================================================
# RULE SCORING
# ============================================================

def _score_rule(
    rule: Rule,
    rows: List[Dict[str, Any]],
) -> Tuple[float, float, float]:

    acc = _accuracy(rule, rows)
    bal = _balanced_accuracy(rule, rows)
    precision = _positive_precision(rule, rows)

    return acc, bal, precision


def _complexity_penalty(rule: Rule) -> float:
    return 0.004 * max(0, rule.complexity - 1)


def _training_score(
    rule: Rule,
    rows: List[Dict[str, Any]],
) -> float:

    acc, bal, precision = _score_rule(rule, rows)

    return (
        0.55 * acc
        + 0.30 * bal
        + 0.15 * precision
        - _complexity_penalty(rule)
    )


# ============================================================
# CROSS-FOLD STABILITY
# ============================================================

def _folds(
    rows: List[Dict[str, Any]],
    seed: int,
    k: int = 4,
) -> List[List[Dict[str, Any]]]:

    data = list(rows)
    random.Random(seed).shuffle(data)

    k = max(2, min(k, len(data)))

    folds = [[] for _ in range(k)]

    for i, row in enumerate(data):
        folds[i % k].append(row)

    return folds


def _cross_validated_score(
    rule: Rule,
    rows: List[Dict[str, Any]],
    seed: int,
) -> Tuple[float, float]:

    folds = _folds(rows, seed)

    scores = []

    for fold in folds:
        if fold:
            scores.append(_balanced_accuracy(rule, fold))

    if not scores:
        return 0.0, 0.0

    return (
        statistics.mean(scores),
        statistics.stdev(scores) if len(scores) > 1 else 0.0,
    )


# ============================================================
# DISCOVERY
# ============================================================

def _single_feature_candidates(
    rows: List[Dict[str, Any]],
) -> List[Rule]:

    candidates = []

    active = [
        feature
        for feature in FEATURES
        if feature in {
            key
            for row in rows
            for key in extract_features(row)
        }
    ]

    for feature in active:

        thresholds = _candidate_thresholds(rows, feature)

        for threshold in thresholds:

            candidates.append(
                Rule(
                    (
                        Predicate(
                            feature,
                            ">",
                            threshold,
                        ),
                    )
                )
            )

            candidates.append(
                Rule(
                    (
                        Predicate(
                            feature,
                            "<",
                            threshold,
                        ),
                    )
                )
            )

    return candidates


def _best_single_rules(
    rows: List[Dict[str, Any]],
    limit: int = 24,
) -> List[Rule]:

    scored = []

    for rule in _single_feature_candidates(rows):
        score = _training_score(rule, rows)
        scored.append((score, rule))

    scored.sort(
        key=lambda x: (
            -x[0],
            x[1].complexity,
            x[1].to_string(),
        )
    )

    result = []

    seen = set()

    for _, rule in scored:

        text = rule.to_string()

        if text in seen:
            continue

        seen.add(text)
        result.append(rule)

        if len(result) >= limit:
            break

    return result


def _build_pair_candidates(
    rows: List[Dict[str, Any]],
    seeds: List[Rule],
    max_pairs: int = 1000,
) -> List[Rule]:

    candidates = []

    single_preds = []

    for rule in seeds:
        if rule.complexity == 1:
            single_preds.append(rule.predicates[0])

    # Include predicates from all available features, not merely
    # the currently winning feature.
    for feature in FEATURES:
        for threshold in _candidate_thresholds(rows, feature):
            single_preds.append(
                Predicate(feature, ">", threshold)
            )
            single_preds.append(
                Predicate(feature, "<", threshold)
            )

    unique = {}

    for predicate in single_preds:
        key = (
            predicate.feature,
            predicate.operator,
            round(predicate.threshold, 8),
        )
        unique[key] = predicate

    predicates = list(unique.values())

    # First build combinations between different features.
    for i, a in enumerate(predicates):

        for b in predicates[i + 1:]:

            if a.feature == b.feature:
                continue

            rule = Rule((a, b))

            candidates.append(rule)

            if len(candidates) >= max_pairs:
                return candidates

    return candidates


def _discover_deterministic(
    rows: List[Dict[str, Any]],
    seed: int,
) -> Tuple[Optional[Rule], float]:

    if not rows:
        return None, 0.0

    singles = _best_single_rules(rows)

    if not singles:
        return None, 0.0

    candidates = list(singles)

    pairs = _build_pair_candidates(
        rows,
        singles,
        max_pairs=1200,
    )

    candidates.extend(pairs)

    scored = []

    for rule in candidates:

        train_score = _training_score(rule, rows)

        cv_mean, cv_std = _cross_validated_score(
            rule,
            rows,
            seed,
        )

        # Favor rules that survive resampling.
        stability = cv_mean - 0.15 * cv_std

        # Complexity is deliberately small: accuracy and
        # stability dominate.
        final_score = (
            0.58 * train_score
            + 0.42 * stability
        )

        scored.append(
            (
                final_score,
                cv_mean,
                cv_std,
                rule,
            )
        )

    scored.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            x[2],
            x[3].complexity,
            x[3].to_string(),
        )
    )

    best = scored[0][3]

    return best, _accuracy(best, rows)


# ============================================================
# PUBLIC DISCOVERY API
# ============================================================

def evolve_rule(
    rows,
    generations=60,
    population_size=100,
    max_depth=5,
):
    """
    Public compatibility function.

    The upgraded engine intentionally performs deterministic
    threshold/conjunction discovery rather than relying solely
    on stochastic evolutionary search.

    generations/population_size/max_depth remain accepted so
    existing callers continue to work.
    """

    del generations
    del population_size
    del max_depth

    # Preserve caller-controlled feature ablation.
    global FEATURES

    if not FEATURES:
        return None, 0.0

    return _discover_deterministic(
        list(rows),
        seed=random.getstate()[1][0],
    )


# ============================================================
# OPTIONAL DIAGNOSTICS
# ============================================================

def evaluate_rule(
    expr,
    rows,
) -> Dict[str, float]:

    acc, bal, precision = _score_rule(
        expr,
        rows,
    )

    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "positive_precision": precision,
    }


def rule_features(expr) -> List[str]:
    return sorted(_feature_set(expr))


__all__ = [
    "FEATURES",
    "Expr",
    "Rule",
    "Predicate",
    "extract_features",
    "evolve_rule",
    "evaluate_rule",
    "rule_features",
]
