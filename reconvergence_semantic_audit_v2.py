#!/usr/bin/env python3

import json
import os
import statistics
from collections import Counter

ROOT = os.path.expanduser("~/BIRTH_EDGE")
DATA = os.path.join(ROOT, "data", "ml_reflection.json")

VERSION = 2


# ============================================================================
# BIRTH_EDGE — SEMANTIC AUDIT V2
#
# PURPOSE
# -------
# Establish the actual meaning of the persisted ml_reflection.json schema
# BEFORE making any reconvergence / phenomenon claim.
#
# IMPORTANT:
#   - Historical data is read-only.
#   - No synthetic cases.
#   - No model modification.
#   - No trading.
#   - No inferred MODEL/REALITY aliases when explicit fields exist.
#
# CANONICAL SEMANTICS
# -------------------
#
# MODEL correctness:
#     "correct"
#
# REALITY:
#     actual_outcome compared against predicted_outcome.
#
# WISDOM correctness:
#     "wisdom_correct"
#
# Supporting variables:
#     model_confidence
#     prediction_error
#     evidence_agreement
#     evidence_strength
#     wisdom_score
#     reflection_score
#
# ============================================================================


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


def canonical_actual_alignment(predicted, actual):
    """
    Determine whether predicted_outcome matches actual_outcome.

    We deliberately do NOT coerce arbitrary strings into binary values here.
    Exact semantic agreement is preferred.
    """

    if predicted is None or actual is None:
        return None

    return int(predicted == actual)


def inspect_record(record, index):
    predicted = record.get("predicted_outcome")
    actual = record.get("actual_outcome")

    correct_raw = record.get("correct")
    wisdom_raw = record.get("wisdom_correct")

    correct = bit(correct_raw)
    wisdom = bit(wisdom_raw)

    actual_alignment = canonical_actual_alignment(
        predicted,
        actual
    )

    consistency = None

    if correct is not None and actual_alignment is not None:
        consistency = int(correct == actual_alignment)

    model = correct
    reality = actual_alignment

    three_way = None
    model_reality = None
    wisdom_reality = None

    if model is not None and wisdom is not None and reality is not None:
        three_way = int(model == wisdom == reality)
        model_reality = int(model == reality)
        wisdom_reality = int(wisdom == reality)

    if three_way == 1:
        state = "FULL_CONVERGENCE"
    elif model_reality == 1:
        state = "MODEL_ANCHORED_DIVERGENCE"
    elif wisdom_reality == 1:
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

        "actual_alignment": actual_alignment,
        "correct_field_consistency": consistency,

        "model_reality": model_reality,
        "wisdom_reality": wisdom_reality,
        "three_way": three_way,

        "state": state,
        "broken_paths": broken,

        "model_confidence": num(
            record.get("model_confidence")
        ),

        "prediction_error": num(
            record.get("prediction_error")
        ),

        "evidence_agreement": num(
            record.get("evidence_agreement")
        ),

        "evidence_strength": num(
            record.get("evidence_strength")
        ),

        "wisdom_score": num(
            record.get("wisdom_score")
        ),

        "reflection_score": num(
            record.get("reflection_score")
        ),

        "raw_keys": sorted(record.keys()),
    }


def semantic_valid(row):
    required = (
        row["model"],
        row["wisdom"],
        row["reality"],
    )

    return all(x in (0, 1) for x in required)


def rate(rows, key):
    values = [
        r[key]
        for r in rows
        if r.get(key) in (0, 1)
    ]

    if not values:
        return None

    return sum(values) / len(values)


def transition_table(rows, field):
    out = Counter()

    for a, b in zip(rows, rows[1:]):
        out[f"{a[field]} -> {b[field]}"] += 1

    return dict(out)


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
                "from_case": prev["identity"],
                "to_case": cur["identity"],
                "from_state": prev["state"],
                "to_state": cur["state"],
                "broken_paths": cur["broken_paths"],
                "confidence_delta": delta(
                    cur["model_confidence"],
                    prev["model_confidence"]
                ),
                "agreement_delta": delta(
                    cur["evidence_agreement"],
                    prev["evidence_agreement"]
                ),
                "strength_delta": delta(
                    cur["evidence_strength"],
                    prev["evidence_strength"]
                ),
                "error_delta": delta(
                    cur["prediction_error"],
                    prev["prediction_error"]
                ),
            })

    return events


def reconvergence_events(rows):
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
                "from_case": prev["identity"],
                "to_case": cur["identity"],
                "from_state": prev["state"],
                "to_state": cur["state"],
                "from_signature": (
                    f"M{prev['model']}"
                    f"W{prev['wisdom']}"
                    f"R{prev['reality']}"
                ),
                "to_signature": (
                    f"M{cur['model']}"
                    f"W{cur['wisdom']}"
                    f"R{cur['reality']}"
                ),
            })

    return events


def delta(a, b):
    if a is None or b is None:
        return None

    return a - b


def signatures(rows):
    out = Counter()

    for r in rows:
        out[
            f"M{r['model']}W{r['wisdom']}R{r['reality']}"
        ] += 1

    return dict(out)


def schema_inventory(records):
    counter = Counter()

    for record in records:
        if isinstance(record, dict):
            counter.update(record.keys())

    return dict(counter.most_common())


def consistency_report(rows):
    values = [
        r["correct_field_consistency"]
        for r in rows
        if r["correct_field_consistency"] is not None
    ]

    return {
        "cases_tested": len(values),
        "consistent": sum(values),
        "inconsistent": len(values) - sum(values),
        "rate": (
            sum(values) / len(values)
            if values
            else None
        ),
    }


def main():
    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE SEMANTIC AUDIT V2")
    print("EXPLICIT SCHEMA / DATA-LINEAGE VALIDATION")
    print("=" * 76)

    records = load_records()

    print()
    print("=" * 76)
    print("RAW SCHEMA")
    print("=" * 76)

    print("HISTORICAL RECORDS:", len(records))

    print(
        json.dumps(
            schema_inventory(records),
            indent=2,
            sort_keys=True
        )
    )

    rows = [
        inspect_record(record, index)
        for index, record in enumerate(records)
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

    consistency = consistency_report(rows)

    print()
    print("=" * 76)
    print("CANONICAL FIELD MAPPING")
    print("=" * 76)

    print("MODEL     <- correct")
    print("WISDOM    <- wisdom_correct")
    print(
        "REALITY   <- "
        "actual_outcome == predicted_outcome"
    )
    print("CONFIDENCE <- model_confidence")
    print("ERROR      <- prediction_error")
    print("AGREEMENT  <- evidence_agreement")
    print("STRENGTH   <- evidence_strength")

    print()
    print("=" * 76)
    print("CORRECT-FIELD CONSISTENCY")
    print("=" * 76)

    print(
        "CASES TESTED:",
        consistency["cases_tested"]
    )
    print(
        "CONSISTENT:",
        consistency["consistent"]
    )
    print(
        "INCONSISTENT:",
        consistency["inconsistent"]
    )
    print(
        "CONSISTENCY RATE:",
        consistency["rate"]
    )

    print()
    print("=" * 76)
    print("PER-CASE SEMANTIC TRACE")
    print("=" * 76)

    for row in rows:
        print()
        print("CASE:", row["identity"])

        print(
            "  PREDICTED:",
            repr(row["predicted_outcome"])
        )

        print(
            "  ACTUAL:",
            repr(row["actual_outcome"])
        )

        print(
            "  MODEL(correct):",
            row["model"]
        )

        print(
            "  WISDOM(wisdom_correct):",
            row["wisdom"]
        )

        print(
            "  REALITY(alignment):",
            row["reality"]
        )

        print(
            "  STORED CORRECT:",
            repr(row["correct_raw"])
        )

        print(
            "  DERIVED CORRECT:",
            row["actual_alignment"]
        )

        print(
            "  CORRECT FIELD CONSISTENT:",
            row["correct_field_consistency"]
        )

        print(
            "  THREE-WAY:",
            row["three_way"]
        )

        print(
            "  STATE:",
            row["state"]
        )

    print()
    print("=" * 76)
    print("SEMANTIC VALIDITY")
    print("=" * 76)

    print("VALID CASES:", len(valid))
    print("INVALID CASES:", len(invalid))

    if invalid:
        print()
        print("INVALID CASES:")
        for row in invalid:
            print(
                row["identity"],
                "MODEL=",
                row["model"],
                "WISDOM=",
                row["wisdom"],
                "REALITY=",
                row["reality"]
            )

    result = {
        "engine":
            "BIRTH_EDGE_RECONVERGENCE_SEMANTIC_AUDIT_V2",

        "version": VERSION,

        "data_source": DATA,

        "canonical_mapping": {
            "model": "correct",
            "wisdom": "wisdom_correct",
            "reality":
                "actual_outcome == predicted_outcome",
            "confidence": "model_confidence",
            "prediction_error": "prediction_error",
            "agreement": "evidence_agreement",
            "strength": "evidence_strength",
        },

        "schema_inventory":
            schema_inventory(records),

        "correct_field_consistency":
            consistency,

        "semantic_validity": {
            "historical_records": len(records),
            "valid_cases": len(valid),
            "invalid_cases": len(invalid),
        },

        "case_diagnostics": rows,

        "data_integrity": {
            "historical_data_modified": False,
            "synthetic_data_used": False,
            "model_modified": False,
            "trading_performed": False,
        },
    }

    if valid:
        model_reality = rate(valid, "model_reality")
        wisdom_reality = rate(valid, "wisdom_reality")
        convergence = rate(valid, "three_way")

        div = divergence_events(valid)
        recon = reconvergence_events(valid)

        sig = signatures(valid)

        result["phenomenon_analysis"] = {
            "cases": len(valid),
            "model_reality_rate": model_reality,
            "wisdom_reality_rate": wisdom_reality,
            "three_way_rate": convergence,
            "divergence_events": div,
            "reconvergence_events": recon,
            "structural_signatures": sig,
            "state_transitions":
                transition_table(valid, "state"),
        }

        print()
        print("=" * 76)
        print("CANONICAL PHENOMENON ANALYSIS")
        print("=" * 76)

        print(
            "MODEL -> REALITY:",
            model_reality
        )

        print(
            "WISDOM -> REALITY:",
            wisdom_reality
        )

        print(
            "THREE-WAY CONVERGENCE:",
            convergence
        )

        print(
            "DIVERGENCE EVENTS:",
            len(div)
        )

        print(
            "RECONVERGENCE EVENTS:",
            len(recon)
        )

        print()
        print("STRUCTURAL SIGNATURES:")

        print(
            json.dumps(
                sig,
                indent=2,
                sort_keys=True
            )
        )

        print()
        print("STATE TRANSITIONS:")

        print(
            json.dumps(
                transition_table(valid, "state"),
                indent=2,
                sort_keys=True
            )
        )

        print()
        print("=" * 76)
        print("RECONVERGENCE EVENTS")
        print("=" * 76)

        if recon:
            for event in recon:
                print(
                    json.dumps(
                        event,
                        indent=2
                    )
                )
        else:
            print("NONE")

        print()
        print("=" * 76)
        print("DIVERGENCE EVENTS")
        print("=" * 76)

        if div:
            for event in div:
                print(
                    json.dumps(
                        event,
                        indent=2
                    )
                )
        else:
            print("NONE")

    else:
        result["phenomenon_analysis"] = {
            "classification":
                "SEMANTICALLY_UNRESOLVED",
            "reason":
                "Canonical MODEL/WISDOM/REALITY mapping "
                "could not be established."
        }

        print()
        print("=" * 76)
        print("PHENOMENON ANALYSIS")
        print("=" * 76)
        print(
            "CLASSIFICATION: SEMANTICALLY_UNRESOLVED"
        )

    print()
    print("=" * 76)
    print("FINAL VERDICT")
    print("=" * 76)

    if (
        len(valid) == len(records)
        and consistency["inconsistent"] == 0
    ):
        print("SEMANTIC STATUS: 💯 LOCKED")
        print(
            "The persisted schema supports a canonical "
            "MODEL/WISDOM/REALITY interpretation."
        )

        if len(valid) >= 3:
            print(
                "Phenomenon analysis is now eligible "
                "for longitudinal evaluation."
            )
        else:
            print(
                "Phenomenon interpretation remains "
                "sample-limited."
            )

    else:
        print("SEMANTIC STATUS: NOT LOCKED")

        if consistency["inconsistent"] > 0:
            print(
                "CRITICAL: stored 'correct' disagrees "
                "with predicted_outcome vs actual_outcome."
            )

        print(
            "Do not make a reconvergence claim until "
            "the discrepancy is understood."
        )

    print()
    print("=" * 76)
    print("DATA INTEGRITY")
    print("=" * 76)

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
    print("SEMANTIC AUDIT V2 COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
