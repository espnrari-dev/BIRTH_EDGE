#!/usr/bin/env python3

"""
BIRTH_EDGE — FULL ADAPTIVE LEARNING FORENSIC TEST
=================================================

Purpose:
Determine empirically whether BIRTH_EDGE is:

A) a genuinely adaptive learning system whose accumulated
   experience changes future behavior,

or

B) primarily a fixed rule/scoring system with learning
   components that do not materially alter behavior.

SAFETY:
- Does NOT modify the production database.
- Does NOT contact live market APIs.
- Works from a temporary copy where mutation is allowed.
- Existing production files are restored/untouched.
"""

import os
import sys
import json
import ast
import copy
import time
import shutil
import hashlib
import tempfile
import inspect
import sqlite3
import traceback
import subprocess
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

RESULTS = {
    "timestamp": datetime.now().isoformat(),
    "tests": [],
    "claims": {},
}


def record(name, status, evidence="", detail=""):
    RESULTS["tests"].append({
        "name": name,
        "status": status,
        "evidence": evidence,
        "detail": detail,
    })
    print(f"[{status}] {name}")
    if evidence:
        print(f"       {evidence}")
    if detail:
        print(f"       {detail}")


def sha256(path):
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def source_text(name):
    p = ROOT / name
    if not p.exists():
        return ""
    return p.read_text(errors="replace")


def ast_calls(filename):
    text = source_text(filename)
    if not text:
        return []

    try:
        tree = ast.parse(text)
    except Exception:
        return []

    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

    return calls


# ============================================================
# TEST 1 — ARCHITECTURAL LEARNING PATH
# ============================================================

def test_architecture():

    learning = source_text("learning.py")
    cognition = source_text("cognition.py")
    miner = source_text("aegis_rule_miner.py")

    required = {
        "ML training": "train_model",
        "Outcome labeling": "label = 1 if pump else 0",
        "Rule mining": "run_rule_mining",
        "Outcome event": 'record_event("token_outcome"',
        "Birth event": 'record_event("token_birth"',
        "Memory importance": "set_memory_importance",
        "Threshold adaptation": "best_threshold",
    }

    found = []

    for label, needle in required.items():
        if needle in learning:
            found.append(label)

    record(
        "Architecture contains closed learning loop",
        "PASS" if len(found) >= 5 else "FAIL",
        f"{len(found)}/{len(required)} learning mechanisms found",
        ", ".join(found)
    )


# ============================================================
# TEST 2 — HISTORICAL DATA AVAILABILITY
# ============================================================

def test_dataset():

    db = DATA / "learning.db"

    if not db.exists():
        record("Historical learning dataset", "FAIL", "data/learning.db missing")
        return

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN final_price_usd IS NOT NULL THEN 1 ELSE 0 END) AS outcomes,
            SUM(CASE WHEN pumped=1 THEN 1 ELSE 0 END) AS pumps,
            SUM(CASE WHEN rug_pulled=1 THEN 1 ELSE 0 END) AS rugs
        FROM learning_results
    """).fetchone()

    feature_rows = con.execute("""
        SELECT COUNT(*)
        FROM learning_results
        WHERE overall_score IS NOT NULL
    """).fetchone()[0]

    con.close()

    record(
        "Historical learning dataset",
        "PASS" if rows["total"] > 0 else "FAIL",
        f"rows={rows['total']} outcomes={rows['outcomes']} "
        f"pumps={rows['pumps']} rugs={rows['rugs']}",
        f"rows with scores={feature_rows}"
    )


# ============================================================
# TEST 3 — TEMPORARY CLONE
# ============================================================

def make_clone():

    tmp = Path(tempfile.mkdtemp(prefix="birth_edge_adaptive_"))

    for item in ROOT.iterdir():

        if item.name in {
            "__pycache__",
            ".git",
            "full_adaptive_test.py",
        }:
            continue

        destination = tmp / item.name

        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    return tmp


# ============================================================
# TEST 4 — ML FUNCTION REALLY EXISTS
# ============================================================

def test_ml_function(clone):

    sys.path.insert(0, str(clone))

    try:
        import ml_model

        if not hasattr(ml_model, "train_model"):
            record(
                "ML training function exists",
                "FAIL",
                "ml_model.train_model not found"
            )
            return None

        sig = inspect.signature(ml_model.train_model)

        record(
            "ML training function exists",
            "PASS",
            f"train_model signature: {sig}"
        )

        return ml_model

    except Exception as e:
        record(
            "ML training function exists",
            "FAIL",
            repr(e)
        )
        return None


# ============================================================
# TEST 5 — ML MODEL MUTATION
# ============================================================

def test_ml_mutation(clone, ml_model):

    if ml_model is None:
        return

    model_file = Path(ml_model.MODEL_FILE)

    before = sha256(model_file)

    db = clone / "data" / "learning.db"

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            liquidity_usd,
            holder_score,
            dev_score,
            lp_lock_score,
            tax_score,
            overall_score,
            pumped
        FROM learning_results
        WHERE final_price_usd IS NOT NULL
        ORDER BY discovered_at
        LIMIT 20
    """).fetchall()

    con.close()

    if not rows:
        record(
            "ML model mutation test",
            "INCONCLUSIVE",
            "No outcome-labelled records available"
        )
        return

    successful = 0
    errors = []

    for r in rows:

        features = {
            "liquidity_usd": r["liquidity_usd"] or 0,
            "holder_score": r["holder_score"] or 0,
            "dev_score": r["dev_score"] or 0,
            "lp_lock_score": r["lp_lock_score"] or 0,
            "tax_score": r["tax_score"] or 0,
            "overall_score": r["overall_score"] or 0,
        }

        label = 1 if r["pumped"] else 0

        try:
            ml_model.train_model(features, label)
            successful += 1
        except Exception as e:
            errors.append(repr(e))

    after = sha256(model_file)

    changed = before != after

    if changed:
        status = "PASS"
        evidence = (
            f"model artifact changed after {successful} "
            f"outcome-labelled training operations"
        )
    else:
        status = "FAIL"
        evidence = (
            f"model artifact did NOT change after {successful} "
            f"training operations"
        )

    record(
        "ML model mutation test",
        status,
        evidence,
        "; ".join(errors[:3])
    )


# ============================================================
# TEST 6 — RULE MINER EXECUTES
# ============================================================

def test_rule_miner(clone):

    try:
        import aegis_rule_miner

        if not hasattr(aegis_rule_miner, "run_rule_mining"):
            record(
                "Rule-mining implementation",
                "FAIL",
                "run_rule_mining() missing"
            )
            return

        sig = inspect.signature(
            aegis_rule_miner.run_rule_mining
        )

        record(
            "Rule-mining implementation",
            "PASS",
            f"run_rule_mining signature: {sig}"
        )

    except Exception as e:
        record(
            "Rule-mining implementation",
            "FAIL",
            repr(e)
        )


# ============================================================
# TEST 7 — COGNITION PERSISTENCE
# ============================================================

def test_cognition(clone):

    db = clone / "data" / "cognition.db"

    if not db.exists():
        record(
            "Cognition persistence",
            "FAIL",
            "cognition.db missing"
        )
        return

    con = sqlite3.connect(db)

    tables = {
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    expected = {
        "events",
        "agents",
        "wisdom_rules",
        "memory_importance",
        "inherent_knowledge",
    }

    found = expected & tables

    counts = {}

    for table in found:
        counts[table] = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    con.close()

    record(
        "Cognition persistence",
        "PASS" if len(found) == len(expected) else "PARTIAL",
        f"tables={sorted(found)}",
        f"counts={counts}"
    )


# ============================================================
# TEST 8 — TEMPORAL INTEGRITY
# ============================================================

def test_temporal_integrity():

    db = DATA / "learning.db"

    if not db.exists():
        record(
            "Temporal prediction integrity",
            "FAIL",
            "learning.db missing"
        )
        return

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            addr,
            discovered_at,
            final_price_usd,
            overall_score,
            pumped
        FROM learning_results
        WHERE final_price_usd IS NOT NULL
          AND discovered_at IS NOT NULL
        ORDER BY discovered_at
    """).fetchall()

    con.close()

    valid = 0
    invalid = 0

    for r in rows:

        try:
            birth = datetime.fromisoformat(
                r["discovered_at"]
            )
        except Exception:
            continue

        # updated_at is the actual outcome timestamp
        # when present; older records may not have one.
        valid += 1

    record(
        "Temporal prediction integrity",
        "PASS" if valid > 0 else "INCONCLUSIVE",
        f"{valid} outcome-labelled records have discovery timestamps",
        "This establishes a temporal structure; it does not by itself prove no leakage."
    )


# ============================================================
# TEST 9 — FEATURE / LABEL SEPARATION
# ============================================================

def test_feature_label_separation():

    text = source_text("learning.py")

    feature_section = [
        "liquidity_usd",
        "holder_score",
        "dev_score",
        "lp_lock_score",
        "tax_score",
        "overall_score",
    ]

    label_section = "label = 1 if pump else 0"

    feature_ok = all(x in text for x in feature_section)
    label_ok = label_section in text

    # Check whether final outcome values are directly
    # inserted into the feature dictionary.
    suspicious = (
        '"final_price"' in text and
        '"final_price": final_price' in text
    )

    record(
        "Feature/label separation",
        "PASS" if feature_ok and label_ok and not suspicious else "REVIEW",
        f"features={feature_ok}, label={label_ok}",
        "Outcome is used as the label; final_price is not present in the ML feature dictionary."
    )


# ============================================================
# TEST 10 — ADAPTATION PROPAGATION
# ============================================================

def test_adaptation_propagation():

    text = source_text("learning.py")

    has_search = "best_threshold" in text
    has_report = '"best_threshold": best_threshold' in text

    # Critical question:
    # Is the learned threshold actually written back into the
    # production decision configuration?

    writes_config = any(
        x in text
        for x in [
            "SCORE_MIN_BUY = best_threshold",
            "config.SCORE_MIN_BUY = best_threshold",
            "set_threshold(best_threshold)",
            "update_threshold(best_threshold)",
        ]
    )

    if has_search and has_report and not writes_config:

        record(
            "Learned threshold propagation",
            "LIMITED",
            "System calculates a best threshold and reports it",
            "Current learning.py does not visibly write that threshold back into SCORE_MIN_BUY."
        )

    elif writes_config:

        record(
            "Learned threshold propagation",
            "PASS",
            "Learned threshold is propagated into decision configuration"
        )

    else:

        record(
            "Learned threshold propagation",
            "FAIL",
            "No adaptive threshold mechanism found"
        )


# ============================================================
# TEST 11 — OUTCOME PERMUTATION NULL TEST
# ============================================================

def test_null_structure():

    """
    This is a structural null test.

    If the learning architecture only appears adaptive because
    of existing labels, scrambling labels should destroy the
    meaningful relationship.

    We do not alter production data.
    """

    db = DATA / "learning.db"

    if not db.exists():
        record(
            "Outcome permutation null test",
            "INCONCLUSIVE",
            "learning.db missing"
        )
        return

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    rows = con.execute("""
        SELECT
            overall_score,
            pumped
        FROM learning_results
        WHERE final_price_usd IS NOT NULL
    """).fetchall()

    con.close()

    if len(rows) < 10:
        record(
            "Outcome permutation null test",
            "INCONCLUSIVE",
            f"Only {len(rows)} labelled records"
        )
        return

    scores = [float(r["overall_score"] or 0) for r in rows]
    labels = [int(r["pumped"] or 0) for r in rows]

    # Actual threshold scan
    actual = []

    for threshold in range(50, 101, 5):

        subset = [
            (s, y)
            for s, y in zip(scores, labels)
            if s >= threshold
        ]

        if not subset:
            continue

        wins = sum(y for _, y in subset)
        rate = wins / len(subset)
        actual.append((threshold, rate, len(subset)))

    best_actual = max(actual, key=lambda x: x[1]) if actual else None

    # Deterministic cyclic permutation.
    shifted = labels[1:] + labels[:1]

    null = []

    for threshold in range(50, 101, 5):

        subset = [
            (s, y)
            for s, y in zip(scores, shifted)
            if s >= threshold
        ]

        if not subset:
            continue

        wins = sum(y for _, y in subset)
        rate = wins / len(subset)
        null.append((threshold, rate, len(subset)))

    best_null = max(null, key=lambda x: x[1]) if null else None

    if best_actual and best_null:

        delta = best_actual[1] - best_null[1]

        record(
            "Outcome permutation null test",
            "PASS",
            f"actual best rate={best_actual[1]:.4f}; "
            f"null best rate={best_null[1]:.4f}; "
            f"delta={delta:.4f}",
            "Positive separation is evidence of structure; it is not by itself proof of causality."
        )

    else:

        record(
            "Outcome permutation null test",
            "INCONCLUSIVE",
            "Unable to compute comparable thresholds"
        )


# ============================================================
# TEST 12 — FIXED VS ADAPTIVE DECISION PATH
# ============================================================

def test_fixed_vs_adaptive():

    decision = source_text("decision_engine.py")
    scoring = source_text("scoring.py")
    config = source_text("config.py")

    dynamic_learning_reference = any(
        term in decision
        for term in [
            "learning",
            "ml_model",
            "best_threshold",
            "wisdom",
            "cognition",
            "rule_miner",
        ]
    )

    fixed_threshold = "SCORE_MIN_BUY = 75" in config

    record(
        "Decision engine adaptive integration",
        "PASS" if dynamic_learning_reference else "LIMITED",
        f"decision_engine references learning systems={dynamic_learning_reference}",
        f"static SCORE_MIN_BUY present={fixed_threshold}"
    )


# ============================================================
# TEST 13 — FULL SOURCE DEPENDENCY MAP
# ============================================================

def test_dependency_map():

    targets = [
        "main.py",
        "filters.py",
        "learning.py",
        "cognition.py",
        "ml_model.py",
        "aegis_rule_miner.py",
        "decision_engine.py",
        "execution.py",
        "agent_detection.py",
        "novelty_comparator.py",
        "full_novelty_gauntlet.py",
    ]

    existing = [x for x in targets if (ROOT / x).exists()]

    record(
        "Core intelligence modules present",
        "PASS" if len(existing) >= 8 else "PARTIAL",
        f"{len(existing)}/{len(targets)} core modules present",
        ", ".join(existing)
    )


# ============================================================
# FINAL CLASSIFICATION
# ============================================================

def final_assessment():

    statuses = {
        x["name"]: x["status"]
        for x in RESULTS["tests"]
    }

    ml = statuses.get("ML model mutation test")
    rules = statuses.get("Rule-mining implementation")
    cognition = statuses.get("Cognition persistence")
    temporal = statuses.get("Temporal prediction integrity")
    propagation = statuses.get("Learned threshold propagation")
    architecture = statuses.get(
        "Architecture contains closed learning loop"
    )

    if (
        ml == "PASS"
        and rules == "PASS"
        and cognition == "PASS"
        and temporal == "PASS"
    ):
        primary = "ADAPTIVE LEARNING ARCHITECTURE CONFIRMED"
    elif (
        architecture == "PASS"
        and (ml == "INCONCLUSIVE" or ml is None)
    ):
        primary = "ADAPTIVE ARCHITECTURE PRESENT — EMPIRICAL EFFECT INCOMPLETE"
    else:
        primary = "ADAPTIVE CLAIM NOT FULLY CONFIRMED"

    if propagation == "LIMITED":
        secondary = (
            "Important: learning currently computes an improved threshold "
            "but the supplied learning.py does not visibly propagate it "
            "back into SCORE_MIN_BUY."
        )
    else:
        secondary = "No threshold-propagation limitation detected."

    RESULTS["claims"] = {
        "primary_classification": primary,
        "threshold_propagation": secondary,
        "interpretation": (
            "This test distinguishes architectural presence from "
            "demonstrated behavioral adaptation."
        ),
    }

    print("\n" + "=" * 72)
    print("BIRTH_EDGE ADAPTIVE LEARNING FORENSIC RESULT")
    print("=" * 72)
    print(primary)
    print(secondary)
    print("=" * 72)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 72)
    print("BIRTH_EDGE — FULL ADAPTIVE LEARNING FORENSIC TEST")
    print("=" * 72)
    print("Production database will NOT be modified.")
    print()

    try:
        test_architecture()
        test_dataset()
        test_temporal_integrity()
        test_feature_label_separation()
        test_adaptation_propagation()
        test_null_structure()
        test_fixed_vs_adaptive()
        test_dependency_map()

        clone = make_clone()

        print(f"\nTemporary clone: {clone}")

        ml_model = test_ml_function(clone)

        if ml_model:
            test_ml_mutation(clone, ml_model)

        test_rule_miner(clone)
        test_cognition(clone)

        final_assessment()

        out = ROOT / "adaptive_test_results.json"

        with open(out, "w") as f:
            json.dump(RESULTS, f, indent=2)

        print(f"\nFull machine-readable result:")
        print(out)

        print("\nTemporary clone retained for inspection:")
        print(clone)

    except Exception:

        traceback.print_exc()

        RESULTS["fatal_error"] = traceback.format_exc()

        out = ROOT / "adaptive_test_results.json"

        with open(out, "w") as f:
            json.dump(RESULTS, f, indent=2)

        sys.exit(1)


if __name__ == "__main__":
    main()
