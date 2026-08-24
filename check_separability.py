"""
Checks whether the 4 features can separate the 8 positive cases
from the 97 negative cases at all, before committing to weighted
training. If ranges/means overlap heavily, no linear model can
discriminate regardless of loss weighting -- that's a data/feature
problem, not a training problem.
"""

import json
import statistics

import ml_model

with open("data/ml_reflection.json") as f:
    payload = json.load(f)
rows = payload.get("reflections", payload)

pos_feats = {name: [] for name in ml_model.FEATURE_NAMES}
neg_feats = {name: [] for name in ml_model.FEATURE_NAMES}

for r in rows:
    actual = r.get("actual_outcome", r.get("actual"))
    if actual is None:
        continue

    a = 1 if float(actual) >= 0.5 else 0
    bucket = pos_feats if a == 1 else neg_feats

    for name in ml_model.FEATURE_NAMES:
        value = r.get(name)
        if value is None:
            value = r.get("raw", {}).get(name)
        if value is not None:
            bucket[name].append(float(value))

print(f"positive_n={len(pos_feats[ml_model.FEATURE_NAMES[0]])} "
      f"negative_n={len(neg_feats[ml_model.FEATURE_NAMES[0]])}")
print()

for name in ml_model.FEATURE_NAMES:
    p = pos_feats[name]
    n = neg_feats[name]

    if not p or not n:
        print(f"{name}: insufficient data (pos={len(p)} neg={len(n)})")
        continue

    p_mean, p_min, p_max = statistics.mean(p), min(p), max(p)
    n_mean, n_min, n_max = statistics.mean(n), min(n), max(n)

    overlap = not (p_max < n_min or n_max < p_min)

    print(f"{name}:")
    print(f"  positive: mean={p_mean:.4f} range=[{p_min:.4f}, {p_max:.4f}]")
    print(f"  negative: mean={n_mean:.4f} range=[{n_min:.4f}, {n_max:.4f}]")
    print(f"  ranges_overlap={overlap}")
    print()
