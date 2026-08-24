#!/usr/bin/env python3

import json
import os
import statistics
from collections import Counter, defaultdict

ROOT = os.path.expanduser("~/BIRTH_EDGE")
DATA = os.path.join(ROOT, "data", "ml_reflection.json")

VERSION = 1

# ---------------------------------------------------------------------------
# PURPOSE
# ---------------------------------------------------------------------------
# Semantic / data-lineage audit for the BIRTH_EDGE reconvergence investigation.
#
# This program:
#   1. Reads the historical record exactly as stored.
#   2. Reports the raw keys and values relevant to MODEL/WISDOM/REALITY.
#   3. Detects ambiguous aliases and conflicting interpretations.
#   4. Does NOT modify historical data.
#   5. Does NOT generate synthetic observations.
#   6. Does NOT modify the model.
#   7. Produces a canonical interpretation only when semantics are defensible.
#   8. Searches for possible extraction artifacts before phenomenon claims.
#
# IMPORTANT:
# A reconvergence result is not considered scientifically usable if the
# underlying labels cannot be traced unambiguously to their source fields.
# ---------------------------------------------------------------------------


MODEL_KEYS = [
    "model",
    "model_correct",
    "model_reality",
    "prediction_correct",
]

WISDOM_KEYS = [
    "wisdom",
    "wisdom_correct",
    "wisdom_reality",
]

REALITY_KEYS = [
    "reality",
    "outcome_correct",
    "actual",
    "real",
]

CONFIDENCE_KEYS = [
    "confidence",
    "model_confidence",
    "prediction_confidence",
]

AGREEMENT_KEYS = [
    "evidence_agreement",
    "agreement",
    "model_wisdom_agreement",
]

STRENGTH_KEYS = [
    "evidence_strength",
    "strength",
    "evidence_score",
]

ERROR_KEYS = [
    "prediction_error",
    "error",
    "model_error",
]


def load_raw():
    with open(DATA, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        for key in ("records", "reflections", "history", "cases", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return value

    raise ValueError(
        "Unsupported ml_reflection.json structure. "
        "Expected list or dict containing records/reflections/history/cases/data."
    )


def first_present(record, keys):
    hits = []
    for key in keys:
        if key in record:
            hits.append((key, record[key]))

    return hits


def normalize_bit(value):
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
            "aligned",
            "success",
            "successful",
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
            "diverged",
            "failure",
            "loss",
            "lost",
        }:
            return 0

    return None


def extract_semantic(record, keys):
    hits = first_present(record, keys)

    normalized = []

    for key, value in hits:
        normalized.append({
            "key": key,
            "raw_value": value,
            "normalized": normalize_bit(value),
        })

    return normalized


def numeric(record, keys):
    hits = first_present(record, keys)

    for key, value in hits:
        try:
            return {
                "key": key,
                "raw_value": value,
                "value": float(value),
            }
        except Exception:
            continue

    return None


def consensus(items):
    usable = [
        x["normalized"]
        for x in items
        if x["normalized"] in (0, 1)
    ]

    if not usable:
        return None

    if all(x == usable[0] for x in usable):
        return usable[0]

    return "CONFLICT"


def audit_semantic_field(record, field_name, keys):
    hits = extract_semantic(record, keys)

    return {
        "field": field_name,
        "candidate_keys": keys,
        "present": len(hits),
        "values": hits,
        "consensus": consensus(hits),
        "ambiguous": consensus(hits) == "CONFLICT",
        "missing": len(hits) == 0,
        "uninterpretable": (
            len(hits) > 0
            and all(x["normalized"] is None for x in hits)
        ),
    }


def raw_key_inventory(records):
    counter = Counter()

    for record in records:
        if isinstance(record, dict):
            counter.update(record.keys())

    return dict(counter.most_common())


def record_identity(record, index):
    possible = [
        "case_id",
        "id",
        "record_id",
        "reflection_id",
        "timestamp",
        "created_at",
        "time",
    ]

    for key in possible:
        if key in record:
            return f"{key}={record[key]}"

    return f"index={index}"


def semantic_audit(records):
    audited = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            audited.append({
                "index": index,
                "identity": record_identity({}, index),
                "record_type": type(record).__name__,
                "valid_object": False,
            })
            continue

        audited.append({
            "index": index,
            "identity": record_identity(record, index),
            "record_type": "dict",
            "valid_object": True,
            "MODEL": audit_semantic_field(
                record, "MODEL", MODEL_KEYS
            ),
            "WISDOM": audit_semantic_field(
                record, "WISDOM", WISDOM_KEYS
            ),
            "REALITY": audit_semantic_field(
                record, "REALITY", REALITY_KEYS
            ),
            "CONFIDENCE": numeric(record, CONFIDENCE_KEYS),
            "AGREEMENT": numeric(record, AGREEMENT_KEYS),
            "STRENGTH": numeric(record, STRENGTH_KEYS),
            "ERROR": numeric(record, ERROR_KEYS),
        })

    return audited


def semantic_status(audited):
    conflicts = []
    missing = []
    uninterpretable = []
    valid = 0

    for row in audited:
        if not row.get("valid_object"):
            conflicts.append(row["index"])
            continue

        bad = False

        for field in ("MODEL", "WISDOM", "REALITY"):
            info = row[field]

            if info["ambiguous"]:
                conflicts.append({
                    "index": row["index"],
                    "field": field,
                    "reason": "CONFLICTING_ALIASES",
                })
                bad = True

            elif info["missing"]:
                missing.append({
                    "index": row["index"],
                    "field": field,
                })
                bad = True

            elif info["uninterpretable"]:
                uninterpretable.append({
                    "index": row["index"],
                    "field": field,
                })
                bad = True

        if not bad:
            valid += 1

    return {
        "total": len(audited),
        "semantically_valid": valid,
        "semantic_invalid": len(audited) - valid,
        "conflicts": conflicts,
        "missing": missing,
        "uninterpretable": uninterpretable,
    }


def canonical_rows(audited):
    rows = []

    for row in audited:
        if not row.get("valid_object"):
            continue

        model = row["MODEL"]["consensus"]
        wisdom = row["WISDOM"]["consensus"]
        reality = row["REALITY"]["consensus"]

        if model not in (0, 1):
            continue

        if wisdom not in (0, 1):
            continue

        if reality not in (0, 1):
            continue

        model_reality = int(model == reality)
        wisdom_reality = int(wisdom == reality)
        three_way = int(model == wisdom == reality)

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

        confidence = (
            row["CONFIDENCE"]["value"]
            if row["CONFIDENCE"] else None
        )

        agreement = (
            row["AGREEMENT"]["value"]
            if row["AGREEMENT"] else None
        )

        strength = (
            row["STRENGTH"]["value"]
            if row["STRENGTH"] else None
        )

        error = (
            row["ERROR"]["value"]
            if row["ERROR"] else None
        )

        rows.append({
            "index": row["index"],
            "identity": row["identity"],
            "model": model,
            "wisdom": wisdom,
            "reality": reality,
            "model_reality": model_reality,
            "wisdom_reality": wisdom_reality,
            "three_way": three_way,
            "state": state,
            "broken_paths": broken,
            "confidence": confidence,
            "agreement": agreement,
            "strength": strength,
            "prediction_error": error,
        })

    return rows


def compare_alias_interpretations(records):
    """
    Look for records where multiple candidate aliases exist for the same
    semantic field and produce different binary interpretations.
    """

    conflicts = []

    fields = {
        "MODEL": MODEL_KEYS,
        "WISDOM": WISDOM_KEYS,
        "REALITY": REALITY_KEYS,
    }

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        for field, keys in fields.items():
            hits = extract_semantic_field_safe(record, keys)

            normalized = [
                (key, value)
                for key, value in hits
                if value is not None
            ]

            unique = sorted(set(value for _, value in normalized))

            if len(unique) > 1:
                conflicts.append({
                    "index": index,
                    "identity": record_identity(record, index),
                    "field": field,
                    "interpretations": normalized,
                })

    return conflicts


def extract_semantic_field_safe(record, keys):
    output = []

    for key, value in first_present(record, keys):
        output.append((key, normalize_bit(value)))

    return output


def compare_previous_style_extraction(records):
    """
    Recreates the broad alias behavior used by the earlier validators.

    This is intentionally diagnostic only. It allows us to determine whether
    different extraction policies produce different phenomenon conclusions.
    """

    rows = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        def broad(keys):
            hits = first_present(record, keys)

            if not hits:
                return 0, None

            key, value = hits[0]
            return normalize_bit(value), key

        model, model_key = broad(MODEL_KEYS)
        wisdom, wisdom_key = broad(WISDOM_KEYS)
        reality, reality_key = broad(REALITY_KEYS)

        if model is None:
            model = 0

        if wisdom is None:
            wisdom = 0

        if reality is None:
            reality = 0

        rows.append({
            "index": index,
            "identity": record_identity(record, index),
            "model": model,
            "wisdom": wisdom,
            "reality": reality,
            "model_key": model_key,
            "wisdom_key": wisdom_key,
            "reality_key": reality_key,
        })

    return rows


def compare_canonical_vs_broad(canonical, broad):
    differences = []

    broad_by_index = {
        row["index"]: row
        for row in broad
    }

    for row in canonical:
        b = broad_by_index.get(row["index"])

        if not b:
            continue

        for field in ("model", "wisdom", "reality"):
            if row[field] != b[field]:
                differences.append({
                    "index": row["index"],
                    "identity": row["identity"],
                    "field": field,
                    "canonical": row[field],
                    "broad": b[field],
                    "canonical_source":
                        row[field],
                    "broad_source":
                        b.get(field + "_key"),
                })

    return differences


def rate(rows, key):
    values = [
        r[key]
        for r in rows
        if r.get(key) is not None
    ]

    return sum(values) / len(values) if values else None


def transitions(rows):
    out = Counter()

    for a, b in zip(rows, rows[1:]):
        out[f"{a['state']} -> {b['state']}"] += 1

    return dict(out)


def reconvergence_events(rows):
    events = []

    for i in range(1, len(rows)):
        prev = rows[i - 1]
        cur = rows[i]

        if not prev["three_way"] and cur["three_way"]:
            events.append({
                "index": i,
                "from_case": prev["identity"],
                "to_case": cur["identity"],
                "from_state": prev["state"],
                "to_state": cur["state"],
                "from_model": prev["model"],
                "from_wisdom": prev["wisdom"],
                "from_reality": prev["reality"],
                "to_model": cur["model"],
                "to_wisdom": cur["wisdom"],
                "to_reality": cur["reality"],
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
                "from_case": prev["identity"],
                "to_case": cur["identity"],
                "from_state": prev["state"],
                "to_state": cur["state"],
                "broken_paths": cur["broken_paths"],
            })

    return events


def structural_signature(rows):
    signatures = Counter()

    for row in rows:
        signatures[
            f"M{row['model']}W{row['wisdom']}R{row['reality']}"
        ] += 1

    return dict(signatures)


def phenomenon_summary(rows):
    if not rows:
        return {
            "classification": "NO_SEMANTICALLY_VALID_CASES",
            "confidence": "NONE",
        }

    recon = reconvergence_events(rows)
    div = divergence_events(rows)

    model_reality = rate(rows, "model_reality")
    wisdom_reality = rate(rows, "wisdom_reality")
    convergence = rate(rows, "three_way")

    repeated_signatures = {
        k: v
        for k, v in structural_signature(rows).items()
        if v > 1
    }

    if len(rows) < 3:
        classification = "SEMANTICS_VALID_BUT_SAMPLE_TOO_SMALL"
        confidence = "LOW"
    elif len(recon) >= 3 and len(div) >= 3:
        classification = "REPEATED_RECONVERGENCE_CANDIDATE"
        confidence = "MEDIUM"
    elif len(div) >= 3:
        classification = "REPEATED_DIVERGENCE_CANDIDATE"
        confidence = "MEDIUM"
    elif repeated_signatures:
        classification = "REPEATED_STATE_STRUCTURE_CANDIDATE"
        confidence = "LOW"
    else:
        classification = "NO_REPEATED_STRUCTURE_YET"
        confidence = "LOW"

    return {
        "classification": classification,
        "confidence": confidence,
        "cases": len(rows),
        "model_reality_rate": model_reality,
        "wisdom_reality_rate": wisdom_reality,
        "three_way_rate": convergence,
        "divergence_events": len(div),
        "reconvergence_events": len(recon),
        "structural_signatures": structural_signature(rows),
        "repeated_signatures": repeated_signatures,
        "state_transitions": transitions(rows),
    }


def main():
    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE SEMANTIC AUDIT V1")
    print("DATA-LINEAGE LOCK BEFORE PHENOMENON VALIDATION")
    print("=" * 76)

    print()
    print("DATA SOURCE:")
    print(DATA)

    if not os.path.exists(DATA):
        raise FileNotFoundError(DATA)

    records = load_raw()

    print()
    print("=" * 76)
    print("RAW DATA INVENTORY")
    print("=" * 76)

    print("HISTORICAL RECORDS:", len(records))
    print("RAW OBJECT TYPES:", Counter(
        type(x).__name__ for x in records
    ))

    print()
    print("RAW KEYS:")
    print(json.dumps(
        raw_key_inventory(records),
        indent=2,
        sort_keys=True
    ))

    audited = semantic_audit(records)
    status = semantic_status(audited)

    alias_conflicts = compare_alias_interpretations(records)

    broad = compare_previous_style_extraction(records)
    canonical = canonical_rows(audited)

    extraction_differences = compare_canonical_vs_broad(
        canonical,
        broad
    )

    print()
    print("=" * 76)
    print("SEMANTIC INTEGRITY")
    print("=" * 76)

    print("TOTAL RECORDS:", status["total"])
    print("SEMANTICALLY VALID:", status["semantically_valid"])
    print("SEMANTICALLY INVALID:", status["semantic_invalid"])
    print("ALIAS CONFLICTS:", len(alias_conflicts))
    print("EXTRACTION DIFFERENCES:", len(extraction_differences))

    print()
    print("=" * 76)
    print("FIELD-LINEAGE AUDIT")
    print("=" * 76)

    for row in audited:
        print()
        print("CASE:", row["identity"])

        if not row["valid_object"]:
            print("  INVALID RECORD OBJECT")
            continue

        for field in ("MODEL", "WISDOM", "REALITY"):
            info = row[field]

            print(f"  {field}:")

            if info["values"]:
                for value in info["values"]:
                    print(
                        "    SOURCE:",
                        value["key"],
                        "RAW:",
                        repr(value["raw_value"]),
                        "NORMALIZED:",
                        value["normalized"]
                    )
            else:
                print("    SOURCE: NONE")

            print(
                "    CONSENSUS:",
                info["consensus"],
                "AMBIGUOUS:",
                info["ambiguous"]
            )

    if alias_conflicts:
        print()
        print("=" * 76)
        print("CRITICAL ALIAS CONFLICTS")
        print("=" * 76)

        for conflict in alias_conflicts:
            print(
                conflict["identity"],
                conflict["field"],
                conflict["interpretations"]
            )

    if extraction_differences:
        print()
        print("=" * 76)
        print("CRITICAL EXTRACTION DIFFERENCES")
        print("=" * 76)

        for diff in extraction_differences:
            print(
                "CASE:",
                diff["identity"]
            )
            print(
                "FIELD:",
                diff["field"]
            )
            print(
                "CANONICAL:",
                diff["canonical"]
            )
            print(
                "BROAD:",
                diff["broad"],
                "SOURCE:",
                diff["broad_source"]
            )

    print()
    print("=" * 76)
    print("CANONICAL INTERPRETATION")
    print("=" * 76)

    print("CANONICAL CASES:", len(canonical))

    for row in canonical:
        print(
            f"CASE {row['index']}: "
            f"M={row['model']} "
            f"W={row['wisdom']} "
            f"R={row['reality']} "
            f"STATE={row['state']}"
        )

    summary = phenomenon_summary(canonical)

    print()
    print("=" * 76)
    print("CANONICAL PHENOMENON CHECK")
    print("=" * 76)

    print(
        "CLASSIFICATION:",
        summary["classification"]
    )

    print(
        "CONFIDENCE:",
        summary["confidence"]
    )

    print(
        "MODEL -> REALITY:",
        summary["model_reality_rate"]
    )

    print(
        "WISDOM -> REALITY:",
        summary["wisdom_reality_rate"]
    )

    print(
        "THREE-WAY CONVERGENCE:",
        summary["three_way_rate"]
    )

    print(
        "DIVERGENCE EVENTS:",
        summary["divergence_events"]
    )

    print(
        "RECONVERGENCE EVENTS:",
        summary["reconvergence_events"]
    )

    print()
    print("=" * 76)
    print("STRUCTURAL SIGNATURES")
    print("=" * 76)

    print(json.dumps(
        summary["structural_signatures"],
        indent=2,
        sort_keys=True
    ))

    print()
    print("=" * 76)
    print("STATE TRANSITIONS")
    print("=" * 76)

    print(json.dumps(
        summary["state_transitions"],
        indent=2,
        sort_keys=True
    ))

    print()
    print("=" * 76)
    print("RECONVERGENCE EVENTS")
    print("=" * 76)

    recon = reconvergence_events(canonical)

    if recon:
        for event in recon:
            print(json.dumps(event, indent=2))
    else:
        print("NONE")

    print()
    print("=" * 76)
    print("DIVERGENCE EVENTS")
    print("=" * 76)

    div = divergence_events(canonical)

    if div:
        for event in div:
            print(json.dumps(event, indent=2))
    else:
        print("NONE")

    print()
    print("=" * 76)
    print("INTERPRETATION SAFETY")
    print("=" * 76)

    safe = (
        status["semantically_valid"] == len(records)
        and len(alias_conflicts) == 0
        and len(extraction_differences) == 0
    )

    if safe:
        print("SEMANTIC STATUS: LOCKED")
        print(
            "The canonical interpretation agrees with the broad "
            "historical extraction policy."
        )
    else:
        print("SEMANTIC STATUS: NOT LOCKED")
        print(
            "Do NOT treat the apparent reconvergence phenomenon "
            "as established until field semantics are resolved."
        )

    print()
    print("=" * 76)
    print("DATA INTEGRITY")
    print("=" * 76)

    print("HISTORICAL DATA MODIFIED: False")
    print("SYNTHETIC DATA USED: False")
    print("MODEL MODIFIED: False")
    print("TRADING PERFORMED: False")
    print("SOURCE FILE MODIFIED: False")

    result = {
        "engine":
            "BIRTH_EDGE_RECONVERGENCE_SEMANTIC_AUDIT",
        "version": VERSION,
        "data_source": DATA,
        "semantic_integrity": status,
        "alias_conflicts": alias_conflicts,
        "extraction_differences": extraction_differences,
        "canonical_cases": canonical,
        "phenomenon_summary": summary,
        "data_integrity": {
            "historical_data_modified": False,
            "synthetic_data_used": False,
            "model_modified": False,
            "trading_performed": False,
            "source_file_modified": False,
        }
    }

    print()
    print("=" * 76)
    print("MACHINE-READABLE RESULT")
    print("=" * 76)

    print(json.dumps(result, indent=2, sort_keys=True))

    print()
    print("=" * 76)
    print("SEMANTIC AUDIT COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
