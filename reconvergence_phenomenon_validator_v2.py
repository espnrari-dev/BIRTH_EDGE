#!/usr/bin/env python3

import json
import math
import os
import statistics
from collections import Counter, defaultdict

ROOT = os.path.expanduser("~/BIRTH_EDGE")
DATA = os.path.join(ROOT, "data", "ml_reflection.json")

MIN_RECURRENCE_CASES = 10
MIN_STATISTICAL_CASES = 30
MIN_STRONG_CASES = 50


def load_records():
    with open(DATA, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        for key in ("records", "reflections", "history", "cases", "data"):
            if isinstance(raw.get(key), list):
                return raw[key]

    raise ValueError("Unsupported ml_reflection.json structure")


def num(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return float(default)


def bit(v):
    if isinstance(v, bool):
        return int(v)

    if isinstance(v, (int, float)):
        return int(v != 0)

    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "correct", "pass", "aligned"}:
            return 1
        if s in {"0", "false", "no", "wrong", "fail", "diverged"}:
            return 0

    return 0


def first_value(r, keys, default=None):
    for k in keys:
        if k in r:
            return r[k]
    return default


def extract(record, index):
    model = bit(first_value(
        record,
        ["model", "model_correct", "model_reality", "prediction_correct"],
        0
    ))

    wisdom = bit(first_value(
        record,
        ["wisdom", "wisdom_correct", "wisdom_reality"],
        0
    ))

    reality = bit(first_value(
        record,
        ["reality", "outcome_correct", "actual", "real"],
        0
    ))

    confidence = num(first_value(
        record,
        ["confidence", "model_confidence", "prediction_confidence"],
        0
    ))

    agreement = num(first_value(
        record,
        ["evidence_agreement", "agreement", "model_wisdom_agreement"],
        int(model == wisdom)
    ))

    strength = num(first_value(
        record,
        ["evidence_strength", "strength", "evidence_score"],
        0
    ))

    prediction_error = num(first_value(
        record,
        ["prediction_error", "error", "model_error"],
        abs(model - reality)
    ))

    three_way = int(model == wisdom == reality)

    model_reality = int(model == reality)
    wisdom_reality = int(wisdom == reality)

    if three_way:
        state = "FULL_CONVERGENCE"
    elif model_reality:
        state = "MODEL_ANCHORED_DIVERGENCE"
    elif wisdom_reality:
        state = "WISDOM_ANCHORED_DIVERGENCE"
    else:
        state = "FULL_DIVERGENCE"

    broken = []

    if model != reality:
        broken.append("MODEL")

    if wisdom != reality:
        broken.append("WISDOM")

    return {
        "index": index,
        "model": model,
        "wisdom": wisdom,
        "reality": reality,
        "confidence": confidence,
        "agreement": agreement,
        "strength": strength,
        "prediction_error": prediction_error,
        "three_way": three_way,
        "model_reality": model_reality,
        "wisdom_reality": wisdom_reality,
        "state": state,
        "broken_paths": broken,
    }


def rate(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else 0.0


def conditional(rows, condition, target):
    subset = [r for r in rows if condition(r)]
    return {
        "n": len(subset),
        "rate": rate(subset, target) if subset else None
    }


def transition_table(rows, field):
    out = Counter()

    for a, b in zip(rows, rows[1:]):
        out[f"{a[field]} -> {b[field]}"] += 1

    return dict(out)


def run_lengths(rows):
    runs = []

    if not rows:
        return runs

    state = rows[0]["three_way"]
    length = 1

    for r in rows[1:]:
        if r["three_way"] == state:
            length += 1
        else:
            runs.append({
                "state": "CONVERGENT" if state else "DIVERGENT",
                "length": length
            })
            state = r["three_way"]
            length = 1

    runs.append({
        "state": "CONVERGENT" if state else "DIVERGENT",
        "length": length
    })

    return runs


def recurrence(rows):
    events = []

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]

        if (
            not prev["three_way"]
            and cur["three_way"]
        ):
            events.append({
                "index": i,
                "from": prev["state"],
                "to": cur["state"],
                "case_index": cur["index"],
                "type": "RECONVERGENCE"
            })

    return events


def divergence_events(rows):
    events = []

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]

        if prev["three_way"] and not cur["three_way"]:
            events.append({
                "index": i,
                "from": prev["state"],
                "to": cur["state"],
                "broken_paths": cur["broken_paths"],
                "confidence_delta":
                    cur["confidence"] - prev["confidence"],
                "agreement_delta":
                    cur["agreement"] - prev["agreement"],
                "strength_delta":
                    cur["strength"] - prev["strength"],
                "prediction_error_delta":
                    cur["prediction_error"] - prev["prediction_error"],
            })

    return events


def precursor_effect(rows):
    events = divergence_events(rows)

    if not events:
        return {
            "events": [],
            "n": 0,
            "mean_confidence_delta": None,
            "mean_agreement_delta": None,
            "mean_strength_delta": None,
            "mean_prediction_error_delta": None
        }

    return {
        "events": events,
        "n": len(events),
        "mean_confidence_delta":
            statistics.mean(e["confidence_delta"] for e in events),
        "mean_agreement_delta":
            statistics.mean(e["agreement_delta"] for e in events),
        "mean_strength_delta":
            statistics.mean(e["strength_delta"] for e in events),
        "mean_prediction_error_delta":
            statistics.mean(e["prediction_error_delta"] for e in events)
    }


def bin_condition(rows, key):
    values = [r[key] for r in rows]

    if not values:
        return {}

    med = statistics.median(values)

    high = [r for r in rows if r[key] >= med]
    low = [r for r in rows if r[key] < med]

    return {
        "median": med,
        "high": {
            "n": len(high),
            "convergence": rate(high, "three_way")
        },
        "low": {
            "n": len(low),
            "convergence": rate(low, "three_way")
        },
        "delta":
            rate(high, "three_way") - rate(low, "three_way")
            if high and low else None
    }


def classify(n, recurrence_count, divergence_count, reconvergence_count):
    if n < MIN_RECURRENCE_CASES:
        return "PHENOMENON_NOT_YET_IDENTIFIABLE", "LOW"

    if reconvergence_count >= 3 and divergence_count >= 3:
        if n >= MIN_STRONG_CASES:
            return "RECURRING_RECONVERGENCE_CANDIDATE", "HIGH"

        return "RECURRING_RECONVERGENCE_CANDIDATE", "MEDIUM"

    if divergence_count >= 3:
        return "RECURRING_DIVERGENCE_STRUCTURE", "MEDIUM"

    if recurrence_count >= 2:
        return "REPEATED_STATE_STRUCTURE", "MEDIUM"

    return "CANDIDATE_STRUCTURE_ONLY", "LOW"


def main():

    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE PHENOMENON VALIDATOR V2")
    print("LONGITUDINAL / NON-SYNTHETIC STRUCTURE DETECTION")
    print("=" * 76)

    records = load_records()
    rows = [extract(r, i) for i, r in enumerate(records)]

    n = len(rows)

    if n == 0:
        raise RuntimeError("No historical records found.")

    recon = recurrence(rows)
    div_events = divergence_events(rows)
    precursors = precursor_effect(rows)
    runs = run_lengths(rows)

    model_reality = rate(rows, "model_reality")
    wisdom_reality = rate(rows, "wisdom_reality")
    convergence = rate(rows, "three_way")

    model_only = [
        r for r in rows
        if r["model_reality"] and not r["wisdom_reality"]
    ]

    wisdom_only = [
        r for r in rows
        if r["wisdom_reality"] and not r["model_reality"]
    ]

    transitions = transition_table(rows, "state")
    signatures = transition_table(rows, "three_way")

    agreement = bin_condition(rows, "agreement")
    confidence = bin_condition(rows, "confidence")
    strength = bin_condition(rows, "strength")

    failure_classes = Counter()

    for r in rows:
        if not r["broken_paths"]:
            failure_classes["NONE"] += 1
        else:
            failure_classes["+".join(r["broken_paths"])] += 1

    recurrence_count = sum(
        1 for a, b in zip(rows, rows[1:])
        if a["three_way"] == b["three_way"]
    )

    classification, confidence_level = classify(
        n,
        recurrence_count,
        len(div_events),
        len(recon)
    )

    result = {
        "engine":
            "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_VALIDATOR_V2",

        "version": 2,

        "data_source": DATA,

        "data_integrity": {
            "historical_records": n,
            "analyzed_cases": n,
            "historical_data_modified": False,
            "model_modified": False,
            "synthetic_data_used": False,
            "trading_performed": False
        },

        "basic_structure": {
            "cases": n,
            "full_convergence_rate": convergence,
            "model_reality_rate": model_reality,
            "wisdom_reality_rate": wisdom_reality,
            "model_only_count": len(model_only),
            "wisdom_only_count": len(wisdom_only),
            "model_only_rate": len(model_only) / n,
            "wisdom_only_rate": len(wisdom_only) / n
        },

        "candidate_structure": {
            "model_reality_anchor": model_reality > wisdom_reality,
            "model_only_reality_cases": len(model_only),
            "wisdom_only_reality_cases": len(wisdom_only),
            "first_break_asymmetry":
                dict(failure_classes)
        },

        "conditioning": {
            "agreement": agreement,
            "confidence": confidence,
            "evidence_strength": strength
        },

        "temporal_structure": {
            "state_transitions": transitions,
            "three_way_transitions": signatures,
            "run_lengths": runs,
            "transition_count": max(0, n - 1)
        },

        "divergence": {
            "events": div_events,
            "count": len(div_events),
            "rate":
                len(div_events) / max(1, n - 1)
        },

        "reconvergence": {
            "events": recon,
            "count": len(recon),
            "rate":
                len(recon) / max(1, n - 1)
        },

        "precursor_analysis": precursors,

        "recurrence": {
            "same_state_transitions": recurrence_count,
            "recurrence_rate":
                recurrence_count / max(1, n - 1),
            "repeated_failure_classes":
                {
                    k: v for k, v in failure_classes.items()
                    if v > 1
                }
        },

        "phenomenon": {
            "classification": classification,
            "confidence": confidence_level,
            "sample_size": n,
            "minimum_recurrence_sample":
                MIN_RECURRENCE_CASES,
            "minimum_statistical_sample":
                MIN_STATISTICAL_CASES,
            "minimum_strong_sample":
                MIN_STRONG_CASES
        },

        "research_question": {
            "question":
                "Does BIRTH_EDGE exhibit a recurring path-specific "
                "reality-alignment/reconvergence phenomenon?",
            "current_answer":
                "NOT YET ESTABLISHED",
            "required_observation":
                "Repeated divergence followed by reconvergence across "
                "independent historical cases.",
            "critical_signature":
                "FULL_CONVERGENCE -> DIVERGENCE -> RECONVERGENCE"
        },

        "case_diagnostics": rows
    }

    print(json.dumps(result, indent=2, sort_keys=True))

    print()
    print("=" * 76)
    print("PHENOMENON VALIDATION VERDICT")
    print("=" * 76)

    print("CLASSIFICATION:", classification)
    print("CONFIDENCE:", confidence_level)
    print("SAMPLE SIZE:", n)

    print()
    print("=" * 76)
    print("REALITY ALIGNMENT")
    print("=" * 76)

    print("MODEL -> REALITY:", model_reality)
    print("WISDOM -> REALITY:", wisdom_reality)
    print("MODEL-ONLY:", len(model_only))
    print("WISDOM-ONLY:", len(wisdom_only))

    print()
    print("=" * 76)
    print("DIVERGENCE / RECONVERGENCE")
    print("=" * 76)

    print("DIVERGENCE EVENTS:", len(div_events))
    print("RECONVERGENCE EVENTS:", len(recon))

    if recon:
        for e in recon:
            print(
                "RECONVERGENCE:",
                e["from"],
                "->",
                e["to"],
                "CASE",
                e["case_index"]
            )
    else:
        print("NO RECONVERGENCE EVENT OBSERVED YET.")

    print()
    print("=" * 76)
    print("PRECURSOR SIGNAL")
    print("=" * 76)

    if precursors["n"]:
        print(
            "MEAN CONFIDENCE DELTA:",
            precursors["mean_confidence_delta"]
        )
        print(
            "MEAN AGREEMENT DELTA:",
            precursors["mean_agreement_delta"]
        )
        print(
            "MEAN STRENGTH DELTA:",
            precursors["mean_strength_delta"]
        )
        print(
            "MEAN ERROR DELTA:",
            precursors["mean_prediction_error_delta"]
        )
    else:
        print("NO DIVERGENCE TRANSITIONS AVAILABLE.")

    print()
    print("=" * 76)
    print("CANDIDATE UNDERLYING STRUCTURE")
    print("=" * 76)

    if model_reality > wisdom_reality:
        print(
            "MODEL_REALITY_ANCHOR: OBSERVED"
        )
    else:
        print(
            "MODEL_REALITY_ANCHOR: NOT OBSERVED"
        )

    if len(recon) > 0:
        print(
            "RECONVERGENCE_STRUCTURE: OBSERVED"
        )
    else:
        print(
            "RECONVERGENCE_STRUCTURE: NOT YET OBSERVED"
        )

    if len(div_events) >= 2 and len(recon) >= 1:
        print(
            "IMPORTANT: A repeated divergence/reconvergence "
            "trajectory is beginning to appear."
        )
    else:
        print(
            "IMPORTANT: Continue accumulating untouched historical "
            "experience. Do not manufacture cases."
        )

    print()
    print("=" * 76)
    print("NOMINALITY")
    print("=" * 76)

    print("ENGINE OPERATION: 💯 NOMINAL")
    print("HISTORICAL RECORDS:", n)
    print("DATA MODIFIED: False")
    print("SYNTHETIC DATA: False")
    print("TRADING: False")

    print()
    print("=" * 76)
    print("NEXT DISCOVERY THRESHOLDS")
    print("=" * 76)

    print(
        f"{MIN_RECURRENCE_CASES} cases: recurrence analysis becomes meaningful."
    )
    print(
        f"{MIN_STATISTICAL_CASES} cases: stronger statistical testing becomes possible."
    )
    print(
        f"{MIN_STRONG_CASES} cases: substantially stronger phenomenon validation."
    )

    print()
    print("=" * 76)
    print("VALIDATOR V2 COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
