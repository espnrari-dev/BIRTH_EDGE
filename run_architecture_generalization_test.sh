#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"
cd "$ROOT"

echo "============================================================"
echo "BIRTH_EDGE — ARCHITECTURE GENERALIZATION / ENGINEER SCRUTINY"
echo "============================================================"
echo
echo "COMMIT:"
git rev-parse --short HEAD
echo
echo "STATUS:"
git status --short
echo

python - <<'PY'
import os
import sys
import json
import inspect
import importlib
from pathlib import Path

ROOT = Path.cwd()

print("=" * 60)
print("DISCOVERY INTERFACE INSPECTION")
print("=" * 60)

candidates = [
    "birth_edge",
    "birth_edge_core",
    "birth_edge_miner",
    "aegis_rule_miner",
    "rule_miner",
]

found = []

for name in candidates:
    try:
        mod = importlib.import_module(name)
        found.append(name)
        print(f"\nMODULE FOUND: {name}")
        print("FILE:", getattr(mod, "__file__", None))

        public = [
            x for x in dir(mod)
            if not x.startswith("_")
        ]

        print("PUBLIC SYMBOLS:")
        for x in public:
            obj = getattr(mod, x)
            if callable(obj):
                try:
                    sig = inspect.signature(obj)
                except Exception:
                    sig = "(signature unavailable)"
                print(f"  {x}{sig}")

    except Exception as e:
        print(f"MODULE NOT AVAILABLE: {name} :: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("PYTHON FILES THAT LOOK LIKE DISCOVERY IMPLEMENTATIONS")
print("=" * 60)

for p in sorted(ROOT.glob("*.py")):
    text = ""
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue

    keys = [
        "discover",
        "rule",
        "predicate",
        "threshold",
        "fit",
        "classify",
    ]

    score = sum(text.lower().count(k) for k in keys)

    if score:
        print(f"{p.name}: relevance_score={score}")

print("\n" + "=" * 60)
print("RESULT")
print("=" * 60)

if not found:
    print("No standard BIRTH_EDGE discovery module was automatically identified.")
    print("The repository was NOT modified.")
    print()
    print("This inspection is intentional: the benchmark refuses to")
    print("guess an API and accidentally test the wrong system.")
    sys.exit(2)

print("Candidate discovery modules:", ", ".join(found))
print()
print("Next phase can bind directly to the discovered implementation.")
PY
