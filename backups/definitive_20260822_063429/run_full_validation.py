#!/usr/bin/env python3

import importlib
import random
from oracle import oracle_label

m = importlib.import_module("aegis_rule_miner")

def make_rows(hs, ls, extra=False):
    rows = []
    for h in hs:
        for l in ls:
            r = {"holder_score": h, "liquidity": l}

            if extra:
                r.update({
                    "volume": (h * 137 + l / 73) % 50000,
                    "age": (h * 19 + int(l / 1000)) % 100,
                    "holders": (h * 311 + int(l / 100)) % 10000,
                    "fees": (l % 997) / 997,
                })

            r["pumped"] = oracle_label(r)
            rows.append(r)

    return rows


def evolve(rows):
    result = m.evolve_rule(rows)

    if isinstance(result, tuple):
        rule = result[0]
        score = result[1] if len(result) > 1 else None
    else:
        rule = result
        score = None

    return rule, score


def predict(rule, row):
    if rule is None:
        return None

    return int(bool(rule.evaluate(m.extract_features(row))))


def accuracy(rule, rows):
    if rule is None or not rows:
        return 0.0

    return sum(
        predict(rule, r) == oracle_label(r)
        for r in rows
    ) / len(rows)


def features(rule):
    if rule is None:
        return []

    return m.rule_features(rule)


def print_result(label, rule, score=None):
    print(label)
    print("RULE:", rule)

    if score is not None:
        print("SCORE:", round(score, 4))

    print("FEATURES:", features(rule))


print("=" * 72)
print("BIRTH_EDGE COMPLETE VALIDATION BATCH")
print("=" * 72)


# ================================================================
# 1. BASE DISCOVERY
# ================================================================

train = make_rows(
    range(0, 13, 2),
    [0, 5000, 10000, 20000, 30000]
)

test = make_rows(
    range(1, 14, 2),
    [2500, 7500, 15000, 25000, 35000]
)

rule, score = evolve(train)

print("\n[1] BASE DISCOVERY")
print_result("", rule, score)
print("TRAIN ACC:", round(accuracy(rule, train), 4))
print("HELD-OUT ACC:", round(accuracy(rule, test), 4))


# ================================================================
# 2. MULTI-SPLIT IDENTIFIABILITY
# ================================================================

print("\n[2] MULTI-SPLIT IDENTIFIABILITY")

splits = [
    ("A",
     range(0, 13, 2),
     [0, 5000, 10000, 20000, 30000]),

    ("B",
     range(1, 14, 2),
     [2500, 7500, 15000, 25000, 35000]),

    ("C",
     [0, 1, 3, 5, 7, 9, 11, 13],
     [1000, 6000, 12000, 18000, 26000, 34000]),

    ("D",
     [2, 4, 6, 8, 10, 12],
     [3000, 9000, 14000, 22000, 32000]),
]

for name, hs, ls in splits:
    rows = make_rows(hs, ls)
    r, s = evolve(rows)

    print(
        name,
        "|",
        r,
        "| score=",
        round(s, 4) if s is not None else None,
        "| features=",
        features(r)
    )


# ================================================================
# 3. NOISE RESISTANCE
# ================================================================

print("\n[3] NOISE RESISTANCE")

noise = make_rows(
    range(0, 13, 2),
    [0, 5000, 10000, 20000, 30000],
    extra=True
)

r, s = evolve(noise)

print_result("NOISE RESULT", r, s)

if set(features(r)) == {"holder_score"}:
    print("PASS — irrelevant features ignored")
else:
    print("FAIL — irrelevant feature entered rule")


# ================================================================
# 4. TRUE-FEATURE PERMUTATION
# ================================================================

print("\n[4] TRUE-FEATURE PERMUTATION")

permuted = make_rows(
    range(0, 13, 2),
    [0, 5000, 10000, 20000, 30000]
)

rng = random.Random(9917)

values = [r["holder_score"] for r in permuted]
rng.shuffle(values)

for r, value in zip(permuted, values):
    r["holder_score"] = value

r, s = evolve(permuted)

print_result("PERMUTATION RESULT", r, s)
print("POST-PERMUTATION ACC:", round(accuracy(r, permuted), 4))


# ================================================================
# 5. LIQUIDITY-ONLY ABLATION
# ================================================================

print("\n[5] LIQUIDITY-ONLY ABLATION")

liq_only = []

for r in train:
    liq_only.append({
        "holder_score": 0,
        "liquidity": r["liquidity"],
        "pumped": r["pumped"]
    })

r, s = evolve(liq_only)

print_result("LIQUIDITY-ONLY RESULT", r, s)
print("ACCURACY:", round(accuracy(r, liq_only), 4))


# ================================================================
# 6. HOLDER-ONLY
# ================================================================

print("\n[6] HOLDER-ONLY")

holder_only = []

for r in train:
    holder_only.append({
        "holder_score": r["holder_score"],
        "liquidity": 0,
        "pumped": r["pumped"]
    })

r, s = evolve(holder_only)

print_result("HOLDER-ONLY RESULT", r, s)
print("ACCURACY:", round(accuracy(r, holder_only), 4))


# ================================================================
# 7. BOUNDARY TEST
# ================================================================

print("\n[7] BOUNDARY TEST")

boundary = [
    {"holder_score": 6.9999, "liquidity": 0},
    {"holder_score": 7.0, "liquidity": 0},
    {"holder_score": 7.0001, "liquidity": 0},
    {"holder_score": 9.9999, "liquidity": 0},
    {"holder_score": 10.0, "liquidity": 0},
    {"holder_score": 10.0001, "liquidity": 0},
]

r, _ = evolve(train)

for x in boundary:
    print(
        x,
        "ORACLE=", oracle_label(x),
        "PRED=", predict(r, x)
    )


# ================================================================
# 8. FEATURE SWAP
# ================================================================

print("\n[8] FEATURE SWAP")

swapped = []

for r in train:
    swapped.append({
        "holder_score": r["liquidity"] / 5000,
        "liquidity": r["holder_score"] * 5000,
        "pumped": r["pumped"]
    })

r, s = evolve(swapped)

print_result("FEATURE-SWAP RESULT", r, s)
print("ACCURACY:", round(accuracy(r, swapped), 4))


# ================================================================
# 9. LABEL SHUFFLE
# ================================================================

print("\n[9] LABEL SHUFFLE")

shuffled = [dict(r) for r in train]

rng = random.Random(44121)

labels = [r["pumped"] for r in shuffled]
rng.shuffle(labels)

for r, y in zip(shuffled, labels):
    r["pumped"] = y

r, s = evolve(shuffled)

print_result("LABEL-SHUFFLE RESULT", r, s)
print("ACCURACY:", round(accuracy(r, shuffled), 4))


# ================================================================
# 10. MULTI-SEED STABILITY
# ================================================================

print("\n[10] MULTI-SEED STABILITY")

seed_results = []

for seed in range(10):
    random.seed(seed)

    rows = make_rows(
        range(0, 13, 2),
        [0, 5000, 10000, 20000, 30000]
    )

    r, s = evolve(rows)

    seed_results.append((seed, r, s))

    print(
        f"SEED {seed:02d} | "
        f"score={s:.4f} | "
        f"features={features(r)} | "
        f"rule={r}"
        if s is not None
        else
        f"SEED {seed:02d} | score=None | "
        f"features={features(r)} | rule={r}"
    )


# ================================================================
# 11. LARGE GRID
# ================================================================

print("\n[11] LARGE GRID")

large = make_rows(
    [x / 2 for x in range(0, 31)],
    [0, 1000, 2500, 5000, 7500, 10000,
     15000, 20000, 30000, 40000]
)

r, s = evolve(large)

print_result("LARGE-GRID RESULT", r, s)
print("SAMPLES:", len(large))
print("ACCURACY:", round(accuracy(r, large), 4))


# ================================================================
# 12. OUT-OF-RANGE GENERALIZATION
# ================================================================

print("\n[12] OUT-OF-RANGE GENERALIZATION")

oor = make_rows(
    [-10, -5, -1, 14, 16, 20, 25],
    [500, 5000, 12500, 22500, 45000, 60000]
)

r, s = evolve(train)

print("RULE:", r)
print("TRAINED ON:", len(train))
print("OUT-OF-RANGE:", len(oor))
print("OOR ACC:", round(accuracy(r, oor), 4))


# ================================================================
# 13. DENSE HOLDER GRID
# ================================================================

print("\n[13] DENSE HOLDER GRID")

dense = make_rows(
    [x / 10 for x in range(0, 201)],
    [0, 10000, 25000, 50000]
)

r, s = evolve(dense)

print_result("DENSE RESULT", r, s)
print("SAMPLES:", len(dense))
print("ACCURACY:", round(accuracy(r, dense), 4))


# ================================================================
# 14. LIQUIDITY RANGE STRESS
# ================================================================

print("\n[14] LIQUIDITY RANGE STRESS")

stress = make_rows(
    [0, 3, 5, 7, 8, 10, 12, 15],
    [-10000, -1, 0, 1, 1000, 10000,
     50000, 100000, 1000000]
)

r, s = evolve(train)

print("RULE:", r)
print("STRESS SAMPLES:", len(stress))
print("STRESS ACC:", round(accuracy(r, stress), 4))


# ================================================================
# 15. REPEATED DISCOVERY CONSISTENCY
# ================================================================

print("\n[15] REPEATED DISCOVERY CONSISTENCY")

rules = []

for i in range(20):
    random.seed(i + 1000)

    r, s = evolve(train)

    rules.append(str(r))

unique_rules = sorted(set(rules))

print("RUNS:", len(rules))
print("UNIQUE RULES:", len(unique_rules))

for i, rule_text in enumerate(unique_rules, 1):
    print(f"RULE {i}: {rule_text}")


# ================================================================
# FINAL SUMMARY
# ================================================================

print("\n" + "=" * 72)
print("BATCH COMPLETE")
print("=" * 72)

base_rule, base_score = evolve(train)

print("BASE RULE:", base_rule)
print("BASE DISCOVERY SCORE:",
      round(base_score, 4) if base_score is not None else None)
print("BASE TRAIN ACC:",
      round(accuracy(base_rule, train), 4))
print("BASE HELD-OUT ACC:",
      round(accuracy(base_rule, test), 4))
print("DISCOVERED FEATURES:",
      features(base_rule))

print("=" * 72)
