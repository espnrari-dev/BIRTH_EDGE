#!/usr/bin/env python3

import inspect
import aegis_rule_miner as m

print("=" * 80)
print("BIRTH_EDGE CORE ARCHITECTURE INSPECTION")
print("=" * 80)

targets = [
    "_discover",
    "evolve_rule",
    "evaluate_rule",
    "extract_features",
    "rule_features",
    "Rule",
    "Predicate",
]

for name in targets:
    print()
    print("=" * 80)
    print(name)
    print("=" * 80)

    obj = getattr(m, name, None)

    if obj is None:
        print("NOT FOUND")
        continue

    try:
        print("TYPE:", type(obj))
    except Exception:
        pass

    try:
        print("SIGNATURE:", inspect.signature(obj))
    except Exception:
        pass

    try:
        print()
        print(inspect.getsource(obj))
    except Exception as exc:
        print("SOURCE UNAVAILABLE:", type(exc).__name__, str(exc))

print()
print("=" * 80)
print("MODULE CONSTANTS / PRIVATE HELPERS")
print("=" * 80)

for name in dir(m):
    if name.startswith("_"):
        obj = getattr(m, name, None)

        if callable(obj):
            print(name)

print()
print("=" * 80)
print("DONE")
print("=" * 80)
