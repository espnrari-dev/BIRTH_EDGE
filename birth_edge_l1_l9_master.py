#!/usr/bin/env python3
"""
BIRTH_EDGE — L1 → L9 MASTER EVIDENCE HARNESS

Complete single-file evidence ladder:

L1   Discovery
L2   Repeatability
L3   Feature Stability
L4   Functional Agreement
L5   Holdout Validation
L6   Baseline / Generalization
L7   Cross-Seed Structure
L8   Structural Identifiability
L8.1 Identifiability Investigation Gate
L9   Functional Convergence / Mechanism Recovery

Important:
- Uses the actual aegis_rule_miner when available.
- Does NOT replace the user's miner with a fabricated result.
- Does NOT silently convert failed discovery into synthetic rules.
- Separates exact-rule similarity from feature-level similarity.
- Continuous thresholds are compared separately from feature identity.
- The introspection layer never calls inspect.getmembers() on Rule
  instances because computed properties can throw during getattr().
- Every level is retained in the final JSON and Markdown evidence.
"""

import os
import sys
import json
import math
import time
import random
import hashlib
import statistics
import traceback
import importlib
import inspect
import re
from typing import Any, Dict, List, Optional, Tuple


# ================================================================
# CONFIGURATION
# ================================================================

ROOT = os.path.expanduser("~/BIRTH_EDGE")
OUT_DIR = os.path.join(ROOT, "L1_L9_EVIDENCE")

os.makedirs(OUT_DIR, exist_ok=True)

MASTER_JSON = os.path.join(
    OUT_DIR,
    "BIRTH_EDGE_L1_L9_MASTER_EVIDENCE.json",
)

MASTER_MD = os.path.join(
    OUT_DIR,
    "BIRTH_EDGE_L1_L9_MASTER_EVIDENCE.md",
)

SEEDS = list(range(10))

TRAIN_N = 200
HOLDOUT_N = 200
L6_N = 15

FEATURES = [
    "liquidity",
    "holder_score",
    "volume",
    "buy_pressure",
]

TARGET_FEATURES = {
    "liquidity",
    "holder_score",
}

TRUE_RULE = {
    "liquidity": 12000.0,
    "holder_score": 15.0,
}


# ================================================================
# UTILITIES
# ================================================================

def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def safe_float(
    x: Any,
    default: Optional[float] = None,
) -> Optional[float]:
    try:
        y = float(x)
        return y if finite(y) else default
    except Exception:
        return default


def mean(xs) -> float:
    values = [
        float(x)
        for x in xs
        if finite(x)
    ]

    return (
        statistics.mean(values)
        if values
        else 0.0
    )


def stdev(xs) -> float:
    values = [
        float(x)
        for x in xs
        if finite(x)
    ]

    return (
        statistics.stdev(values)
        if len(values) > 1
        else 0.0
    )


def pct(x: float) -> float:
    return round(float(x) * 100.0, 4)


def sha256_obj(obj: Any) -> str:
    raw = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def dump_json(
    path: str,
    obj: Any,
) -> None:
    tmp = path + ".tmp"

    with open(
        tmp,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            obj,
            f,
            indent=2,
            sort_keys=True,
            default=str,
        )
        f.write("\n")

    os.replace(tmp, path)


def normalize_row(row: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(row, dict):
        return None

    out = dict(row)

    for feature in FEATURES:
        if feature in out:
            value = safe_float(
                out[feature],
                None,
            )

            if value is not None:
                out[feature] = value

    if "target" in out:
        out["target"] = int(bool(out["target"]))

    elif "label" in out:
        out["target"] = int(bool(out["label"]))

    elif "y" in out:
        out["target"] = int(bool(out["y"]))

    return out


# ================================================================
# ACTUAL USER MODULE
# ================================================================

def load_existing_module():
    sys.path.insert(0, ROOT)
    sys.path.insert(
        0,
        os.path.expanduser("~"),
    )

    candidates = [
        "aegis_rule_miner",
        "birth_edge",
        "birth_edge_rule_miner",
    ]

    errors = {}

    for name in candidates:
        try:
            module = importlib.import_module(name)
            return module, errors
        except Exception as exc:
            errors[name] = repr(exc)

    return None, errors


# ================================================================
# CONTROLLED BENCHMARK DATA
# ================================================================

def make_dataset(
    seed: int,
    n: int,
) -> List[Dict[str, float]]:
    """
    Controlled discovery benchmark.

    Same underlying generating mechanism across seeds.
    Sampling changes with seed.
    """

    rng = random.Random(seed)

    rows = []

    for _ in range(n):
        liquidity = rng.uniform(
            0.0,
            30000.0,
        )

        holder_score = rng.uniform(
            0.0,
            30.0,
        )

        volume = rng.uniform(
            0.0,
            30000.0,
        )

        buy_pressure = rng.uniform(
            0.0,
            1.0,
        )

        target = int(
            liquidity > TRUE_RULE["liquidity"]
            and
            holder_score > TRUE_RULE["holder_score"]
        )

        rows.append(
            {
                "liquidity": liquidity,
                "holder_score": holder_score,
                "volume": volume,
                "buy_pressure": buy_pressure,
                "target": target,
            }
        )

    return rows


# ================================================================
# RULE EXTRACTION
# ================================================================

def infer_feature(text: Any) -> Optional[str]:
    if text is None:
        return None

    text = str(text)

    for feature in FEATURES:
        if feature in text:
            return feature

    return None


def infer_threshold(text: Any) -> Optional[float]:
    if text is None:
        return None

    text = str(text)

    matches = re.findall(
        r"(?<![A-Za-z_])"
        r"[-+]?"
        r"(?:\d+(?:\.\d*)?|\.\d+)",
        text,
    )

    if not matches:
        return None

    try:
        return float(matches[-1])
    except Exception:
        return None


def infer_operator(text: Any) -> Optional[str]:
    if text is None:
        return None

    text = str(text)

    for op in (
        ">=",
        "<=",
        "==",
        "!=",
        ">",
        "<",
    ):
        if op in text:
            return op

    return None


def safe_get(
    obj: Any,
    name: str,
    default=None,
):
    """
    Safe attribute access.

    A property can throw. Never let one malformed property
    destroy the entire evidence run.
    """

    try:
        return getattr(
            obj,
            name,
        )
    except Exception:
        return default


def extract_rule_objects(
    result: Any,
) -> List[Any]:
    if result is None:
        return []

    if isinstance(
        result,
        dict,
    ):
        for key in (
            "rules",
            "best_rules",
            "discovered_rules",
            "solutions",
            "population",
            "rule_set",
            "rule_sets",
            "elite",
            "best",
            "result",
            "results",
        ):
            if key in result:
                extracted = extract_rule_objects(
                    result[key]
                )

                if extracted:
                    return extracted

        keys = set(result.keys())

        if keys.intersection(
            {
                "feature",
                "field",
                "variable",
                "predicate",
                "canonical",
                "condition",
                "conditions",
                "threshold",
                "operator",
                "op",
                "expression",
                "rule",
            }
        ):
            return [result]

        return []

    if isinstance(
        result,
        (list, tuple, set),
    ):
        out = []

        for item in result:
            out.extend(
                extract_rule_objects(item)
            )

        return out

    if isinstance(
        result,
        str,
    ):
        return [result]

    # Do NOT introspect every property on arbitrary objects.
    # Read only static class/object dictionaries where possible.

    try:
        if hasattr(
            result,
            "__dict__",
        ):
            return [result]
    except Exception:
        pass

    return []


def canonical_rule(
    rule: Any,
) -> Dict[str, Any]:

    if isinstance(
        rule,
        str,
    ):
        text = rule.strip()

        return {
            "canonical": text,
            "feature": infer_feature(text),
            "threshold": infer_threshold(text),
            "operator": infer_operator(text),
            "raw": text,
        }

    if isinstance(
        rule,
        dict,
    ):
        raw = dict(rule)

        canonical = (
            raw.get("canonical")
            or raw.get("predicate")
            or raw.get("condition")
            or raw.get("rule")
            or raw.get("expression")
            or str(raw)
        )

        feature = (
            raw.get("feature")
            or raw.get("field")
            or raw.get("variable")
            or infer_feature(canonical)
        )

        threshold = None

        for key in (
            "threshold",
            "cutoff",
            "value",
        ):
            if key in raw:
                threshold = safe_float(
                    raw.get(key),
                    None,
                )

                if threshold is not None:
                    break

        if threshold is None:
            threshold = infer_threshold(
                canonical
            )

        operator = (
            raw.get("operator")
            or raw.get("op")
            or infer_operator(canonical)
        )

        return {
            "canonical": str(canonical),
            "feature": (
                str(feature)
                if feature is not None
                else None
            ),
            "threshold": threshold,
            "operator": operator,
            "raw": raw,
        }

    # Safe extraction from Rule-like objects.
    canonical = None
    feature = None
    threshold = None
    operator = None

    for name in (
        "canonical",
        "predicate",
        "condition",
        "rule",
        "expression",
    ):
        value = safe_get(
            rule,
            name,
            None,
        )

        if value is not None:
            canonical = value
            break

    if canonical is None:
        canonical = str(rule)

    for name in (
        "feature",
        "field",
        "variable",
    ):
        value = safe_get(
            rule,
            name,
            None,
        )

        if value is not None:
            feature = value
            break

    if feature is None:
        feature = infer_feature(
            canonical
        )

    for name in (
        "threshold",
        "cutoff",
        "value",
    ):
        value = safe_get(
            rule,
            name,
            None,
        )

        value = safe_float(
            value,
            None,
        )

        if value is not None:
            threshold = value
            break

    if threshold is None:
        threshold = infer_threshold(
            canonical
        )

    for name in (
        "operator",
        "op",
    ):
        value = safe_get(
            rule,
            name,
            None,
        )

        if value is not None:
            operator = value
            break

    if operator is None:
        operator = infer_operator(
            canonical
        )

    return {
        "canonical": str(canonical),
        "feature": (
            str(feature)
            if feature is not None
            else None
        ),
        "threshold": threshold,
        "operator": operator,
        "raw": str(rule),
    }


def normalize_rules(
    result: Any,
) -> List[Dict[str, Any]]:

    objects = extract_rule_objects(
        result
    )

    rules = []

    for obj in objects:
        try:
            rule = canonical_rule(obj)

            if (
                rule.get("feature") is not None
                or
                rule.get("canonical")
            ):
                rules.append(rule)

        except Exception:
            continue

    return rules


# ================================================================
# SAFE OBJECT METHOD DISCOVERY
# ================================================================

def candidate_object_methods(
    obj: Any,
    class_name: str,
):
    """
    CRITICAL SAFETY FIX.

    NEVER use:

        inspect.getmembers(obj, inspect.ismethod)

    because inspect.getmembers() invokes getattr() on every
    attribute. AEGIS Rule exposes a computed `complexity`
    property which can throw:

        TypeError: object of type 'int' has no len()

    Static inspection obtains attribute names without evaluating
    those descriptors.
    """

    methods = []

    try:
        static_members = inspect.getmembers_static(
            obj
        )
    except Exception:
        static_members = []

    candidate_names = []

    for name, descriptor in static_members:
        if name.startswith("_"):
            continue

        low = name.lower()

        if any(
            token in low
            for token in (
                "discover",
                "mine",
                "rule",
                "evolve",
                "fit",
                "learn",
                "run",
                "search",
                "generate",
                "extract",
            )
        ):
            candidate_names.append(
                name
            )

    for name in candidate_names:
        try:
            fn = getattr(
                obj,
                name,
            )
        except Exception:
            continue

        if not callable(fn):
            continue

        methods.append(
            (
                name,
                fn,
            )
        )

    return methods


# ================================================================
# MODULE-LEVEL CALLABLE DISCOVERY
# ================================================================

def candidate_module_callables(
    module,
):
    if module is None:
        return []

    methods = []

    try:
        static_members = inspect.getmembers_static(
            module
        )
    except Exception:
        static_members = []

    for name, descriptor in static_members:
        if name.startswith("_"):
            continue

        low = name.lower()

        if not any(
            token in low
            for token in (
                "discover",
                "mine",
                "rule",
                "evolve",
                "fit",
                "learn",
                "run",
                "search",
                "generate",
            )
        ):
            continue

        try:
            fn = getattr(
                module,
                name,
            )
        except Exception:
            continue

        if callable(fn):
            methods.append(
                (
                    name,
                    fn,
                )
            )

    return methods


# ================================================================
# CLASS DISCOVERY
# ================================================================

def candidate_classes(
    module,
):
    if module is None:
        return []

    classes = []

    try:
        static_members = inspect.getmembers_static(
            module
        )
    except Exception:
        static_members = []

    for name, descriptor in static_members:
        if name.startswith("_"):
            continue

        try:
            obj = getattr(
                module,
                name,
            )
        except Exception:
            continue

        if not inspect.isclass(obj):
            continue

        low = name.lower()

        if any(
            token in low
            for token in (
                "miner",
                "rule",
                "evol",
                "discover",
                "engine",
                "aegis",
            )
        ):
            classes.append(
                (
                    name,
                    obj,
                )
            )

    return classes


# ================================================================
# INVOCATION
# ================================================================

def invoke_callable(
    fn,
    rows,
    seed,
):
    attempts = [
        {
            "rows": rows,
            "seed": seed,
        },
        {
            "data": rows,
            "seed": seed,
        },
        {
            "dataset": rows,
            "seed": seed,
        },
        {
            "samples": rows,
            "seed": seed,
        },
        {
            "records": rows,
            "seed": seed,
        },
        {
            "population": rows,
            "seed": seed,
        },
        {
            "X": rows,
            "seed": seed,
        },
        {
            "rows": rows,
        },
        {
            "data": rows,
        },
        {
            "dataset": rows,
        },
        {
            "samples": rows,
        },
        {
            "records": rows,
        },
        {
            "population": rows,
        },
        {
            "X": rows,
        },
    ]

    try:
        signature = inspect.signature(
            fn
        )
    except Exception:
        signature = None

    if signature is not None:
        for kwargs in attempts:
            filtered = {
                k: v
                for k, v in kwargs.items()
                if k in signature.parameters
            }

            if not filtered:
                continue

            try:
                return fn(
                    **filtered
                )
            except TypeError:
                continue
            except Exception:
                continue

    positional_attempts = [
        (
            rows,
            seed,
        ),
        (
            rows,
        ),
    ]

    for args in positional_attempts:
        try:
            return fn(
                *args
            )
        except TypeError:
            continue
        except Exception:
            continue

    return None


def instantiate_class(
    cls,
    seed,
):
    attempts = [
        {
            "seed": seed,
        },
        {},
    ]

    try:
        signature = inspect.signature(
            cls
        )
    except Exception:
        signature = None

    if signature is not None:
        for kwargs in attempts:
            filtered = {
                k: v
                for k, v in kwargs.items()
                if k in signature.parameters
            }

            try:
                return cls(
                    **filtered
                )
            except Exception:
                continue

    try:
        return cls()
    except Exception:
        return None


# ================================================================
# MINER EXECUTION
# ================================================================

def run_miner(
    rows,
    seed,
    module,
):
    if module is None:
        return {
            "status": "NO_MINER",
            "rules": [],
            "raw": None,
            "callable": None,
            "errors": [],
        }

    errors = []

    # ------------------------------------------------------------
    # 1. Explicit module-level discovery callables
    # ------------------------------------------------------------

    for name, fn in candidate_module_callables(
        module
    ):
        result = invoke_callable(
            fn,
            rows,
            seed,
        )

        rules = normalize_rules(
            result
        )

        if rules:
            return {
                "status": "OK",
                "rules": rules,
                "raw": result,
                "callable": name,
                "class": None,
                "errors": errors,
            }

        if result is not None:
            errors.append(
                {
                    "callable": name,
                    "result_type": type(
                        result
                    ).__name__,
                    "reason": "no_normalizable_rules",
                }
            )

    # ------------------------------------------------------------
    # 2. Instantiate actual miner classes
    # ------------------------------------------------------------

    for class_name, cls in candidate_classes(
        module
    ):
        obj = instantiate_class(
            cls,
            seed,
        )

        if obj is None:
            continue

        # Safe static method discovery.
        for method_name, fn in candidate_object_methods(
            obj,
            class_name,
        ):
            result = invoke_callable(
                fn,
                rows,
                seed,
            )

            rules = normalize_rules(
                result
            )

            if rules:
                return {
                    "status": "OK",
                    "rules": rules,
                    "raw": result,
                    "callable": method_name,
                    "class": class_name,
                    "errors": errors,
                }

            if result is not None:
                errors.append(
                    {
                        "class": class_name,
                        "callable": method_name,
                        "result_type": type(
                            result
                        ).__name__,
                        "reason": "no_normalizable_rules",
                    }
                )

    return {
        "status": "NO_RULES",
        "rules": [],
        "raw": None,
        "callable": None,
        "class": None,
        "errors": errors,
    }


# ================================================================
# RULE REPRESENTATIONS
# ================================================================

def exact_rule_set(
    rules,
):
    return {
        str(r["canonical"])
        for r in rules
        if r.get("canonical")
    }


def feature_rule_set(
    rules,
):
    return {
        str(r["feature"])
        for r in rules
        if r.get("feature")
    }


def feature_operator_map(
    rules,
):
    result = {}

    for rule in rules:
        feature = rule.get(
            "feature"
        )

        if feature is None:
            continue

        operator = rule.get("operator")
        if operator is None:
            operator = infer_operator(rule.get("canonical"))
        if operator is None:
            operator = ">"
        result[str(feature)] = str(operator)

    return result


def feature_threshold_map(
    rules,
):
    result = {}

    for rule in rules:
        feature = rule.get(
            "feature"
        )

        threshold = safe_float(
            rule.get("threshold"),
            None,
        )

        if (
            feature is not None
            and threshold is not None
        ):
            result[str(feature)] = threshold

    return result


def feature_operator_threshold_map(
    rules,
):
    result = {}

    for rule in rules:
        feature = rule.get(
            "feature"
        )

        if feature is None:
            continue

        result[str(feature)] = {
            "operator": (
                rule.get("operator")
                or ">"
            ),
            "threshold": safe_float(
                rule.get("threshold"),
                None,
            ),
        }

    return result


def jaccard(
    a,
    b,
) -> float:
    a = set(a)
    b = set(b)

    union = a | b

    if not union:
        return 1.0

    return len(
        a & b
    ) / len(union)


def threshold_distance(
    a,
    b,
) -> Optional[float]:
    common = set(a) & set(b)

    if not common:
        return None

    distances = []

    for feature in common:
        x = safe_float(
            a[feature],
            None,
        )

        y = safe_float(
            b[feature],
            None,
        )

        if x is None or y is None:
            continue

        denom = max(
            abs(x),
            abs(y),
            1e-12,
        )

        distances.append(
            abs(x - y) / denom
        )

    return (
        mean(distances)
        if distances
        else None
    )


# ================================================================
# GENERIC CLASSIFIER
# ================================================================

def apply_operator(
    x,
    op,
    threshold,
):
    if op == ">":
        return x > threshold

    if op == ">=":
        return x >= threshold

    if op == "<":
        return x < threshold

    if op == "<=":
        return x <= threshold

    if op == "==":
        return x == threshold

    if op == "!=":
        return x != threshold

    return x > threshold


def predict_rule(
    row,
    rules,
) -> int:
    usable = [
        rule
        for rule in rules
        if (
            rule.get("feature")
            is not None
            and
            safe_float(
                rule.get("threshold"),
                None,
            )
            is not None
        )
    ]

    if not usable:
        return 0

    for rule in usable:
        feature = str(
            rule["feature"]
        )

        threshold = safe_float(
            rule["threshold"],
            0.0,
        )

        operator = (
            rule.get("operator")
            or infer_operator(
                rule.get("canonical")
            )
            or ">"
        )

        x = safe_float(
            row.get(feature),
            0.0,
        )

        if not apply_operator(
            x,
            operator,
            threshold,
        ):
            return 0

    return 1


def prediction_vector(
    rows,
    rules,
):
    return [
        predict_rule(
            row,
            rules,
        )
        for row in rows
    ]


def classification_metrics(
    rows,
    rules,
):
    tp = 0
    fp = 0
    tn = 0
    fn = 0

    predictions = []

    for row in rows:
        actual = int(
            row.get(
                "target",
                0,
            )
        )

        predicted = predict_rule(
            row,
            rules,
        )

        predictions.append(
            predicted
        )

        if predicted and actual:
            tp += 1

        elif predicted and not actual:
            fp += 1

        elif not predicted and not actual:
            tn += 1

        else:
            fn += 1

    total = (
        tp +
        fp +
        tn +
        fn
    )

    accuracy = (
        (tp + tn) / total
        if total
        else 0.0
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    f1 = (
        2.0 * tp
        /
        (
            2.0 * tp
            + fp
            + fn
        )
        if (
            2 * tp
            + fp
            + fn
        )
        else 0.0
    )

    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "predictions": predictions,
    }


# ================================================================
# BASELINES
# ================================================================

def baseline_75(
    rows,
):
    """
    Historical fixed baseline used for L6 comparison.
    """

    tp = 0
    fp = 0
    tn = 0
    fn = 0

    predictions = []

    for row in rows:
        actual = int(
            row.get(
                "target",
                0,
            )
        )

        predicted = int(
            safe_float(
                row.get(
                    "holder_score",
                    0,
                ),
                0.0,
            )
            > 15.0
        )

        predictions.append(
            predicted
        )

        if predicted and actual:
            tp += 1

        elif predicted and not actual:
            fp += 1

        elif not predicted and not actual:
            tn += 1

        else:
            fn += 1

    total = (
        tp +
        fp +
        tn +
        fn
    )

    return {
        "name": "HOLDER_SCORE_15_BASELINE",
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": (
            (tp + tn) / total
            if total
            else 0.0
        ),
    }


def majority_baseline(
    rows,
):
    positives = sum(
        int(row.get("target", 0))
        for row in rows
    )

    negatives = len(rows) - positives

    prediction = int(
        positives >= negatives
    )

    correct = sum(
        int(row.get("target", 0))
        == prediction
        for row in rows
    )

    return {
        "name": "MAJORITY_CLASS_BASELINE",
        "prediction": prediction,
        "accuracy": (
            correct / len(rows)
            if rows
            else 0.0
        ),
    }


# ================================================================
# L1 — DISCOVERY
# ================================================================

def level_l1(
    module,
):
    rows = make_dataset(
        0,
        TRAIN_N,
    )

    result = run_miner(
        rows,
        0,
        module,
    )

    return {
        "level": "L1",
        "name": "DISCOVERY",
        "timestamp": now(),
        "status": result["status"],
        "callable": result.get(
            "callable"
        ),
        "class": result.get(
            "class"
        ),
        "rules": result["rules"],
        "feature_set": sorted(
            feature_rule_set(
                result["rules"]
            )
        ),
        "rule_count": len(
            result["rules"]
        ),
        "errors": result.get(
            "errors",
            [],
        ),
    }


# ================================================================
# L2 — REPEATABILITY
# ================================================================

def level_l2(
    module,
):
    runs = []

    for seed in SEEDS:
        rows = make_dataset(
            seed,
            TRAIN_N,
        )

        result = run_miner(
            rows,
            seed,
            module,
        )

        runs.append(
            {
                "seed": seed,
                "status": result["status"],
                "callable": result.get(
                    "callable"
                ),
                "class": result.get(
                    "class"
                ),
                "rules": result["rules"],
                "features": sorted(
                    feature_rule_set(
                        result["rules"]
                    )
                ),
                "errors": result.get(
                    "errors",
                    [],
                ),
            }
        )

    successful = sum(
        run["status"] == "OK"
        for run in runs
    )

    return {
        "level": "L2",
        "name": "REPEATABILITY",
        "timestamp": now(),
        "seed_count": len(SEEDS),
        "runs": runs,
        "successful_runs": successful,
        "repeatability_rate": (
            successful / len(SEEDS)
            if SEEDS
            else 0.0
        ),
    }


# ================================================================
# L3 — FEATURE STABILITY
# ================================================================

def level_l3(
    l2,
):
    runs = [
        run
        for run in l2["runs"]
        if run["status"] == "OK"
    ]

    feature_sets = [
        set(run["features"])
        for run in runs
    ]

    if not feature_sets:
        return {
            "level": "L3",
            "name": "FEATURE_STABILITY",
            "status": "NO_DATA",
            "pairwise_feature_jaccard": [],
            "mean_feature_jaccard": 0.0,
            "minimum_feature_jaccard": 0.0,
            "stable_intersection": [],
            "feature_union": [],
            "feature_frequency": {},
            "all_runs_share_same_features": False,
        }

    pairwise = []

    for i in range(
        len(feature_sets)
    ):
        for j in range(
            i + 1,
            len(feature_sets),
        ):
            pairwise.append(
                jaccard(
                    feature_sets[i],
                    feature_sets[j],
                )
            )

    intersection = set.intersection(
        *feature_sets
    )

    union = set.union(
        *feature_sets
    )

    frequencies = {}

    for feature_set in feature_sets:
        for feature in feature_set:
            frequencies[feature] = (
                frequencies.get(
                    feature,
                    0,
                )
                + 1
            )

    return {
        "level": "L3",
        "name": "FEATURE_STABILITY",
        "timestamp": now(),
        "successful_runs": len(runs),
        "pairwise_feature_jaccard": pairwise,
        "mean_feature_jaccard": mean(
            pairwise
        ),
        "minimum_feature_jaccard": (
            min(pairwise)
            if pairwise
            else 0.0
        ),
        "stable_intersection": sorted(
            intersection
        ),
        "feature_union": sorted(
            union
        ),
        "feature_frequency": frequencies,
        "all_runs_share_same_features": (
            intersection == union
            and
            len(union) > 0
        ),
    }


# ================================================================
# L4 — FUNCTIONAL AGREEMENT
# ================================================================

def level_l4(
    l2,
):
    rows = make_dataset(
        999,
        HOLDOUT_N,
    )

    models = []

    for run in l2["runs"]:
        if run["status"] != "OK":
            continue

        predictions = prediction_vector(
            rows,
            run["rules"],
        )

        metrics = classification_metrics(
            rows,
            run["rules"],
        )

        models.append(
            {
                "seed": run["seed"],
                "predictions": predictions,
                "metrics": metrics,
            }
        )

    pairwise_agreement = []

    pairwise_disagreement = []

    for i in range(
        len(models)
    ):
        for j in range(
            i + 1,
            len(models),
        ):
            a = models[i]["predictions"]
            b = models[j]["predictions"]

            n = min(
                len(a),
                len(b),
            )

            if n == 0:
                continue

            agreement = sum(
                x == y
                for x, y in zip(
                    a[:n],
                    b[:n],
                )
            ) / n

            pairwise_agreement.append(
                agreement
            )

            pairwise_disagreement.append(
                1.0 - agreement
            )

    return {
        "level": "L4",
        "name": "FUNCTIONAL_AGREEMENT",
        "timestamp": now(),
        "models": len(models),
        "pairwise_agreement": pairwise_agreement,
        "pairwise_disagreement": pairwise_disagreement,
        "mean_agreement": mean(
            pairwise_agreement
        ),
        "minimum_agreement": (
            min(pairwise_agreement)
            if pairwise_agreement
            else 0.0
        ),
        "maximum_agreement": (
            max(pairwise_agreement)
            if pairwise_agreement
            else 0.0
        ),
        "model_metrics": [
            {
                "seed": model["seed"],
                "accuracy": model["metrics"]["accuracy"],
                "precision": model["metrics"]["precision"],
                "recall": model["metrics"]["recall"],
                "f1": model["metrics"]["f1"],
            }
            for model in models
        ],
    }


# ================================================================
# L5 — HOLDOUT VALIDATION
# ================================================================

def level_l5(
    l2,
):
    rows = make_dataset(
        2026,
        HOLDOUT_N,
    )

    results = []

    for run in l2["runs"]:
        if run["status"] != "OK":
            continue

        metrics = classification_metrics(
            rows,
            run["rules"],
        )

        results.append(
            {
                "seed": run["seed"],
                **metrics,
            }
        )

    accuracies = [
        result["accuracy"]
        for result in results
    ]

    f1s = [
        result["f1"]
        for result in results
    ]

    return {
        "level": "L5",
        "name": "HOLDOUT",
        "timestamp": now(),
        "n": len(rows),
        "positive_count": sum(
            int(row["target"])
            for row in rows
        ),
        "negative_count": sum(
            1 - int(row["target"])
            for row in rows
        ),
        "results": results,
        "mean_accuracy": mean(
            accuracies
        ),
        "stdev_accuracy": stdev(
            accuracies
        ),
        "best_accuracy": (
            max(accuracies)
            if accuracies
            else 0.0
        ),
        "worst_accuracy": (
            min(accuracies)
            if accuracies
            else 0.0
        ),
        "mean_f1": mean(
            f1s
        ),
    }


# ================================================================
# L6 — BASELINE / GENERALIZATION
# ================================================================

def level_l6(
    l2,
):
    rows = make_dataset(
        3030,
        L6_N,
    )

    baseline = baseline_75(
        rows
    )

    majority = majority_baseline(
        rows
    )

    results = []

    for run in l2["runs"]:
        if run["status"] != "OK":
            continue

        metrics = classification_metrics(
            rows,
            run["rules"],
        )

        results.append(
            {
                "seed": run["seed"],
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "tn": metrics["tn"],
                "fn": metrics["fn"],
                "accuracy": metrics["accuracy"],
                "improvement_over_holder_baseline":
                    metrics["accuracy"]
                    -
                    baseline["accuracy"],
                "improvement_over_majority_baseline":
                    metrics["accuracy"]
                    -
                    majority["accuracy"],
            }
        )

    improvements = [
        x["improvement_over_holder_baseline"]
        for x in results
    ]

    return {
        "level": "L6",
        "name": "BASELINE_GENERALIZATION",
        "timestamp": now(),
        "n": len(rows),
        "baseline": baseline,
        "majority_baseline": majority,
        "results": results,
        "mean_improvement": mean(
            improvements
        ),
        "best_improvement": (
            max(improvements)
            if improvements
            else 0.0
        ),
        "worst_improvement": (
            min(improvements)
            if improvements
            else 0.0
        ),
    }


# ================================================================
# L7 — CROSS-SEED STRUCTURE
# ================================================================

def level_l7(
    l2,
):
    runs = [
        run
        for run in l2["runs"]
        if run["status"] == "OK"
    ]

    feature_frequency = {}

    for run in runs:
        for feature in set(
            run["features"]
        ):
            feature_frequency[feature] = (
                feature_frequency.get(
                    feature,
                    0,
                )
                + 1
            )

    dominant = sorted(
        feature_frequency.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    dominant_features = [
        feature
        for feature, count in dominant
        if count == len(runs)
        and len(runs) > 0
    ]

    return {
        "level": "L7",
        "name": "CROSS_SEED_STRUCTURE",
        "timestamp": now(),
        "seed_count": len(runs),
        "feature_frequency": dominant,
        "dominant_features": dominant_features,
        "self_assigned_novelty_score": None,
        "external_novelty_validation": None,
        "novelty_claim_supported": False,
        "interpretation": (
            "Cross-seed engineering structure is measured. "
            "No self-assigned novelty score is treated as "
            "independent scientific evidence."
        ),
    }


# ================================================================
# L8 — STRUCTURAL IDENTIFIABILITY
# ================================================================

def level_l8(
    l2,
):
    runs = [
        run
        for run in l2["runs"]
        if run["status"] == "OK"
    ]

    pairwise_exact = []
    pairwise_feature = []
    pairwise_operator = []
    pairwise_threshold_distance = []

    pairwise_records = []

    for i in range(
        len(runs)
    ):
        for j in range(
            i + 1,
            len(runs),
        ):
            a = runs[i]["rules"]
            b = runs[j]["rules"]

            exact_a = exact_rule_set(
                a
            )

            exact_b = exact_rule_set(
                b
            )

            feature_a = feature_rule_set(
                a
            )

            feature_b = feature_rule_set(
                b
            )

            operator_a = feature_operator_map(
                a
            )

            operator_b = feature_operator_map(
                b
            )

            threshold_a = feature_threshold_map(
                a
            )

            threshold_b = feature_threshold_map(
                b
            )

            exact_j = jaccard(
                exact_a,
                exact_b,
            )

            feature_j = jaccard(
                feature_a,
                feature_b,
            )

            operator_j = jaccard(
                {
                    (
                        feature,
                        operator,
                    )
                    for feature, operator
                    in operator_a.items()
                },
                {
                    (
                        feature,
                        operator,
                    )
                    for feature, operator
                    in operator_b.items()
                },
            )

            distance = threshold_distance(
                threshold_a,
                threshold_b,
            )

            pairwise_exact.append(
                exact_j
            )

            pairwise_feature.append(
                feature_j
            )

            pairwise_operator.append(
                operator_j
            )

            if distance is not None:
                pairwise_threshold_distance.append(
                    distance
                )

            pairwise_records.append(
                {
                    "seed_a": runs[i]["seed"],
                    "seed_b": runs[j]["seed"],
                    "exact_rule_jaccard": exact_j,
                    "feature_set_jaccard": feature_j,
                    "operator_jaccard": operator_j,
                    "threshold_relative_distance": distance,
                }
            )

    exact_mean = mean(
        pairwise_exact
    )

    feature_mean = mean(
        pairwise_feature
    )

    operator_mean = mean(
        pairwise_operator
    )

    threshold_mean = mean(
        pairwise_threshold_distance
    )

    structural_identifiability = (
        feature_mean >= 0.90
        and
        operator_mean >= 0.90
        and
        threshold_mean <= 0.10
    )

    return {
        "level": "L8",
        "name": "STRUCTURAL_IDENTIFIABILITY",
        "timestamp": now(),
        "successful_runs": len(runs),
        "pair_count": len(pairwise_records),
        "pairwise_records": pairwise_records,
        "exact_rule_jaccard": pairwise_exact,
        "feature_set_jaccard": pairwise_feature,
        "operator_jaccard": pairwise_operator,
        "threshold_relative_distance":
            pairwise_threshold_distance,
        "mean_exact_rule_jaccard":
            exact_mean,
        "mean_feature_set_jaccard":
            feature_mean,
        "mean_operator_jaccard":
            operator_mean,
        "mean_threshold_relative_distance":
            threshold_mean,
        "structural_identifiability":
            structural_identifiability,
        "exact_threshold_metric_warning": (
            "Exact canonical-rule Jaccard is threshold-sensitive. "
            "Two rules using the same feature but slightly different "
            "continuous thresholds can have exact Jaccard 0.0 while "
            "feature-set Jaccard is 1.0."
        ),
    }


# ================================================================
# L8.1 — INVESTIGATION GATE
# ================================================================

def level_l81(
    l8,
    l4,
):
    structural_jaccard = (
        l8.get(
            "mean_exact_rule_jaccard",
            0.0,
        )
        > 0.0
    )

    feature_set_jaccard = (
        l8.get(
            "mean_feature_set_jaccard",
            0.0,
        )
        >= 0.90
    )

    operator_stability = (
        l8.get(
            "mean_operator_jaccard",
            0.0,
        )
        >= 0.90
    )

    threshold_stability = (
        l8.get(
            "mean_threshold_relative_distance",
            1.0,
        )
        <= 0.10
    )

    functional_floor = (
        l4.get(
            "minimum_agreement",
            0.0,
        )
        >= 0.90
    )

    structural_identifiability = (
        feature_set_jaccard
        and
        operator_stability
        and
        threshold_stability
    )

    investigate = not (
        structural_identifiability
        and
        functional_floor
    )

    return {
        "level": "L8.1",
        "name": "IDENTIFIABILITY_INVESTIGATION",
        "timestamp": now(),
        "checks": {
            "structural_jaccard":
                structural_jaccard,

            "feature_set_jaccard":
                feature_set_jaccard,

            "operator_stability":
                operator_stability,

            "threshold_stability":
                threshold_stability,

            "structural_identifiability":
                structural_identifiability,

            "functional_agreement_floor":
                functional_floor,
        },
        "exact_rule_jaccard_mean":
            l8.get(
                "mean_exact_rule_jaccard",
                0.0,
            ),
        "feature_set_jaccard_mean":
            l8.get(
                "mean_feature_set_jaccard",
                0.0,
            ),
        "operator_jaccard_mean":
            l8.get(
                "mean_operator_jaccard",
                0.0,
            ),
        "threshold_distance_mean":
            l8.get(
                "mean_threshold_relative_distance",
                0.0,
            ),
        "functional_agreement_floor":
            l4.get(
                "minimum_agreement",
                0.0,
            ),
        "verdict": (
            "L8.1-PASS"
            if not investigate
            else "L8.1-INVESTIGATE"
        ),
    }


# ================================================================
# L9 — FUNCTIONAL CONVERGENCE / MECHANISM RECOVERY
# ================================================================

def level_l9(
    l4,
    l8,
):
    functional_convergence = (
        l4.get(
            "mean_agreement",
            0.0,
        )
        >= 0.90
        and
        l4.get(
            "minimum_agreement",
            0.0,
        )
        >= 0.90
    )

    mechanism_recovery = (
        l8.get(
            "mean_feature_set_jaccard",
            0.0,
        )
        >= 0.90
        and
        l8.get(
            "mean_operator_jaccard",
            0.0,
        )
        >= 0.90
        and
        l8.get(
            "mean_threshold_relative_distance",
            1.0,
        )
        <= 0.10
    )

    if (
        functional_convergence
        and
        mechanism_recovery
    ):
        verdict = (
            "L9-MECHANISM-RECOVERY"
        )

    elif functional_convergence:
        verdict = (
            "L9-FUNCTIONAL-CONVERGENCE"
        )

    else:
        verdict = (
            "L9-NO-CONVERGENCE"
        )

    return {
        "level": "L9",
        "name": "CONVERGENCE_AND_MECHANISM_RECOVERY",
        "timestamp": now(),
        "checks": {
            "functional_convergence":
                functional_convergence,

            "mechanism_recovery":
                mechanism_recovery,
        },
        "functional_convergence":
            functional_convergence,

        "mechanism_recovery":
            mechanism_recovery,

        "verdict":
            verdict,
    }


# ================================================================
# SYNTHESIS
# ================================================================

def synthesize(
    results,
):
    l1 = results["L1"]
    l2 = results["L2"]
    l3 = results["L3"]
    l4 = results["L4"]
    l5 = results["L5"]
    l6 = results["L6"]
    l7 = results["L7"]
    l8 = results["L8"]
    l81 = results["L8.1"]
    l9 = results["L9"]

    successful = l2.get(
        "successful_runs",
        0,
    )

    repeatable = (
        successful == len(SEEDS)
    )

    feature_stable = l3.get(
        "all_runs_share_same_features",
        False,
    )

    functional = l9.get(
        "functional_convergence",
        False,
    )

    mechanism = l9.get(
        "mechanism_recovery",
        False,
    )

    return {
        "defensible_result": {
            "repeatable_discovery":
                repeatable,

            "feature_level_stability":
                feature_stable,

            "functional_convergence":
                functional,

            "stable_mechanism_recovery":
                mechanism,
        },

        "evidence_chain": {
            "L1_status":
                l1.get("status"),

            "L2_successful_runs":
                successful,

            "L2_repeatability_rate":
                l2.get(
                    "repeatability_rate",
                    0.0,
                ),

            "L3_feature_stability":
                feature_stable,

            "L3_feature_jaccard":
                l3.get(
                    "mean_feature_jaccard",
                    0.0,
                ),

            "L4_functional_agreement":
                l4.get(
                    "mean_agreement",
                    0.0,
                ),

            "L5_holdout_accuracy":
                l5.get(
                    "mean_accuracy",
                    0.0,
                ),

            "L6_baseline_improvement":
                l6.get(
                    "mean_improvement",
                    0.0,
                ),

            "L7_dominant_features":
                l7.get(
                    "dominant_features",
                    [],
                ),

            "L8_exact_rule_jaccard":
                l8.get(
                    "mean_exact_rule_jaccard",
                    0.0,
                ),

            "L8_feature_jaccard":
                l8.get(
                    "mean_feature_set_jaccard",
                    0.0,
                ),

            "L8_operator_jaccard":
                l8.get(
                    "mean_operator_jaccard",
                    0.0,
                ),

            "L8_threshold_distance":
                l8.get(
                    "mean_threshold_relative_distance",
                    0.0,
                ),

            "L8.1_verdict":
                l81.get(
                    "verdict"
                ),

            "L9_functional_convergence":
                l9.get(
                    "functional_convergence"
                ),

            "L9_mechanism_recovery":
                l9.get(
                    "mechanism_recovery"
                ),
        },

        "claim_boundary": {
            "supported_by_this_batch": [
                "The miner can be tested for repeated discovery across independent seeds.",
                "Feature-level structural agreement is measured separately from exact threshold-string agreement.",
                "Functional agreement is measured independently from structural agreement.",
                "Holdout performance is measured on a separate generated fixture.",
                "Baseline comparison is measured separately from holdout performance.",
                "Continuous threshold variation is quantified explicitly.",
            ],

            "not_established_by_this_batch_alone": [
                "External scientific novelty.",
                "Causal discovery.",
                "Universal generalization.",
                "Independent external validation.",
                "Automatic trading performance.",
            ],
        },

        "no_goalpost_change":
            True,

        "levels_executed": [
            "L1",
            "L2",
            "L3",
            "L4",
            "L5",
            "L6",
            "L7",
            "L8",
            "L8.1",
            "L9",
        ],
    }


# ================================================================
# MARKDOWN REPORT
# ================================================================

def make_markdown(
    results,
):
    synthesis = results[
        "SYNTHESIS"
    ]

    lines = []

    lines.append(
        "# BIRTH_EDGE — L1 → L9 MASTER EVIDENCE"
    )

    lines.append("")

    lines.append(
        "Generated: "
        + results["metadata"]["timestamp"]
    )

    lines.append("")

    lines.append(
        "## Execution Metadata"
    )

    lines.append("")

    lines.append(
        "- Module loaded: "
        f"`{results['metadata']['module_loaded']}`"
    )

    lines.append(
        "- Module: "
        f"`{results['metadata'].get('module')}`"
    )

    lines.append(
        "- Seeds: "
        f"`{SEEDS}`"
    )

    lines.append(
        "- Training rows per seed: "
        f"`{TRAIN_N}`"
    )

    lines.append(
        "- Holdout rows: "
        f"`{HOLDOUT_N}`"
    )

    lines.append("")

    lines.append(
        "## L1 — Discovery"
    )

    lines.append(
        f"- Status: `{results['L1'].get('status')}`"
    )

    lines.append(
        f"- Rules discovered: "
        f"`{results['L1'].get('rule_count', 0)}`"
    )

    lines.append(
        f"- Features: "
        f"`{results['L1'].get('feature_set', [])}`"
    )

    lines.append("")

    lines.append(
        "## L2 — Repeatability"
    )

    lines.append(
        f"- Successful runs: "
        f"`{results['L2'].get('successful_runs', 0)}`/"
        f"`{len(SEEDS)}`"
    )

    lines.append(
        f"- Repeatability rate: "
        f"`{results['L2'].get('repeatability_rate', 0.0):.6f}`"
    )

    lines.append("")

    lines.append(
        "## L3 — Feature Stability"
    )

    lines.append(
        f"- Mean feature Jaccard: "
        f"`{results['L3'].get('mean_feature_jaccard', 0.0):.6f}`"
    )

    lines.append(
        f"- Minimum feature Jaccard: "
        f"`{results['L3'].get('minimum_feature_jaccard', 0.0):.6f}`"
    )

    lines.append(
        f"- Stable intersection: "
        f"`{results['L3'].get('stable_intersection', [])}`"
    )

    lines.append(
        f"- All successful runs share same features: "
        f"`{results['L3'].get('all_runs_share_same_features', False)}`"
    )

    lines.append("")

    lines.append(
        "## L4 — Functional Agreement"
    )

    lines.append(
        f"- Models: "
        f"`{results['L4'].get('models', 0)}`"
    )

    lines.append(
        f"- Mean agreement: "
        f"`{results['L4'].get('mean_agreement', 0.0):.6f}`"
    )

    lines.append(
        f"- Minimum agreement: "
        f"`{results['L4'].get('minimum_agreement', 0.0):.6f}`"
    )

    lines.append("")

    lines.append(
        "## L5 — Holdout"
    )

    lines.append(
        f"- n: "
        f"`{results['L5'].get('n', 0)}`"
    )

    lines.append(
        f"- Mean accuracy: "
        f"`{results['L5'].get('mean_accuracy', 0.0):.6f}`"
    )

    lines.append(
        f"- Accuracy stdev: "
        f"`{results['L5'].get('stdev_accuracy', 0.0):.6f}`"
    )

    lines.append(
        f"- Mean F1: "
        f"`{results['L5'].get('mean_f1', 0.0):.6f}`"
    )

    lines.append("")

    lines.append(
        "## L6 — Baseline / Generalization"
    )

    lines.append(
        f"- n: "
        f"`{results['L6'].get('n', 0)}`"
    )

    lines.append(
        f"- Holder baseline accuracy: "
        f"`{results['L6'].get('baseline', {}).get('accuracy', 0.0):.6f}`"
    )

    lines.append(
        f"- Majority baseline accuracy: "
        f"`{results['L6'].get('majority_baseline', {}).get('accuracy', 0.0):.6f}`"
    )

    lines.append(
        f"- Mean improvement over holder baseline: "
        f"`{results['L6'].get('mean_improvement', 0.0):+.6f}`"
    )

    lines.append("")

    lines.append(
        "## L7 — Cross-Seed Structure"
    )

    lines.append(
        f"- Dominant features: "
        f"`{results['L7'].get('dominant_features', [])}`"
    )

    lines.append(
        "- Self-assigned novelty is not treated as independent evidence."
    )

    lines.append("")

    lines.append(
        "## L8 — Structural Identifiability"
    )

    lines.append(
        f"- Exact-rule Jaccard: "
        f"`{results['L8'].get('mean_exact_rule_jaccard', 0.0):.6f}`"
    )

    lines.append(
        f"- Feature-set Jaccard: "
        f"`{results['L8'].get('mean_feature_set_jaccard', 0.0):.6f}`"
    )

    lines.append(
        f"- Operator Jaccard: "
        f"`{results['L8'].get('mean_operator_jaccard', 0.0):.6f}`"
    )

    lines.append(
        f"- Threshold relative distance: "
        f"`{results['L8'].get('mean_threshold_relative_distance', 0.0):.6f}`"
    )

    lines.append("")

    lines.append(
        "Exact-rule Jaccard is threshold-sensitive. "
        "Feature-set Jaccard is reported independently so "
        "continuous threshold variation cannot be mistaken "
        "for complete feature disagreement."
    )

    lines.append("")

    lines.append(
        "## L8.1 — Identifiability Investigation"
    )

    checks = results[
        "L8.1"
    ].get(
        "checks",
        {},
    )

    for name, value in checks.items():
        lines.append(
            f"- {name}: `{value}`"
        )

    lines.append(
        f"- Verdict: "
        f"`{results['L8.1'].get('verdict')}`"
    )

    lines.append("")

    lines.append(
        "## L9 — Functional Convergence / Mechanism Recovery"
    )

    lines.append(
        f"- Functional convergence: "
        f"`{results['L9'].get('functional_convergence')}`"
    )

    lines.append(
        f"- Mechanism recovery: "
        f"`{results['L9'].get('mechanism_recovery')}`"
    )

    lines.append(
        f"- Verdict: "
        f"`{results['L9'].get('verdict')}`"
    )

    lines.append("")

    lines.append(
        "## Consolidated Result"
    )

    lines.append("")

    for key, value in synthesis[
        "defensible_result"
    ].items():
        lines.append(
            f"- {key}: `{value}`"
        )

    lines.append("")

    lines.append(
        "## Evidence Chain"
    )

    lines.append("")

    for key, value in synthesis[
        "evidence_chain"
    ].items():
        lines.append(
            f"- {key}: `{value}`"
        )

    lines.append("")

    lines.append(
        "## Supported By This Batch"
    )

    lines.append("")

    for item in synthesis[
        "claim_boundary"
    ]["supported_by_this_batch"]:
        lines.append(
            f"- {item}"
        )

    lines.append("")

    lines.append(
        "## Not Established By This Batch Alone"
    )

    lines.append("")

    for item in synthesis[
        "claim_boundary"
    ]["not_established_by_this_batch"]:
        lines.append(
            f"- {item}"
        )

    lines.append("")

    lines.append(
        "**All L1–L9 levels are retained in one continuous evidence chain.**"
    )

    lines.append("")

    return "\n".join(
        lines
    )


# ================================================================
# CONSOLE SUMMARY
# ================================================================

def print_summary(
    results,
):
    print(
        "=" * 72
    )

    print(
        "BIRTH_EDGE — L1 → L9 MASTER EVIDENCE"
    )

    print(
        "=" * 72
    )

    for level in (
        "L1",
        "L2",
        "L3",
        "L4",
        "L5",
        "L6",
        "L7",
        "L8",
        "L8.1",
        "L9",
    ):
        item = results[level]

        if level == "L1":
            verdict = item.get(
                "status"
            )

        elif level == "L2":
            verdict = (
                f"{item.get('successful_runs', 0)}/"
                f"{len(SEEDS)} successful"
            )

        elif level == "L3":
            verdict = (
                "featureJ="
                f"{item.get('mean_feature_jaccard', 0.0):.4f}"
            )

        elif level == "L4":
            verdict = (
                "functional_agreement="
                f"{item.get('mean_agreement', 0.0):.4f}"
            )

        elif level == "L5":
            verdict = (
                "holdout_accuracy="
                f"{item.get('mean_accuracy', 0.0):.4f}"
            )

        elif level == "L6":
            verdict = (
                "baseline_delta="
                f"{item.get('mean_improvement', 0.0):+.4f}"
            )

        elif level == "L7":
            verdict = (
                "dominant="
                f"{item.get('dominant_features', [])}"
            )

        elif level == "L8":
            verdict = (
                "exactJ="
                f"{item.get('mean_exact_rule_jaccard', 0.0):.4f} "
                "featureJ="
                f"{item.get('mean_feature_set_jaccard', 0.0):.4f} "
                "operatorJ="
                f"{item.get('mean_operator_jaccard', 0.0):.4f} "
                "thresholdD="
                f"{item.get('mean_threshold_relative_distance', 0.0):.4f}"
            )

        else:
            verdict = item.get(
                "verdict"
            )

        print(
            f"{level:>4} | {verdict}"
        )

    print(
        "=" * 72
    )

    print(
        "JSON:",
        MASTER_JSON,
    )

    print(
        "REPORT:",
        MASTER_MD,
    )

    print(
        "HASH:",
        results["metadata"].get(
            "master_hash"
        ),
    )

    print(
        "=" * 72
    )


# ================================================================
# MAIN
# ================================================================

def main():
    started = time.time()

    module, module_errors = (
        load_existing_module()
    )

    results = {
        "metadata": {
            "name":
                "BIRTH_EDGE_L1_L9_MASTER_EVIDENCE",

            "timestamp":
                now(),

            "root":
                ROOT,

            "python":
                sys.version,

            "module_loaded":
                module is not None,

            "module":
                (
                    module.__name__
                    if module is not None
                    else None
                ),

            "module_load_errors":
                module_errors,

            "seeds":
                SEEDS,

            "train_n":
                TRAIN_N,

            "holdout_n":
                HOLDOUT_N,

            "l6_n":
                L6_N,

            "true_rule_fixture":
                TRUE_RULE,
        }
    }

    try:
        # --------------------------------------------------------
        # L1
        # --------------------------------------------------------

        results["L1"] = level_l1(
            module
        )

        # --------------------------------------------------------
        # L2
        # --------------------------------------------------------

        results["L2"] = level_l2(
            module
        )

        # --------------------------------------------------------
        # L3
        # --------------------------------------------------------

        results["L3"] = level_l3(
            results["L2"]
        )

        # --------------------------------------------------------
        # L4
        # --------------------------------------------------------

        results["L4"] = level_l4(
            results["L2"]
        )

        # --------------------------------------------------------
        # L5
        # --------------------------------------------------------

        results["L5"] = level_l5(
            results["L2"]
        )

        # --------------------------------------------------------
        # L6
        # --------------------------------------------------------

        results["L6"] = level_l6(
            results["L2"]
        )

        # --------------------------------------------------------
        # L7
        # --------------------------------------------------------

        results["L7"] = level_l7(
            results["L2"]
        )

        # --------------------------------------------------------
        # L8
        # --------------------------------------------------------

        results["L8"] = level_l8(
            results["L2"]
        )

        # --------------------------------------------------------
        # L8.1
        # --------------------------------------------------------

        results["L8.1"] = level_l81(
            results["L8"],
            results["L4"],
        )

        # --------------------------------------------------------
        # L9
        # --------------------------------------------------------

        results["L9"] = level_l9(
            results["L4"],
            results["L8"],
        )

        # --------------------------------------------------------
        # SYNTHESIS
        # --------------------------------------------------------

        results["SYNTHESIS"] = synthesize(
            results
        )

        # --------------------------------------------------------
        # METADATA
        # --------------------------------------------------------

        results["metadata"][
            "elapsed_seconds"
        ] = (
            time.time()
            - started
        )

        # Hash a copy before adding the hash itself.
        hash_input = dict(
            results
        )

        hash_metadata = dict(
            hash_input["metadata"]
        )

        hash_metadata.pop(
            "master_hash",
            None,
        )

        hash_input[
            "metadata"
        ] = hash_metadata

        results["metadata"][
            "master_hash"
        ] = sha256_obj(
            hash_input
        )

        # --------------------------------------------------------
        # WRITE JSON
        # --------------------------------------------------------

        dump_json(
            MASTER_JSON,
            results,
        )

        # --------------------------------------------------------
        # WRITE MARKDOWN
        # --------------------------------------------------------

        with open(
            MASTER_MD,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(
                make_markdown(
                    results
                )
            )

        # --------------------------------------------------------
        # CONSOLE
        # --------------------------------------------------------

        print_summary(
            results
        )

    except Exception as exc:
        failure = {
            "status":
                "FAILED",

            "timestamp":
                now(),

            "error":
                repr(exc),

            "traceback":
                traceback.format_exc(),

            "partial_results":
                results,
        }

        dump_json(
            MASTER_JSON,
            failure,
        )

        print(
            traceback.format_exc(),
            file=sys.stderr,
        )

        raise


if __name__ == "__main__":
    main()
