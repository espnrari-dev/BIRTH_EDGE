#!/usr/bin/env python3
"""
BIRTH_EDGE RECONVERGENCE V4
===========================

DETERMINISTIC HISTORICAL CHANNEL REPLAY
WITH EXPLICIT FEATURE-SCHEMA RECONCILIATION

Purpose
-------
V3 discovered that the persisted model expects:

    liquidity_usd

while historical learning_results stores:

    initial_liquidity_usd

V4 resolves this deterministic schema mismatch without changing
the underlying value and without introducing synthetic information.

Architecture

    learning_results
            |
            v
    FEATURE RECONCILIATION
            |
       +----+----+
       |         |
       v         v
    MODEL      WISDOM
    REPLAY     REPLAY
       |         |
       +----+----+
            |
            v
       OBSERVED REALITY
            |
            v
       RECONVERGENCE

Integrity rules
---------------

1. No random values.
2. No synthetic cases.
3. No generated outcomes.
4. No outcome leakage into model replay.
5. No outcome leakage into wisdom replay.
6. Model parameters come only from ml_model.json.
7. Wisdom comes only from cognition.db wisdom_rules.
8. Reality comes only from learning_results.
9. liquidity_usd is deterministically mapped from
   initial_liquidity_usd when necessary.
10. Every feature mapping is recorded as provenance.
"""

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple


ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

LEARNING_DB = os.path.join(DATA, "learning.db")
COGNITION_DB = os.path.join(DATA, "cognition.db")

MODEL_FILE = os.path.join(DATA, "ml_model.json")
REFLECTION_FILE = os.path.join(DATA, "ml_reflection.json")
AUDIT_FILE = os.path.join(
    DATA,
    "reflection_reconciliation_audit.json",
)

EPS = 1e-12


# ================================================================
# BASIC UTILITIES
# ================================================================

def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def atomic_save(path: str, payload: Any) -> None:
    temp = path + ".tmp"

    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temp, path)


def finite(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None

        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None


def clamp01(value: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def sigmoid(value: float) -> float:
    value = max(
        -60.0,
        min(
            60.0,
            value,
        ),
    )

    return 1.0 / (
        1.0 + math.exp(-value)
    )


# ================================================================
# HISTORICAL DATA
# ================================================================

def stable_case_id(row: Dict[str, Any]) -> str:
    addr = row.get("addr")

    if addr not in (
        None,
        "",
    ):
        return str(addr)

    canonical = json.dumps(
        row,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]

    return f"learning_results:sha256:{digest}"


def load_learning_rows() -> List[Dict[str, Any]]:
    if not os.path.exists(LEARNING_DB):
        raise RuntimeError(
            f"Missing learning database: {LEARNING_DB}"
        )

    connection = sqlite3.connect(
        f"file:{LEARNING_DB}?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT *
            FROM learning_results
            ORDER BY
                updated_at ASC,
                discovered_at ASC,
                addr ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def load_wisdom_rules() -> List[Dict[str, Any]]:
    if not os.path.exists(COGNITION_DB):
        return []

    connection = sqlite3.connect(
        f"file:{COGNITION_DB}?mode=ro",
        uri=True,
    )

    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                id,
                rule_text,
                confidence,
                source,
                created_at
            FROM wisdom_rules
            ORDER BY id ASC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


# ================================================================
# FEATURE SCHEMA RECONCILIATION
# ================================================================

FEATURE_ALIASES = {
    "liquidity_usd": [
        "liquidity_usd",
        "initial_liquidity_usd",
    ],
    "initial_liquidity_usd": [
        "initial_liquidity_usd",
        "liquidity_usd",
    ],
}


def resolve_feature(
    row: Dict[str, Any],
    feature: str,
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """
    Resolve a model feature against historical row fields.

    Returns:

        value
        source_field
        mapping_mode

    Important:
        This performs schema reconciliation only.
        It does not manufacture or infer a value.
    """

    candidates = [
        feature
    ]

    candidates.extend(
        FEATURE_ALIASES.get(
            feature,
            [],
        )
    )

    seen = set()

    for source_field in candidates:
        if source_field in seen:
            continue

        seen.add(source_field)

        value = finite(
            row.get(source_field)
        )

        if value is None:
            continue

        if source_field == feature:
            mode = "DIRECT_FIELD"

        else:
            mode = "DETERMINISTIC_SCHEMA_ALIAS"

        return (
            value,
            source_field,
            mode,
        )

    return (
        None,
        None,
        None,
    )


# ================================================================
# MODEL SCALING
# ================================================================

def extract_scale_params(
    scale: Any,
) -> Tuple[float, float, str]:

    if isinstance(
        scale,
        (int, float),
    ):
        number = finite(scale)

        if (
            number is not None
            and abs(number) > EPS
        ):
            return (
                0.0,
                number,
                "DIVIDE_BY_SCALAR",
            )

        return (
            0.0,
            1.0,
            "IDENTITY_INVALID_SCALAR",
        )

    if isinstance(scale, dict):

        mean = finite(
            scale.get(
                "mean",
                scale.get(
                    "center",
                    scale.get(
                        "offset",
                        0.0,
                    ),
                ),
            )
        )

        std = finite(
            scale.get(
                "std",
                scale.get(
                    "scale",
                    scale.get(
                        "stddev",
                        None,
                    ),
                ),
            )
        )

        if (
            mean is not None
            and std is not None
            and abs(std) > EPS
        ):
            return (
                mean,
                std,
                "STANDARDIZE",
            )

        minimum = finite(
            scale.get("min")
        )

        maximum = finite(
            scale.get("max")
        )

        if (
            minimum is not None
            and maximum is not None
            and abs(maximum - minimum) > EPS
        ):
            return (
                minimum,
                maximum - minimum,
                "MINMAX",
            )

        scalar = finite(
            scale.get(
                "value",
                scale.get(
                    "factor",
                    None,
                ),
            )
        )

        if (
            scalar is not None
            and abs(scalar) > EPS
        ):
            return (
                0.0,
                scalar,
                "DIVIDE_BY_DICT_SCALAR",
            )

    return (
        0.0,
        1.0,
        "IDENTITY_UNKNOWN_SCALE",
    )


def transform_feature(
    value: float,
    scale: Any,
) -> Tuple[float, str]:

    a, b, mode = extract_scale_params(scale)

    if mode in (
        "MINMAX",
        "STANDARDIZE",
    ):
        return (
            (value - a) / b,
            mode,
        )

    if mode.startswith("DIVIDE"):
        return (
            value / b,
            mode,
        )

    return (
        value,
        mode,
    )


# ================================================================
# MODEL REPLAY
# ================================================================

def replay_model(
    row: Dict[str, Any],
    model: Dict[str, Any],
) -> Dict[str, Any]:

    feature_names = model.get(
        "feature_names",
        [],
    )

    weights = model.get(
        "weights",
        {},
    )

    feature_scale = model.get(
        "feature_scale",
        {},
    )

    bias = finite(
        model.get(
            "bias",
            0.0,
        )
    )

    if bias is None:
        bias = 0.0

    if not isinstance(
        feature_names,
        list,
    ):
        raise RuntimeError(
            "Model feature_names is not a list"
        )

    if not isinstance(
        weights,
        dict,
    ):
        raise RuntimeError(
            "Model weights is not a dictionary"
        )

    if not isinstance(
        feature_scale,
        dict,
    ):
        feature_scale = {}

    score = bias

    transformed_features = {}
    source_features = {}
    scale_modes = {}

    missing_features = []

    for feature in feature_names:

        raw, source_field, mapping_mode = resolve_feature(
            row,
            feature,
        )

        weight = finite(
            weights.get(feature)
        )

        if raw is None:
            missing_features.append(
                feature
            )
            continue

        if weight is None:
            missing_features.append(
                f"{feature}:missing_weight"
            )
            continue

        transformed, scale_mode = transform_feature(
            raw,
            feature_scale.get(feature),
        )

        transformed_features[feature] = transformed

        source_features[feature] = {
            "source_field": source_field,
            "mapping_mode": mapping_mode,
            "raw_value": raw,
        }

        scale_modes[feature] = scale_mode

        score += (
            weight * transformed
        )

    if missing_features:
        return {
            "available": False,
            "reason": "MISSING_REQUIRED_MODEL_FEATURES",
            "missing": missing_features,
            "source_features": source_features,
        }

    probability = sigmoid(score)

    return {
        "available": True,
        "probability": probability,
        "predicted_outcome": (
            1
            if probability >= 0.5
            else 0
        ),
        "model_confidence": (
            abs(probability - 0.5) * 2.0
        ),
        "raw_logit": score,
        "transformed_features": transformed_features,
        "source_features": source_features,
        "scale_modes": scale_modes,
        "feature_names": feature_names,
        "model_version": model.get(
            "version"
        ),
    }


# ================================================================
# WISDOM REPLAY
# ================================================================

def normalize_rule_text(
    text: Any,
) -> str:

    return " ".join(
        str(text or "")
        .lower()
        .strip()
        .split()
    )


def rule_vote(
    rule: Dict[str, Any],
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = normalize_rule_text(
        rule.get("rule_text")
    )

    confidence = finite(
        rule.get("confidence")
    )

    if confidence is None:
        confidence = 0.5

    confidence = clamp01(
        confidence
    )

    aliases = [
        (
            "holder_score",
            [
                "holder score",
                "holders",
                "holder",
            ],
        ),
        (
            "dev_score",
            [
                "dev score",
                "developer score",
                "dev",
            ],
        ),
        (
            "lp_lock_score",
            [
                "lp lock",
                "liquidity lock",
                "lock score",
            ],
        ),
        (
            "tax_score",
            [
                "tax score",
                "tax",
            ],
        ),
        (
            "overall_score",
            [
                "overall score",
                "score",
            ],
        ),
        (
            "initial_liquidity_usd",
            [
                "liquidity",
            ],
        ),
    ]

    matched_field = None

    for field, phrases in aliases:
        for phrase in phrases:
            if phrase in text:
                if finite(
                    row.get(field)
                ) is not None:
                    matched_field = field
                    break

        if matched_field is not None:
            break

    if matched_field is None:
        return {
            "applicable": False,
            "reason": "NO_SUPPORTED_CASE_FIELD",
        }

    match = re.search(
        r"([<>])\s*\$?\s*(\d+(?:\.\d+)?)",
        text,
    )

    if match is not None:

        operator = match.group(1)
        threshold = float(
            match.group(2)
        )

    else:

        match = re.search(
            r"(?:above|over|greater than|higher than|more than)\s+\$?\s*(\d+(?:\.\d+)?)",
            text,
        )

        if match:

            operator = ">"
            threshold = float(
                match.group(1)
            )

        else:

            match = re.search(
                r"(?:below|under|less than|lower than|fewer than)\s+\$?\s*(\d+(?:\.\d+)?)",
                text,
            )

            if match:

                operator = "<"
                threshold = float(
                    match.group(1)
                )

            else:

                return {
                    "applicable": False,
                    "reason": "NO_DETERMINISTIC_THRESHOLD",
                }

    value = finite(
        row.get(matched_field)
    )

    if value is None:
        return {
            "applicable": False,
            "reason": "FIELD_VALUE_MISSING",
        }

    condition = (
        value > threshold
        if operator == ">"
        else value < threshold
    )

    negative_words = [
        "rug",
        "loss",
        "dangerous",
        "risk",
        "fail",
        "bad",
        "avoid",
    ]

    positive_words = [
        "pump",
        "success",
        "gain",
        "profit",
        "bullish",
        "positive",
        "safe",
    ]

    negative = any(
        word in text
        for word in negative_words
    )

    positive = any(
        word in text
        for word in positive_words
    )

    if not positive and not negative:
        return {
            "applicable": False,
            "reason": "NO_DETERMINISTIC_DIRECTION",
        }

    if condition:
        vote = (
            0
            if negative
            else 1
        )
    else:
        vote = (
            1
            if negative
            else 0
        )

    return {
        "applicable": True,
        "field": matched_field,
        "value": value,
        "operator": operator,
        "threshold": threshold,
        "condition": condition,
        "vote": vote,
        "confidence": confidence,
        "rule_id": rule.get("id"),
        "rule_text": rule.get("rule_text"),
    }


def replay_wisdom(
    row: Dict[str, Any],
    rules: List[Dict[str, Any]],
) -> Dict[str, Any]:

    applicable = []
    inapplicable = []

    positive_weight = 0.0
    negative_weight = 0.0

    for rule in rules:

        result = rule_vote(
            rule,
            row,
        )

        if result.get("applicable"):

            applicable.append(
                result
            )

            weight = result[
                "confidence"
            ]

            if result["vote"] == 1:
                positive_weight += weight
            else:
                negative_weight += weight

        else:

            inapplicable.append(
                {
                    "rule_id": rule.get("id"),
                    "reason": result.get(
                        "reason"
                    ),
                }
            )

    total_weight = (
        positive_weight
        + negative_weight
    )

    if total_weight <= EPS:
        return {
            "available": False,
            "reason": "NO_CASE_APPLICABLE_WISDOM_RULE",
            "applicable_rule_count": 0,
            "inapplicable_rule_count": len(
                inapplicable
            ),
            "inapplicable": inapplicable,
        }

    wisdom_score = (
        positive_weight
        / total_weight
    )

    return {
        "available": True,
        "wisdom_score": clamp01(
            wisdom_score
        ),
        "wisdom_direction": (
            1
            if wisdom_score >= 0.5
            else 0
        ),
        "applicable_rule_count": len(
            applicable
        ),
        "inapplicable_rule_count": len(
            inapplicable
        ),
        "positive_weight": positive_weight,
        "negative_weight": negative_weight,
        "applicable_rules": applicable,
    }


# ================================================================
# OBSERVED REALITY
# ================================================================

def observed_reality(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    pumped = finite(
        row.get("pumped")
    )

    rug_pulled = finite(
        row.get("rug_pulled")
    )

    if pumped is None:
        return {
            "available": False,
            "reason": "MISSING_PUMPED_OUTCOME",
        }

    if rug_pulled is None:
        return {
            "available": False,
            "reason": "MISSING_RUG_OUTCOME",
        }

    pumped = (
        1
        if pumped >= 0.5
        else 0
    )

    rug_pulled = (
        1
        if rug_pulled >= 0.5
        else 0
    )

    if rug_pulled == 1:
        actual_outcome = 0
    else:
        actual_outcome = pumped

    return {
        "available": True,
        "actual_outcome": actual_outcome,
        "pumped": pumped,
        "rug_pulled": rug_pulled,
        "final_price_usd": finite(
            row.get("final_price_usd")
        ),
        "price_change_24h": finite(
            row.get("price_change_24h")
        ),
    }


# ================================================================
# EXISTING REFLECTIONS
# ================================================================

def existing_reflections() -> List[Dict[str, Any]]:

    payload = load_json(
        REFLECTION_FILE,
        {
            "reflections": [],
        },
    )

    if isinstance(
        payload,
        dict,
    ):
        payload = payload.get(
            "reflections",
            [],
        )

    if not isinstance(
        payload,
        list,
    ):
        return []

    return [
        item
        for item in payload
        if isinstance(
            item,
            dict,
        )
    ]


def valid_existing(
    reflection: Dict[str, Any],
) -> bool:

    required = [
        "probability",
        "wisdom_score",
        "actual_outcome",
    ]

    for field in required:

        if finite(
            reflection.get(field)
        ) is None:
            return False

    return True


def reflection_id(
    case_id: str,
) -> str:

    digest = hashlib.sha256(
        (
            "BIRTH_EDGE_RECONVERGENCE_V4:"
            + case_id
        ).encode("utf-8")
    ).hexdigest()[:24]

    return f"replay:{digest}"


# ================================================================
# MAIN
# ================================================================

def main() -> int:

    started = time.time()

    model = load_json(
        MODEL_FILE,
        {},
    )

    if not isinstance(
        model,
        dict,
    ):
        raise RuntimeError(
            "ml_model.json is invalid"
        )

    rows = load_learning_rows()
    rules = load_wisdom_rules()

    old = existing_reflections()

    preserved = [
        reflection
        for reflection in old
        if valid_existing(
            reflection
        )
    ]

    existing_case_ids = set()

    for reflection in preserved:

        case_id = (
            reflection.get(
                "case_id"
            )
            or reflection.get(
                "addr"
            )
            or reflection.get(
                "memory_id"
            )
            or reflection.get(
                "reflection_id"
            )
        )

        if case_id is not None:
            existing_case_ids.add(
                str(case_id)
            )

    new_reflections = []
    rejected = []

    model_available = 0
    wisdom_available = 0
    reality_available = 0

    direct_features = 0
    aliased_features = 0

    for row in rows:

        case_id = stable_case_id(
            row
        )

        model_result = replay_model(
            row,
            model,
        )

        if model_result.get(
            "available"
        ):
            model_available += 1

            for mapping in model_result.get(
                "source_features",
                {},
            ).values():

                if mapping.get(
                    "mapping_mode"
                ) == "DIRECT_FIELD":
                    direct_features += 1

                elif mapping.get(
                    "mapping_mode"
                ) == "DETERMINISTIC_SCHEMA_ALIAS":
                    aliased_features += 1

        wisdom_result = replay_wisdom(
            row,
            rules,
        )

        if wisdom_result.get(
            "available"
        ):
            wisdom_available += 1

        reality_result = observed_reality(
            row,
        )

        if reality_result.get(
            "available"
        ):
            reality_available += 1

        if case_id in existing_case_ids:
            continue

        missing_channels = []

        if not model_result.get(
            "available"
        ):
            missing_channels.append(
                {
                    "channel": "MODEL",
                    "reason": model_result.get(
                        "reason"
                    ),
                    "missing": model_result.get(
                        "missing",
                        [],
                    ),
                }
            )

        if not wisdom_result.get(
            "available"
        ):
            missing_channels.append(
                {
                    "channel": "WISDOM",
                    "reason": wisdom_result.get(
                        "reason"
                    ),
                }
            )

        if not reality_result.get(
            "available"
        ):
            missing_channels.append(
                {
                    "channel": "REALITY",
                    "reason": reality_result.get(
                        "reason"
                    ),
                }
            )

        if missing_channels:

            rejected.append(
                {
                    "case_id": case_id,
                    "status": "REJECTED",
                    "reason": "INCOMPLETE_CHANNEL_REPLAY",
                    "missing_channels": missing_channels,
                }
            )

            continue

        probability = model_result[
            "probability"
        ]

        predicted_outcome = model_result[
            "predicted_outcome"
        ]

        actual_outcome = reality_result[
            "actual_outcome"
        ]

        wisdom_score = wisdom_result[
            "wisdom_score"
        ]

        wisdom_direction = wisdom_result[
            "wisdom_direction"
        ]

        model_confidence = model_result[
            "model_confidence"
        ]

        prediction_error = abs(
            probability
            - float(actual_outcome)
        )

        model_wisdom_agreement = (
            1.0
            if predicted_outcome
            == wisdom_direction
            else 0.0
        )

        model_reality_alignment = (
            1.0
            if predicted_outcome
            == actual_outcome
            else 0.0
        )

        wisdom_reality_alignment = (
            1.0
            if wisdom_direction
            == actual_outcome
            else 0.0
        )

        three_way = (
            1.0
            if (
                model_wisdom_agreement
                == 1.0
                and model_reality_alignment
                == 1.0
                and wisdom_reality_alignment
                == 1.0
            )
            else 0.0
        )

        reflection = {
            "case_id": case_id,
            "reflection_id": reflection_id(
                case_id
            ),
            "probability": probability,
            "predicted_outcome": predicted_outcome,
            "wisdom_score": wisdom_score,
            "actual_outcome": actual_outcome,
            "model_confidence": model_confidence,
            "prediction_error": prediction_error,
            "correct": (
                predicted_outcome
                == actual_outcome
            ),
            "model_wisdom_agreement": model_wisdom_agreement,
            "model_reality_alignment": model_reality_alignment,
            "wisdom_reality_alignment": wisdom_reality_alignment,
            "three_way_convergence": three_way,

            "reconstruction": {
                "version": 4,
                "synthetic": False,
                "model_mode": (
                    "DETERMINISTIC_PARAMETER_REPLAY"
                ),
                "wisdom_mode": (
                    "DETERMINISTIC_RULE_APPLICATION"
                ),
                "reality_mode": (
                    "OBSERVED_OUTCOME"
                ),
                "schema_reconciliation": (
                    "DETERMINISTIC_FEATURE_ALIAS"
                ),
                "outcome_leakage": False,
            },

            "source_integrity": {
                "model_source": (
                    "data/ml_model.json"
                ),
                "model_version": (
                    model_result.get(
                        "model_version"
                    )
                ),
                "wisdom_source": (
                    "data/cognition.db:"
                    "wisdom_rules"
                ),
                "reality_source": (
                    "data/learning.db:"
                    "learning_results"
                ),
                "synthetic": False,
                "outcome_leakage": False,
                "reconciled_at": time.time(),
            },

            "model_replay": {
                "raw_logit": (
                    model_result[
                        "raw_logit"
                    ]
                ),
                "feature_names": (
                    model_result[
                        "feature_names"
                    ]
                ),
                "scale_modes": (
                    model_result[
                        "scale_modes"
                    ]
                ),
                "source_features": (
                    model_result[
                        "source_features"
                    ]
                ),
                "transformed_features": (
                    model_result[
                        "transformed_features"
                    ]
                ),
            },

            "wisdom_replay": {
                "applicable_rule_count": (
                    wisdom_result[
                        "applicable_rule_count"
                    ]
                ),
                "inapplicable_rule_count": (
                    wisdom_result[
                        "inapplicable_rule_count"
                    ]
                ),
                "applicable_rules": (
                    wisdom_result[
                        "applicable_rules"
                    ]
                ),
            },

            "reality": reality_result,

            "metadata": {
                "addr": row.get(
                    "addr"
                ),
                "chain": row.get(
                    "chain"
                ),
                "symbol": row.get(
                    "symbol"
                ),
                "discovered_at": row.get(
                    "discovered_at"
                ),
                "updated_at": row.get(
                    "updated_at"
                ),
            },
        }

        new_reflections.append(
            reflection
        )

        existing_case_ids.add(
            case_id
        )

    final_reflections = (
        preserved
        + new_reflections
    )

    metadata = {
        "schema": (
            "BIRTH_EDGE_REAL_REFLECTION_V4"
        ),
        "synthetic_data": False,
        "outcome_leakage": False,
        "generated_at": time.time(),
        "count": len(
            final_reflections
        ),
        "preserved_existing": len(
            preserved
        ),
        "replayed_historical": len(
            new_reflections
        ),
        "schema_reconciliation": {
            "enabled": True,
            "liquidity_usd_alias": (
                "initial_liquidity_usd"
            ),
            "mapping_is_value_preserving": True,
        },
    }

    atomic_save(
        REFLECTION_FILE,
        {
            "metadata": metadata,
            "reflections": final_reflections,
        },
    )

    reason_counts = {}

    for item in rejected:

        for channel in item.get(
            "missing_channels",
            [],
        ):

            key = (
                f"{channel.get('channel')}:"
                f"{channel.get('reason')}"
            )

            reason_counts[key] = (
                reason_counts.get(
                    key,
                    0,
                )
                + 1
            )

    audit = {
        "engine": (
            "BIRTH_EDGE_REFLECTION_RECONCILIATION"
        ),
        "version": 4,
        "synthetic_data": False,
        "outcome_leakage": False,

        "started_at": started,
        "completed_at": time.time(),

        "learning_rows": len(
            rows
        ),
        "wisdom_rules": len(
            rules
        ),

        "existing_reflection_count": len(
            old
        ),

        "preserved_existing_reflections": (
            len(preserved)
        ),

        "model_channel_available": (
            model_available
        ),

        "wisdom_channel_available": (
            wisdom_available
        ),

        "reality_channel_available": (
            reality_available
        ),

        "direct_feature_resolutions": (
            direct_features
        ),

        "aliased_feature_resolutions": (
            aliased_features
        ),

        "new_valid_reflections": len(
            new_reflections
        ),

        "final_reflection_count": len(
            final_reflections
        ),

        "rejected_count": len(
            rejected
        ),

        "rejection_reasons": (
            reason_counts
        ),

        "rejected_candidates": rejected,

        "schema_reconciliation": {
            "liquidity_usd_source": (
                "initial_liquidity_usd"
            ),
            "method": (
                "DETERMINISTIC_SCHEMA_ALIAS"
            ),
            "synthetic": False,
            "outcome_leakage": False,
        },
    }

    atomic_save(
        AUDIT_FILE,
        audit,
    )

    print("=" * 72)
    print(
        "BIRTH_EDGE RECONVERGENCE V4"
    )
    print(
        "DETERMINISTIC HISTORICAL CHANNEL REPLAY"
    )
    print(
        "WITH FEATURE-SCHEMA RECONCILIATION"
    )
    print("=" * 72)

    print(
        "HISTORICAL LEARNING ROWS:",
        len(rows),
    )

    print(
        "WISDOM RULES:",
        len(rules),
    )

    print(
        "MODEL CHANNEL AVAILABLE:",
        model_available,
    )

    print(
        "WISDOM CHANNEL AVAILABLE:",
        wisdom_available,
    )

    print(
        "REALITY CHANNEL AVAILABLE:",
        reality_available,
    )

    print(
        "DIRECT FEATURE RESOLUTIONS:",
        direct_features,
    )

    print(
        "ALIASED FEATURE RESOLUTIONS:",
        aliased_features,
    )

    print(
        "PRESERVED REFLECTIONS:",
        len(preserved),
    )

    print(
        "NEW REPLAYED REFLECTIONS:",
        len(new_reflections),
    )

    print(
        "FINAL REFLECTIONS:",
        len(final_reflections),
    )

    print(
        "REJECTED:",
        len(rejected),
    )

    print(
        "SYNTHETIC DATA: NO"
    )

    print(
        "OUTCOME LEAKAGE: NO"
    )

    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
