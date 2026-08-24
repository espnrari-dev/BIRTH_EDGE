#!/usr/bin/env python3

"""
BIRTH_EDGE — RECONVERGENCE GAUNTLET V1

Research-grade temporal-structure attack suite.

Purpose
-------
Determine whether FULL_CONVERGENCE -> DIVERGENCE -> FULL_CONVERGENCE
and related temporal motifs contain structure that survives:

    * temporal permutation
    * label permutation
    * base-rate correction
    * Markov null comparison
    * motif discovery
    * leave-one-out analysis
    * bootstrap resampling
    * chronological split testing
    * transition-information analysis
    * recovery-hazard analysis
    * path-specific recovery analysis

STRICT RULES
------------
1. Only persisted BIRTH_EDGE historical records are loaded.
2. The source dataset is never modified.
3. No synthetic observations are inserted into the source dataset.
4. No model is modified.
5. No trading is performed.
6. Null data exist only in memory for statistical testing.
7. Every statistical claim identifies its null model.
8. Small samples are explicitly reported rather than hidden.
9. No phenomenon is declared merely because one motif occurred.
"""

import json
import math
import os
import random
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
    "reconvergence_gauntlet_v1_result.json",
)

SEED = 20260822

PERMUTATIONS = 5000
BOOTSTRAPS = 3000

MIN_CASES = 20
MIN_REPLICATION_CASES = 20

MAX_MOTIF_LENGTH = 8


# ==============================================================
# IO
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


# ==============================================================
# SEMANTICS
# ==============================================================

def bit(value):
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return int(value != 0)

    if isinstance(value, str):
        s = value.strip().lower()

        if s in {
            "1", "true", "yes", "correct", "pass",
            "passed", "success", "successful",
            "aligned", "win", "winner",
        }:
            return 1

        if s in {
            "0", "false", "no", "wrong", "fail",
            "failed", "failure", "diverged",
            "loss", "lost",
        }:
            return 0

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


def inspect_record(record, index):
    predicted = record.get("predicted_outcome")
    actual = record.get("actual_outcome")

    model = bit(record.get("correct"))
    wisdom = bit(record.get("wisdom_correct"))

    if predicted is None or actual is None:
        reality = None
    else:
        reality = int(predicted == actual)

    if (
        model is None
        or wisdom is None
        or reality is None
    ):
        return None

    three_way = int(
        model == wisdom == reality
    )

    if three_way:
        state = "C"
    else:
        state = "D"

    broken = []

    if model != reality:
        broken.append("MODEL")

    if wisdom != reality:
        broken.append("WISDOM")

    return {
        "index": index,
        "identity": identity(record, index),

        "model": model,
        "wisdom": wisdom,
        "reality": reality,

        "three_way": three_way,
        "state": state,

        "broken_paths": broken,

        "model_confidence": record.get(
            "model_confidence"
        ),
        "prediction_error": record.get(
            "prediction_error"
        ),
        "evidence_agreement": record.get(
            "evidence_agreement"
        ),
        "evidence_strength": record.get(
            "evidence_strength"
        ),
        "wisdom_score": record.get(
            "wisdom_score"
        ),
        "reflection_score": record.get(
            "reflection_score"
        ),
    }


# ==============================================================
# NUMERIC HELPERS
# ==============================================================

def finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def mean(values):
    values = [
        finite(x)
        for x in values
    ]
    values = [
        x for x in values
        if x is not None
    ]

    if not values:
        return None

    return statistics.mean(values)


def median(values):
    values = [
        finite(x)
        for x in values
    ]
    values = [
        x for x in values
        if x is not None
    ]

    if not values:
        return None

    return statistics.median(values)


def safe_rate(n, d):
    if d == 0:
        return None
    return n / d


# ==============================================================
# SEQUENCE BASICS
# ==============================================================

def states(rows):
    return [
        row["three_way"]
        for row in rows
    ]


def state_string(seq):
    return "".join(
        "C" if x else "D"
        for x in seq
    )


def count_pattern(seq, pattern):
    n = len(pattern)

    if len(seq) < n:
        return 0

    return sum(
        1
        for i in range(
            len(seq) - n + 1
        )
        if seq[i:i + n] == pattern
    )


def motif_counts(seq, max_length=8):
    result = {}

    for length in range(2, max_length + 1):
        counter = Counter()

        for i in range(
            len(seq) - length + 1
        ):
            motif = state_string(
                seq[i:i + length]
            )
            counter[motif] += 1

        result[str(length)] = dict(
            sorted(
                counter.items(),
                key=lambda x: (-x[1], x[0]),
            )
        )

    return result


# ==============================================================
# RECONVERGENCE METRICS
# ==============================================================

def direct_cdc(seq):
    return count_pattern(
        seq,
        [1, 0, 1],
    )


def generalized_reconvergence(seq):
    """
    C -> one or more D -> C
    """

    events = []

    i = 0

    while i < len(seq) - 2:

        if seq[i] != 1:
            i += 1
            continue

        j = i + 1

        if seq[j] != 0:
            i += 1
            continue

        while (
            j < len(seq)
            and seq[j] == 0
        ):
            j += 1

        if (
            j < len(seq)
            and seq[j] == 1
        ):
            events.append({
                "start": i,
                "recovery": j,
                "distance": j - i - 1,
            })

            i = j
        else:
            i = j

    return events


def recovery_latency(seq):
    return [
        event["distance"]
        for event in generalized_reconvergence(seq)
    ]


def transition_counts(seq):
    out = Counter()

    for a, b in zip(
        seq,
        seq[1:],
    ):
        out[
            f"{'C' if a else 'D'}->"
            f"{'C' if b else 'D'}"
        ] += 1

    return dict(out)


def transition_probabilities(seq):
    counts = Counter()

    for a, b in zip(seq, seq[1:]):
        counts[(a, b)] += 1

    out = {}

    for source in (0, 1):
        total = sum(
            counts[(source, target)]
            for target in (0, 1)
        )

        if total:
            out[
                "C" if source else "D"
            ] = {
                "to_C":
                    counts[(source, 1)]
                    / total,
                "to_D":
                    counts[(source, 0)]
                    / total,
            }

    return out


# ==============================================================
# BASE-RATE EXPECTATION
# ==============================================================

def independent_expected_cdc(seq):
    """
    IID base-rate expectation.

    E[C-D-C] =
        P(C) * P(D) * P(C)
        times number of possible windows.
    """

    n = len(seq)

    if n < 3:
        return None

    p_c = sum(seq) / n
    p_d = 1 - p_c

    windows = n - 2

    return (
        windows
        * p_c
        * p_d
        * p_c
    )


def base_rate_report(seq):
    observed = direct_cdc(seq)
    expected = independent_expected_cdc(seq)

    ratio = None

    if (
        expected is not None
        and expected > 0
    ):
        ratio = observed / expected

    return {
        "sample_size": len(seq),
        "convergence_rate":
            safe_rate(
                sum(seq),
                len(seq),
            ),
        "divergence_rate":
            safe_rate(
                len(seq) - sum(seq),
                len(seq),
            ),
        "observed_cdc": observed,
        "iid_expected_cdc": expected,
        "observed_to_expected_ratio": ratio,
    }


# ==============================================================
# MARKOV TEST
# ==============================================================

def markov_cdc_expected(seq):
    """
    First-order Markov expected C-D-C count.

    Estimates transition probabilities from
    the observed sequence, then predicts expected
    C-D-C windows under that Markov structure.
    """

    if len(seq) < 3:
        return None

    counts = Counter(
        zip(seq, seq[1:])
    )

    row_totals = {
        source: sum(
            counts[(source, target)]
            for target in (0, 1)
        )
        for source in (0, 1)
    }

    if (
        row_totals[1] == 0
        or row_totals[0] == 0
    ):
        return None

    p_cc = counts[(1, 1)] / row_totals[1]
    p_cd = counts[(1, 0)] / row_totals[1]
    p_dc = counts[(0, 1)] / row_totals[0]

    stationary_c = None

    denominator = (
        p_dc + p_cd
    )

    if denominator > 0:
        stationary_c = (
            p_dc / denominator
        )

    if stationary_c is None:
        return None

    expected = (
        (len(seq) - 2)
        * stationary_c
        * p_cd
        * p_dc
    )

    return {
        "stationary_C":
            stationary_c,
        "P_C_to_D":
            p_cd,
        "P_D_to_C":
            p_dc,
        "expected_cdc":
            expected,
        "observed_cdc":
            direct_cdc(seq),
        "ratio":
            (
                direct_cdc(seq) / expected
                if expected > 0
                else None
            ),
    }


# ==============================================================
# PERMUTATION TESTS
# ==============================================================

def permutation_test(
    seq,
    statistic,
    permutations,
    rng,
    mode="shuffle",
):
    observed = statistic(seq)

    if observed is None:
        return {
            "observed": None,
            "permutations": 0,
            "p_value": None,
        }

    values = []

    for _ in range(permutations):

        shuffled = list(seq)

        rng.shuffle(shuffled)

        values.append(
            statistic(shuffled)
        )

    if not values:
        return {
            "observed": observed,
            "permutations": 0,
            "p_value": None,
        }

    extreme = sum(
        1
        for x in values
        if x >= observed
    )

    p = (
        extreme + 1
    ) / (
        len(values) + 1
    )

    return {
        "observed": observed,
        "permutations": len(values),
        "null_mean": mean(values),
        "null_median": median(values),
        "null_max": max(values),
        "null_min": min(values),
        "p_value": p,
    }


def cdc_stat(seq):
    return direct_cdc(seq)


def reconvergence_stat(seq):
    return len(
        generalized_reconvergence(seq)
    )


def long_recovery_stat(seq):
    return sum(
        1
        for e in generalized_reconvergence(seq)
        if e["distance"] > 1
    )


# ==============================================================
# RUN-LENGTH / RECOVERY HAZARD
# ==============================================================

def recovery_hazard(seq):
    """
    For each divergence run length L, calculate:

        P(C next | currently in D run of length L)
    """

    opportunities = Counter()
    recoveries = Counter()

    i = 0

    while i < len(seq) - 1:

        if seq[i] != 1:
            i += 1
            continue

        j = i + 1

        while (
            j < len(seq)
            and seq[j] == 0
        ):
            j += 1

        run_length = j - i - 1

        if run_length > 0:

            if j < len(seq):
                opportunities[run_length] += 1

                if seq[j] == 1:
                    recoveries[run_length] += 1

        i = j

    result = {}

    for length in sorted(opportunities):
        result[str(length)] = {
            "opportunities":
                opportunities[length],
            "recoveries":
                recoveries[length],
            "hazard":
                recoveries[length]
                / opportunities[length],
        }

    return result


# ==============================================================
# INFORMATION THEORY
# ==============================================================

def entropy(probabilities):
    total = sum(probabilities)

    if total <= 0:
        return 0.0

    value = 0.0

    for count in probabilities:
        if count <= 0:
            continue

        p = count / total
        value -= p * math.log2(p)

    return value


def mutual_information_lag(
    seq,
    lag,
):
    if len(seq) <= lag:
        return None

    joint = Counter()

    for i in range(
        len(seq) - lag
    ):
        joint[
            (seq[i], seq[i + lag])
        ] += 1

    total = sum(joint.values())

    if total == 0:
        return None

    x = Counter()
    y = Counter()

    for (
        (a, b),
        count,
    ) in joint.items():
        x[a] += count
        y[b] += count

    mi = 0.0

    for (
        (a, b),
        count,
    ) in joint.items():

        pxy = count / total
        px = x[a] / total
        py = y[b] / total

        mi += (
            pxy
            * math.log2(
                pxy / (px * py)
            )
        )

    return mi


def information_profile(seq):
    return {
        str(lag): mutual_information_lag(
            seq,
            lag,
        )
        for lag in range(
            1,
            min(len(seq), 12),
        )
    }


# ==============================================================
# TEMPORAL DESTRUCTION
# ==============================================================

def temporal_destruction(seq):
    """
    Compare original sequence to its shuffled
    temporal order while preserving the exact
    C/D marginal distribution.
    """

    if not seq:
        return {}

    rng = random.Random(SEED + 77)

    shuffled = list(seq)

    rng.shuffle(shuffled)

    return {
        "original":
            state_string(seq),
        "destroyed":
            state_string(shuffled),

        "original_cdc":
            direct_cdc(seq),
        "destroyed_cdc":
            direct_cdc(shuffled),

        "original_reconvergence":
            len(
                generalized_reconvergence(seq)
            ),
        "destroyed_reconvergence":
            len(
                generalized_reconvergence(
                    shuffled
                )
            ),
    }


# ==============================================================
# BOOTSTRAP
# ==============================================================

def bootstrap_metric(
    seq,
    statistic,
    iterations,
    rng,
):
    if len(seq) < 2:
        return {
            "observed": statistic(seq),
            "iterations": 0,
            "lower": None,
            "upper": None,
        }

    values = []

    for _ in range(iterations):

        sample = [
            seq[
                rng.randrange(
                    len(seq)
                )
            ]
            for _ in range(len(seq))
        ]

        values.append(
            statistic(sample)
        )

    values.sort()

    lo = values[
        int(0.025 * len(values))
    ]

    hi = values[
        min(
            len(values) - 1,
            int(0.975 * len(values)),
        )
    ]

    return {
        "observed": statistic(seq),
        "iterations": iterations,
        "mean": mean(values),
        "median": median(values),
        "lower_95": lo,
        "upper_95": hi,
    }


# ==============================================================
# LEAVE-ONE-OUT
# ==============================================================

def leave_one_out(
    seq,
    statistic,
):
    if len(seq) < 3:
        return {
            "cases": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "values": [],
        }

    values = []

    for i in range(len(seq)):

        reduced = (
            seq[:i]
            + seq[i + 1:]
        )

        values.append(
            statistic(reduced)
        )

    return {
        "cases": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "mean": mean(values),
        "values": values,
    }


# ==============================================================
# EPISODE INDEPENDENCE
# ==============================================================

def episode_details(rows):
    seq = states(rows)

    events = []

    for event in generalized_reconvergence(seq):

        start = event["start"]
        recovery = event["recovery"]

        events.append({
            "start_index":
                rows[start]["index"],
            "recovery_index":
                rows[recovery]["index"],
            "distance":
                event["distance"],
            "start_case":
                rows[start]["identity"],
            "recovery_case":
                rows[recovery]["identity"],
        })

    return events


# ==============================================================
# PATH-SPECIFIC RECOVERY
# ==============================================================

def path_recovery(rows):
    events = []

    for i in range(len(rows)):

        if rows[i]["three_way"] != 1:
            continue

        j = i + 1

        if (
            j >= len(rows)
            or rows[j]["three_way"] == 1
        ):
            continue

        broken = set()

        while (
            j < len(rows)
            and rows[j]["three_way"] == 0
        ):
            broken.update(
                rows[j]["broken_paths"]
            )
            j += 1

        if j >= len(rows):
            continue

        recovered = set()

        recovery = rows[j]

        if (
            "MODEL" in broken
            and recovery["model"] == recovery["reality"]
        ):
            recovered.add("MODEL")

        if (
            "WISDOM" in broken
            and recovery["wisdom"] == recovery["reality"]
        ):
            recovered.add("WISDOM")

        events.append({
            "start":
                rows[i]["index"],
            "recovery":
                recovery["index"],
            "broken":
                sorted(broken),
            "recovered":
                sorted(recovered),
            "full":
                broken.issubset(recovered),
        })

    return events


# ==============================================================
# CHRONOLOGICAL REPLICATION
# ==============================================================

def chronological_replication(rows):
    n = len(rows)

    if n < MIN_REPLICATION_CASES:
        return {
            "eligible": False,
            "reason":
                f"Need at least "
                f"{MIN_REPLICATION_CASES} "
                f"valid cases.",
        }

    cut1 = n // 3
    cut2 = (2 * n) // 3

    early = rows[:cut1]
    middle = rows[cut1:cut2]
    late = rows[cut2:]

    def summarize(part):
        seq = states(part)

        return {
            "n": len(part),
            "convergence_rate":
                safe_rate(
                    sum(seq),
                    len(seq),
                ),
            "cdc":
                direct_cdc(seq),
            "reconvergence":
                len(
                    generalized_reconvergence(
                        seq
                    )
                ),
            "motifs":
                motif_counts(
                    seq,
                    max_length=5,
                ),
        }

    return {
        "eligible": True,
        "split": "EARLY_MIDDLE_LATE",
        "early": summarize(early),
        "middle": summarize(middle),
        "late": summarize(late),
    }


# ==============================================================
# DISCOVERY
# ==============================================================

def enriched_motifs(
    seq,
    permutations,
    rng,
):
    observed = motif_counts(
        seq,
        max_length=MAX_MOTIF_LENGTH,
    )

    discovered = []

    for length_string, counts in observed.items():

        length = int(length_string)

        for motif, observed_count in counts.items():

            if observed_count < 2:
                continue

            pattern = [
                1 if x == "C"
                else 0
                for x in motif
            ]

            null_values = []

            for _ in range(
                min(
                    permutations,
                    1000,
                )
            ):
                shuffled = list(seq)
                rng.shuffle(shuffled)

                null_values.append(
                    count_pattern(
                        shuffled,
                        pattern,
                    )
                )

            null_mean = mean(
                null_values
            )

            extreme = sum(
                x >= observed_count
                for x in null_values
            )

            p = (
                extreme + 1
            ) / (
                len(null_values) + 1
            )

            enrichment = None

            if (
                null_mean is not None
                and null_mean > 0
            ):
                enrichment = (
                    observed_count
                    / null_mean
                )

            discovered.append({
                "motif": motif,
                "length": length,
                "observed": observed_count,
                "null_mean": null_mean,
                "enrichment": enrichment,
                "p_value": p,
            })

    discovered.sort(
        key=lambda x: (
            x["p_value"],
            -(x["enrichment"] or 0),
        )
    )

    return discovered[:50]


# ==============================================================
# ADVERSARIAL ROBUSTNESS
# ==============================================================

def robustness(rows):
    seq = states(rows)

    result = {
        "original": {
            "n": len(seq),
            "cdc":
                direct_cdc(seq),
            "reconvergence":
                len(
                    generalized_reconvergence(
                        seq
                    )
                ),
        }
    }

    # Remove every position individually.
    loo_cdc = []

    for i in range(len(seq)):
        reduced = (
            seq[:i]
            + seq[i + 1:]
        )

        loo_cdc.append(
            direct_cdc(reduced)
        )

    result["leave_one_out_cdc"] = {
        "minimum": min(loo_cdc)
        if loo_cdc else None,
        "maximum": max(loo_cdc)
        if loo_cdc else None,
        "mean": mean(loo_cdc),
        "all_values": loo_cdc,
    }

    # Remove every observed episode's interior.
    events = generalized_reconvergence(seq)

    event_results = []

    for event in events:

        start = event["start"]
        recovery = event["recovery"]

        reduced = (
            seq[:start + 1]
            + seq[recovery:]
        )

        event_results.append({
            "removed_divergence_length":
                event["distance"],
            "cdc_after_removal":
                direct_cdc(reduced),
            "reconvergence_after_removal":
                len(
                    generalized_reconvergence(
                        reduced
                    )
                ),
        })

    result["episode_removal"] = event_results

    return result


# ==============================================================
# NULL COMPARISON SUITE
# ==============================================================

def null_suite(seq):
    rng = random.Random(
        SEED + 1001
    )

    return {
        "iid_temporal_permutation":
            permutation_test(
                seq,
                cdc_stat,
                PERMUTATIONS,
                rng,
            ),

        "generalized_reconvergence":
            permutation_test(
                seq,
                reconvergence_stat,
                PERMUTATIONS,
                rng,
            ),

        "long_recovery":
            permutation_test(
                seq,
                long_recovery_stat,
                PERMUTATIONS,
                rng,
            ),
    }


# ==============================================================
# VERDICT ENGINE
# ==============================================================

def verdict(
    n,
    cdc,
    reconvergence,
    cdc_p,
    reconvergence_p,
    enrichment,
    replication,
    loo,
):
    reasons = []

    if n < MIN_CASES:
        reasons.append(
            "INSUFFICIENT_HISTORICAL_SAMPLE"
        )

    if cdc == 0:
        reasons.append(
            "NO_DIRECT_CDC_OBSERVED"
        )

    if (
        cdc_p is not None
        and cdc_p < 0.05
    ):
        reasons.append(
            "CDC_SURVIVES_PERMUTATION_TEST"
        )

    if (
        reconvergence_p is not None
        and reconvergence_p < 0.05
    ):
        reasons.append(
            "GENERALIZED_RECONVERGENCE_SURVIVES_NULL"
        )

    if enrichment is not None:
        if enrichment > 2:
            reasons.append(
                "MOTIF_ENRICHMENT_GT_2X"
            )

    if loo["minimum"] == cdc and cdc > 0:
        reasons.append(
            "CDC_COUNT_ROBUST_TO_SINGLE_RECORD_REMOVAL"
        )

    if (
        replication.get("eligible")
        and replication["late"]["cdc"] > 0
    ):
        reasons.append(
            "CDC_REAPPEARS_IN_LATE_CHRONOLOGICAL_SPLIT"
        )

    if (
        n < MIN_CASES
    ):
        classification = (
            "INSUFFICIENT_DATA_FOR_PHENOMENON_CLAIM"
        )
        confidence = "LOW"

    elif (
        cdc > 0
        and cdc_p is not None
        and cdc_p < 0.01
        and reconvergence_p is not None
        and reconvergence_p < 0.01
        and (
            enrichment is None
            or enrichment > 2
        )
    ):
        classification = (
            "STRONG_TEMPORAL_RECONVERGENCE_SIGNAL"
        )
        confidence = "HIGH"

    elif (
        reconvergence > 0
        and (
            cdc_p is not None
            and cdc_p < 0.05
        )
    ):
        classification = (
            "RECONVERGENCE_SIGNAL_WORTH_REPLICATION"
        )
        confidence = "MEDIUM"

    elif reconvergence > 0:
        classification = (
            "RECONVERGENCE_OBSERVED_BUT_NULL_NOT_REJECTED"
        )
        confidence = "LOW"

    else:
        classification = (
            "NO_RECONVERGENCE_SIGNAL_DETECTED"
        )
        confidence = "LOW"

    return {
        "classification": classification,
        "confidence": confidence,
        "reasons": reasons,
    }


# ==============================================================
# MAIN
# ==============================================================

def main():

    print("=" * 78)
    print("BIRTH_EDGE — RECONVERGENCE GAUNTLET V1")
    print("TEMPORAL STRUCTURE / NULL / ROBUSTNESS ATTACK")
    print("=" * 78)

    records = load_records()

    rows = []

    for i, record in enumerate(records):

        if not isinstance(record, dict):
            continue

        row = inspect_record(
            record,
            i,
        )

        if row is not None:
            rows.append(row)

    n = len(rows)

    if n == 0:
        raise RuntimeError(
            "No semantically valid canonical cases."
        )

    seq = states(rows)

    print()
    print("HISTORICAL RECORDS:", len(records))
    print("VALID CANONICAL CASES:", n)

    print()
    print("=" * 78)
    print("1. RAW TEMPORAL STRUCTURE")
    print("=" * 78)

    print(
        "STATE SEQUENCE:",
        state_string(seq),
    )

    print(
        "CONVERGENCE RATE:",
        safe_rate(sum(seq), n),
    )

    print(
        "DIRECT C-D-C:",
        direct_cdc(seq),
    )

    print(
        "GENERALIZED C-D+-C:",
        len(
            generalized_reconvergence(seq)
        ),
    )

    print(
        "LATENCIES:",
        recovery_latency(seq),
    )

    print()
    print("=" * 78)
    print("2. BASE-RATE CORRECTION")
    print("=" * 78)

    base_rate = base_rate_report(seq)

    print(
        json.dumps(
            base_rate,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("3. FIRST-ORDER MARKOV NULL")
    print("=" * 78)

    markov = markov_cdc_expected(seq)

    print(
        json.dumps(
            markov,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("4. TRANSITION STRUCTURE")
    print("=" * 78)

    transitions = transition_counts(seq)
    probabilities = transition_probabilities(seq)

    print(
        json.dumps(
            transitions,
            indent=2,
        )
    )

    print(
        json.dumps(
            probabilities,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("5. NULL / PERMUTATION GAUNTLET")
    print("=" * 78)

    nulls = null_suite(seq)

    print(
        json.dumps(
            nulls,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("6. TEMPORAL DESTRUCTION")
    print("=" * 78)

    destruction = temporal_destruction(seq)

    print(
        json.dumps(
            destruction,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("7. MOTIF DISCOVERY")
    print("=" * 78)

    rng = random.Random(
        SEED + 202
    )

    discovered = enriched_motifs(
        seq,
        PERMUTATIONS,
        rng,
    )

    if discovered:
        for item in discovered[:20]:
            print(
                json.dumps(
                    item,
                    indent=2,
                )
            )
    else:
        print(
            "NO MOTIFS WITH >= 2 OBSERVATIONS"
        )

    print()
    print("=" * 78)
    print("8. INFORMATION-THEORETIC TEMPORAL MEMORY")
    print("=" * 78)

    information = information_profile(seq)

    print(
        json.dumps(
            information,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("9. RECOVERY HAZARD")
    print("=" * 78)

    hazard = recovery_hazard(seq)

    print(
        json.dumps(
            hazard,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("10. PATH-SPECIFIC RECOVERY")
    print("=" * 78)

    paths = path_recovery(rows)

    print(
        "PATH RECOVERY EVENTS:",
        len(paths),
    )

    for event in paths:
        print(
            json.dumps(
                event,
                indent=2,
            )
        )

    print()
    print("=" * 78)
    print("11. EPISODE INDEPENDENCE")
    print("=" * 78)

    episodes = episode_details(rows)

    print(
        "RECONVERGENCE EPISODES:",
        len(episodes),
    )

    for event in episodes:
        print(
            json.dumps(
                event,
                indent=2,
            )
        )

    print()
    print("=" * 78)
    print("12. BOOTSTRAP")
    print("=" * 78)

    bootstrap_rng = random.Random(
        SEED + 303
    )

    bootstrap = {
        "cdc":
            bootstrap_metric(
                seq,
                cdc_stat,
                BOOTSTRAPS,
                bootstrap_rng,
            ),
        "reconvergence":
            bootstrap_metric(
                seq,
                reconvergence_stat,
                BOOTSTRAPS,
                bootstrap_rng,
            ),
    }

    print(
        json.dumps(
            bootstrap,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("13. LEAVE-ONE-OUT ROBUSTNESS")
    print("=" * 78)

    loo = leave_one_out(
        seq,
        cdc_stat,
    )

    print(
        json.dumps(
            loo,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("14. ADVERSARIAL ROBUSTNESS")
    print("=" * 78)

    robustness_result = robustness(rows)

    print(
        json.dumps(
            robustness_result,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("15. CHRONOLOGICAL REPLICATION")
    print("=" * 78)

    replication = chronological_replication(
        rows
    )

    print(
        json.dumps(
            replication,
            indent=2,
        )
    )

    print()
    print("=" * 78)
    print("16. STATISTICAL DISCOVERY")
    print("=" * 78)

    best_enrichment = None

    for item in discovered:
        if (
            item["motif"]
            in {"CDC", "CDDC", "CDDDC"}
            and item["enrichment"] is not None
        ):
            if (
                best_enrichment is None
                or item["enrichment"]
                > best_enrichment
            ):
                best_enrichment = (
                    item["enrichment"]
                )

    verdict_result = verdict(
        n=n,
        cdc=direct_cdc(seq),
        reconvergence=len(
            generalized_reconvergence(seq)
        ),
        cdc_p=nulls[
            "iid_temporal_permutation"
        ]["p_value"],
        reconvergence_p=nulls[
            "generalized_reconvergence"
        ]["p_value"],
        enrichment=best_enrichment,
        replication=replication,
        loo=loo,
    )

    print(
        json.dumps(
            verdict_result,
            indent=2,
        )
    )

    # ==========================================================
    # COMPLETE REPORT
    # ==========================================================

    result = {

        "engine":
            "BIRTH_EDGE_RECONVERGENCE_GAUNTLET_V1",

        "version": 1,

        "research_question":
            "Does BIRTH_EDGE contain statistically "
            "nontrivial temporal reconvergence structure "
            "beyond what is explained by marginal "
            "base rates, temporal permutation, or "
            "simple Markov structure?",

        "data_source":
            DATA,

        "configuration": {
            "seed": SEED,
            "permutations":
                PERMUTATIONS,
            "bootstraps":
                BOOTSTRAPS,
            "minimum_cases":
                MIN_CASES,
            "maximum_motif_length":
                MAX_MOTIF_LENGTH,
        },

        "integrity": {
            "historical_records":
                len(records),
            "valid_cases":
                n,
            "source_modified":
                False,
            "synthetic_records_added_to_source":
                False,
            "model_modified":
                False,
            "trading_performed":
                False,
        },

        "raw_structure": {
            "state_sequence":
                state_string(seq),
            "sample_size":
                n,
            "convergence_rate":
                safe_rate(
                    sum(seq),
                    n,
                ),
            "direct_cdc":
                direct_cdc(seq),
            "generalized_reconvergence":
                len(
                    generalized_reconvergence(
                        seq
                    )
                ),
            "latencies":
                recovery_latency(seq),
        },

        "base_rate":
            base_rate,

        "markov":
            markov,

        "transitions": {
            "counts":
                transitions,
            "probabilities":
                probabilities,
        },

        "null_tests":
            nulls,

        "temporal_destruction":
            destruction,

        "motif_discovery": {
            "top_enriched":
                discovered,
        },

        "information_profile":
            information,

        "recovery_hazard":
            hazard,

        "path_specific_recovery":
            paths,

        "episodes":
            episodes,

        "bootstrap":
            bootstrap,

        "leave_one_out":
            loo,

        "adversarial_robustness":
            robustness_result,

        "chronological_replication":
            replication,

        "verdict":
            verdict_result,

        "interpretation_rules": {
            "strong_signal":
                "Observed reconvergence must exceed "
                "appropriate null expectations and "
                "survive statistical testing.",
            "recurrence":
                "Repeated observation alone is not "
                "sufficient; enrichment relative to "
                "null structure is required.",
            "temporal_claim":
                "A temporal phenomenon requires evidence "
                "that depends on ordering.",
            "replication":
                "Chronological reappearance strengthens "
                "the case but is not required when "
                "sample size is insufficient.",
            "small_sample":
                "Small historical samples are reported "
                "as insufficient rather than treated "
                "as negative evidence.",
        },

        "case_diagnostics":
            rows,
    }

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

    # ==========================================================
    # FINAL VERDICT
    # ==========================================================

    print()
    print("=" * 78)
    print("RECONVERGENCE GAUNTLET — FINAL VERDICT")
    print("=" * 78)

    print(
        "CLASSIFICATION:",
        verdict_result["classification"],
    )

    print(
        "CONFIDENCE:",
        verdict_result["confidence"],
    )

    print(
        "VALID CASES:",
        n,
    )

    print(
        "DIRECT C-D-C:",
        direct_cdc(seq),
    )

    print(
        "GENERALIZED RECONVERGENCE:",
        len(
            generalized_reconvergence(seq)
        ),
    )

    print(
        "CDC PERMUTATION P:",
        nulls[
            "iid_temporal_permutation"
        ]["p_value"],
    )

    print(
        "RECONVERGENCE PERMUTATION P:",
        nulls[
            "generalized_reconvergence"
        ]["p_value"],
    )

    print(
        "CDC BASE-RATE RATIO:",
        base_rate[
            "observed_to_expected_ratio"
        ],
    )

    print(
        "MARKOV EXPECTED CDC:",
        (
            markov["expected_cdc"]
            if markov
            else None
        ),
    )

    print(
        "TEMPORAL MUTUAL INFORMATION LAG 1:",
        information.get("1"),
    )

    print(
        "CHRONOLOGICAL REPLICATION ELIGIBLE:",
        replication.get("eligible"),
    )

    print()
    print("REASONS:")

    for reason in verdict_result["reasons"]:
        print(
            " -",
            reason,
        )

    print()
    print("REPORT:")
    print(REPORT)

    print()
    print("=" * 78)
    print("RECONVERGENCE GAUNTLET V1 COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
