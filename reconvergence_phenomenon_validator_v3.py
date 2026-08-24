#!/usr/bin/env python3

"""
BIRTH_EDGE — RECONVERGENCE PHENOMENON VALIDATOR V3

Purpose
-------
Test whether BIRTH_EDGE exhibits a recurring:

    FULL_CONVERGENCE
        ->
    DIVERGENCE
        ->
    FULL_CONVERGENCE

trajectory using ONLY persisted historical records.

V3 explicitly separates:

1. SEMANTIC VALIDITY
2. STATE TRANSITIONS
3. TRUE C-D-C RECONVERGENCE MOTIFS
4. PATH-SPECIFIC RECOVERY
5. NON-ADJACENT RECONVERGENCE
6. REPEATED EPISODES
7. PRECURSOR CHANGES
8. RUN STRUCTURE
9. NULL / SAMPLE LIMITATIONS

No synthetic data.
No model modification.
No historical-data modification.
No trading.
"""

import json
import math
import os
import statistics
from collections import Counter

ROOT = os.path.expanduser("~/BIRTH_EDGE")
DATA = os.path.join(ROOT, "data", "ml_reflection.json")

VERSION = 3

MIN_CASES = 10
MIN_REPEATED_EPISODES = 3
MIN_STRONG_SAMPLE = 50


# ==============================================================
# BASIC UTILITIES
# ==============================================================

def load_records():
    with open(DATA, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        for key in (
            "records",
            "reflections",
            "history",
            "cases",
            "data",
        ):
            value = raw.get(key)
            if isinstance(value, list):
                return value

    raise ValueError("Unsupported ml_reflection.json structure")


def bit(value):
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value != 0)

    if isinstance(value, str):
        s = value.strip().lower()

        if s in {
            "1",
            "true",
            "yes",
            "correct",
            "pass",
            "passed",
            "success",
            "successful",
            "aligned",
            "win",
            "winner",
        }:
            return 1

        if s in {
            "0",
            "false",
            "no",
            "wrong",
            "fail",
            "failed",
            "failure",
            "diverged",
            "loss",
            "lost",
        }:
            return 0

    return None


def num(value):
    try:
        return float(value)
    except Exception:
        return None


def identity(record, index):
    for key in (
        "reflection_id",
        "memory_id",
        "id",
        "record_id",
        "timestamp",
        "created_at",
    ):
        if key in record:
            return f"{key}={record[key]}"

    return f"index={index}"


def rate(rows, key):
    values = [
        r[key]
        for r in rows
        if r.get(key) in (0, 1)
    ]

    if not values:
        return None

    return sum(values) / len(values)


def delta(a, b):
    if a is None or b is None:
        return None

    return a - b


# ==============================================================
# CANONICAL SEMANTICS
# ==============================================================

def canonical_actual_alignment(predicted, actual):
    """
    REALITY = whether the stored prediction actually matched
    the stored outcome.

    No arbitrary binary coercion of outcome strings.
    """

    if predicted is None or actual is None:
        return None

    return int(predicted == actual)


def inspect_record(record, index):
    predicted = record.get("predicted_outcome")
    actual = record.get("actual_outcome")

    correct_raw = record.get("correct")
    wisdom_raw = record.get("wisdom_correct")

    model = bit(correct_raw)
    wisdom = bit(wisdom_raw)

    reality = canonical_actual_alignment(
        predicted,
        actual
    )

    consistency = None

    if model is not None and reality is not None:
        consistency = int(model == reality)

    three_way = None
    model_reality = None
    wisdom_reality = None

    if (
        model is not None
        and wisdom is not None
        and reality is not None
    ):
        three_way = int(model == wisdom == reality)
        model_reality = int(model == reality)
        wisdom_reality = int(wisdom == reality)

    if three_way == 1:
        state = "FULL_CONVERGENCE"

    elif (
        model_reality == 1
        and wisdom_reality == 0
    ):
        state = "MODEL_ANCHORED_DIVERGENCE"

    elif (
        model_reality == 0
        and wisdom_reality == 1
    ):
        state = "WISDOM_ANCHORED_DIVERGENCE"

    elif (
        model is not None
        and wisdom is not None
        and reality is not None
    ):
        state = "FULL_DIVERGENCE"

    else:
        state = "SEMANTICALLY_INCOMPLETE"

    broken = []

    if model is not None and reality is not None:
        if model != reality:
            broken.append("MODEL")

    if wisdom is not None and reality is not None:
        if wisdom != reality:
            broken.append("WISDOM")

    return {
        "index": index,
        "identity": identity(record, index),

        "predicted_outcome": predicted,
        "actual_outcome": actual,

        "model": model,
        "wisdom": wisdom,
        "reality": reality,

        "correct_raw": correct_raw,
        "wisdom_correct_raw": wisdom_raw,

        "actual_alignment": reality,
        "correct_field_consistency": consistency,

        "model_reality": model_reality,
        "wisdom_reality": wisdom_reality,
        "three_way": three_way,

        "state": state,
        "broken_paths": broken,

        "model_confidence":
            num(record.get("model_confidence")),

        "prediction_error":
            num(record.get("prediction_error")),

        "evidence_agreement":
            num(record.get("evidence_agreement")),

        "evidence_strength":
            num(record.get("evidence_strength")),

        "wisdom_score":
            num(record.get("wisdom_score")),

        "reflection_score":
            num(record.get("reflection_score")),
    }


def semantic_valid(row):
    return (
        row["model"] in (0, 1)
        and row["wisdom"] in (0, 1)
        and row["reality"] in (0, 1)
        and row["three_way"] in (0, 1)
    )


# ==============================================================
# SIGNATURES
# ==============================================================

def signature(row):
    return (
        f"M{row['model']}"
        f"W{row['wisdom']}"
        f"R{row['reality']}"
    )


def state_signature(row):
    return row["state"]


def signatures(rows):
    out = Counter()

    for row in rows:
        out[signature(row)] += 1

    return dict(out)


def transition_table(rows):
    out = Counter()

    for a, b in zip(rows, rows[1:]):
        out[
            f"{a['state']} -> {b['state']}"
        ] += 1

    return dict(out)


# ==============================================================
# TRUE RECONVERGENCE
# ==============================================================

def true_cdc_motifs(rows):
    """
    Detect the strict local motif:

        C -> D -> C

    where C = FULL_CONVERGENCE
    and D = any divergent state.
    """

    events = []

    for i in range(2, len(rows)):
        a = rows[i - 2]
        b = rows[i - 1]
        c = rows[i]

        if (
            a["three_way"] == 1
            and b["three_way"] == 0
            and c["three_way"] == 1
        ):
            events.append({
                "divergence_index": i - 1,
                "reconvergence_index": i,

                "from_case": a["identity"],
                "divergence_case": b["identity"],
                "reconvergence_case": c["identity"],

                "from_state": a["state"],
                "divergence_state": b["state"],
                "to_state": c["state"],

                "divergence_signature": signature(b),

                "broken_paths":
                    b["broken_paths"],

                "model_recovered":
                    int(
                        b["model_reality"] == 0
                        and c["model_reality"] == 1
                    ),

                "wisdom_recovered":
                    int(
                        b["wisdom_reality"] == 0
                        and c["wisdom_reality"] == 1
                    ),
            })

    return events


def nonadjacent_reconvergence(rows):
    """
    Detect:

        C -> D ... D -> C

    allowing one or more divergent cases between divergence
    and recovery.

    This is stronger than simply detecting D -> C.
    """

    events = []

    i = 0

    while i < len(rows):
        if rows[i]["three_way"] != 1:
            i += 1
            continue

        start = i
        j = i + 1

        if j >= len(rows):
            break

        if rows[j]["three_way"] == 1:
            i += 1
            continue

        divergence_start = j

        while (
            j < len(rows)
            and rows[j]["three_way"] == 0
        ):
            j += 1

        if j < len(rows):
            recovery = rows[j]

            if recovery["three_way"] == 1:
                events.append({
                    "start_index": start,
                    "divergence_start_index":
                        divergence_start,
                    "recovery_index": j,

                    "start_case":
                        rows[start]["identity"],

                    "divergence_start_case":
                        rows[divergence_start]["identity"],

                    "recovery_case":
                        recovery["identity"],

                    "divergence_length":
                        j - divergence_start,

                    "divergence_states":
                        [
                            rows[k]["state"]
                            for k in range(
                                divergence_start,
                                j
                            )
                        ],

                    "divergence_signatures":
                        [
                            signature(rows[k])
                            for k in range(
                                divergence_start,
                                j
                            )
                        ],

                    "broken_paths":
                        sorted({
                            p
                            for k in range(
                                divergence_start,
                                j
                            )
                            for p in rows[k]["broken_paths"]
                        }),
                })

        i = max(j, i + 1)

    return events


# ==============================================================
# PATH-SPECIFIC RECOVERY
# ==============================================================

def path_recovery(events):
    out = Counter()

    for event in events:
        for path in event["broken_paths"]:
            out[path] += 1

    return dict(out)


def path_recovery_strict(rows):
    """
    For every divergent state, determine whether each broken
    path later returns to reality alignment before another
    divergence episode begins.
    """

    results = []

    for i, row in enumerate(rows):

        if row["three_way"] != 0:
            continue

        broken = set(row["broken_paths"])

        if not broken:
            continue

        for j in range(i + 1, len(rows)):

            candidate = rows[j]

            if candidate["three_way"] == 1:
                recovered = []

                for path in broken:
                    if path == "MODEL":
                        if (
                            row["model_reality"] == 0
                            and candidate["model_reality"] == 1
                        ):
                            recovered.append(path)

                    if path == "WISDOM":
                        if (
                            row["wisdom_reality"] == 0
                            and candidate["wisdom_reality"] == 1
                        ):
                            recovered.append(path)

                results.append({
                    "divergence_case":
                        row["identity"],

                    "recovery_case":
                        candidate["identity"],

                    "distance":
                        j - i,

                    "broken_paths":
                        sorted(broken),

                    "recovered_paths":
                        sorted(recovered),

                    "full_path_recovery":
                        broken.issubset(set(recovered)),
                })

                break

    return results


# ==============================================================
# DIVERGENCE / RECOVERY EVENTS
# ==============================================================

def divergence_events(rows):
    events = []

    for i in range(1, len(rows)):

        prev = rows[i - 1]
        cur = rows[i]

        if (
            prev["three_way"] == 1
            and cur["three_way"] == 0
        ):
            events.append({
                "index": i,
                "from_case":
                    prev["identity"],
                "to_case":
                    cur["identity"],

                "from_state":
                    prev["state"],

                "to_state":
                    cur["state"],

                "broken_paths":
                    cur["broken_paths"],

                "confidence_delta":
                    delta(
                        cur["model_confidence"],
                        prev["model_confidence"]
                    ),

                "agreement_delta":
                    delta(
                        cur["evidence_agreement"],
                        prev["evidence_agreement"]
                    ),

                "strength_delta":
                    delta(
                        cur["evidence_strength"],
                        prev["evidence_strength"]
                    ),

                "error_delta":
                    delta(
                        cur["prediction_error"],
                        prev["prediction_error"]
                    ),
            })

    return events


def immediate_recovery_events(rows):
    events = []

    for i in range(1, len(rows)):

        prev = rows[i - 1]
        cur = rows[i]

        if (
            prev["three_way"] == 0
            and cur["three_way"] == 1
        ):
            events.append({
                "index": i,

                "from_case":
                    prev["identity"],

                "to_case":
                    cur["identity"],

                "from_state":
                    prev["state"],

                "to_state":
                    cur["state"],

                "from_signature":
                    signature(prev),

                "to_signature":
                    signature(cur),

                "broken_paths":
                    prev["broken_paths"],
            })

    return events


# ==============================================================
# RUN STRUCTURE
# ==============================================================

def run_lengths(rows):
    if not rows:
        return []

    runs = []

    current = rows[0]["three_way"]
    start = 0

    for i in range(1, len(rows)):

        if rows[i]["three_way"] != current:

            runs.append({
                "state":
                    "CONVERGENT"
                    if current
                    else "DIVERGENT",

                "start_index":
                    start,

                "end_index":
                    i - 1,

                "length":
                    i - start,
            })

            current = rows[i]["three_way"]
            start = i

    runs.append({
        "state":
            "CONVERGENT"
            if current
            else "DIVERGENT",

        "start_index":
            start,

        "end_index":
            len(rows) - 1,

        "length":
            len(rows) - start,
    })

    return runs


# ==============================================================
# PRECURSOR ANALYSIS
# ==============================================================

def precursor_summary(events):
    if not events:
        return {
            "events": [],
            "n": 0,
            "mean_confidence_delta": None,
            "mean_agreement_delta": None,
            "mean_strength_delta": None,
            "mean_error_delta": None,
        }

    def mean(key):
        values = [
            e[key]
            for e in events
            if e[key] is not None
        ]

        return (
            statistics.mean(values)
            if values
            else None
        )

    return {
        "events": events,
        "n": len(events),
        "mean_confidence_delta":
            mean("confidence_delta"),
        "mean_agreement_delta":
            mean("agreement_delta"),
        "mean_strength_delta":
            mean("strength_delta"),
        "mean_error_delta":
            mean("error_delta"),
    }


# ==============================================================
# CLASSIFICATION
# ==============================================================

def classify(
    n,
    strict_cdc,
    nonadjacent,
    path_recovery,
):
    if n < MIN_CASES:
        return (
            "PHENOMENON_NOT_YET_IDENTIFIABLE",
            "LOW"
        )

    if strict_cdc >= MIN_REPEATED_EPISODES:
        if n >= MIN_STRONG_SAMPLE:
            return (
                "RECURRING_RECONVERGENCE_PHENOMENON",
                "HIGH"
            )

        return (
            "RECURRING_RECONVERGENCE_CANDIDATE",
            "MEDIUM"
        )

    if nonadjacent >= MIN_REPEATED_EPISODES:
        return (
            "NONADJACENT_RECONVERGENCE_CANDIDATE",
            "MEDIUM"
        )

    if path_recovery >= MIN_REPEATED_EPISODES:
        return (
            "PATH_RECOVERY_STRUCTURE",
            "MEDIUM"
        )

    if strict_cdc > 0 or nonadjacent > 0:
        return (
            "SINGLE_RECONVERGENCE_EVENT",
            "LOW"
        )

    return (
        "NO_RECONVERGENCE_STRUCTURE_YET",
        "LOW"
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE PHENOMENON VALIDATOR V3")
    print("STRICT C-D-C + PATH-SPECIFIC RECOVERY ANALYSIS")
    print("=" * 76)

    records = load_records()

    rows = [
        inspect_record(record, i)
        for i, record in enumerate(records)
        if isinstance(record, dict)
    ]

    valid = [
        row
        for row in rows
        if semantic_valid(row)
    ]

    invalid = [
        row
        for row in rows
        if not semantic_valid(row)
    ]

    n = len(valid)

    if not valid:
        raise RuntimeError(
            "No semantically valid canonical cases."
        )

    model_rate = rate(valid, "model_reality")
    wisdom_rate = rate(valid, "wisdom_reality")
    convergence_rate = rate(valid, "three_way")

    div = divergence_events(valid)
    immediate = immediate_recovery_events(valid)

    strict_cdc = true_cdc_motifs(valid)
    nonadjacent = nonadjacent_reconvergence(valid)

    recovery = path_recovery_strict(valid)

    full_path_recoveries = [
        x for x in recovery
        if x["full_path_recovery"]
    ]

    precursor = precursor_summary(div)

    runs = run_lengths(valid)

    classification, confidence = classify(
        n,
        len(strict_cdc),
        len(nonadjacent),
        len(full_path_recoveries),
    )

    result = {
        "engine":
            "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_VALIDATOR_V3",

        "version": VERSION,

        "data_source": DATA,

        "data_integrity": {
            "historical_records":
                len(records),

            "analyzed_cases":
                n,

            "invalid_cases":
                len(invalid),

            "historical_data_modified":
                False,

            "synthetic_data_used":
                False,

            "model_modified":
                False,

            "trading_performed":
                False,
        },

        "semantic_status": {
            "canonical_mapping":
                "LOCKED",

            "valid_cases":
                n,

            "invalid_cases":
                len(invalid),
        },

        "basic_alignment": {
            "model_reality_rate":
                model_rate,

            "wisdom_reality_rate":
                wisdom_rate,

            "full_convergence_rate":
                convergence_rate,
        },

        "structural_signatures":
            signatures(valid),

        "state_transitions":
            transition_table(valid),

        "divergence": {
            "count":
                len(div),

            "events":
                div,

            "rate":
                len(div) / max(1, n - 1),
        },

        "strict_cdc_reconvergence": {
            "definition":
                "FULL_CONVERGENCE -> DIVERGENCE -> FULL_CONVERGENCE",

            "count":
                len(strict_cdc),

            "events":
                strict_cdc,

            "rate":
                len(strict_cdc) / max(1, n - 2),
        },

        "nonadjacent_reconvergence": {
            "definition":
                "FULL_CONVERGENCE -> one_or_more_DIVERGENCE -> FULL_CONVERGENCE",

            "count":
                len(nonadjacent),

            "events":
                nonadjacent,

            "rate":
                len(nonadjacent) / max(1, n),
        },

        "immediate_recovery": {
            "count":
                len(immediate),

            "events":
                immediate,
        },

        "path_specific_recovery": {
            "count":
                len(recovery),

            "full_path_recovery_count":
                len(full_path_recoveries),

            "full_path_recoveries":
                full_path_recoveries,

            "all_events":
                recovery,

            "broken_path_frequency":
                dict(
                    Counter(
                        path
                        for row in valid
                        for path in row["broken_paths"]
                    )
                ),
        },

        "precursor_analysis":
            precursor,

        "temporal_structure": {
            "runs":
                runs,

            "total_transitions":
                max(0, n - 1),
        },

        "phenomenon": {
            "classification":
                classification,

            "confidence":
                confidence,

            "sample_size":
                n,

            "minimum_cases":
                MIN_CASES,

            "minimum_repeated_episodes":
                MIN_REPEATED_EPISODES,

            "minimum_strong_sample":
                MIN_STRONG_SAMPLE,
        },

        "research_question": {
            "question":
                "Does BIRTH_EDGE exhibit a recurring "
                "path-specific reality-alignment "
                "reconvergence phenomenon?",

            "strict_signature":
                "FULL_CONVERGENCE -> DIVERGENCE "
                "-> FULL_CONVERGENCE",

            "current_answer":
                classification,

            "interpretation":
                (
                    "A single DIVERGENCE -> CONVERGENCE "
                    "transition is not sufficient to establish "
                    "recurring reconvergence."
                ),

            "evidence_required":
                (
                    "Repeated C-D-C trajectories across "
                    "untouched historical cases."
                ),
        },

        "case_diagnostics":
            valid,
    }

    # ==========================================================
    # HUMAN-READABLE REPORT
    # ==========================================================

    print()
    print("=" * 76)
    print("SEMANTIC STATUS")
    print("=" * 76)

    print("VALID CASES:", n)
    print("INVALID CASES:", len(invalid))
    print("SEMANTICS: LOCKED")

    print()
    print("=" * 76)
    print("REALITY ALIGNMENT")
    print("=" * 76)

    print("MODEL -> REALITY:", model_rate)
    print("WISDOM -> REALITY:", wisdom_rate)
    print("THREE-WAY CONVERGENCE:", convergence_rate)

    print()
    print("=" * 76)
    print("STRUCTURAL SIGNATURES")
    print("=" * 76)

    print(
        json.dumps(
            signatures(valid),
            indent=2,
            sort_keys=True
        )
    )

    print()
    print("=" * 76)
    print("STATE TRANSITIONS")
    print("=" * 76)

    print(
        json.dumps(
            transition_table(valid),
            indent=2,
            sort_keys=True
        )
    )

    print()
    print("=" * 76)
    print("DIVERGENCE")
    print("=" * 76)

    print("DIVERGENCE EVENTS:", len(div))

    for event in div:
        print()
        print(json.dumps(event, indent=2))

    if not div:
        print("NONE")

    print()
    print("=" * 76)
    print("STRICT C-D-C RECONVERGENCE")
    print("=" * 76)

    print(
        "SIGNATURE:",
        "FULL_CONVERGENCE -> DIVERGENCE -> FULL_CONVERGENCE"
    )

    print(
        "EVENTS:",
        len(strict_cdc)
    )

    if strict_cdc:
        for event in strict_cdc:
            print()
            print(json.dumps(event, indent=2))
    else:
        print("NONE")

    print()
    print("=" * 76)
    print("NON-ADJACENT RECONVERGENCE")
    print("=" * 76)

    print(
        "EVENTS:",
        len(nonadjacent)
    )

    if nonadjacent:
        for event in nonadjacent:
            print()
            print(json.dumps(event, indent=2))
    else:
        print("NONE")

    print()
    print("=" * 76)
    print("PATH-SPECIFIC RECOVERY")
    print("=" * 76)

    print(
        "RECOVERY EPISODES:",
        len(recovery)
    )

    print(
        "FULL PATH RECOVERIES:",
        len(full_path_recoveries)
    )

    if recovery:
        for event in recovery:
            print()
            print(json.dumps(event, indent=2))
    else:
        print("NONE")

    print()
    print("=" * 76)
    print("PRECURSOR SIGNAL")
    print("=" * 76)

    if precursor["n"]:
        print(
            "MEAN CONFIDENCE DELTA:",
            precursor["mean_confidence_delta"]
        )

        print(
            "MEAN AGREEMENT DELTA:",
            precursor["mean_agreement_delta"]
        )

        print(
            "MEAN STRENGTH DELTA:",
            precursor["mean_strength_delta"]
        )

        print(
            "MEAN ERROR DELTA:",
            precursor["mean_error_delta"]
        )

    else:
        print("NO CONVERGENCE -> DIVERGENCE TRANSITIONS.")

    print()
    print("=" * 76)
    print("RUN STRUCTURE")
    print("=" * 76)

    for run in runs:
        print(
            run["state"],
            "START=",
            run["start_index"],
            "END=",
            run["end_index"],
            "LENGTH=",
            run["length"],
        )

    print()
    print("=" * 76)
    print("PHENOMENON VALIDATION VERDICT")
    print("=" * 76)

    print("CLASSIFICATION:", classification)
    print("CONFIDENCE:", confidence)
    print("SAMPLE SIZE:", n)

    if len(strict_cdc) > 0:
        print(
            "STRICT RECONVERGENCE:",
            "OBSERVED"
        )
    else:
        print(
            "STRICT RECONVERGENCE:",
            "NOT YET OBSERVED"
        )

    if len(nonadjacent) > 0:
        print(
            "NON-ADJACENT RECONVERGENCE:",
            "OBSERVED"
        )
    else:
        print(
            "NON-ADJACENT RECONVERGENCE:",
            "NOT YET OBSERVED"
        )

    if len(full_path_recoveries) > 0:
        print(
            "PATH-SPECIFIC RECOVERY:",
            "OBSERVED"
        )
    else:
        print(
            "PATH-SPECIFIC RECOVERY:",
            "NOT YET OBSERVED"
        )

    print()
    print("=" * 76)
    print("INTERPRETATION")
    print("=" * 76)

    if n < MIN_CASES:
        print(
            "The canonical semantics are locked, but the "
            "historical sample is too small for recurrence "
            "claims."
        )

    elif len(strict_cdc) >= MIN_REPEATED_EPISODES:
        print(
            "REPEATED C-D-C RECONVERGENCE IS OBSERVED."
        )

    elif len(nonadjacent) >= MIN_REPEATED_EPISODES:
        print(
            "REPEATED NON-ADJACENT RECONVERGENCE IS OBSERVED."
        )

    elif len(strict_cdc) > 0:
        print(
            "A STRICT RECONVERGENCE MOTIF EXISTS, "
            "BUT RECURRENCE IS NOT YET ESTABLISHED."
        )

    elif len(nonadjacent) > 0:
        print(
            "A NON-ADJACENT RECONVERGENCE EVENT EXISTS, "
            "BUT RECURRENCE IS NOT YET ESTABLISHED."
        )

    else:
        print(
            "No true C-D-C reconvergence motif is present "
            "in the current historical sequence."
        )

    print()
    print(
        "IMPORTANT: Continue using untouched historical "
        "experience. Do not manufacture cases."
    )

    print()
    print("=" * 76)
    print("NOMINALITY")
    print("=" * 76)

    print("ENGINE OPERATION: 💯 NOMINAL")
    print("HISTORICAL DATA MODIFIED: False")
    print("SYNTHETIC DATA USED: False")
    print("MODEL MODIFIED: False")
    print("TRADING PERFORMED: False")

    print()
    print("=" * 76)
    print("MACHINE-READABLE RESULT")
    print("=" * 76)

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True
        )
    )

    print()
    print("=" * 76)
    print("RECONVERGENCE VALIDATOR V3 COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
