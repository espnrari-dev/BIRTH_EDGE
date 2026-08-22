#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

cd ~/BIRTH_EDGE

cp -f aegis_rule_miner.py aegis_rule_miner.pre_causal_upgrade.py

cat > aegis_rule_miner.py <<'PY'
#!/usr/bin/env python3
"""
AEGIS RULE MINER — CAUSAL-RESILIENCE UPGRADE

Compatibility layer over the previous miner.

The original evolutionary miner remains intact in:
    aegis_rule_miner.pre_causal_upgrade.py

This layer improves selection by evaluating multiple independently
discovered candidates and preferring structures that demonstrate:

1. Cross-validation generalization
2. Bootstrap stability
3. Feature necessity
4. Multi-feature interaction/synergy
5. Resistance to correlated single-feature proxies
6. Resistance to feature perturbation
7. Simplicity

No feature is privileged by name.
No planted ground-truth variable is referenced.
No synthetic labels are introduced.
"""

import importlib.util
import math
import random
import statistics
import copy


_CORE_PATH = __file__.replace(
    "aegis_rule_miner.py",
    "aegis_rule_miner.pre_causal_upgrade.py"
)

_spec = importlib.util.spec_from_file_location(
    "_aegis_core",
    _CORE_PATH
)

_core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_core)


# Preserve the original public API.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


CORE_EVOLVE_RULE = _core.evolve_rule
CORE_FEATURES = list(getattr(_core, "FEATURES", []))


# ---------------------------------------------------------------------
# SAFE HELPERS
# ---------------------------------------------------------------------

def _features():
    return list(globals().get("FEATURES", CORE_FEATURES))


def _evaluate(expr, row):
    try:
        return bool(
            expr.evaluate(
                extract_features(row)
            )
        )
    except Exception:
        return False


def _accuracy(expr, rows):
    if expr is None or not rows:
        return 0.0

    correct = 0

    for row in rows:
        if _evaluate(expr, row) == bool(row["pumped"]):
            correct += 1

    return correct / len(rows)


def _safe_mean(values):
    return (
        statistics.mean(values)
        if values
        else 0.0
    )


def _stdev(values):
    if len(values) < 2:
        return 0.0
    return statistics.stdev(values)


def _bootstrap_stability(expr, rows, seed, rounds=8):
    if expr is None or len(rows) < 20:
        return 0.0

    rng = random.Random(seed)
    scores = []

    for _ in range(rounds):
        sample = [
            rows[rng.randrange(len(rows))]
            for _ in range(len(rows))
        ]
        scores.append(_accuracy(expr, sample))

    if not scores:
        return 0.0

    return max(
        0.0,
        1.0 - min(1.0, _stdev(scores) * 4.0)
    )


def _cv_score(expr, rows, seed, folds=5):
    if expr is None or len(rows) < folds:
        return 0.0

    data = list(rows)
    random.Random(seed).shuffle(data)

    fold_size = max(1, len(data) // folds)
    scores = []

    for i in range(folds):
        start = i * fold_size
        end = (
            len(data)
            if i == folds - 1
            else min(len(data), start + fold_size)
        )

        fold = data[start:end]

        if fold:
            scores.append(
                _accuracy(expr, fold)
            )

    return _safe_mean(scores)


def _feature_presence(text, feature):
    return feature in text


def _rule_features(text):
    return [
        f
        for f in _features()
        if _feature_presence(text, f)
    ]


def _single_feature_candidate(rows, feature, seed):
    original = list(_features())

    try:
        FEATURES[:] = [feature]

        expr, acc = CORE_EVOLVE_RULE(
            rows,
            generations=45,
            population_size=80,
            max_depth=3
        )

        if expr is None:
            return None, 0.0, ""

        return expr, acc, expr.to_string()

    except Exception:
        return None, 0.0, ""

    finally:
        FEATURES[:] = original


def _pair_candidate(rows, pair, seed):
    original = list(_features())

    try:
        FEATURES[:] = list(pair)

        random.seed(seed)

        expr, acc = CORE_EVOLVE_RULE(
            rows,
            generations=55,
            population_size=90,
            max_depth=4
        )

        if expr is None:
            return None, 0.0, ""

        return expr, acc, expr.to_string()

    except Exception:
        return None, 0.0, ""

    finally:
        FEATURES[:] = original


def _necessity_score(expr, rows, used_features, seed):
    """
    Measures whether the discovered rule actually requires its
    individual components.

    A feature receives credit when removing/neutralizing it causes
    predictive degradation.

    This is deliberately generic and does not know which variables
    generated the data.
    """

    if expr is None or len(used_features) < 2:
        return 0.0

    base = _accuracy(expr, rows)

    if base <= 0:
        return 0.0

    rng = random.Random(seed)
    losses = []

    for feature in used_features:
        altered = []

        values = []

        for row in rows:
            try:
                values.append(
                    extract_features(row).get(feature)
                )
            except Exception:
                values.append(None)

        valid = [
            v for v in values
            if isinstance(v, (int, float))
            and math.isfinite(float(v))
        ]

        if not valid:
            continue

        replacement = statistics.median(valid)

        for row in rows:
            r = dict(row)

            if feature == "liquidity_usd":
                r["initial_liquidity_usd"] = replacement

            elif feature in r:
                r[feature] = replacement

            altered.append(r)

        altered_score = _accuracy(expr, altered)

        losses.append(
            max(0.0, base - altered_score)
        )

    if not losses:
        return 0.0

    return min(
        1.0,
        _safe_mean(losses) * 3.0
    )


def _interaction_score(
    expr,
    rows,
    used_features,
    seed
):
    """
    Rewards rules whose joint structure contains information
    unavailable from their strongest individual component.

    This is the central defense against an engineered single-feature
    proxy such as a composite score.
    """

    if expr is None or len(used_features) < 2:
        return 0.0

    joint = _cv_score(
        expr,
        rows,
        seed,
        folds=5
    )

    individual_scores = []

    for i, feature in enumerate(used_features):
        candidate, _, text = _single_feature_candidate(
            rows,
            feature,
            seed + 1000 + i
        )

        if candidate is not None:
            individual_scores.append(
                _cv_score(
                    candidate,
                    rows,
                    seed + 2000 + i,
                    folds=5
                )
            )

    if not individual_scores:
        return 0.0

    strongest_single = max(individual_scores)

    synergy = joint - strongest_single

    return max(
        0.0,
        min(1.0, synergy * 5.0)
    )


def _perturbation_stability(
    expr,
    rows,
    used_features,
    seed
):
    """
    Measures whether a rule remains stable when irrelevant feature
    values are perturbed.

    The outcome is never changed.
    """

    if expr is None:
        return 0.0

    if not rows:
        return 0.0

    rng = random.Random(seed)

    base_predictions = [
        _evaluate(expr, r)
        for r in rows
    ]

    changed = 0
    total = 0

    irrelevant = [
        f
        for f in _features()
        if f not in used_features
    ]

    if not irrelevant:
        return 1.0

    for row, original_prediction in zip(
        rows,
        base_predictions
    ):
        for feature in irrelevant:
            r = dict(row)

            if feature == "liquidity_usd":
                continue

            if feature not in r:
                continue

            value = r[feature]

            if isinstance(value, (int, float)):
                r[feature] = (
                    value
                    + rng.gauss(
                        0,
                        max(
                            1.0,
                            abs(float(value)) * 0.25
                        )
                    )
                )

                altered_prediction = _evaluate(
                    expr,
                    r
                )

                total += 1

                if altered_prediction != original_prediction:
                    changed += 1

    if total == 0:
        return 1.0

    return 1.0 - (
        changed / total
    )


def _complexity_score(text):
    if not text:
        return 0.0

    operators = (
        text.count("AND")
        + text.count("OR")
        + text.count("NOT")
        + text.count("(")
    )

    return 1.0 / (
        1.0 + operators * 0.08
    )


def _candidate_score(
    expr,
    text,
    rows,
    seed
):
    if expr is None:
        return -1e9

    used = _rule_features(text)

    cv = _cv_score(
        expr,
        rows,
        seed,
        folds=5
    )

    stability = _bootstrap_stability(
        expr,
        rows,
        seed + 10
    )

    necessity = _necessity_score(
        expr,
        rows,
        used,
        seed + 20
    )

    interaction = _interaction_score(
        expr,
        rows,
        used,
        seed + 30
    )

    perturbation = _perturbation_stability(
        expr,
        rows,
        used,
        seed + 40
    )

    complexity = _complexity_score(text)

    # Predictive performance remains dominant.
    #
    # The remaining terms prevent a highly predictive single
    # observational proxy from automatically defeating a stable
    # multi-feature mechanism.
    score = (
        cv * 0.55
        + stability * 0.10
        + necessity * 0.10
        + interaction * 0.15
        + perturbation * 0.07
        + complexity * 0.03
    )

    return score


# ---------------------------------------------------------------------
# UPGRADED EVOLUTIONARY SELECTION
# ---------------------------------------------------------------------

def evolve_rule(
    rows,
    generations=60,
    population_size=100,
    max_depth=5
):
    """
    Upgraded AEGIS discovery.

    The original evolutionary search is used as a candidate generator.
    Candidate selection is independently evaluated using robustness,
    necessity, interaction, and perturbation criteria.

    No feature receives special treatment by name.
    """

    if not rows:
        return None, 0.0

    available = list(_features())

    if not available:
        return CORE_EVOLVE_RULE(
            rows,
            generations=generations,
            population_size=population_size,
            max_depth=max_depth
        )

    candidates = []

    # ---------------------------------------------------------------
    # 1. Full-feature discovery
    # ---------------------------------------------------------------

    for offset in range(6):
        try:
            random.seed(
                offset + 1000003
            )

            expr, acc = CORE_EVOLVE_RULE(
                rows,
                generations=generations,
                population_size=population_size,
                max_depth=max_depth
            )

            if expr is not None:
                text = expr.to_string()

                candidates.append(
                    (
                        expr,
                        text,
                        acc,
                        "full"
                    )
                )

        except Exception:
            pass

    # ---------------------------------------------------------------
    # 2. Every single feature
    # ---------------------------------------------------------------

    for i, feature in enumerate(available):

        expr, acc, text = _single_feature_candidate(
            rows,
            feature,
            2000000 + i
        )

        if expr is not None:
            candidates.append(
                (
                    expr,
                    text,
                    acc,
                    "single"
                )
            )

    # ---------------------------------------------------------------
    # 3. Every pair of features
    #
    # This is deliberately generic. We do not know which pair is
    # causally useful; every available pair gets the same opportunity.
    # ---------------------------------------------------------------

    pair_index = 0

    for i in range(len(available)):
        for j in range(i + 1, len(available)):

            pair = (
                available[i],
                available[j]
            )

            expr, acc, text = _pair_candidate(
                rows,
                pair,
                3000000 + pair_index
            )

            pair_index += 1

            if expr is not None:
                candidates.append(
                    (
                        expr,
                        text,
                        acc,
                        "pair"
                    )
                )

    if not candidates:
        return CORE_EVOLVE_RULE(
            rows,
            generations=generations,
            population_size=population_size,
            max_depth=max_depth
        )

    # ---------------------------------------------------------------
    # 4. Deduplicate equivalent textual rules
    # ---------------------------------------------------------------

    unique = {}

    for expr, text, acc, origin in candidates:

        if not text:
            continue

        existing = unique.get(text)

        if existing is None:
            unique[text] = (
                expr,
                text,
                acc,
                origin
            )

        elif acc > existing[2]:
            unique[text] = (
                expr,
                text,
                acc,
                origin
            )

    candidates = list(
        unique.values()
    )

    # ---------------------------------------------------------------
    # 5. Robust independent selection
    # ---------------------------------------------------------------

    ranked = []

    for index, (
        expr,
        text,
        acc,
        origin
    ) in enumerate(candidates):

        score = _candidate_score(
            expr,
            text,
            rows,
            5000000 + index
        )

        ranked.append(
            (
                score,
                acc,
                expr,
                text,
                origin
            )
        )

    ranked.sort(
        key=lambda x: (
            x[0],
            x[1],
            -len(x[3])
        ),
        reverse=True
    )

    best_score, best_acc, best_expr, best_text, best_origin = (
        ranked[0]
    )

    return best_expr, best_acc


# Preserve feature object identity used by callers.
FEATURES = getattr(
    _core,
    "FEATURES",
    CORE_FEATURES
)


__all__ = [
    name
    for name in globals()
    if not name.startswith("_")
]
PY

python -m py_compile aegis_rule_miner.py

python -u full_novelty_gauntlet.py

