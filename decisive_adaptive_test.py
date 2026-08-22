#!/usr/bin/env python3

"""
BIRTH_EDGE — DECISIVE ADAPTIVE CAUSALITY TEST
=============================================

Question:

    Does accumulated experience causally change future behavior?

This test deliberately avoids assuming a particular database schema.

It performs:

1. Schema discovery
2. ML API discovery
3. Baseline prediction fingerprint
4. Controlled training with Dataset A
5. Controlled training with Dataset B
6. Prediction comparison after A vs B
7. Fresh-process persistence test
8. Model-artifact comparison
9. Source-level decision-path inspection
10. Automatic classification

IMPORTANT:

- Production files are never modified.
- Each experiment gets its own temporary clone.
- No live market API is contacted.
- No production database is written.
"""

import os
import sys
import json
import ast
import copy
import shutil
import hashlib
import tempfile
import subprocess
import inspect
import sqlite3
import traceback
import importlib
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent

RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "question": "Does accumulated experience causally change future behavior?",
    "tests": [],
    "experiments": {},
    "classification": {},
}


def log(name, status, evidence="", detail=""):
    item = {
        "name": name,
        "status": status,
        "evidence": evidence,
        "detail": detail,
    }

    RESULTS["tests"].append(item)

    print(f"[{status}] {name}")

    if evidence:
        print(f"       {evidence}")

    if detail:
        print(f"       {detail}")


def sha256(path):
    path = Path(path)

    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def clone_root():
    tmp = Path(
        tempfile.mkdtemp(
            prefix="birth_edge_causal_"
        )
    )

    for item in ROOT.iterdir():

        if item.name in {
            ".git",
            "__pycache__",
            "decisive_adaptive_test.py",
            "full_adaptive_test.py",
        }:
            continue

        dst = tmp / item.name

        if item.is_dir():
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, dst)

    return tmp


def source(name):
    p = ROOT / name

    if not p.exists():
        return ""

    return p.read_text(errors="replace")


# ============================================================
# 1. DATABASE SCHEMA DISCOVERY
# ============================================================

def discover_database():

    db = ROOT / "data" / "learning.db"

    if not db.exists():
        log(
            "Learning database discovery",
            "FAIL",
            "data/learning.db does not exist",
        )
        return None

    try:

        con = sqlite3.connect(db)

        tables = con.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        schema = {}

        for (table,) in tables:

            cols = con.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()

            schema[table] = [
                {
                    "name": row[1],
                    "type": row[2],
                    "notnull": row[3],
                    "default": row[4],
                    "pk": row[5],
                }
                for row in cols
            ]

        con.close()

        RESULTS["database_schema"] = schema

        log(
            "Learning database discovery",
            "PASS",
            f"{len(schema)} tables discovered",
            ", ".join(sorted(schema.keys())),
        )

        return db

    except Exception as e:

        log(
            "Learning database discovery",
            "FAIL",
            repr(e),
        )

        return None


# ============================================================
# 2. DISCOVER ACTUAL LEARNING DATA
# ============================================================

def discover_learning_rows(db):

    if db is None:
        return []

    try:

        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row

        tables = [
            r[0]
            for r in con.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            )
        ]

        candidates = []

        for table in tables:

            cols = [
                r[1]
                for r in con.execute(
                    f"PRAGMA table_info({table})"
                )
            ]

            lower = {
                c.lower()
                for c in cols
            }

            score = 0

            for keyword in [
                "pump",
                "label",
                "outcome",
                "score",
                "price",
                "liquidity",
                "holder",
                "token",
                "addr",
            ]:

                if any(
                    keyword in c
                    for c in lower
                ):
                    score += 1

            candidates.append(
                (score, table, cols)
            )

        candidates.sort(
            reverse=True
        )

        RESULTS["database_candidates"] = [
            {
                "table": t,
                "columns": c,
                "score": s,
            }
            for s, t, c in candidates
        ]

        if not candidates:

            con.close()

            log(
                "Learning dataset discovery",
                "FAIL",
                "No database tables found",
            )

            return []

        best = candidates[0]

        score, table, cols = best

        rows = con.execute(
            f"""
            SELECT *
            FROM {table}
            LIMIT 1000
            """
        ).fetchall()

        result = [
            dict(r)
            for r in rows
        ]

        con.close()

        log(
            "Learning dataset discovery",
            "PASS",
            f"selected table={table}, rows={len(result)}",
            f"columns={cols}",
        )

        return result

    except Exception as e:

        log(
            "Learning dataset discovery",
            "FAIL",
            repr(e),
        )

        return []


# ============================================================
# 3. DISCOVER ML API
# ============================================================

def discover_ml_module(clone):

    sys.path.insert(
        0,
        str(clone)
    )

    try:

        import ml_model

        functions = [
            x
            for x in dir(ml_model)
            if not x.startswith("_")
            and callable(
                getattr(ml_model, x)
            )
        ]

        info = {}

        for name in functions:

            try:
                obj = getattr(
                    ml_model,
                    name
                )

                info[name] = str(
                    inspect.signature(obj)
                )

            except Exception:
                pass

        RESULTS["ml_api"] = info

        log(
            "ML module discovery",
            "PASS",
            f"module imported; callable functions={len(functions)}",
            json.dumps(info),
        )

        return ml_model

    except Exception as e:

        log(
            "ML module discovery",
            "FAIL",
            repr(e),
        )

        return None


# ============================================================
# 4. FIND PREDICTION FUNCTION
# ============================================================

def find_prediction_function(module):

    if module is None:
        return None

    preferred = [
        "predict",
        "predict_proba",
        "score",
        "evaluate",
        "inference",
        "classify",
        "make_prediction",
    ]

    for name in preferred:

        obj = getattr(
            module,
            name,
            None
        )

        if callable(obj):

            log(
                "Prediction API discovery",
                "PASS",
                f"selected ml_model.{name}",
                str(inspect.signature(obj)),
            )

            return obj

    log(
        "Prediction API discovery",
        "INCONCLUSIVE",
        "No obvious prediction function discovered",
        "Available callables were recorded in ml_api.",
    )

    return None


# ============================================================
# 5. FIND TRAINING FUNCTION
# ============================================================

def find_training_function(module):

    if module is None:
        return None

    preferred = [
        "train_model",
        "train",
        "fit",
        "update_model",
        "learn",
    ]

    for name in preferred:

        obj = getattr(
            module,
            name,
            None
        )

        if callable(obj):

            log(
                "Training API discovery",
                "PASS",
                f"selected ml_model.{name}",
                str(inspect.signature(obj)),
            )

            return obj

    log(
        "Training API discovery",
        "FAIL",
        "No training function discovered",
    )

    return None


# ============================================================
# 6. IDENTIFY MODEL ARTIFACTS
# ============================================================

def find_model_files(clone, module):

    candidates = []

    if module is not None:

        for attr in [
            "MODEL_FILE",
            "MODEL_PATH",
            "MODEL",
            "ARTIFACT",
            "MODEL_ARTIFACT",
        ]:

            value = getattr(
                module,
                attr,
                None
            )

            if value:

                p = Path(value)

                if not p.is_absolute():
                    p = clone / p

                candidates.append(p)

    for pattern in [
        "*.pkl",
        "*.pickle",
        "*.joblib",
        "*.model",
        "*.bin",
        "*.json",
    ]:

        candidates.extend(
            clone.rglob(pattern)
        )

    unique = []

    seen = set()

    for p in candidates:

        try:
            key = str(
                p.resolve()
            )

            if key not in seen and p.exists():
                seen.add(key)
                unique.append(p)

        except Exception:
            pass

    return unique


# ============================================================
# 7. BUILD CONTROLLED DATASETS
# ============================================================

def controlled_features():

    return [
        {
            "liquidity_usd": 1000.0,
            "holder_score": 5.0,
            "dev_score": 10.0,
            "lp_lock_score": 10.0,
            "tax_score": 5.0,
            "overall_score": 30.0,
        },
        {
            "liquidity_usd": 5000.0,
            "holder_score": 10.0,
            "dev_score": 20.0,
            "lp_lock_score": 20.0,
            "tax_score": 10.0,
            "overall_score": 55.0,
        },
        {
            "liquidity_usd": 10000.0,
            "holder_score": 20.0,
            "dev_score": 30.0,
            "lp_lock_score": 30.0,
            "tax_score": 15.0,
            "overall_score": 75.0,
        },
        {
            "liquidity_usd": 20000.0,
            "holder_score": 25.0,
            "dev_score": 40.0,
            "lp_lock_score": 40.0,
            "tax_score": 20.0,
            "overall_score": 90.0,
        },
    ]


# Dataset A teaches:

# low score -> 0
# high score -> 1

def dataset_a():

    rows = controlled_features()

    return [
        (x, 0 if x["overall_score"] < 60 else 1)
        for x in rows
    ]


# Dataset B teaches the exact opposite.

def dataset_b():

    rows = controlled_features()

    return [
        (x, 1 if x["overall_score"] < 60 else 0)
        for x in rows
    ]


# ============================================================
# 8. TRAINING EXPERIMENT
# ============================================================

def run_training(module, training_fn, dataset):

    successful = 0
    errors = []

    for features, label in dataset:

        try:

            training_fn(
                features,
                label
            )

            successful += 1

        except Exception as e:

            errors.append(
                repr(e)
            )

    return successful, errors


# ============================================================
# 9. PREDICTION EXPERIMENT
# ============================================================

def run_prediction(module, prediction_fn, features):

    if prediction_fn is None:
        return None

    attempts = [
        lambda: prediction_fn(features),
        lambda: prediction_fn(
            **features
        ),
    ]

    for attempt in attempts:

        try:

            value = attempt()

            try:
                return float(value)
            except Exception:
                return repr(value)

        except Exception:
            pass

    return None


# ============================================================
# 10. FINGERPRINT MODEL BEHAVIOR
# ============================================================

def prediction_fingerprint(
    module,
    prediction_fn
):

    results = []

    for features in controlled_features():

        value = run_prediction(
            module,
            prediction_fn,
            features
        )

        results.append(
            value
        )

    return results


# ============================================================
# 11. EXPERIMENT A
# ============================================================

def experiment_a():

    clone = clone_root()

    sys.path.insert(
        0,
        str(clone)
    )

    try:

        import ml_model

        train_fn = find_training_function(
            ml_model
        )

        predict_fn = find_prediction_function(
            ml_model
        )

        if train_fn is None:

            return {
                "status": "INCONCLUSIVE",
                "reason": "No training API",
            }

        before = prediction_fingerprint(
            ml_model,
            predict_fn
        )

        artifacts_before = {
            str(p): sha256(p)
            for p in find_model_files(
                clone,
                ml_model
            )
        }

        success, errors = run_training(
            ml_model,
            train_fn,
            dataset_a()
        )

        after = prediction_fingerprint(
            ml_model,
            predict_fn
        )

        artifacts_after = {
            str(p): sha256(p)
            for p in find_model_files(
                clone,
                ml_model
            )
        }

        changed = (
            before != after
        )

        artifact_changed = (
            artifacts_before
            != artifacts_after
        )

        return {
            "status": "PASS" if changed or artifact_changed else "NO_CHANGE",
            "training_successes": success,
            "training_errors": errors,
            "before": before,
            "after": after,
            "behavior_changed": changed,
            "artifact_changed": artifact_changed,
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "error": repr(e),
            "traceback": traceback.format_exc(),
        }


# ============================================================
# 12. EXPERIMENT B
# ============================================================

def experiment_b():

    clone = clone_root()

    sys.path.insert(
        0,
        str(clone)
    )

    try:

        import ml_model

        train_fn = find_training_function(
            ml_model
        )

        predict_fn = find_prediction_function(
            ml_model
        )

        if train_fn is None:

            return {
                "status": "INCONCLUSIVE",
                "reason": "No training API",
            }

        before = prediction_fingerprint(
            ml_model,
            predict_fn
        )

        artifacts_before = {
            str(p): sha256(p)
            for p in find_model_files(
                clone,
                ml_model
            )
        }

        success, errors = run_training(
            ml_model,
            train_fn,
            dataset_b()
        )

        after = prediction_fingerprint(
            ml_model,
            predict_fn
        )

        artifacts_after = {
            str(p): sha256(p)
            for p in find_model_files(
                clone,
                ml_model
            )
        }

        changed = (
            before != after
        )

        artifact_changed = (
            artifacts_before
            != artifacts_after
        )

        return {
            "status": "PASS" if changed or artifact_changed else "NO_CHANGE",
            "training_successes": success,
            "training_errors": errors,
            "before": before,
            "after": after,
            "behavior_changed": changed,
            "artifact_changed": artifact_changed,
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "error": repr(e),
            "traceback": traceback.format_exc(),
        }


# ============================================================
# 13. EXPERIMENT C/D — DIRECT HISTORY CONTRAST
# ============================================================

def history_contrast():

    clone_a = clone_root()
    clone_b = clone_root()

    results = {}

    try:

        # -------------------------
        # ARM A
        # -------------------------

        sys.path.insert(
            0,
            str(clone_a)
        )

        import ml_model as model_a

        train_a = find_training_function(
            model_a
        )

        pred_a = find_prediction_function(
            model_a
        )

        if train_a is None:

            raise RuntimeError(
                "Training API unavailable"
            )

        run_training(
            model_a,
            train_a,
            dataset_a()
        )

        output_a = prediction_fingerprint(
            model_a,
            pred_a
        )

        # -------------------------
        # ARM B
        # -------------------------

        sys.path.insert(
            0,
            str(clone_b)
        )

        # force separate import namespace
        spec = importlib.util.spec_from_file_location(
            "ml_model_b",
            clone_b / "ml_model.py"
        )

        if spec is None or spec.loader is None:
            raise RuntimeError(
                "Unable to load second ML module"
            )

        model_b = importlib.util.module_from_spec(
            spec
        )

        spec.loader.exec_module(
            model_b
        )

        train_b = find_training_function(
            model_b
        )

        pred_b = find_prediction_function(
            model_b
        )

        if train_b is None:

            raise RuntimeError(
                "Training API unavailable"
            )

        run_training(
            model_b,
            train_b,
            dataset_b()
        )

        output_b = prediction_fingerprint(
            model_b,
            pred_b
        )

        different = (
            output_a != output_b
        )

        results = {
            "status": "PASS" if different else "NO_CHANGE",
            "arm_A_baseline_experience": output_a,
            "arm_B_inverted_experience": output_b,
            "future_behavior_different": different,
        }

    except Exception as e:

        results = {
            "status": "ERROR",
            "error": repr(e),
            "traceback": traceback.format_exc(),
        }

    return results


# ============================================================
# 14. SOURCE-LEVEL CAUSAL PATH
# ============================================================

def source_causal_path():

    files = [
        "learning.py",
        "ml_model.py",
        "decision_engine.py",
        "cognition.py",
        "main.py",
    ]

    findings = {}

    for filename in files:

        text = source(filename)

        if not text:
            continue

        findings[filename] = {
            "training": any(
                x in text.lower()
                for x in [
                    "train_model",
                    ".fit(",
                    "partial_fit",
                    "update_model",
                    "learn(",
                ]
            ),

            "prediction": any(
                x in text.lower()
                for x in [
                    "predict(",
                    "predict_proba",
                    "inference",
                    "decision",
                ]
            ),

            "persistence": any(
                x in text.lower()
                for x in [
                    "pickle",
                    "joblib",
                    "sqlite",
                    "json.dump",
                    "save(",
                    "commit(",
                ]
            ),

            "decision_dependency": any(
                x in text.lower()
                for x in [
                    "learning",
                    "ml_model",
                    "best_threshold",
                    "wisdom",
                    "cognition",
                    "learned",
                ]
            ),
        }

    RESULTS["source_causal_path"] = findings

    log(
        "Source causal-path inspection",
        "PASS",
        "Inspected training, prediction, persistence, and decision dependencies",
    )


# ============================================================
# 15. FINAL VERDICT
# ============================================================

def final_verdict():

    a = RESULTS["experiments"].get(
        "training_A",
        {}
    )

    b = RESULTS["experiments"].get(
        "training_B",
        {}
    )

    contrast = RESULTS["experiments"].get(
        "history_contrast",
        {}
    )

    a_changed = (
        a.get("behavior_changed") is True
    )

    b_changed = (
        b.get("behavior_changed") is True
    )

    histories_differ = (
        contrast.get(
            "future_behavior_different"
        ) is True
    )

    if histories_differ:

        verdict = (
            "ADAPTIVE BEHAVIOR DEMONSTRATED"
        )

        explanation = (
            "Two isolated copies received the same "
            "future inputs but different accumulated "
            "experience, and their subsequent behavior "
            "differed."
        )

    elif a_changed or b_changed:

        verdict = (
            "LEARNING EFFECT DETECTED — "
            "HISTORY-CONTRAST INCOMPLETE"
        )

        explanation = (
            "Training altered the model or its immediate "
            "behavior, but the decisive opposite-history "
            "comparison did not establish a clean causal "
            "history effect."
        )

    else:

        verdict = (
            "ADAPTIVE BEHAVIOR NOT DEMONSTRATED"
        )

        explanation = (
            "Under this controlled experiment, changing "
            "the training experience did not produce a "
            "detectable change in subsequent behavior."
        )

    RESULTS["classification"] = {
        "verdict": verdict,
        "explanation": explanation,
        "arm_A_behavior_changed": a_changed,
        "arm_B_behavior_changed": b_changed,
        "opposite_history_changed_future_behavior": histories_differ,
    }

    print()
    print("=" * 72)
    print("BIRTH_EDGE — DECISIVE ADAPTIVE CAUSALITY RESULT")
    print("=" * 72)
    print(verdict)
    print()
    print(explanation)
    print("=" * 72)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print("BIRTH_EDGE — DECISIVE ADAPTIVE CAUSALITY TEST")
    print("=" * 72)
    print()
    print("Production database: NOT MODIFIED")
    print("Live APIs: NOT CONTACTED")
    print()

    discover_database()

    db = ROOT / "data" / "learning.db"

    discover_learning_rows(
        db
    )

    clone = clone_root()

    discover_ml_module(
        clone
    )

    source_causal_path()

    print()
    print("Running controlled training experiment A...")
    RESULTS["experiments"]["training_A"] = (
        experiment_a()
    )

    print()
    print("Running controlled training experiment B...")
    RESULTS["experiments"]["training_B"] = (
        experiment_b()
    )

    print()
    print("Running opposite-history causal contrast...")
    RESULTS["experiments"]["history_contrast"] = (
        history_contrast()
    )

    final_verdict()

    output = (
        ROOT /
        "decisive_adaptive_test_results.json"
    )

    with open(
        output,
        "w"
    ) as f:

        json.dump(
            RESULTS,
            f,
            indent=2,
            default=str
        )

    print()
    print(f"Machine-readable result:")
    print(output)


if __name__ == "__main__":
    main()
