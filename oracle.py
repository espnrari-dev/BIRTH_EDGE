#!/usr/bin/env python3
"""
========================================================================
BIRTH_EDGE ORACLE
========================================================================

Purpose
-------
This module is the explicit ground-truth reference for BIRTH_EDGE.

The Oracle is NOT the discovery system.

The Oracle defines the hidden rule / ground truth that a discovery engine
is expected to recover from observations.

Architecture
------------

    REAL / GENERATED OBSERVATION
                |
                v
        +---------------+
        |    ORACLE     |
        | ground truth  |
        +---------------+
                |
                v
        expected outcome

                vs.

        +---------------+
        | BIRTH_EDGE    |
        |    MINER      |
        +---------------+
                |
                v
        discovered rule

The two must remain separate.

The miner must never import the Oracle's implementation in order to
discover the rule. The Oracle exists for evaluation.

========================================================================
DESIGN PRINCIPLES
========================================================================

1. Deterministic
   Same observation -> same truth.

2. Explicit
   The hidden rule is readable and inspectable.

3. Stateless
   No hidden mutable state.

4. No network dependency.

5. No random behavior.

6. No synthetic market prices.

7. No trading execution.

8. Supports exact labels as well as continuous scores.

9. Supports counterfactual evaluation.

10. Supports independent test suites.

11. Does not modify the miner.

12. Does not leak its rule through feature names or miner APIs.

========================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


# ======================================================================
# ORACLE SPECIFICATION
# ======================================================================

@dataclass(frozen=True)
class OracleSpec:
    """
    Human-readable description of the hidden ground truth.

    These values describe the rule itself and are useful when reporting
    experiments. They are deliberately kept separate from the Oracle
    implementation.
    """

    name: str
    version: str
    task: str

    positive_threshold: float
    strong_threshold: float

    required_features: Tuple[str, ...]


ORACLE_SPEC = OracleSpec(
    name="BIRTH_EDGE_GROUND_TRUTH",
    version="1.0",
    task="deterministic_binary_and_strength_classification",
    positive_threshold=7.0,
    strong_threshold=10.0,
    required_features=(
        "holder_score",
        "liquidity",
    ),
)


# ======================================================================
# INPUT NORMALIZATION
# ======================================================================

def _number(
    observation: Mapping[str, Any],
    key: str,
    default: float = 0.0,
) -> float:
    """
    Safely extract a numeric feature.

    Missing/non-numeric values are treated as the supplied default.

    This function performs no inference.
    """

    value = observation.get(key, default)

    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


# ======================================================================
# CORE GROUND TRUTH
# ======================================================================

def oracle_score(observation: Mapping[str, Any]) -> float:
    """
    Return the hidden continuous ground-truth score.

    Ground truth:

        score = holder_score + liquidity_component

    The liquidity component is normalized so that the score remains
    interpretable across ordinary liquidity magnitudes.

    IMPORTANT:
    This is the reference implementation.

    The discovery engine should NOT call this function while learning.
    It should only be used by evaluation code after a prediction has been
    produced.
    """

    holder_score = _number(observation, "holder_score")
    liquidity = _number(observation, "liquidity")

    # Normalize liquidity into a bounded contribution.
    #
    # The transformation is deterministic and monotonic.
    #
    # liquidity <= 0 -> 0 contribution
    # liquidity >= 30000 -> 3 contribution
    #
    # Between those values the contribution is linear.

    liquidity_component = max(0.0, min(liquidity / 10000.0, 3.0))

    return holder_score + liquidity_component


def oracle_label(observation: Mapping[str, Any]) -> int:
    """
    Binary ground-truth label.

        1 = positive / qualifying
        0 = negative / non-qualifying

    The threshold is defined by ORACLE_SPEC.
    """

    score = oracle_score(observation)

    return int(score > ORACLE_SPEC.positive_threshold)


def oracle_class(observation: Mapping[str, Any]) -> str:
    """
    Three-level ground-truth classification.

        NEGATIVE
        POSITIVE
        STRONG

    This is useful for testing whether a miner can recover more than
    merely a binary boundary.
    """

    score = oracle_score(observation)

    if score > ORACLE_SPEC.strong_threshold:
        return "STRONG"

    if score > ORACLE_SPEC.positive_threshold:
        return "POSITIVE"

    return "NEGATIVE"


# ======================================================================
# DECISION / EXPLANATION
# ======================================================================

def oracle_decision(observation: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Return a complete ground-truth decision record.

    This is the preferred interface for evaluation code.
    """

    holder_score = _number(observation, "holder_score")
    liquidity = _number(observation, "liquidity")

    score = oracle_score(observation)
    label = int(score > ORACLE_SPEC.positive_threshold)
    classification = oracle_class(observation)

    return {
        "oracle": ORACLE_SPEC.name,
        "oracle_version": ORACLE_SPEC.version,

        "holder_score": holder_score,
        "liquidity": liquidity,

        "oracle_score": score,
        "oracle_label": label,
        "oracle_class": classification,

        "positive_threshold": ORACLE_SPEC.positive_threshold,
        "strong_threshold": ORACLE_SPEC.strong_threshold,

        "ground_truth": True,
    }


# ======================================================================
# COUNTERFACTUAL SUPPORT
# ======================================================================

def oracle_counterfactual(
    observation: Mapping[str, Any],
    *,
    holder_score: Optional[float] = None,
    liquidity: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Evaluate the same observation after changing one or more variables.

    This is important for causal-resilience testing.

    Example:

        original = {
            "holder_score": 8,
            "liquidity": 10000,
        }

        oracle_counterfactual(
            original,
            holder_score=4,
        )

    The returned result shows whether changing the feature actually
    changes the ground-truth outcome.

    No randomization occurs.
    """

    modified = dict(observation)

    if holder_score is not None:
        modified["holder_score"] = float(holder_score)

    if liquidity is not None:
        modified["liquidity"] = float(liquidity)

    result = oracle_decision(modified)

    result["counterfactual"] = True
    result["original_observation"] = dict(observation)
    result["modified_observation"] = modified

    return result


# ======================================================================
# FEATURE INTERVENTIONS
# ======================================================================

def intervene(
    observation: Mapping[str, Any],
    feature: str,
    value: float,
) -> Dict[str, Any]:
    """
    Generic deterministic intervention.

    Used by robustness and causal tests.

    The Oracle itself remains unchanged; only the supplied observation
    is modified.
    """

    modified = dict(observation)
    modified[feature] = float(value)

    return oracle_decision(modified)


# ======================================================================
# BOUNDARY ANALYSIS
# ======================================================================

def boundary_distance(observation: Mapping[str, Any]) -> float:
    """
    Signed distance from the binary decision boundary.

        > 0  -> positive side
        < 0  -> negative side
        = 0  -> exact boundary

    This is useful for margin and near-boundary tests.
    """

    return (
        oracle_score(observation)
        - ORACLE_SPEC.positive_threshold
    )


def is_boundary_case(
    observation: Mapping[str, Any],
    tolerance: float = 1e-9,
) -> bool:
    """
    Return True when the observation lies essentially on the
    classification boundary.
    """

    return abs(boundary_distance(observation)) <= tolerance


# ======================================================================
# MONOTONICITY CHECKS
# ======================================================================

def holder_monotonicity_check(
    base_observation: Mapping[str, Any],
    lower: float,
    upper: float,
) -> Dict[str, Any]:
    """
    Verify the Oracle's expected monotonic relationship with
    holder_score.

    Increasing holder_score cannot decrease oracle_score.
    """

    if upper < lower:
        lower, upper = upper, lower

    low = dict(base_observation)
    high = dict(base_observation)

    low["holder_score"] = lower
    high["holder_score"] = upper

    low_score = oracle_score(low)
    high_score = oracle_score(high)

    return {
        "feature": "holder_score",
        "lower_value": lower,
        "upper_value": upper,
        "lower_score": low_score,
        "upper_score": high_score,
        "monotonic": high_score >= low_score,
    }


def liquidity_monotonicity_check(
    base_observation: Mapping[str, Any],
    lower: float,
    upper: float,
) -> Dict[str, Any]:
    """
    Verify the Oracle's expected monotonic relationship with liquidity.
    """

    if upper < lower:
        lower, upper = upper, lower

    low = dict(base_observation)
    high = dict(base_observation)

    low["liquidity"] = lower
    high["liquidity"] = upper

    low_score = oracle_score(low)
    high_score = oracle_score(high)

    return {
        "feature": "liquidity",
        "lower_value": lower,
        "upper_value": upper,
        "lower_score": low_score,
        "upper_score": high_score,
        "monotonic": high_score >= low_score,
    }


# ======================================================================
# BATCH EVALUATION
# ======================================================================

def evaluate(
    observations: Sequence[Mapping[str, Any]],
) -> list[Dict[str, Any]]:
    """
    Evaluate many observations against the ground truth.
    """

    return [
        oracle_decision(observation)
        for observation in observations
    ]


# ======================================================================
# PREDICTION COMPARISON
# ======================================================================

def compare_prediction(
    observation: Mapping[str, Any],
    predicted_label: Any,
) -> Dict[str, Any]:
    """
    Compare an external miner prediction with the Oracle.

    predicted_label may be bool, int, or a numeric/string value that can
    reasonably be interpreted as 0 or 1.
    """

    truth = oracle_label(observation)

    try:
        prediction = int(predicted_label)
    except (TypeError, ValueError):
        prediction = -1

    correct = prediction == truth

    return {
        "prediction": prediction,
        "oracle_label": truth,
        "correct": correct,
        "oracle_score": oracle_score(observation),
        "boundary_distance": boundary_distance(observation),
    }


# ======================================================================
# METRICS
# ======================================================================

def accuracy(
    observations: Sequence[Mapping[str, Any]],
    predictions: Sequence[Any],
) -> float:
    """
    Exact binary accuracy against Oracle labels.
    """

    if len(observations) != len(predictions):
        raise ValueError(
            "observations and predictions must have identical length"
        )

    if not observations:
        return 0.0

    correct = 0

    for observation, prediction in zip(observations, predictions):
        try:
            predicted = int(prediction)
        except (TypeError, ValueError):
            predicted = -1

        if predicted == oracle_label(observation):
            correct += 1

    return correct / len(observations)


def confusion_matrix(
    observations: Sequence[Mapping[str, Any]],
    predictions: Sequence[Any],
) -> Dict[str, int]:
    """
    Binary confusion matrix against the Oracle.

    Keys:

        TP
        TN
        FP
        FN
    """

    if len(observations) != len(predictions):
        raise ValueError(
            "observations and predictions must have identical length"
        )

    tp = tn = fp = fn = 0

    for observation, prediction in zip(observations, predictions):

        truth = oracle_label(observation)

        try:
            pred = int(prediction)
        except (TypeError, ValueError):
            pred = -1

        if truth == 1 and pred == 1:
            tp += 1
        elif truth == 0 and pred == 0:
            tn += 1
        elif truth == 0 and pred == 1:
            fp += 1
        elif truth == 1 and pred == 0:
            fn += 1

    return {
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
    }


# ======================================================================
# SELF-TEST
# ======================================================================

def self_test() -> None:
    """
    Deterministic integrity test for the Oracle itself.

    These tests verify the reference implementation rather than
    pretending the Oracle is a discovery result.
    """

    # --------------------------------------------------------------
    # Basic negative
    # --------------------------------------------------------------

    obs = {
        "holder_score": 2.0,
        "liquidity": 0.0,
    }

    assert oracle_score(obs) == 2.0
    assert oracle_label(obs) == 0
    assert oracle_class(obs) == "NEGATIVE"

    # --------------------------------------------------------------
    # Exact positive-side case
    # --------------------------------------------------------------

    obs = {
        "holder_score": 7.1,
        "liquidity": 0.0,
    }

    assert oracle_label(obs) == 1
    assert oracle_class(obs) == "POSITIVE"

    # --------------------------------------------------------------
    # Strong case
    # --------------------------------------------------------------

    obs = {
        "holder_score": 10.0,
        "liquidity": 10000.0,
    }

    assert oracle_score(obs) == 11.0
    assert oracle_label(obs) == 1
    assert oracle_class(obs) == "STRONG"

    # --------------------------------------------------------------
    # Liquidity contribution
    # --------------------------------------------------------------

    obs = {
        "holder_score": 5.0,
        "liquidity": 20000.0,
    }

    assert oracle_score(obs) == 7.0
    assert oracle_label(obs) == 0

    # --------------------------------------------------------------
    # Counterfactual
    # --------------------------------------------------------------

    original = {
        "holder_score": 5.0,
        "liquidity": 20000.0,
    }

    changed = oracle_counterfactual(
        original,
        holder_score=8.0,
    )

    assert changed["oracle_label"] == 1
    assert changed["counterfactual"] is True

    # --------------------------------------------------------------
    # Boundary
    # --------------------------------------------------------------

    boundary = {
        "holder_score": 7.0,
        "liquidity": 0.0,
    }

    assert boundary_distance(boundary) == 0.0
    assert is_boundary_case(boundary)

    # --------------------------------------------------------------
    # Monotonicity
    # --------------------------------------------------------------

    base = {
        "holder_score": 5.0,
        "liquidity": 10000.0,
    }

    holder_test = holder_monotonicity_check(
        base,
        2.0,
        8.0,
    )

    liquidity_test = liquidity_monotonicity_check(
        base,
        0.0,
        30000.0,
    )

    assert holder_test["monotonic"] is True
    assert liquidity_test["monotonic"] is True

    print("ORACLE SELF-TEST: PASS")
    print()
    print("Oracle:", ORACLE_SPEC.name)
    print("Version:", ORACLE_SPEC.version)
    print("Task:", ORACLE_SPEC.task)
    print("Positive threshold:", ORACLE_SPEC.positive_threshold)
    print("Strong threshold:", ORACLE_SPEC.strong_threshold)


# ======================================================================
# CLI
# ======================================================================

if __name__ == "__main__":
    self_test()
