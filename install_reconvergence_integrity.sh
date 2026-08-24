#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

cd "$HOME/BIRTH_EDGE"

mkdir -p data logs backups

TS="$(date +%Y%m%d_%H%M%S)"

[ -f data/ml_reflection.json ] && \
cp data/ml_reflection.json "backups/ml_reflection_${TS}.json" || true

cat > reflection_reconcile.py <<'PY'
#!/usr/bin/env python3
"""
BIRTH_EDGE REAL REFLECTION RECONCILIATION

Purpose:
- discover real persisted evidence
- build only fully evidenced reconvergence reflections
- never synthesize predictions, wisdom, or outcomes
- preserve existing valid reflections
- audit every rejection
"""

import hashlib
import json
import math
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

DB_FILES = [
    os.path.join(DATA, "birth_edge.db"),
    os.path.join(DATA, "learning.db"),
    os.path.join(DATA, "cognition.db"),
]

REFLECTION_FILE = os.path.join(DATA, "ml_reflection.json")
MEMORY_FILE = os.path.join(DATA, "ml_memory.json")
MODEL_FILE = os.path.join(DATA, "ml_model.json")
AUDIT_FILE = os.path.join(DATA, "reflection_reconciliation_audit.json")


def finite(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def direction(value: Any) -> Optional[int]:
    number = finite(value)
    if number is None:
        return None
    return 1 if number >= 0.5 else 0


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def save_json(path: str, payload: Any) -> None:
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def flatten_dict(obj: Any, prefix: str = "") -> Dict[str, Any]:
    output: Dict[str, Any] = {}

    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            output.update(flatten_dict(value, name))
    else:
        output[prefix] = obj

    return output


def normalized_keys(record: Dict[str, Any]) -> Dict[str, Any]:
    flat = flatten_dict(record)
    result = {}

    for key, value in flat.items():
        result[key.lower().replace("-", "_").replace(" ", "_")] = value

    return result


def first_value(record: Dict[str, Any], names: List[str]) -> Any:
    flat = normalized_keys(record)

    for name in names:
        name = name.lower()
        if name in flat:
            return flat[name]

    for name in names:
        needle = name.lower()
        for key, value in flat.items():
            if key.endswith("." + needle):
                return value

    return None


ID_FIELDS = [
    "id", "case_id", "event_id", "token_id", "address",
    "mint", "contract", "symbol", "name",
]

MODEL_FIELDS = [
    "probability",
    "prediction_probability",
    "model_probability",
    "model_score",
    "predicted_probability",
]

WISDOM_FIELDS = [
    "wisdom_score",
    "wisdom_probability",
    "wisdom_prediction",
    "wisdom_direction",
]

OUTCOME_FIELDS = [
    "actual_outcome",
    "outcome",
    "realized_outcome",
    "actual_result",
    "result",
    "success",
    "label",
]

EVIDENCE_AGREEMENT_FIELDS = [
    "evidence_agreement",
    "agreement",
]

EVIDENCE_STRENGTH_FIELDS = [
    "evidence_strength",
    "strength",
]

CONFIDENCE_FIELDS = [
    "model_confidence",
    "confidence",
    "prediction_confidence",
]

REFLECTION_SCORE_FIELDS = [
    "reflection_score",
]

TIMESTAMP_FIELDS = [
    "timestamp",
    "created_at",
    "updated_at",
    "time",
]


def stable_id(record: Dict[str, Any], source: str) -> str:
    value = first_value(record, ID_FIELDS)

    if value not in (None, ""):
        return f"{source}:{str(value).strip()}"

    canonical = json.dumps(
        record,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

    return f"{source}:sha256:{digest}"


def sqlite_records(path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    records = []
    audit = []

    if not os.path.exists(path):
        return records, audit

    try:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row

        tables = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        for table_row in tables:
            table = table_row["name"]

            try:
                rows = connection.execute(
                    f'SELECT * FROM "{table}"'
                ).fetchall()

                for row in rows:
                    payload = dict(row)
                    payload["__source_db"] = os.path.basename(path)
                    payload["__source_table"] = table
                    records.append(payload)

            except Exception as exc:
                audit.append({
                    "source": path,
                    "table": table,
                    "status": "TABLE_READ_ERROR",
                    "reason": repr(exc),
                })

        connection.close()

    except Exception as exc:
        audit.append({
            "source": path,
            "status": "DB_READ_ERROR",
            "reason": repr(exc),
        })

    return records, audit


def json_records(path: str) -> List[Tuple[str, Dict[str, Any]]]:
    payload = load_json(path, None)

    if payload is None:
        return []

    items = []

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                items.append((os.path.basename(path), item))

    elif isinstance(payload, dict):
        for key, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        items.append(
                            (f"{os.path.basename(path)}:{key}", item)
                        )
            else:
                items.append((os.path.basename(path), payload))
                break

    return items


def build_indexes(
    records: List[Tuple[str, Dict[str, Any]]]
) -> Dict[str, Dict[str, List[Tuple[str, Dict[str, Any]]]]]:
    indexes = {
        "model": {},
        "wisdom": {},
        "outcome": {},
    }

    for source, record in records:
        case_id = stable_id(record, source)

        if first_value(record, MODEL_FIELDS) is not None:
            indexes["model"].setdefault(case_id, []).append((source, record))

        if first_value(record, WISDOM_FIELDS) is not None:
            indexes["wisdom"].setdefault(case_id, []).append((source, record))

        if first_value(record, OUTCOME_FIELDS) is not None:
            indexes["outcome"].setdefault(case_id, []).append((source, record))

    return indexes


def find_by_identity(
    records: List[Tuple[str, Dict[str, Any]]],
    source_record: Dict[str, Any],
    fields: List[str],
) -> Optional[Tuple[str, Dict[str, Any]]]:

    source_id = first_value(source_record, ID_FIELDS)

    if source_id in (None, ""):
        return None

    target = str(source_id).strip().lower()

    for source, record in records:
        value = first_value(record, ID_FIELDS)

        if value not in (None, ""):
            if str(value).strip().lower() == target:
                if first_value(record, fields) is not None:
                    return source, record

    return None


def existing_reflections() -> List[Dict[str, Any]]:
    payload = load_json(REFLECTION_FILE, {"reflections": []})

    if isinstance(payload, dict):
        payload = payload.get("reflections", [])

    if not isinstance(payload, list):
        return []

    return [item for item in payload if isinstance(item, dict)]


def valid_existing(reflection: Dict[str, Any]) -> bool:
    return (
        first_value(reflection, MODEL_FIELDS) is not None
        and first_value(reflection, WISDOM_FIELDS) is not None
        and first_value(reflection, OUTCOME_FIELDS) is not None
    )


def main() -> int:
    started = time.time()

    db_records = []
    read_audit = []

    for db in DB_FILES:
        rows, audit = sqlite_records(db)
        db_records.extend(
            (os.path.basename(db), row)
            for row in rows
        )
        read_audit.extend(audit)

    json_sources = [
        MODEL_FILE,
        MEMORY_FILE,
    ]

    all_records = list(db_records)

    for path in json_sources:
        all_records.extend(json_records(path))

    old_reflections = existing_reflections()

    valid_old = [
        item for item in old_reflections
        if valid_existing(item)
    ]

    rejected_existing = [
        {
            "case_id": stable_id(item, "existing_reflection"),
            "status": "EXISTING_REFLECTION_INCOMPLETE",
        }
        for item in old_reflections
        if not valid_existing(item)
    ]

    existing_ids = set()

    for item in valid_old:
        existing_ids.add(
            str(
                item.get("case_id")
                or item.get("id")
                or stable_id(item, "existing_reflection")
            )
        )

    candidates = []
    rejection = []

    model_candidates = []

    for source, record in all_records:
        model_value = first_value(record, MODEL_FIELDS)

        if model_value is not None:
            model_candidates.append((source, record))

    for source, model_record in model_candidates:
        identity = first_value(model_record, ID_FIELDS)

        if identity in (None, ""):
            rejection.append({
                "source": source,
                "status": "REJECTED",
                "reason": "NO_STABLE_IDENTITY",
            })
            continue

        case_id = str(identity)

        if case_id in existing_ids:
            continue

        wisdom_match = find_by_identity(
            all_records,
            model_record,
            WISDOM_FIELDS,
        )

        outcome_match = find_by_identity(
            all_records,
            model_record,
            OUTCOME_FIELDS,
        )

        if wisdom_match is None:
            rejection.append({
                "case_id": case_id,
                "source": source,
                "status": "REJECTED",
                "reason": "MISSING_WISDOM",
            })
            continue

        if outcome_match is None:
            rejection.append({
                "case_id": case_id,
                "source": source,
                "status": "REJECTED",
                "reason": "MISSING_REAL_OUTCOME",
            })
            continue

        wisdom_source, wisdom_record = wisdom_match
        outcome_source, outcome_record = outcome_match

        probability = finite(
            first_value(model_record, MODEL_FIELDS)
        )

        wisdom_score = finite(
            first_value(wisdom_record, WISDOM_FIELDS)
        )

        actual_outcome = finite(
            first_value(outcome_record, OUTCOME_FIELDS)
        )

        if (
            probability is None
            or wisdom_score is None
            or actual_outcome is None
        ):
            rejection.append({
                "case_id": case_id,
                "status": "REJECTED",
                "reason": "NON_NUMERIC_REQUIRED_EVIDENCE",
            })
            continue

        evidence_agreement = finite(
            first_value(model_record, EVIDENCE_AGREEMENT_FIELDS)
        )

        if evidence_agreement is None:
            evidence_agreement = finite(
                first_value(wisdom_record, EVIDENCE_AGREEMENT_FIELDS)
            )

        evidence_strength = finite(
            first_value(model_record, EVIDENCE_STRENGTH_FIELDS)
        )

        if evidence_strength is None:
            evidence_strength = finite(
                first_value(wisdom_record, EVIDENCE_STRENGTH_FIELDS)
            )

        model_confidence = finite(
            first_value(model_record, CONFIDENCE_FIELDS)
        )

        if model_confidence is None:
            model_confidence = abs(probability - 0.5) * 2.0

        reflection_score = finite(
            first_value(outcome_record, REFLECTION_SCORE_FIELDS)
        )

        if reflection_score is None:
            reflection_score = None

        timestamp = (
            first_value(outcome_record, TIMESTAMP_FIELDS)
            or first_value(model_record, TIMESTAMP_FIELDS)
            or first_value(wisdom_record, TIMESTAMP_FIELDS)
        )

        reflection = {
            "case_id": case_id,
            "probability": probability,
            "wisdom_score": wisdom_score,
            "actual_outcome": actual_outcome,
            "model_confidence": model_confidence,
            "prediction_error": abs(
                probability - (1.0 if actual_outcome >= 0.5 else 0.0)
            ),
            "source_integrity": {
                "model_source": source,
                "wisdom_source": wisdom_source,
                "outcome_source": outcome_source,
                "synthetic": False,
                "reconciled_at": time.time(),
            },
        }

        if evidence_agreement is not None:
            reflection["evidence_agreement"] = max(
                0.0, min(1.0, evidence_agreement)
            )

        if evidence_strength is not None:
            reflection["evidence_strength"] = max(
                0.0, min(1.0, evidence_strength)
            )

        if reflection_score is not None:
            reflection["reflection_score"] = max(
                0.0, min(1.0, reflection_score)
            )

        if timestamp is not None:
            reflection["timestamp"] = timestamp

        candidates.append(reflection)
        existing_ids.add(case_id)

    final_reflections = valid_old + candidates

    save_json(
        REFLECTION_FILE,
        {
            "reflections": final_reflections,
            "metadata": {
                "schema": "BIRTH_EDGE_REAL_REFLECTION_V1",
                "synthetic_data": False,
                "generated_at": time.time(),
                "count": len(final_reflections),
            },
        },
    )

    audit_payload = {
        "engine": "BIRTH_EDGE_REFLECTION_RECONCILIATION",
        "version": 1,
        "synthetic_data": False,
        "started_at": started,
        "completed_at": time.time(),
        "source_record_count": len(all_records),
        "existing_reflection_count": len(old_reflections),
        "valid_existing_reflections": len(valid_old),
        "new_valid_reflections": len(candidates),
        "final_reflection_count": len(final_reflections),
        "rejected_existing": rejected_existing,
        "rejected_candidates": rejection,
        "read_audit": read_audit,
    }

    save_json(AUDIT_FILE, audit_payload)

    print("=" * 72)
    print("BIRTH_EDGE REAL REFLECTION RECONCILIATION")
    print("=" * 72)
    print("SOURCE RECORDS:", len(all_records))
    print("EXISTING VALID:", len(valid_old))
    print("NEW VALID:", len(candidates))
    print("FINAL REFLECTIONS:", len(final_reflections))
    print("REJECTED:", len(rejection) + len(rejected_existing))
    print("SYNTHETIC DATA: NO")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

python3 -m py_compile reflection_reconcile.py

python3 reflection_reconcile.py

echo
echo "=== RECONVERGENCE AFTER REAL RECONCILIATION ==="

python3 reconvergence.py

echo
echo "=== AUDIT SUMMARY ==="

python3 - <<'PY'
import json

with open("data/reflection_reconciliation_audit.json", "r") as f:
    a = json.load(f)

for k in [
    "source_record_count",
    "existing_reflection_count",
    "valid_existing_reflections",
    "new_valid_reflections",
    "final_reflection_count",
]:
    print(f"{k}: {a.get(k)}")

rejected = a.get("rejected_candidates", [])
reasons = {}

for row in rejected:
    reason = row.get("reason", "UNKNOWN")
    reasons[reason] = reasons.get(reason, 0) + 1

print("rejection_reasons:", reasons)
PY

echo
echo "=== INSTALL COMPLETE ==="
echo "Reflection evidence is now audited and non-synthetic."
