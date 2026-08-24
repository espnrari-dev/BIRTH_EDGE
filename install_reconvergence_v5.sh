#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

cd "$HOME/BIRTH_EDGE"

mkdir -p logs backups

TS="$(date +%Y%m%d_%H%M%S)"

for f in \
    data/ml_reflection.json \
    data/reflection_reconciliation_audit.json
do
    if [ -f "$f" ]; then
        cp "$f" "backups/$(basename "$f").${TS}.v5_readonly.bak"
    fi
done

cat > reconvergence_v5.py <<'PY'
#!/usr/bin/env python3
"""
BIRTH_EDGE RECONVERGENCE V5
HISTORICAL DIVERGENCE GAUNTLET

Purpose
-------
Determine whether the V4 DIVERGENT result is:

    1. globally stable,
    2. concentrated in a small subset,
    3. driven by one disagreement path,
    4. driven by outcome imbalance,
    5. driven by low-confidence cases,
    6. driven by weak wisdom applicability,
    7. sensitive to individual cases,
    8. or structurally persistent.

IMPORTANT
---------
This module does NOT:

    - generate synthetic cases
    - alter historical outcomes
    - retrain the model
    - modify model parameters
    - modify wisdom rules
    - modify reflection history
    - inject random market data
    - perform trading

All calculations operate on the already reconciled historical
reflection records.

Statistical resampling, where used, is explicitly labeled as
RESAMPLING OF OBSERVED CASES and never creates new observations.
"""

import json
import math
import os
import statistics
import hashlib
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

REFLECTION_FILE = os.path.join(
    DATA,
    "ml_reflection.json",
)

AUDIT_FILE = os.path.join(
    DATA,
    "reflection_reconciliation_audit.json",
)

OUTPUT_FILE = os.path.join(
    DATA,
    "reconvergence_v5_gauntlet.json",
)


EPS = 1e-12


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def finite(value: Any):
    try:
        if value is None:
            return None

        x = float(value)

        if not math.isfinite(x):
            return None

        return x

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None


def clamp01(x: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(x),
        ),
    )


def mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def load_reflections() -> List[Dict[str, Any]]:
    payload = load_json(
        REFLECTION_FILE,
        {},
    )

    if isinstance(payload, dict):
        rows = payload.get(
            "reflections",
            [],
        )
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []

    return [
        row
        for row in rows
        if isinstance(row, dict)
    ]


def case_id(row: Dict[str, Any], index: int) -> str:
    for key in (
        "case_id",
        "reflection_id",
        "addr",
        "memory_id",
    ):
        value = row.get(key)

        if value not in (
            None,
            "",
        ):
            return str(value)

    digest = hashlib.sha256(
        json.dumps(
            row,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:20]

    return f"anonymous:{index}:{digest}"


def binary(row: Dict[str, Any], key: str):
    value = finite(row.get(key))

    if value is None:
        return None

    return 1 if value >= 0.5 else 0


def extract_cases(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    cases = []

    for index, row in enumerate(rows):
        model = binary(
            row,
            "predicted_outcome",
        )

        wisdom = binary(
            row,
            "wisdom_score",
        )

        reality = binary(
            row,
            "actual_outcome",
        )

        convergence = binary(
            row,
            "three_way_convergence",
        )

        model_wisdom = binary(
            row,
            "model_wisdom_agreement",
        )

        model_reality = binary(
            row,
            "model_reality_alignment",
        )

        wisdom_reality = binary(
            row,
            "wisdom_reality_alignment",
        )

        probability = finite(
            row.get("probability")
        )

        confidence = finite(
            row.get("model_confidence")
        )

        error = finite(
            row.get("prediction_error")
        )

        cases.append(
            {
                "index": index,
                "case_id": case_id(
                    row,
                    index,
                ),
                "model": model,
                "wisdom": wisdom,
                "reality": reality,
                "three_way": convergence,
                "model_wisdom": model_wisdom,
                "model_reality": model_reality,
                "wisdom_reality": wisdom_reality,
                "probability": probability,
                "confidence": confidence,
                "error": error,
                "raw": row,
            }
        )

    return cases


def valid_triplets(
    cases: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    return [
        c
        for c in cases
        if (
            c["model"] is not None
            and c["wisdom"] is not None
            and c["reality"] is not None
        )
    ]


def convergence_rate(
    cases: List[Dict[str, Any]],
) -> float:

    values = [
        c["three_way"]
        for c in cases
        if c["three_way"] is not None
    ]

    return mean(values)


def alignment_rate(
    cases: List[Dict[str, Any]],
    field: str,
) -> float:

    values = [
        c[field]
        for c in cases
        if c[field] is not None
    ]

    return mean(values)


def channel_counts(
    cases: List[Dict[str, Any]],
) -> Dict[str, int]:

    return {
        "model_positive": sum(
            c["model"] == 1
            for c in cases
        ),
        "model_negative": sum(
            c["model"] == 0
            for c in cases
        ),
        "wisdom_positive": sum(
            c["wisdom"] == 1
            for c in cases
        ),
        "wisdom_negative": sum(
            c["wisdom"] == 0
            for c in cases
        ),
        "reality_positive": sum(
            c["reality"] == 1
            for c in cases
        ),
        "reality_negative": sum(
            c["reality"] == 0
            for c in cases
        ),
    }


def pair_matrix(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    pairs = {
        "MODEL_WISDOM": defaultdict(int),
        "MODEL_REALITY": defaultdict(int),
        "WISDOM_REALITY": defaultdict(int),
    }

    for c in cases:

        if (
            c["model"] is not None
            and c["wisdom"] is not None
        ):
            pairs["MODEL_WISDOM"][
                f"{c['model']}_{c['wisdom']}"
            ] += 1

        if (
            c["model"] is not None
            and c["reality"] is not None
        ):
            pairs["MODEL_REALITY"][
                f"{c['model']}_{c['reality']}"
            ] += 1

        if (
            c["wisdom"] is not None
            and c["reality"] is not None
        ):
            pairs["WISDOM_REALITY"][
                f"{c['wisdom']}_{c['reality']}"
            ] += 1

    return {
        name: dict(values)
        for name, values in pairs.items()
    }


def failure_classes(
    cases: List[Dict[str, Any]],
) -> Dict[str, int]:

    counts = Counter()

    for c in cases:

        failed = []

        if c["model_wisdom"] == 0:
            failed.append(
                "MODEL_WISDOM"
            )

        if c["model_reality"] == 0:
            failed.append(
                "MODEL_REALITY"
            )

        if c["wisdom_reality"] == 0:
            failed.append(
                "WISDOM_REALITY"
            )

        if not failed:
            counts["NO_FAILURE"] += 1

        elif len(failed) == 1:
            counts[
                f"SINGLE:{failed[0]}"
            ] += 1

        else:
            counts["MULTIPLE_PATHS"] += 1

    return dict(counts)


def divergence_components(
    cases: List[Dict[str, Any]],
) -> Dict[str, float]:

    n = len(cases)

    if n == 0:
        return {
            "model_wisdom_conflict_rate": 0.0,
            "model_reality_conflict_rate": 0.0,
            "wisdom_reality_conflict_rate": 0.0,
            "three_way_failure_rate": 0.0,
        }

    mw = sum(
        c["model_wisdom"] == 0
        for c in cases
    )

    mr = sum(
        c["model_reality"] == 0
        for c in cases
    )

    wr = sum(
        c["wisdom_reality"] == 0
        for c in cases
    )

    tf = sum(
        c["three_way"] == 0
        for c in cases
    )

    return {
        "model_wisdom_conflict_rate": mw / n,
        "model_reality_conflict_rate": mr / n,
        "wisdom_reality_conflict_rate": wr / n,
        "three_way_failure_rate": tf / n,
    }


def confidence_bands(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    bands = {
        "VERY_LOW_0_20": [],
        "LOW_20_40": [],
        "MEDIUM_40_60": [],
        "HIGH_60_80": [],
        "VERY_HIGH_80_100": [],
        "MISSING": [],
    }

    for c in cases:
        confidence = c["confidence"]

        if confidence is None:
            bands["MISSING"].append(c)
        elif confidence < 0.20:
            bands["VERY_LOW_0_20"].append(c)
        elif confidence < 0.40:
            bands["LOW_20_40"].append(c)
        elif confidence < 0.60:
            bands["MEDIUM_40_60"].append(c)
        elif confidence < 0.80:
            bands["HIGH_60_80"].append(c)
        else:
            bands["VERY_HIGH_80_100"].append(c)

    result = {}

    for name, group in bands.items():
        result[name] = {
            "count": len(group),
            "convergence": convergence_rate(group),
            "model_reality": alignment_rate(
                group,
                "model_reality",
            ),
            "model_wisdom": alignment_rate(
                group,
                "model_wisdom",
            ),
            "wisdom_reality": alignment_rate(
                group,
                "wisdom_reality",
            ),
        }

    return result


def outcome_strata(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    result = {}

    for outcome in (
        0,
        1,
    ):
        group = [
            c
            for c in cases
            if c["reality"] == outcome
        ]

        result[str(outcome)] = {
            "count": len(group),
            "convergence": convergence_rate(group),
            "model_reality": alignment_rate(
                group,
                "model_reality",
            ),
            "model_wisdom": alignment_rate(
                group,
                "model_wisdom",
            ),
            "wisdom_reality": alignment_rate(
                group,
                "wisdom_reality",
            ),
        }

    return result


def model_probability_bands(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    definitions = [
        ("0.00_0.20", 0.0, 0.20),
        ("0.20_0.40", 0.20, 0.40),
        ("0.40_0.50", 0.40, 0.50),
        ("0.50_0.60", 0.50, 0.60),
        ("0.60_0.80", 0.60, 0.80),
        ("0.80_1.00", 0.80, 1.0000001),
    ]

    result = {}

    for name, low, high in definitions:
        group = [
            c
            for c in cases
            if (
                c["probability"] is not None
                and low <= c["probability"] < high
            )
        ]

        result[name] = {
            "count": len(group),
            "convergence": convergence_rate(group),
            "model_reality": alignment_rate(
                group,
                "model_reality",
            ),
            "wisdom_reality": alignment_rate(
                group,
                "wisdom_reality",
            ),
        }

    return result


def leave_one_out(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    valid = [
        c
        for c in cases
        if c["three_way"] is not None
    ]

    if len(valid) < 2:
        return {
            "available": False,
        }

    baseline = convergence_rate(valid)

    values = []

    for index, removed in enumerate(valid):

        remaining = (
            valid[:index]
            + valid[index + 1:]
        )

        score = convergence_rate(
            remaining
        )

        values.append(
            {
                "case_id": removed["case_id"],
                "removed_three_way": removed[
                    "three_way"
                ],
                "remaining_convergence": score,
                "delta_from_baseline": (
                    score - baseline
                ),
            }
        )

    highest = max(
        values,
        key=lambda x: x[
            "remaining_convergence"
        ],
    )

    lowest = min(
        values,
        key=lambda x: x[
            "remaining_convergence"
        ],
    )

    return {
        "available": True,
        "baseline": baseline,
        "count": len(values),
        "max_remaining_convergence": highest,
        "min_remaining_convergence": lowest,
        "range": (
            highest["remaining_convergence"]
            - lowest["remaining_convergence"]
        ),
        "positive_case_removals": sum(
            item["removed_three_way"] == 1
            for item in values
        ),
        "negative_case_removals": sum(
            item["removed_three_way"] == 0
            for item in values
        ),
    }


def deterministic_half_split(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    ordered = sorted(
        cases,
        key=lambda c: (
            str(
                c.get("raw", {}).get(
                    "updated_at",
                    "",
                )
            ),
            str(c["case_id"]),
        ),
    )

    midpoint = len(ordered) // 2

    first = ordered[:midpoint]
    second = ordered[midpoint:]

    return {
        "first_half": {
            "count": len(first),
            "convergence": convergence_rate(first),
            "model_reality": alignment_rate(
                first,
                "model_reality",
            ),
            "model_wisdom": alignment_rate(
                first,
                "model_wisdom",
            ),
            "wisdom_reality": alignment_rate(
                first,
                "wisdom_reality",
            ),
        },
        "second_half": {
            "count": len(second),
            "convergence": convergence_rate(second),
            "model_reality": alignment_rate(
                second,
                "model_reality",
            ),
            "model_wisdom": alignment_rate(
                second,
                "model_wisdom",
            ),
            "wisdom_reality": alignment_rate(
                second,
                "wisdom_reality",
            ),
        },
    }


def rolling_windows(
    cases: List[Dict[str, Any]],
    window: int = 20,
) -> List[Dict[str, Any]]:

    ordered = sorted(
        cases,
        key=lambda c: (
            str(
                c.get("raw", {}).get(
                    "updated_at",
                    "",
                )
            ),
            str(c["case_id"]),
        ),
    )

    if len(ordered) < window:
        return []

    output = []

    for start in range(
        0,
        len(ordered) - window + 1,
    ):
        group = ordered[
            start:start + window
        ]

        output.append(
            {
                "start_index": start,
                "end_index": (
                    start + window - 1
                ),
                "count": len(group),
                "convergence": convergence_rate(
                    group
                ),
                "model_reality": alignment_rate(
                    group,
                    "model_reality",
                ),
                "model_wisdom": alignment_rate(
                    group,
                    "model_wisdom",
                ),
                "wisdom_reality": alignment_rate(
                    group,
                    "wisdom_reality",
                ),
            }
        )

    return output


def exact_observed_pattern(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    patterns = Counter()

    for c in cases:
        patterns[
            (
                c["model"],
                c["wisdom"],
                c["reality"],
            )
        ] += 1

    result = []

    for pattern, count in patterns.most_common():

        result.append(
            {
                "model": pattern[0],
                "wisdom": pattern[1],
                "reality": pattern[2],
                "count": count,
                "fraction": (
                    count / len(cases)
                    if cases
                    else 0.0
                ),
                "is_full_convergence": (
                    pattern[0]
                    == pattern[1]
                    == pattern[2]
                ),
            }
        )

    return {
        "patterns": result,
        "unique_patterns": len(result),
    }


def concentration_analysis(
    cases: List[Dict[str, Any]],
) -> Dict[str, Any]:

    failures = [
        c
        for c in cases
        if c["three_way"] == 0
    ]

    if not failures:
        return {
            "failure_count": 0,
            "failure_fraction": 0.0,
            "status": "NO_THREE_WAY_FAILURES",
        }

    failure_paths = Counter()

    for c in failures:

        paths = []

        if c["model_wisdom"] == 0:
            paths.append(
                "MODEL_WISDOM"
            )

        if c["model_reality"] == 0:
            paths.append(
                "MODEL_REALITY"
            )

        if c["wisdom_reality"] == 0:
            paths.append(
                "WISDOM_REALITY"
            )

        failure_paths[
            "+".join(paths)
        ] += 1

    return {
        "failure_count": len(failures),
        "failure_fraction": (
            len(failures) / len(cases)
        ),
        "failure_path_counts": dict(
            failure_paths
        ),
        "status": (
            "CONCENTRATED"
            if (
                len(failure_paths) <= 2
            )
            else "DISTRIBUTED"
        ),
    }


def score_decomposition(
    cases: List[Dict[str, Any]],
) -> Dict[str, float]:

    if not cases:
        return {}

    n = len(cases)

    mw = alignment_rate(
        cases,
        "model_wisdom",
    )

    mr = alignment_rate(
        cases,
        "model_reality",
    )

    wr = alignment_rate(
        cases,
        "wisdom_reality",
    )

    three = convergence_rate(cases)

    return {
        "model_wisdom_agreement": mw,
        "model_reality_agreement": mr,
        "wisdom_reality_agreement": wr,
        "three_way_convergence": three,
        "average_pairwise_agreement": (
            mw + mr + wr
        ) / 3.0,
        "three_way_gap_from_pairwise": (
            three
            - (
                mw + mr + wr
            ) / 3.0
        ),
        "model_reality_minus_wisdom_reality": (
            mr - wr
        ),
    }


def generate_verdict(
    cases: List[Dict[str, Any]],
    loo: Dict[str, Any],
    concentration: Dict[str, Any],
    halves: Dict[str, Any],
    bands: Dict[str, Any],
) -> Dict[str, Any]:

    n = len(cases)

    if n == 0:
        return {
            "classification": "NO_DATA",
            "confidence": "NONE",
            "reason": "No reconciled cases available.",
        }

    convergence = convergence_rate(cases)

    model_reality = alignment_rate(
        cases,
        "model_reality",
    )

    wisdom_reality = alignment_rate(
        cases,
        "wisdom_reality",
    )

    model_wisdom = alignment_rate(
        cases,
        "model_wisdom",
    )

    loo_range = finite(
        loo.get("range")
    ) if loo else None

    half_values = [
        finite(
            halves[key].get(
                "convergence"
            )
        )
        for key in (
            "first_half",
            "second_half",
        )
    ]

    half_values = [
        x
        for x in half_values
        if x is not None
    ]

    half_gap = (
        abs(
            half_values[0]
            - half_values[1]
        )
        if len(half_values) == 2
        else None
    )

    high_conf = []

    for key in (
        "HIGH_60_80",
        "VERY_HIGH_80_100",
    ):
        high_conf.append(
            bands[key]
        )

    high_count = sum(
        item["count"]
        for item in high_conf
    )

    high_convergence = (
        sum(
            item["convergence"]
            * item["count"]
            for item in high_conf
        )
        / high_count
        if high_count
        else None
    )

    reasons = []

    if model_reality >= 0.95:
        reasons.append(
            "MODEL_REALITY_STRONG"
        )
    elif model_reality < 0.80:
        reasons.append(
            "MODEL_REALITY_WEAK"
        )

    if wisdom_reality < 0.80:
        reasons.append(
            "WISDOM_REALITY_WEAK"
        )

    if model_wisdom < 0.80:
        reasons.append(
            "MODEL_WISDOM_WEAK"
        )

    if high_convergence is not None:
        if high_convergence > convergence + 0.10:
            reasons.append(
                "LOW_CONFIDENCE_DRIVEN_DIVERGENCE_POSSIBLE"
            )

    if half_gap is not None:
        if half_gap > 0.20:
            reasons.append(
                "TEMPORAL_OR_ORDER_INSTABILITY"
            )

    if loo_range is not None:
        if loo_range > 0.10:
            reasons.append(
                "CASE_SENSITIVITY_DETECTED"
            )
        else:
            reasons.append(
                "CASE_SENSITIVITY_LOW"
            )

    if (
        concentration.get(
            "status"
        )
        == "CONCENTRATED"
    ):
        reasons.append(
            "FAILURES_CONCENTRATED"
        )

    if (
        convergence < 0.20
        and model_reality >= 0.95
        and wisdom_reality < 0.50
    ):
        classification = (
            "WISDOM_CHANNEL_DIVERGENCE"
        )

    elif (
        convergence < 0.20
        and model_wisdom < 0.50
        and model_reality >= 0.80
    ):
        classification = (
            "MODEL_WISDOM_DIVERGENCE"
        )

    elif (
        convergence < 0.20
        and half_gap is not None
        and half_gap > 0.20
    ):
        classification = (
            "NONSTATIONARY_DIVERGENCE"
        )

    elif (
        convergence < 0.20
        and loo_range is not None
        and loo_range <= 0.10
    ):
        classification = (
            "STABLE_DIVERGENCE"
        )

    else:
        classification = (
            "DIVERGENCE_REQUIRES_DECOMPOSITION"
        )

    return {
        "classification": classification,
        "cases": n,
        "three_way_convergence": convergence,
        "model_wisdom_agreement": model_wisdom,
        "model_reality_agreement": model_reality,
        "wisdom_reality_agreement": wisdom_reality,
        "leave_one_out_range": loo_range,
        "half_split_gap": half_gap,
        "high_confidence_convergence": high_convergence,
        "reasons": reasons,
    }


def main() -> int:

    print("=" * 72)
    print(
        "BIRTH_EDGE RECONVERGENCE V5"
    )
    print(
        "HISTORICAL DIVERGENCE GAUNTLET"
    )
    print("=" * 72)

    rows = load_reflections()
    cases = extract_cases(rows)
    cases = valid_triplets(cases)

    print()
    print(
        "RECONCILED CASES:",
        len(cases),
    )

    if not cases:
        print(
            "NO VALID RECONVERGENCE CASES"
        )
        return 1

    print()
    print(
        "=== CHANNEL DISTRIBUTION ==="
    )

    for key, value in channel_counts(
        cases
    ).items():
        print(
            f"{key}: {value}"
        )

    print()
    print(
        "=== EXACT OBSERVED PATTERNS ==="
    )

    patterns = exact_observed_pattern(
        cases
    )

    for item in patterns[
        "patterns"
    ]:
        print(
            "MODEL={model} "
            "WISDOM={wisdom} "
            "REALITY={reality} "
            "COUNT={count} "
            "FRACTION={fraction:.6f} "
            "FULL={is_full_convergence}".format(
                **item
            )
        )

    print()
    print(
        "=== PAIRWISE AGREEMENT ==="
    )

    decomposition = score_decomposition(
        cases
    )

    for key, value in decomposition.items():
        print(
            f"{key}: {value:.6f}"
        )

    print()
    print(
        "=== FAILURE CLASSES ==="
    )

    failures = failure_classes(
        cases
    )

    for key, value in failures.items():
        print(
            f"{key}: {value}"
        )

    print()
    print(
        "=== DIVERGENCE COMPONENTS ==="
    )

    components = divergence_components(
        cases
    )

    for key, value in components.items():
        print(
            f"{key}: {value:.6f}"
        )

    print()
    print(
        "=== OUTCOME STRATIFICATION ==="
    )

    outcomes = outcome_strata(
        cases
    )

    for key, value in outcomes.items():
        print(
            "OUTCOME",
            key,
            json.dumps(
                value,
                sort_keys=True,
            )
        )

    print()
    print(
        "=== CONFIDENCE STRATIFICATION ==="
    )

    confidence = confidence_bands(
        cases
    )

    for key, value in confidence.items():
        print(
            key,
            json.dumps(
                value,
                sort_keys=True,
            )
        )

    print()
    print(
        "=== MODEL PROBABILITY STRATIFICATION ==="
    )

    probability_bands = model_probability_bands(
        cases
    )

    for key, value in probability_bands.items():
        print(
            key,
            json.dumps(
                value,
                sort_keys=True,
            )
        )

    print()
    print(
        "=== CONCENTRATION ANALYSIS ==="
    )

    concentration = concentration_analysis(
        cases
    )

    print(
        json.dumps(
            concentration,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print(
        "=== DETERMINISTIC HALF SPLIT ==="
    )

    halves = deterministic_half_split(
        cases
    )

    print(
        json.dumps(
            halves,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print(
        "=== ROLLING WINDOW ANALYSIS ==="
    )

    rolling = rolling_windows(
        cases,
        window=20,
    )

    if rolling:
        min_window = min(
            rolling,
            key=lambda x: x[
                "convergence"
            ],
        )

        max_window = max(
            rolling,
            key=lambda x: x[
                "convergence"
            ],
        )

        print(
            "WINDOWS:",
            len(rolling),
        )

        print(
            "LOWEST:",
            json.dumps(
                min_window,
                sort_keys=True,
            )
        )

        print(
            "HIGHEST:",
            json.dumps(
                max_window,
                sort_keys=True,
            )
        )

    else:
        print(
            "WINDOWS: unavailable"
        )

    print()
    print(
        "=== LEAVE-ONE-OUT SENSITIVITY ==="
    )

    loo = leave_one_out(
        cases
    )

    print(
        json.dumps(
            loo,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print(
        "=== FINAL V5 VERDICT ==="
    )

    verdict = generate_verdict(
        cases,
        loo,
        concentration,
        halves,
        confidence,
    )

    print(
        "CLASSIFICATION:",
        verdict[
            "classification"
        ],
    )

    print(
        "THREE-WAY:",
        f"{verdict['three_way_convergence']:.6f}",
    )

    print(
        "MODEL-WISDOM:",
        f"{verdict['model_wisdom_agreement']:.6f}",
    )

    print(
        "MODEL-REALITY:",
        f"{verdict['model_reality_agreement']:.6f}",
    )

    print(
        "WISDOM-REALITY:",
        f"{verdict['wisdom_reality_agreement']:.6f}",
    )

    print(
        "LEAVE-ONE-OUT RANGE:",
        f"{verdict['leave_one_out_range']:.6f}"
        if verdict[
            "leave_one_out_range"
        ] is not None
        else "N/A",
    )

    print(
        "HALF-SPLIT GAP:",
        f"{verdict['half_split_gap']:.6f}"
        if verdict[
            "half_split_gap"
        ] is not None
        else "N/A",
    )

    print(
        "HIGH-CONFIDENCE CONVERGENCE:",
        (
            f"{verdict['high_confidence_convergence']:.6f}"
            if verdict[
                "high_confidence_convergence"
            ] is not None
            else "N/A"
        ),
    )

    print(
        "REASONS:"
    )

    for reason in verdict[
        "reasons"
    ]:
        print(
            "  -",
            reason,
        )

    print("=" * 72)

    output = {
        "engine": (
            "BIRTH_EDGE_RECONVERGENCE_V5"
        ),
        "version": 5,
        "synthetic_data": False,
        "outcome_leakage": False,
        "source": (
            "data/ml_reflection.json"
        ),
        "case_count": len(cases),
        "channel_distribution": channel_counts(
            cases
        ),
        "exact_observed_patterns": patterns,
        "score_decomposition": decomposition,
        "failure_classes": failures,
        "divergence_components": components,
        "outcome_stratification": outcomes,
        "confidence_stratification": confidence,
        "probability_stratification": probability_bands,
        "concentration": concentration,
        "half_split": halves,
        "rolling_windows": rolling,
        "leave_one_out": loo,
        "verdict": verdict,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            output,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )

    print()
    print(
        "AUDIT FILE:",
        OUTPUT_FILE,
    )

    print()
    print(
        "V5 COMPLETE — HISTORICAL DATA UNMODIFIED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
PY

python3 -m py_compile reconvergence_v5.py

echo
echo "========================================================================"
echo "RUNNING RECONVERGENCE V5 DIVERGENCE GAUNTLET"
echo "========================================================================"

python3 reconvergence_v5.py

echo
echo "========================================================================"
echo "V5 MACHINE-READABLE SUMMARY"
echo "========================================================================"

python3 - <<'PY'
import json

path = "data/reconvergence_v5_gauntlet.json"

with open(
    path,
    "r",
    encoding="utf-8",
) as handle:
    data = json.load(handle)

print(
    json.dumps(
        {
            "case_count": data.get(
                "case_count"
            ),
            "score_decomposition": data.get(
                "score_decomposition"
            ),
            "failure_classes": data.get(
                "failure_classes"
            ),
            "divergence_components": data.get(
                "divergence_components"
            ),
            "concentration": data.get(
                "concentration"
            ),
            "leave_one_out": data.get(
                "leave_one_out"
            ),
            "verdict": data.get(
                "verdict"
            ),
        },
        indent=2,
        sort_keys=True,
    )
)
PY

echo
echo "========================================================================"
echo "V5 COMPLETE"
echo "========================================================================"
echo "No historical records were modified."
echo "No synthetic cases were generated."
echo "No outcomes were changed."
echo "Audit: data/reconvergence_v5_gauntlet.json"
