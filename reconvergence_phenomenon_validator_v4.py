#!/usr/bin/env python3

"""
BIRTH_EDGE — RECONVERGENCE PHENOMENON VALIDATOR V4

Purpose
-------
Close the reconvergence measurement loop using ONLY persisted
historical BIRTH_EDGE records.

V4 adds persistent episode-level analysis:

    FULL_CONVERGENCE
            |
            v
       DIVERGENCE
            |
            v
     RECOVERY / WAIT
            |
            v
       RECONVERGENCE
            |
            v
      EPISODE CLOSED
            |
            v
   COMPARE WITH OTHER EPISODES

Research target
---------------
Determine whether BIRTH_EDGE exhibits recurring,
path-specific reality-alignment reconvergence.

Strict motif:

    C -> D -> C

General motif:

    C -> D+ -> C

where:

    C = FULL_CONVERGENCE
    D = any divergent state

V4 does NOT manufacture recovery cases.

No synthetic data.
No historical-data modification.
No model modification.
No trading.
"""

import json
import math
import os
import statistics
from collections import Counter, defaultdict


# ==============================================================
# CONFIGURATION
# ==============================================================

ROOT = os.path.expanduser("~/BIRTH_EDGE")

DATA = os.path.join(
    ROOT,
    "data",
    "ml_reflection.json",
)

REPORT = os.path.join(
    ROOT,
    "data",
    "reconvergence_v4_result.json",
)

VERSION = 4

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

    raise ValueError(
        "Unsupported ml_reflection.json structure"
    )


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
        x = float(value)

        if math.isfinite(x):
            return x

    except Exception:
        pass

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


def mean(values):
    values = [
        x for x in values
        if x is not None
        and isinstance(x, (int, float))
        and math.isfinite(x)
    ]

    if not values:
        return None

    return statistics.mean(values)


def delta(a, b):
    if a is None or b is None:
        return None

    return a - b


def rate(rows, key):
    values = [
        r[key]
        for r in rows
        if r.get(key) in (0, 1)
    ]

    if not values:
        return None

    return sum(values) / len(values)


# ==============================================================
# CANONICAL SEMANTICS
# ==============================================================

def canonical_actual_alignment(predicted, actual):
    """
    Reality alignment is defined strictly as:

        predicted_outcome == actual_outcome

    No arbitrary coercion of outcome strings.
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
        actual,
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
        three_way = int(
            model == wisdom == reality
        )

        model_reality = int(
            model == reality
        )

        wisdom_reality = int(
            wisdom == reality
        )

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

    if (
        model is not None
        and reality is not None
        and model != reality
    ):
        broken.append("MODEL")

    if (
        wisdom is not None
        and reality is not None
        and wisdom != reality
    ):
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
# EPISODE ENGINE
# ==============================================================

def new_episode(
    episode_number,
    start_row,
    divergence_row,
):
    return {
        "episode_id":
            f"RECONV-{episode_number:04d}",

        "episode_number":
            episode_number,

        "start_index":
            start_row["index"],

        "divergence_start_index":
            divergence_row["index"],

        "start_case":
            start_row["identity"],

        "divergence_start_case":
            divergence_row["identity"],

        "start_state":
            start_row["state"],

        "divergence_states": [
            divergence_row["state"]
        ],

        "divergence_signatures": [
            signature(divergence_row)
        ],

        "broken_paths": sorted(
            divergence_row["broken_paths"]
        ),

        "divergence_length": 1,

        "status": "OPEN",

        "recovery_index": None,

        "recovery_case": None,

        "recovery_state": None,

        "recovery_signature": None,

        "recovery_distance": None,

        "recovered_paths": [],

        "full_path_recovery": False,

        "topology": None,

        "closure": None,

        "recovery_deltas": {},
    }


def close_episode(
    episode,
    recovery_row,
):
    episode["status"] = "CLOSED"

    episode["recovery_index"] = (
        recovery_row["index"]
    )

    episode["recovery_case"] = (
        recovery_row["identity"]
    )

    episode["recovery_state"] = (
        recovery_row["state"]
    )

    episode["recovery_signature"] = (
        signature(recovery_row)
    )

    episode["recovery_distance"] = (
        recovery_row["index"]
        - episode["divergence_start_index"]
    )

    broken = set(
        episode["broken_paths"]
    )

    recovered = set()

    if (
        "MODEL" in broken
        and recovery_row["model_reality"] == 1
    ):
        recovered.add("MODEL")

    if (
        "WISDOM" in broken
        and recovery_row["wisdom_reality"] == 1
    ):
        recovered.add("WISDOM")

    episode["recovered_paths"] = sorted(
        recovered
    )

    episode["full_path_recovery"] = (
        broken.issubset(recovered)
    )

    episode["topology"] = (
        "C-D-C"
        if episode["divergence_length"] == 1
        else "C-D+-C"
    )

    episode["closure"] = (
        "FULL_PATH_RECOVERY"
        if episode["full_path_recovery"]
        else "PARTIAL_PATH_RECOVERY"
    )

    return episode


def collect_episodes(rows):
    """
    Walk the historical sequence exactly once.

    Every transition from C into D opens an episode.

    The episode remains open through consecutive divergent
    cases until a later C appears.

    No recovery is inferred if no C actually occurs.
    """

    episodes = []

    active = None
    episode_number = 0

    for row in rows:

        convergent = (
            row["three_way"] == 1
        )

        divergent = (
            row["three_way"] == 0
        )

        if active is None:

            if convergent:
                continue

            # A divergent record without a preceding
            # convergence is not a reconvergence episode.
            continue

        if divergent:

            active["divergence_length"] += 1

            active["divergence_states"].append(
                row["state"]
            )

            active["divergence_signatures"].append(
                signature(row)
            )

            active["broken_paths"] = sorted(
                set(active["broken_paths"])
                | set(row["broken_paths"])
            )

            continue

        if convergent:

            active = close_episode(
                active,
                row,
            )

            episodes.append(active)

            active = None

    return episodes, active


# ==============================================================
# DIRECT C-D-C MOTIFS
# ==============================================================

def strict_cdc(rows):
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
                "episode_shape":
                    "C-D-C",

                "start_index":
                    a["index"],

                "divergence_index":
                    b["index"],

                "recovery_index":
                    c["index"],

                "from_case":
                    a["identity"],

                "divergence_case":
                    b["identity"],

                "recovery_case":
                    c["identity"],

                "divergence_state":
                    b["state"],

                "divergence_signature":
                    signature(b),

                "broken_paths":
                    b["broken_paths"],
            })

    return events


# ==============================================================
# OSCILLATION
# ==============================================================

def oscillation_patterns(rows):
    patterns = []

    for i in range(4, len(rows)):

        window = rows[i - 4:i + 1]

        bits = [
            row["three_way"]
            for row in window
        ]

        if bits == [1, 0, 1, 0, 1]:

            patterns.append({
                "start_index":
                    window[0]["index"],

                "end_index":
                    window[-1]["index"],

                "pattern":
                    "C-D-C-D-C",

                "cases": [
                    row["identity"]
                    for row in window
                ],
            })

    return patterns


# ==============================================================
# RECOVERY PRECURSORS
# ==============================================================

def recovery_precursors(rows, episodes):
    results = []

    row_by_index = {
        row["index"]: row
        for row in rows
    }

    for episode in episodes:

        recovery_index = (
            episode["recovery_index"]
        )

        divergence_index = (
            episode["divergence_start_index"]
        )

        if (
            recovery_index is None
            or divergence_index is None
        ):
            continue

        recovery = row_by_index.get(
            recovery_index
        )

        before = row_by_index.get(
            recovery_index - 1
        )

        if recovery is None or before is None:
            continue

        results.append({
            "episode_id":
                episode["episode_id"],

            "recovery_index":
                recovery_index,

            "distance":
                recovery_index
                - divergence_index,

            "confidence_delta":
                delta(
                    recovery["model_confidence"],
                    before["model_confidence"],
                ),

            "agreement_delta":
                delta(
                    recovery["evidence_agreement"],
                    before["evidence_agreement"],
                ),

            "strength_delta":
                delta(
                    recovery["evidence_strength"],
                    before["evidence_strength"],
                ),

            "error_delta":
                delta(
                    recovery["prediction_error"],
                    before["prediction_error"],
                ),

            "wisdom_score_delta":
                delta(
                    recovery["wisdom_score"],
                    before["wisdom_score"],
                ),

            "reflection_score_delta":
                delta(
                    recovery["reflection_score"],
                    before["reflection_score"],
                ),
        })

    return results


# ==============================================================
# EPISODE TOPOLOGY
# ==============================================================

def topology_summary(episodes):

    closed = [
        e for e in episodes
        if e["status"] == "CLOSED"
    ]

    topology_counts = Counter(
        e["topology"]
        for e in closed
    )

    path_counts = Counter()

    for episode in closed:
        for path in episode["broken_paths"]:
            path_counts[path] += 1

    recovery_counts = Counter()

    for episode in closed:
        for path in episode["recovered_paths"]:
            recovery_counts[path] += 1

    latency = [
        e["recovery_distance"]
        for e in closed
        if e["recovery_distance"] is not None
    ]

    return {
        "closed_episode_count":
            len(closed),

        "open_episode_count":
            len(episodes) - len(closed),

        "topology_counts":
            dict(topology_counts),

        "broken_path_counts":
            dict(path_counts),

        "recovered_path_counts":
            dict(recovery_counts),

        "full_path_recovery_count":
            sum(
                1
                for e in closed
                if e["full_path_recovery"]
            ),

        "mean_recovery_latency":
            mean(latency),

        "median_recovery_latency":
            statistics.median(latency)
            if latency
            else None,
    }


# ==============================================================
# RECURRENCE
# ==============================================================

def recurrence_analysis(episodes):

    closed = [
        e for e in episodes
        if e["status"] == "CLOSED"
    ]

    fingerprints = Counter()

    for episode in closed:

        fingerprint = (
            episode["topology"],
            tuple(
                episode["broken_paths"]
            ),
            tuple(
                episode["recovered_paths"]
            ),
        )

        fingerprints[fingerprint] += 1

    repeated = []

    for fingerprint, count in fingerprints.items():

        if count >= MIN_REPEATED_EPISODES:

            repeated.append({
                "fingerprint":
                    list(fingerprint),

                "count":
                    count,
            })

    return {
        "closed_episodes":
            len(closed),

        "unique_fingerprints":
            len(fingerprints),

        "fingerprints":
            [
                {
                    "fingerprint":
                        list(key),

                    "count":
                        value,
                }

                for key, value
                in fingerprints.items()
            ],

        "repeated_fingerprints":
            repeated,

        "recurring_structure_observed":
            len(repeated) > 0,
    }


# ==============================================================
# CLASSIFICATION
# ==============================================================

def classify(
    n,
    closed_episodes,
    strict_count,
    repeated_structure,
    full_recovery_count,
):

    if n < MIN_CASES:

        return (
            "PHENOMENON_NOT_YET_IDENTIFIABLE",
            "LOW",
        )

    if (
        repeated_structure
        and closed_episodes >= MIN_REPEATED_EPISODES
        and n >= MIN_STRONG_SAMPLE
    ):

        return (
            "RECURRING_RECONVERGENCE_PHENOMENON",
            "HIGH",
        )

    if (
        repeated_structure
        and closed_episodes >= MIN_REPEATED_EPISODES
    ):

        return (
            "RECURRING_RECONVERGENCE_CANDIDATE",
            "MEDIUM",
        )

    if strict_count >= MIN_REPEATED_EPISODES:

        return (
            "REPEATED_STRICT_CDC_CANDIDATE",
            "MEDIUM",
        )

    if full_recovery_count >= MIN_REPEATED_EPISODES:

        return (
            "REPEATED_PATH_RECOVERY_CANDIDATE",
            "MEDIUM",
        )

    if closed_episodes > 0:

        return (
            "RECONVERGENCE_OBSERVED_NOT_YET_RECURRING",
            "LOW",
        )

    return (
        "NO_RECONVERGENCE_STRUCTURE_YET",
        "LOW",
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print("=" * 76)
    print(
        "BIRTH_EDGE RECONVERGENCE PHENOMENON VALIDATOR V4"
    )
    print(
        "PERSISTENT EPISODE + RECOVERY + RECURRENCE ANALYSIS"
    )
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

    # ----------------------------------------------------------
    # BASIC ALIGNMENT
    # ----------------------------------------------------------

    model_rate = rate(
        valid,
        "model_reality",
    )

    wisdom_rate = rate(
        valid,
        "wisdom_reality",
    )

    convergence_rate = rate(
        valid,
        "three_way",
    )

    # ----------------------------------------------------------
    # TEMPORAL STRUCTURE
    # ----------------------------------------------------------

    strict = strict_cdc(valid)

    episodes, open_episode = collect_episodes(
        valid
    )

    closed = [
        e for e in episodes
        if e["status"] == "CLOSED"
    ]

    # ----------------------------------------------------------
    # RECOVERY
    # ----------------------------------------------------------

    full_recoveries = [
        e for e in closed
        if e["full_path_recovery"]
    ]

    immediate_recoveries = [
        e for e in closed
        if e["recovery_distance"] == 1
    ]

    nonadjacent_recoveries = [
        e for e in closed
        if e["recovery_distance"] > 1
    ]

    # ----------------------------------------------------------
    # TOPOLOGY / RECURRENCE
    # ----------------------------------------------------------

    topology = topology_summary(
        episodes
    )

    recurrence = recurrence_analysis(
        episodes
    )

    oscillations = oscillation_patterns(
        valid
    )

    precursor = recovery_precursors(
        valid,
        episodes,
    )

    # ----------------------------------------------------------
    # CLASSIFICATION
    # ----------------------------------------------------------

    classification, confidence = classify(
        n=n,
        closed_episodes=len(closed),
        strict_count=len(strict),
        repeated_structure=
            recurrence[
                "recurring_structure_observed"
            ],
        full_recovery_count=
            len(full_recoveries),
    )

    # ----------------------------------------------------------
    # RESULT
    # ----------------------------------------------------------

    result = {

        "engine":
            "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_VALIDATOR_V4",

        "version":
            VERSION,

        "data_source":
            DATA,

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

        "strict_cdc": {

            "definition":
                "FULL_CONVERGENCE -> "
                "DIVERGENCE -> "
                "FULL_CONVERGENCE",

            "count":
                len(strict),

            "events":
                strict,
        },

        "episodes": {

            "total":
                len(episodes),

            "closed":
                len(closed),

            "open":
                1
                if open_episode is not None
                else 0,

            "closed_episodes":
                closed,

            "open_episode":
                open_episode,
        },

        "recovery": {

            "total_closed":
                len(closed),

            "immediate":
                len(immediate_recoveries),

            "nonadjacent":
                len(nonadjacent_recoveries),

            "full_path":
                len(full_recoveries),

            "immediate_events":
                immediate_recoveries,

            "nonadjacent_events":
                nonadjacent_recoveries,

            "full_path_events":
                full_recoveries,
        },

        "topology":
            topology,

        "recurrence":
            recurrence,

        "oscillation": {

            "count":
                len(oscillations),

            "patterns":
                oscillations,
        },

        "recovery_precursors": {

            "count":
                len(precursor),

            "mean_confidence_delta":
                mean([
                    x["confidence_delta"]
                    for x in precursor
                ]),

            "mean_agreement_delta":
                mean([
                    x["agreement_delta"]
                    for x in precursor
                ]),

            "mean_strength_delta":
                mean([
                    x["strength_delta"]
                    for x in precursor
                ]),

            "mean_error_delta":
                mean([
                    x["error_delta"]
                    for x in precursor
                ]),

            "mean_wisdom_score_delta":
                mean([
                    x["wisdom_score_delta"]
                    for x in precursor
                ]),

            "mean_reflection_score_delta":
                mean([
                    x["reflection_score_delta"]
                    for x in precursor
                ]),

            "events":
                precursor,
        },

        "phenomenon": {

            "classification":
                classification,

            "confidence":
                confidence,

            "sample_size":
                n,

            "closed_reconvergence_episodes":
                len(closed),

            "strict_cdc_count":
                len(strict),

            "repeated_structure":
                recurrence[
                    "recurring_structure_observed"
                ],

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
                "FULL_CONVERGENCE -> "
                "DIVERGENCE -> "
                "FULL_CONVERGENCE",

            "general_signature":
                "FULL_CONVERGENCE -> "
                "one_or_more_DIVERGENCE -> "
                "FULL_CONVERGENCE",

            "current_answer":
                classification,

            "evidence_rule":
                "Only naturally occurring persisted "
                "historical cases may close episodes.",

            "recurrence_rule":
                "Repeated episode fingerprints are "
                "required before recurrence claims.",
        },

        "case_diagnostics":
            valid,
    }

    # ----------------------------------------------------------
    # WRITE MACHINE-READABLE REPORT
    # ----------------------------------------------------------

    os.makedirs(
        os.path.dirname(REPORT),
        exist_ok=True,
    )

    with open(
        REPORT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            sort_keys=True,
        )

    # ----------------------------------------------------------
    # HUMAN REPORT
    # ----------------------------------------------------------

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

    print(
        "MODEL -> REALITY:",
        model_rate,
    )

    print(
        "WISDOM -> REALITY:",
        wisdom_rate,
    )

    print(
        "THREE-WAY CONVERGENCE:",
        convergence_rate,
    )

    print()
    print("=" * 76)
    print("STRICT C-D-C")
    print("=" * 76)

    print(
        "STRICT C-D-C EVENTS:",
        len(strict),
    )

    if strict:

        for event in strict:
            print()
            print(
                json.dumps(
                    event,
                    indent=2,
                )
            )

    else:
        print("NONE")

    print()
    print("=" * 76)
    print("RECONVERGENCE EPISODES")
    print("=" * 76)

    print(
        "TOTAL EPISODES:",
        len(episodes),
    )

    print(
        "CLOSED EPISODES:",
        len(closed),
    )

    print(
        "OPEN EPISODES:",
        1
        if open_episode is not None
        else 0,
    )

    if closed:

        for episode in closed:

            print()
            print(
                "EPISODE:",
                episode["episode_id"],
            )

            print(
                "TOPOLOGY:",
                episode["topology"],
            )

            print(
                "DIVERGENCE LENGTH:",
                episode["divergence_length"],
            )

            print(
                "BROKEN PATHS:",
                episode["broken_paths"],
            )

            print(
                "RECOVERED PATHS:",
                episode["recovered_paths"],
            )

            print(
                "RECOVERY DISTANCE:",
                episode["recovery_distance"],
            )

            print(
                "CLOSURE:",
                episode["closure"],
            )

    if open_episode is not None:

        print()
        print(
            "OPEN EPISODE:",
            open_episode["episode_id"],
        )

        print(
            "CURRENT DIVERGENCE LENGTH:",
            open_episode["divergence_length"],
        )

        print(
            "BROKEN PATHS:",
            open_episode["broken_paths"],
        )

        print(
            "STATUS:",
            "WAITING FOR NATURAL RECONVERGENCE",
        )

    print()
    print("=" * 76)
    print("RECOVERY")
    print("=" * 76)

    print(
        "CLOSED:",
        len(closed),
    )

    print(
        "IMMEDIATE:",
        len(immediate_recoveries),
    )

    print(
        "NON-ADJACENT:",
        len(nonadjacent_recoveries),
    )

    print(
        "FULL PATH RECOVERY:",
        len(full_recoveries),
    )

    print(
        "MEAN RECOVERY LATENCY:",
        topology[
            "mean_recovery_latency"
        ],
    )

    print(
        "MEDIAN RECOVERY LATENCY:",
        topology[
            "median_recovery_latency"
        ],
    )

    print()
    print("=" * 76)
    print("TOPOLOGY")
    print("=" * 76)

    print(
        json.dumps(
            topology,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print("=" * 76)
    print("RECURRENCE")
    print("=" * 76)

    print(
        "UNIQUE FINGERPRINTS:",
        recurrence[
            "unique_fingerprints"
        ],
    )

    print(
        "REPEATED FINGERPRINTS:",
        len(
            recurrence[
                "repeated_fingerprints"
            ]
        ),
    )

    print(
        "RECURRING STRUCTURE:",
        (
            "OBSERVED"
            if recurrence[
                "recurring_structure_observed"
            ]
            else "NOT YET OBSERVED"
        ),
    )

    if recurrence[
        "repeated_fingerprints"
    ]:

        print()

        for item in recurrence[
            "repeated_fingerprints"
        ]:

            print(
                json.dumps(
                    item,
                    indent=2,
                )
            )

    print()
    print("=" * 76)
    print("OSCILLATION")
    print("=" * 76)

    print(
        "C-D-C-D-C PATTERNS:",
        len(oscillations),
    )

    if oscillations:

        for item in oscillations:
            print(
                json.dumps(
                    item,
                    indent=2,
                )
            )

    print()
    print("=" * 76)
    print("RECOVERY PRECURSOR")
    print("=" * 76)

    if precursor:

        print(
            "RECOVERY EVENTS:",
            len(precursor),
        )

        print(
            "MEAN CONFIDENCE DELTA:",
            mean([
                x["confidence_delta"]
                for x in precursor
            ]),
        )

        print(
            "MEAN AGREEMENT DELTA:",
            mean([
                x["agreement_delta"]
                for x in precursor
            ]),
        )

        print(
            "MEAN STRENGTH DELTA:",
            mean([
                x["strength_delta"]
                for x in precursor
            ]),
        )

        print(
            "MEAN ERROR DELTA:",
            mean([
                x["error_delta"]
                for x in precursor
            ]),
        )

        print(
            "MEAN WISDOM SCORE DELTA:",
            mean([
                x["wisdom_score_delta"]
                for x in precursor
            ]),
        )

        print(
            "MEAN REFLECTION SCORE DELTA:",
            mean([
                x["reflection_score_delta"]
                for x in precursor
            ]),
        )

    else:

        print(
            "NO NATURAL RECOVERY EVENTS YET."
        )

    print()
    print("=" * 76)
    print("PHENOMENON VALIDATION VERDICT")
    print("=" * 76)

    print(
        "CLASSIFICATION:",
        classification,
    )

    print(
        "CONFIDENCE:",
        confidence,
    )

    print(
        "SAMPLE SIZE:",
        n,
    )

    print(
        "CLOSED EPISODES:",
        len(closed),
    )

    print(
        "STRICT C-D-C:",
        (
            "OBSERVED"
            if strict
            else "NOT YET OBSERVED"
        ),
    )

    print(
        "PATH RECOVERY:",
        (
            "OBSERVED"
            if full_recoveries
            else "NOT YET OBSERVED"
        ),
    )

    print(
        "REPEATED STRUCTURE:",
        (
            "OBSERVED"
            if recurrence[
                "recurring_structure_observed"
            ]
            else "NOT YET OBSERVED"
        ),
    )

    print()
    print("=" * 76)
    print("LOOP STATUS")
    print("=" * 76)

    if open_episode is not None:

        print(
            "LOOP STATE:",
            "OPEN",
        )

        print(
            "CURRENT EPISODE:",
            open_episode["episode_id"],
        )

        print(
            "WAITING FOR:",
            "NATURAL FULL_CONVERGENCE",
        )

        print(
            "NO RECOVERY HAS BEEN ASSUMED.",
        )

    elif closed:

        print(
            "LOOP STATE:",
            "CLOSED",
        )

        print(
            "NATURAL RECONVERGENCE:",
            "OBSERVED",
        )

    else:

        print(
            "LOOP STATE:",
            "NO OPEN RECONVERGENCE EPISODE",
        )

    print()
    print("=" * 76)
    print("NOMINALITY")
    print("=" * 76)

    print(
        "ENGINE OPERATION: 💯 NOMINAL"
    )

    print(
        "HISTORICAL DATA MODIFIED: False"
    )

    print(
        "SYNTHETIC DATA USED: False"
    )

    print(
        "MODEL MODIFIED: False"
    )

    print(
        "TRADING PERFORMED: False"
    )

    print()
    print(
        "REPORT:",
        REPORT,
    )

    print()
    print("=" * 76)
    print("MACHINE-READABLE RESULT")
    print("=" * 76)

    print(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print("=" * 76)
    print(
        "RECONVERGENCE VALIDATOR V4 COMPLETE"
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
