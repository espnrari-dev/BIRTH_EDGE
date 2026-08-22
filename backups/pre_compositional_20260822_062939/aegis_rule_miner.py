#!/usr/bin/env python3

"""
BIRTH_EDGE / AEGIS RULE MINER
SIGNIFICANCE-GATED DISCOVERY ENGINE

Architecture preserved:
    feature extraction
        ->
    threshold generation
        ->
    predicate generation
        ->
    single-rule search
        ->
    two-feature conjunction search
        ->
    candidate scoring
        ->
    balanced-performance gate

Upgrade:
    whole-search-space permutation significance gate

Purpose:
    Prevent the miner from declaring structure merely because
    random labels happen to produce a strong-looking rule.

The permutation test uses the maximum score found across the
ENTIRE rule-search space for each shuffled-label realization.
This controls for the "best rule wins by chance" problem.

The discovered rule itself is NEVER selected using shuffled labels.
Permutations are used only to determine whether the observed
best-rule score is exceptional relative to chance.

Existing public interfaces are preserved.
"""

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# CONFIGURATION
# ============================================================

FEATURES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]

# Existing discovery gate.
BALANCED_MIN = 0.55

# New significance gate.
#
# 39 permutations gives an exact-ish 0.025 minimum resolution,
# while 59 gives ~0.0167 and 99 gives ~0.01.
#
# 99 is deliberately used here because the architecture is
# small enough for this search to remain practical.
PERMUTATIONS = 99

# Reject a discovered rule unless its score is above the
# 95th percentile of maximum scores obtained under shuffled
# labels.
SIGNIFICANCE_ALPHA = 0.05

# Require the observed score to beat the null distribution.
MIN_NULL_MARGIN = 0.0

# Preserve the original support and complexity behavior.
COMPLEXITY_PENALTY = 0.012


# ============================================================
# BASIC DATA STRUCTURES
# ============================================================

@dataclass(frozen=True)
class Predicate:
    feature: str
    operator: str
    threshold: float

    def evaluate(self, values):
        x = float(values.get(self.feature, 0.0))

        if self.operator == ">":
            return x > self.threshold

        return x < self.threshold

    def to_string(self):
        return f"({self.feature} {self.operator} {self.threshold:.6g})"


@dataclass(frozen=True)
class Rule:
    predicates: Tuple[Predicate, ...]

    def evaluate(self, values):
        return all(
            p.evaluate(values)
            for p in self.predicates
        )

    def to_string(self):
        if len(self.predicates) == 1:
            return self.predicates[0].to_string()

        return "(" + " AND ".join(
            p.to_string()
            for p in self.predicates
        ) + ")"

    @property
    def complexity(self):
        return len(self.predicates)


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_features(row):
    out = {}

    for f in FEATURES:

        if f == "liquidity_usd":
            v = row.get(
                "initial_liquidity_usd",
                row.get("liquidity_usd", 0.0),
            )
        else:
            v = row.get(f, 0.0)

        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0

        out[f] = (
            v
            if math.isfinite(v)
            else 0.0
        )

    return out


def rule_features(expr):
    if expr is None:
        return []

    return sorted({
        p.feature
        for p in expr.predicates
    })


# ============================================================
# METRICS
# ============================================================

def _metrics(pred, labels):
    n = len(labels)

    if not n:
        return 0.0, 0.0, 0.0

    tp = tn = fp = fn = 0

    for p, y in zip(pred, labels):

        if y:

            if p:
                tp += 1
            else:
                fn += 1

        else:

            if p:
                fp += 1
            else:
                tn += 1

    acc = (tp + tn) / n

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

    bal = (tpr + tnr) / 2.0

    prec = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    return acc, bal, prec


def _support(pred):
    if not pred:
        return 0.0

    return sum(bool(x) for x in pred) / len(pred)


# ============================================================
# THRESHOLD GENERATION
# ============================================================

def _thresholds(values, limit=20):

    vals = sorted(set(values))

    if len(vals) < 2:
        return []

    mids = [
        (a + b) / 2.0
        for a, b in zip(vals, vals[1:])
        if a != b
    ]

    if len(mids) <= limit:
        return mids

    return [
        mids[
            round(
                i * (len(mids) - 1)
                / (limit - 1)
            )
        ]
        for i in range(limit)
    ]


# ============================================================
# MATRIX
# ============================================================

def _matrix(rows, labels_override=None):

    names = list(FEATURES)

    cols = {
        f: []
        for f in names
    }

    labels = []

    for row in rows:

        x = extract_features(row)

        for f in names:
            cols[f].append(x[f])

        if labels_override is not None:
            labels.append(
                bool(labels_override[len(labels)])
            )
        else:
            labels.append(
                bool(row["pumped"])
            )

    return names, cols, labels


# ============================================================
# PREDICATE GENERATION
# ============================================================

def _predicates(cols, active):

    out = []

    for f in active:

        for t in _thresholds(cols[f]):

            for op in (">", "<"):

                if op == ">":
                    p = tuple(
                        x > t
                        for x in cols[f]
                    )
                else:
                    p = tuple(
                        x < t
                        for x in cols[f]
                    )

                out.append(
                    (
                        Predicate(
                            f,
                            op,
                            t,
                        ),
                        p,
                    )
                )

    return out


# ============================================================
# CANDIDATE SCORING
# ============================================================

def _candidate_score(
    pred,
    labels,
    complexity,
):

    acc, bal, prec = _metrics(
        pred,
        labels,
    )

    support = _support(pred)

    penalty = (
        COMPLEXITY_PENALTY
        * max(0, complexity - 1)
    )

    if support < 0.05:

        penalty += (
            (0.05 - support)
            * 2.0
        )

    score = (
        0.45 * acc
        + 0.40 * bal
        + 0.15 * prec
        - penalty
    )

    return score, acc, bal


# ============================================================
# CORE SEARCH
# ============================================================

def _discover_core(
    rows,
    labels,
):

    if len(rows) < 20 or not FEATURES:
        return None, 0.0, 0.0

    names, cols, labels = _matrix(
        rows,
        labels_override=labels,
    )

    active = [
        f
        for f in names
        if len(set(cols[f])) >= 2
    ]

    if not active:
        return None, 0.0, 0.0

    singles = _predicates(
        cols,
        active,
    )

    ranked = []

    for pred_obj, pred in singles:

        score, acc, bal = _candidate_score(
            pred,
            labels,
            1,
        )

        ranked.append(
            (
                score,
                bal,
                acc,
                Rule((pred_obj,)),
                pred,
            )
        )

    ranked.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            x[3].to_string(),
        )
    )

    top = ranked[:24]

    candidates = list(top)

    # Preserve the original two-feature architecture.
    for i in range(len(top)):

        for j in range(i + 1, len(top)):

            r1 = top[i][3]
            r2 = top[j][3]

            if (
                r1.predicates[0].feature
                ==
                r2.predicates[0].feature
            ):
                continue

            pred1 = top[i][4]
            pred2 = top[j][4]

            pred = tuple(
                x and y
                for x, y in zip(
                    pred1,
                    pred2,
                )
            )

            rule = Rule(
                (
                    r1.predicates[0],
                    r2.predicates[0],
                )
            )

            score, acc, bal = _candidate_score(
                pred,
                labels,
                2,
            )

            candidates.append(
                (
                    score,
                    bal,
                    acc,
                    rule,
                    pred,
                )
            )

    candidates.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            -x[2],
            x[3].complexity,
            x[3].to_string(),
        )
    )

    if not candidates:
        return None, 0.0, 0.0

    score, bal, acc, best, _ = candidates[0]

    if bal < BALANCED_MIN:
        return None, bal, score

    return best, acc, score


# ============================================================
# PERMUTATION SIGNIFICANCE
# ============================================================

def _permutation_null_scores(
    rows,
    observed_labels,
    rng,
    permutations=PERMUTATIONS,
):

    null_scores = []

    labels = list(observed_labels)

    for _ in range(permutations):

        shuffled = list(labels)
        rng.shuffle(shuffled)

        _, _, best_score = _discover_core(
            rows,
            shuffled,
        )

        # Even when the balanced gate rejects the rule,
        # its raw maximum score is still useful as a
        # conservative null benchmark.
        #
        # Re-run without the gate only when necessary.
        if best_score is None:
            best_score = 0.0

        null_scores.append(
            float(best_score)
        )

    return null_scores


def _empirical_p_value(
    observed_score,
    null_scores,
):

    if not null_scores:
        return 1.0

    extreme = sum(
        s >= observed_score
        for s in null_scores
    )

    # Add-one correction.
    return (
        extreme + 1.0
    ) / (
        len(null_scores) + 1.0
    )


def _quantile(values, q):

    if not values:
        return 1.0

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    pos = q * (len(values) - 1)

    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))

    if lo == hi:
        return values[lo]

    frac = pos - lo

    return (
        values[lo]
        * (1.0 - frac)
        +
        values[hi]
        * frac
    )


# ============================================================
# DISCOVERY
# ============================================================

def _discover(rows, seed):

    if len(rows) < 20:
        return None, 0.0

    observed_labels = [
        bool(row["pumped"])
        for row in rows
    ]

    # First perform the actual discovery.
    best, acc, observed_score = _discover_core(
        rows,
        observed_labels,
    )

    if best is None:
        return None, acc

    # Deterministic significance RNG.
    #
    # This uses the supplied discovery seed rather than
    # contaminating the caller's global random state.
    rng = random.Random(
        int(seed) & 0xFFFFFFFF
    )

    null_scores = _permutation_null_scores(
        rows,
        observed_labels,
        rng,
        permutations=PERMUTATIONS,
    )

    p_value = _empirical_p_value(
        observed_score,
        null_scores,
    )

    null_threshold = _quantile(
        null_scores,
        1.0 - SIGNIFICANCE_ALPHA,
    )

    # The rule must beat the strongest 95%-tail
    # null benchmark.
    significant = (
        p_value <= SIGNIFICANCE_ALPHA
        and
        observed_score
        >
        null_threshold + MIN_NULL_MARGIN
    )

    if not significant:
        return None, 0.0

    return best, acc


# ============================================================
# PUBLIC API
# ============================================================

def evolve_rule(
    rows,
    generations=60,
    population_size=100,
    max_depth=5,
):

    # Preserve the original public signature.
    del generations
    del population_size
    del max_depth

    data = list(rows)

    state = random.getstate()

    try:
        seed = state[1][0]
    except Exception:
        seed = 0

    return _discover(
        data,
        seed,
    )


def evaluate_rule(expr, rows):

    labels = [
        bool(r["pumped"])
        for r in rows
    ]

    pred = [
        bool(
            expr.evaluate(
                extract_features(r)
            )
        )
        for r in rows
    ]

    acc, bal, precision = _metrics(
        pred,
        labels,
    )

    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "positive_precision": precision,
    }


# ============================================================
# OPTIONAL DIAGNOSTIC API
# ============================================================

def significance_report(
    rows,
    permutations=PERMUTATIONS,
    seed=0,
):

    observed_labels = [
        bool(row["pumped"])
        for row in rows
    ]

    best, acc, observed_score = _discover_core(
        rows,
        observed_labels,
    )

    if best is None:
        return {
            "discovered": False,
            "rule": None,
            "accuracy": acc,
            "observed_score": observed_score,
            "p_value": 1.0,
            "null_threshold_95": None,
            "null_mean": None,
            "permutations": permutations,
        }

    rng = random.Random(
        int(seed) & 0xFFFFFFFF
    )

    null_scores = _permutation_null_scores(
        rows,
        observed_labels,
        rng,
        permutations=permutations,
    )

    p = _empirical_p_value(
        observed_score,
        null_scores,
    )

    q95 = _quantile(
        null_scores,
        0.95,
    )

    return {
        "discovered": (
            p <= SIGNIFICANCE_ALPHA
            and observed_score > q95
        ),
        "rule": best.to_string(),
        "features": rule_features(best),
        "accuracy": acc,
        "observed_score": observed_score,
        "p_value": p,
        "null_threshold_95": q95,
        "null_mean": (
            statistics.mean(null_scores)
            if null_scores
            else None
        ),
        "null_max": (
            max(null_scores)
            if null_scores
            else None
        ),
        "permutations": permutations,
        "alpha": SIGNIFICANCE_ALPHA,
    }


# ============================================================
# MODULE SELF-CHECK
# ============================================================

if __name__ == "__main__":

    print("=" * 72)
    print("BIRTH_EDGE SIGNIFICANCE-GATED RULE MINER")
    print("=" * 72)
    print("FEATURES:", FEATURES)
    print("BALANCED_MIN:", BALANCED_MIN)
    print("PERMUTATIONS:", PERMUTATIONS)
    print("SIGNIFICANCE_ALPHA:", SIGNIFICANCE_ALPHA)
    print()
    print("Public API:")
    print("  evolve_rule")
    print("  evaluate_rule")
    print("  extract_features")
    print("  rule_features")
    print("  Rule")
    print("  Predicate")
    print("  significance_report")
    print("=" * 72)
