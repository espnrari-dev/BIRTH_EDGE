#!/usr/bin/env python3

"""
BIRTH_EDGE — DECISIVE ADAPTIVE CAUSALITY TEST V2
================================================

Question:

    Does accumulated experience causally change future behavior?

Experimental design:

    ARM A:
        Train on history H_A.

    ARM B:
        Train on exactly opposite history H_B.

    FUTURE:
        Give both systems exactly the same unseen inputs.

    If:

        behavior(A | H_A) != behavior(B | H_B)

    after identical future inputs, then accumulated
    experience demonstrably affects future behavior.

Important:

    This test distinguishes:

        1. training API existence
        2. model mutation
        3. behavioral adaptation
        4. persistent adaptation
        5. history-dependent behavior

    It does NOT assume a prediction function name.

Safety:

    - Production database is never modified.
    - Production source files are never modified.
    - Every experiment runs in a temporary clone.
    - No live market API is contacted.
    - Training data is synthetic and deliberately controlled.
"""

import os
import sys
import json
import shutil
import hashlib
import tempfile
import subprocess
import traceback
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent
RESULT_FILE = ROOT / "decisive_adaptive_test_v2_results.json"


# ============================================================
# CONTROLLED EXPERIMENT DATA
# ============================================================

def features(score):
    return {
        "liquidity_usd": float(score * 100),
        "holder_score": float(score / 2),
        "dev_score": float(score / 2),
        "lp_lock_score": float(score / 2),
        "tax_score": float(score / 4),
        "overall_score": float(score),
    }


# History A:
# Low scores = 0
# High scores = 1
def history_a():
    return [
        (features(20), 0),
        (features(30), 0),
        (features(40), 0),
        (features(50), 0),
        (features(60), 1),
        (features(70), 1),
        (features(80), 1),
        (features(90), 1),
    ]


# History B:
# EXACT opposite labels
def history_b():
    return [
        (features(20), 1),
        (features(30), 1),
        (features(40), 1),
        (features(50), 1),
        (features(60), 0),
        (features(70), 0),
        (features(80), 0),
        (features(90), 0),
    ]


# These are deliberately held out from training.
def future_inputs():
    return [
        features(25),
        features(35),
        features(45),
        features(55),
        features(65),
        features(75),
        features(85),
    ]


# ============================================================
# UTILITIES
# ============================================================

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
            prefix="birth_edge_causal_v2_"
        )
    )

    excluded = {
        ".git",
        "__pycache__",
        "decisive_adaptive_test.py",
        "decisive_adaptive_test_v2.py",
        "full_adaptive_test.py",
    }

    for item in ROOT.iterdir():

        if item.name in excluded:
            continue

        destination = tmp / item.name

        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)

    return tmp


def model_files(root):
    patterns = [
        "*.pkl",
        "*.pickle",
        "*.joblib",
        "*.model",
        "*.bin",
        "*model*.json",
        "*model*.txt",
    ]

    found = []

    for pattern in patterns:
        found.extend(root.rglob(pattern))

    unique = []
    seen = set()

    for p in found:

        if not p.is_file():
            continue

        key = str(p.resolve())

        if key in seen:
            continue

        seen.add(key)
        unique.append(p)

    return unique


def artifact_fingerprint(root):
    return {
        str(p.relative_to(root)): sha256(p)
        for p in model_files(root)
    }


def discover_prediction_name():
    """
    Discover the actual prediction API from ml_model.py.

    Specifically includes predict_pump_probability,
    which the previous test failed to recognize.
    """

    path = ROOT / "ml_model.py"

    if not path.exists():
        return None

    text = path.read_text(errors="replace")

    candidates = [
        "predict_pump_probability",
        "predict",
        "predict_proba",
        "inference",
        "classify",
        "make_prediction",
        "score",
        "evaluate",
    ]

    for name in candidates:

        if f"def {name}(" in text:
            return name

    return None


# ============================================================
# SUBPROCESS EXPERIMENT
# ============================================================

WORKER = r'''
import sys
import json
import hashlib
from pathlib import Path


ROOT = Path(sys.argv[1])
HISTORY = json.loads(sys.argv[2])
MODE = sys.argv[3]

sys.path.insert(0, str(ROOT))


import ml_model


# ------------------------------------------------------------
# Find training API
# ------------------------------------------------------------

training_names = [
    "train_model",
    "train",
    "fit",
    "update_model",
    "learn",
]

train_fn = None

for name in training_names:

    fn = getattr(
        ml_model,
        name,
        None
    )

    if callable(fn):
        train_fn = fn
        break


if train_fn is None:

    print(json.dumps({
        "status": "FAIL",
        "reason": "No training function found"
    }))

    raise SystemExit(0)


# ------------------------------------------------------------
# Find ACTUAL prediction API
# ------------------------------------------------------------

prediction_names = [
    "predict_pump_probability",
    "predict",
    "predict_proba",
    "inference",
    "classify",
    "make_prediction",
    "score",
    "evaluate",
]

predict_fn = None
prediction_name = None

for name in prediction_names:

    fn = getattr(
        ml_model,
        name,
        None
    )

    if callable(fn):

        predict_fn = fn
        prediction_name = name
        break


if predict_fn is None:

    print(json.dumps({
        "status": "INCONCLUSIVE",
        "reason": "No prediction API found",
        "available": [
            x for x in dir(ml_model)
            if not x.startswith("_")
        ]
    }))

    raise SystemExit(0)


# ------------------------------------------------------------
# Model artifact discovery
# ------------------------------------------------------------

def sha256(path):

    if not path.exists() or not path.is_file():
        return None

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(
            lambda: f.read(65536),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


artifact_candidates = []

for attr in [
    "MODEL_FILE",
    "MODEL_PATH",
    "MODEL",
    "ARTIFACT",
    "MODEL_ARTIFACT",
]:

    value = getattr(
        ml_model,
        attr,
        None
    )

    if value:

        p = Path(value)

        if not p.is_absolute():
            p = ROOT / p

        artifact_candidates.append(p)


for pattern in [
    "*.pkl",
    "*.pickle",
    "*.joblib",
    "*.model",
    "*.bin",
]:

    artifact_candidates.extend(
        ROOT.rglob(pattern)
    )


def artifacts():

    result = {}

    seen = set()

    for p in artifact_candidates:

        try:

            p = p.resolve()

            if not p.exists():
                continue

            key = str(p)

            if key in seen:
                continue

            seen.add(key)

            result[str(p.relative_to(ROOT))] = sha256(p)

        except Exception:
            pass

    return result


# ------------------------------------------------------------
# Prediction wrapper
# ------------------------------------------------------------

def predict(features):

    attempts = [
        lambda: predict_fn(features),
        lambda: predict_fn(**features),
    ]

    errors = []

    for attempt in attempts:

        try:

            value = attempt()

            if isinstance(value, dict):

                for key in [
                    "probability",
                    "pump_probability",
                    "prob",
                    "score",
                    "prediction",
                ]:

                    if key in value:
                        return float(value[key])

            return float(value)

        except Exception as e:

            errors.append(repr(e))

    return {
        "prediction_error": errors
    }


# ------------------------------------------------------------
# Capture baseline
# ------------------------------------------------------------

future = [
    json.loads(x)
    for x in json.loads(
        sys.argv[4]
    )
]


before_predictions = [
    predict(x)
    for x in future
]

before_artifacts = artifacts()


# ------------------------------------------------------------
# TRAIN
# ------------------------------------------------------------

successful = 0
errors = []

for item in HISTORY:

    features, label = item

    try:

        train_fn(
            features,
            int(label)
        )

        successful += 1

    except Exception as e:

        errors.append(
            repr(e)
        )


after_predictions = [
    predict(x)
    for x in future
]

after_artifacts = artifacts()


print(
    json.dumps(
        {
            "status": "PASS",
            "mode": MODE,
            "training_successes": successful,
            "training_errors": errors,
            "prediction_api": prediction_name,
            "before_predictions": before_predictions,
            "after_predictions": after_predictions,
            "before_artifacts": before_artifacts,
            "after_artifacts": after_artifacts,
            "artifact_changed": (
                before_artifacts != after_artifacts
            ),
        }
    )
)
'''


def run_worker(root, history, mode):

    future = future_inputs()

    cmd = [
        sys.executable,
        "-c",
        WORKER,
        str(root),
        json.dumps(history),
        mode,
        json.dumps(future),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    stdout = proc.stdout.strip()

    if not stdout:

        return {
            "status": "ERROR",
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }

    lines = stdout.splitlines()

    # Worker emits JSON as final line.
    for line in reversed(lines):

        try:
            return json.loads(line)

        except Exception:
            continue

    return {
        "status": "ERROR",
        "stdout": stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }


# ============================================================
# MAIN CAUSAL EXPERIMENT
# ============================================================

def main():

    print("=" * 72)
    print("BIRTH_EDGE — DECISIVE ADAPTIVE CAUSALITY TEST V2")
    print("=" * 72)

    print()
    print("Production database: NOT MODIFIED")
    print("Production source:   NOT MODIFIED")
    print("Live APIs:           NOT CONTACTED")
    print()

    prediction_name = discover_prediction_name()

    print(
        "Detected prediction API:",
        prediction_name or "NONE"
    )

    print()

    if prediction_name is None:

        print("=" * 72)
        print("INCONCLUSIVE")
        print("=" * 72)
        print(
            "No prediction function could be discovered."
        )
        return


    # --------------------------------------------------------
    # ARM A
    # --------------------------------------------------------

    print("Creating isolated ARM A...")

    clone_a = clone_root()

    print(
        "ARM A:",
        clone_a
    )

    result_a = run_worker(
        clone_a,
        history_a(),
        "HISTORY_A"
    )

    print()
    print("ARM A RESULT")
    print("-" * 72)

    print(
        json.dumps(
            result_a,
            indent=2
        )
    )


    # --------------------------------------------------------
    # ARM B
    # --------------------------------------------------------

    print()
    print("Creating isolated ARM B...")

    clone_b = clone_root()

    print(
        "ARM B:",
        clone_b
    )

    result_b = run_worker(
        clone_b,
        history_b(),
        "HISTORY_B"
    )

    print()
    print("ARM B RESULT")
    print("-" * 72)

    print(
        json.dumps(
            result_b,
            indent=2
        )
    )


    # --------------------------------------------------------
    # DIRECT HISTORY CONTRAST
    # --------------------------------------------------------

    a_after = result_a.get(
        "after_predictions",
        []
    )

    b_after = result_b.get(
        "after_predictions",
        []
    )


    numeric_a = [
        x for x in a_after
        if isinstance(x, (int, float))
    ]

    numeric_b = [
        x for x in b_after
        if isinstance(x, (int, float))
    ]


    different = False
    max_delta = None
    deltas = []


    if (
        len(numeric_a)
        == len(numeric_b)
        and len(numeric_a) > 0
    ):

        deltas = [
            abs(a - b)
            for a, b in zip(
                numeric_a,
                numeric_b
            )
        ]

        max_delta = max(deltas)

        # Floating point tolerance.
        different = any(
            d > 1e-12
            for d in deltas
        )


    # --------------------------------------------------------
    # WITHIN-ARM CHANGE
    # --------------------------------------------------------

    a_before = result_a.get(
        "before_predictions",
        []
    )

    b_before = result_b.get(
        "before_predictions",
        []
    )


    def changed(before, after):

        if (
            len(before)
            != len(after)
        ):
            return False

        for x, y in zip(
            before,
            after
        ):

            if (
                isinstance(x, (int, float))
                and isinstance(y, (int, float))
            ):

                if abs(x - y) > 1e-12:
                    return True

        return False


    a_changed = changed(
        a_before,
        a_after
    )

    b_changed = changed(
        b_before,
        b_after
    )


    # --------------------------------------------------------
    # ARTIFACT CHANGE
    # --------------------------------------------------------

    artifact_a = result_a.get(
        "artifact_changed"
    )

    artifact_b = result_b.get(
        "artifact_changed"
    )


    # --------------------------------------------------------
    # FINAL CAUSAL CLASSIFICATION
    # --------------------------------------------------------

    if different:

        verdict = (
            "ADAPTIVE BEHAVIOR DEMONSTRATED"
        )

        explanation = (
            "Two isolated systems received "
            "opposite accumulated experiences "
            "and then received identical future "
            "inputs. Their predictions differed."
        )

    elif a_changed or b_changed:

        verdict = (
            "LEARNING EFFECT DETECTED — "
            "CAUSAL BEHAVIORAL EFFECT NOT ESTABLISHED"
        )

        explanation = (
            "Training altered immediate model "
            "behavior in at least one arm, but "
            "opposite histories did not produce "
            "different future behavior."
        )

    elif artifact_a or artifact_b:

        verdict = (
            "PERSISTENT MODEL MUTATION DETECTED — "
            "BEHAVIORAL ADAPTATION NOT ESTABLISHED"
        )

        explanation = (
            "Training changed a model artifact, "
            "but the controlled future predictions "
            "did not demonstrate a behavioral "
            "difference."
        )

    else:

        verdict = (
            "ADAPTIVE BEHAVIOR NOT DEMONSTRATED"
        )

        explanation = (
            "Under a controlled opposite-history "
            "experiment, accumulated experience "
            "did not produce detectable differences "
            "in future predictions."
        )


    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    RESULTS = {

        "timestamp":
            datetime.now().isoformat(),

        "prediction_api":
            prediction_name,

        "experiment": {

            "history_A": (
                "low score -> 0, "
                "high score -> 1"
            ),

            "history_B": (
                "exact inverse labels"
            ),

            "future_inputs":
                future_inputs(),

            "arm_A":
                result_a,

            "arm_B":
                result_b,

            "future_behavior_different":
                different,

            "maximum_prediction_delta":
                max_delta,

            "prediction_deltas":
                deltas,

            "arm_A_behavior_changed":
                a_changed,

            "arm_B_behavior_changed":
                b_changed,

            "arm_A_artifact_changed":
                artifact_a,

            "arm_B_artifact_changed":
                artifact_b,
        },

        "classification": {

            "verdict":
                verdict,

            "explanation":
                explanation,

            "causal_standard":
                (
                    "Opposite training histories "
                    "+ identical future inputs "
                    "+ different future behavior"
                ),

        },
    }


    with open(
        RESULT_FILE,
        "w"
    ) as f:

        json.dump(
            RESULTS,
            f,
            indent=2,
            default=str
        )


    print()
    print("=" * 72)
    print("BIRTH_EDGE — DECISIVE CAUSALITY RESULT")
    print("=" * 72)

    print()
    print(verdict)

    print()
    print(explanation)

    print()
    print(
        "Prediction API:",
        prediction_name
    )

    print(
        "ARM A changed:",
        a_changed
    )

    print(
        "ARM B changed:",
        b_changed
    )

    print(
        "ARM A artifact changed:",
        artifact_a
    )

    print(
        "ARM B artifact changed:",
        artifact_b
    )

    print(
        "Maximum A/B prediction delta:",
        max_delta
    )

    print()
    print(
        "Machine-readable result:"
    )

    print(
        RESULT_FILE
    )

    print()
    print(
        "Temporary ARM A:"
    )

    print(
        clone_a
    )

    print()
    print(
        "Temporary ARM B:"
    )

    print(
        clone_b
    )

    print("=" * 72)


if __name__ == "__main__":
    main()
