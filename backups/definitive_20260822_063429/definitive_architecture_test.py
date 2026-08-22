#!/usr/bin/env python3

import json
import math
import random
import statistics
import traceback
from pathlib import Path

import aegis_rule_miner as arm


OUT = Path("BIRTH_EDGE_DEFINITIVE_ARCHITECTURE_REPORT.json")

FEATURES = list(arm.FEATURES)

SEEDS = list(range(20))


# ============================================================
# WORLD GENERATORS
# ============================================================

def base_row(rng):
    return {
        "liquidity_usd": rng.uniform(0, 30000),
        "holder_score": rng.uniform(0, 30),
        "dev_score": rng.uniform(0, 30),
        "lp_lock_score": rng.uniform(0, 30),
        "tax_score": rng.uniform(0, 30),
        "overall_score": rng.uniform(0, 100),
    }


def make_world(kind, seed, n=400, noise=0.0, distractors=0):
    rng = random.Random(seed)
    rows = []

    for _ in range(n):
        r = base_row(rng)

        L = r["liquidity_usd"]
        H = r["holder_score"]
        D = r["dev_score"]
        P = r["lp_lock_score"]
        T = r["tax_score"]
        O = r["overall_score"]

        if kind == "LIQUIDITY":
            truth = L > 15000

        elif kind == "REVERSE_HOLDER":
            truth = H < 10

        elif kind == "DEV":
            truth = D > 20

        elif kind == "LP":
            truth = P > 18

        elif kind == "OVERALL":
            truth = O > 70

        elif kind == "AND":
            truth = L > 15000 and H > 15

        elif kind == "AND_REVERSE":
            truth = L > 15000 and H < 15

        elif kind == "THREE_WAY":
            truth = L > 15000 and H > 15 and D > 15

        elif kind == "OR":
            truth = L > 15000 or H > 25

        elif kind == "XOR":
            truth = (L > 15000) ^ (H > 15)

        elif kind == "ABSOLUTE_NONLINEAR":
            truth = abs(H - 15) > 8

        elif kind == "PRODUCT":
            truth = (L / 30000.0) * (H / 30.0) > 0.50

        elif kind == "RATIO":
            truth = (L / 30000.0) > (H / 30.0)

        elif kind == "NOISE":
            truth = L > 15000

        elif kind == "NULL":
            truth = rng.random() < 0.5

        elif kind == "RARE":
            truth = L > 29700

        elif kind == "IMBALANCED":
            truth = L > 28500

        elif kind == "REDUNDANT":
            truth = L > 15000

        elif kind == "DISTRACTOR":
            truth = L > 15000

        elif kind == "MULTI_SIGNAL":
            truth = (
                L > 15000
                and H > 15
                and D > 15
                and P > 15
            )

        else:
            raise ValueError(kind)

        # Label noise.
        if noise > 0 and rng.random() < noise:
            truth = not truth

        r["pumped"] = bool(truth)

        if kind == "REDUNDANT":
            # Correlated copy of the true signal.
            r["overall_score"] = L / 300.0

        if kind == "DISTRACTOR":
            # Many unrelated features.
            for i in range(distractors):
                r[f"distractor_{i}"] = rng.uniform(-1e9, 1e9)

        rows.append(r)

    return rows


def make_shifted_world(seed, train=True):
    rng = random.Random(seed)
    rows = []

    if train:
        lo, hi = 0, 15000
    else:
        lo, hi = 15000, 30000

    for _ in range(400):
        r = base_row(rng)

        # Force the feature distribution to differ.
        r["liquidity_usd"] = rng.uniform(lo, hi)

        # Ground truth remains identical.
        r["pumped"] = r["liquidity_usd"] > 15000

        rows.append(r)

    return rows


def make_out_of_range(seed, train=True):
    rng = random.Random(seed)
    rows = []

    if train:
        lo, hi = 0, 10000
    else:
        lo, hi = 10000, 30000

    for _ in range(400):
        r = base_row(rng)
        r["liquidity_usd"] = rng.uniform(lo, hi)
        r["pumped"] = r["liquidity_usd"] > 7000
        rows.append(r)

    return rows


# ============================================================
# METRICS
# ============================================================

def labels(rows):
    return [bool(r["pumped"]) for r in rows]


def predict(expr, rows):
    pred = []

    for row in rows:
        try:
            pred.append(bool(expr.evaluate(arm.extract_features(row))))
        except Exception:
            pred.append(False)

    return pred


def metrics(pred, truth):
    tp = tn = fp = fn = 0

    for p, y in zip(pred, truth):
        if y and p:
            tp += 1
        elif not y and not p:
            tn += 1
        elif not y and p:
            fp += 1
        else:
            fn += 1

    n = len(truth)

    accuracy = (tp + tn) / n if n else 0.0

    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0

    balanced = (tpr + tnr) / 2.0

    precision = tp / (tp + fp) if tp + fp else 0.0

    return {
        "accuracy": accuracy,
        "balanced_accuracy": balanced,
        "precision": precision,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def safe_discover(rows):
    try:
        result = arm.evolve_rule(
            rows,
            generations=60,
            population_size=100,
            max_depth=5,
        )

        if isinstance(result, tuple):
            expr = result[0]
            score = result[1] if len(result) > 1 else None
        else:
            expr = result
            score = None

        return {
            "success": expr is not None,
            "expr": expr,
            "score": score,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "expr": None,
            "score": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }


def rule_string(expr):
    if expr is None:
        return None

    try:
        return expr.to_string()
    except Exception:
        return repr(expr)


def rule_features(expr):
    if expr is None:
        return []

    try:
        return arm.rule_features(expr)
    except Exception:
        return []


# ============================================================
# STANDARD HELD-OUT TEST
# ============================================================

def run_standard_world(kind, seed, noise=0.0, distractors=0):
    train = make_world(
        kind,
        seed,
        n=400,
        noise=noise,
        distractors=distractors,
    )

    test = make_world(
        kind,
        seed + 100000,
        n=1000,
        noise=noise,
        distractors=distractors,
    )

    discovery = safe_discover(train)

    result = {
        "seed": seed,
        "discovered": discovery["success"],
        "rule": rule_string(discovery["expr"]),
        "features": rule_features(discovery["expr"]),
        "discovery_score": discovery["score"],
        "train": None,
        "held_out": None,
        "error": discovery["error"],
    }

    if discovery["expr"] is not None:
        expr = discovery["expr"]

        result["train"] = metrics(
            predict(expr, train),
            labels(train),
        )

        result["held_out"] = metrics(
            predict(expr, test),
            labels(test),
        )

    return result


# ============================================================
# MAIN EXPERIMENTS
# ============================================================

def aggregate(results):
    discoveries = [r["discovered"] for r in results]

    train_acc = [
        r["train"]["accuracy"]
        for r in results
        if r["train"] is not None
    ]

    test_acc = [
        r["held_out"]["accuracy"]
        for r in results
        if r["held_out"] is not None
    ]

    test_bal = [
        r["held_out"]["balanced_accuracy"]
        for r in results
        if r["held_out"] is not None
    ]

    return {
        "runs": len(results),
        "discovery_rate": sum(discoveries) / len(discoveries),
        "mean_train_accuracy": (
            statistics.mean(train_acc) if train_acc else None
        ),
        "mean_held_out_accuracy": (
            statistics.mean(test_acc) if test_acc else None
        ),
        "mean_held_out_balanced_accuracy": (
            statistics.mean(test_bal) if test_bal else None
        ),
        "min_held_out_accuracy": (
            min(test_acc) if test_acc else None
        ),
    }


def run():
    print("=" * 80)
    print("BIRTH_EDGE — DEFINITIVE ARCHITECTURE TEST")
    print("=" * 80)
    print("Actual miner:", arm.__file__)
    print("Seeds:", len(SEEDS))
    print("Features:", FEATURES)
    print()

    report = {
        "system": "BIRTH_EDGE",
        "test": "DEFINITIVE_ARCHITECTURE_TEST",
        "version": 1,
        "features": FEATURES,
        "experiments": {},
        "failures": [],
    }

    # --------------------------------------------------------
    # FAMILY 1 — IN-FAMILY STRUCTURAL DISCOVERY
    # --------------------------------------------------------

    standard_worlds = [
        "LIQUIDITY",
        "REVERSE_HOLDER",
        "DEV",
        "LP",
        "OVERALL",
        "AND",
        "AND_REVERSE",
    ]

    for world in standard_worlds:
        print("=" * 80)
        print("WORLD:", world)
        print("=" * 80)

        results = []

        for seed in SEEDS:
            r = run_standard_world(world, seed)
            results.append(r)

            print(
                f"Seed {seed:02d} | "
                f"discover={r['discovered']} | "
                f"train={None if not r['train'] else round(r['train']['accuracy'],4)} | "
                f"heldout={None if not r['held_out'] else round(r['held_out']['accuracy'],4)} | "
                f"rule={r['rule']}"
            )

        report["experiments"][world] = {
            "results": results,
            "aggregate": aggregate(results),
        }

        print("AGGREGATE:", json.dumps(
            report["experiments"][world]["aggregate"],
            indent=2
        ))
        print()

    # --------------------------------------------------------
    # FAMILY 2 — COMPLEXITY ESCALATION
    # --------------------------------------------------------

    complexity_worlds = [
        "THREE_WAY",
        "MULTI_SIGNAL",
        "OR",
        "XOR",
        "ABSOLUTE_NONLINEAR",
        "PRODUCT",
        "RATIO",
    ]

    for world in complexity_worlds:
        print("=" * 80)
        print("STRUCTURAL GENERALIZATION:", world)
        print("=" * 80)

        results = []

        for seed in SEEDS:
            r = run_standard_world(world, seed)
            results.append(r)

            print(
                f"Seed {seed:02d} | "
                f"discover={r['discovered']} | "
                f"train={None if not r['train'] else round(r['train']['accuracy'],4)} | "
                f"heldout={None if not r['held_out'] else round(r['held_out']['accuracy'],4)} | "
                f"rule={r['rule']}"
            )

        report["experiments"][world] = {
            "results": results,
            "aggregate": aggregate(results),
        }

        print("AGGREGATE:", json.dumps(
            report["experiments"][world]["aggregate"],
            indent=2
        ))
        print()

    # --------------------------------------------------------
    # FAMILY 3 — NOISE ROBUSTNESS
    # --------------------------------------------------------

    for noise in [0.05, 0.10, 0.20, 0.30]:
        name = f"LABEL_NOISE_{int(noise*100)}"

        print("=" * 80)
        print("NOISE:", noise)
        print("=" * 80)

        results = [
            run_standard_world(
                "NOISE",
                seed,
                noise=noise,
            )
            for seed in SEEDS
        ]

        report["experiments"][name] = {
            "results": results,
            "aggregate": aggregate(results),
        }

        print(json.dumps(
            report["experiments"][name]["aggregate"],
            indent=2
        ))
        print()

    # --------------------------------------------------------
    # FAMILY 4 — DISTRACTOR RESISTANCE
    # --------------------------------------------------------

    for d in [10, 50, 100, 250]:
        name = f"DISTRACTORS_{d}"

        print("=" * 80)
        print("DISTRACTORS:", d)
        print("=" * 80)

        results = [
            run_standard_world(
                "DISTRACTOR",
                seed,
                distractors=d,
            )
            for seed in SEEDS
        ]

        report["experiments"][name] = {
            "results": results,
            "aggregate": aggregate(results),
        }

        print(json.dumps(
            report["experiments"][name]["aggregate"],
            indent=2
        ))
        print()

    # --------------------------------------------------------
    # FAMILY 5 — RARE / IMBALANCED EVENTS
    # --------------------------------------------------------

    for world in ["RARE", "IMBALANCED"]:
        print("=" * 80)
        print("RARE / IMBALANCED:", world)
        print("=" * 80)

        results = [
            run_standard_world(world, seed)
            for seed in SEEDS
        ]

        report["experiments"][world] = {
            "results": results,
            "aggregate": aggregate(results),
        }

        print(json.dumps(
            report["experiments"][world]["aggregate"],
            indent=2
        ))
        print()

    # --------------------------------------------------------
    # FAMILY 6 — NULL / FALSE DISCOVERY
    # --------------------------------------------------------

    print("=" * 80)
    print("NULL REALITY")
    print("=" * 80)

    null_results = []

    for seed in SEEDS:
        r = run_standard_world("NULL", seed)
        null_results.append(r)

        print(
            f"Seed {seed:02d} | "
            f"discovered={r['discovered']} | "
            f"rule={r['rule']}"
        )

    report["experiments"]["NULL"] = {
        "results": null_results,
        "aggregate": aggregate(null_results),
        "false_discovery_rate": (
            sum(r["discovered"] for r in null_results)
            / len(null_results)
        ),
    }

    print()

    # --------------------------------------------------------
    # FAMILY 7 — DISTRIBUTION SHIFT
    # --------------------------------------------------------

    print("=" * 80)
    print("DISTRIBUTION SHIFT")
    print("=" * 80)

    shift_results = []

    for seed in SEEDS:
        train = make_shifted_world(seed, True)
        test = make_shifted_world(seed + 100000, False)

        d = safe_discover(train)

        item = {
            "seed": seed,
            "discovered": d["success"],
            "rule": rule_string(d["expr"]),
            "train": None,
            "held_out": None,
            "error": d["error"],
        }

        if d["expr"] is not None:
            item["train"] = metrics(
                predict(d["expr"], train),
                labels(train),
            )

            item["held_out"] = metrics(
                predict(d["expr"], test),
                labels(test),
            )

        shift_results.append(item)

        print(
            f"Seed {seed:02d} | "
            f"discover={item['discovered']} | "
            f"heldout={None if not item['held_out'] else round(item['held_out']['accuracy'],4)} | "
            f"rule={item['rule']}"
        )

    report["experiments"]["DISTRIBUTION_SHIFT"] = {
        "results": shift_results,
        "aggregate": aggregate(shift_results),
    }

    print()

    # --------------------------------------------------------
    # FAMILY 8 — OUT OF RANGE GENERALIZATION
    # --------------------------------------------------------

    print("=" * 80)
    print("OUT-OF-RANGE GENERALIZATION")
    print("=" * 80)

    oor_results = []

    for seed in SEEDS:
        train = make_out_of_range(seed, True)
        test = make_out_of_range(seed + 100000, False)

        d = safe_discover(train)

        item = {
            "seed": seed,
            "discovered": d["success"],
            "rule": rule_string(d["expr"]),
            "train": None,
            "held_out": None,
            "error": d["error"],
        }

        if d["expr"] is not None:
            item["train"] = metrics(
                predict(d["expr"], train),
                labels(train),
            )

            item["held_out"] = metrics(
                predict(d["expr"], test),
                labels(test),
            )

        oor_results.append(item)

        print(
            f"Seed {seed:02d} | "
            f"discover={item['discovered']} | "
            f"heldout={None if not item['held_out'] else round(item['held_out']['accuracy'],4)} | "
            f"rule={item['rule']}"
        )

    report["experiments"]["OUT_OF_RANGE"] = {
        "results": oor_results,
        "aggregate": aggregate(oor_results),
    }

    print()

    # --------------------------------------------------------
    # FAMILY 9 — RULE STABILITY
    # --------------------------------------------------------

    print("=" * 80)
    print("RULE STABILITY")
    print("=" * 80)

    stability = {}

    for world in [
        "LIQUIDITY",
        "REVERSE_HOLDER",
        "AND",
        "AND_REVERSE",
    ]:
        rules = []

        for seed in range(50):
            r = run_standard_world(world, seed)

            if r["rule"]:
                rules.append(r["rule"])

        counts = {}

        for rule in rules:
            counts[rule] = counts.get(rule, 0) + 1

        stability[world] = {
            "runs": len(rules),
            "unique_rules": len(counts),
            "rules": sorted(
                counts.items(),
                key=lambda x: (-x[1], x[0])
            )[:20],
        }

        print(world)
        print(json.dumps(stability[world], indent=2))
        print()

    report["experiments"]["RULE_STABILITY"] = stability

    # --------------------------------------------------------
    # FINAL SCORECARD
    # --------------------------------------------------------

    def agg(name):
        return report["experiments"][name]["aggregate"]

    structured = [
        agg(x) for x in standard_worlds
    ]

    structured_discovery = statistics.mean(
        x["discovery_rate"] for x in structured
    )

    structured_holdout = statistics.mean(
        x["mean_held_out_accuracy"]
        for x in structured
        if x["mean_held_out_accuracy"] is not None
    )

    null_fdr = report["experiments"]["NULL"]["false_discovery_rate"]

    complex_names = [
        "THREE_WAY",
        "MULTI_SIGNAL",
        "OR",
        "XOR",
        "ABSOLUTE_NONLINEAR",
        "PRODUCT",
        "RATIO",
    ]

    complex_discovery = statistics.mean(
        agg(x)["discovery_rate"]
        for x in complex_names
    )

    noise_results = [
        report["experiments"][f"LABEL_NOISE_{x}"]["aggregate"]
        for x in [5, 10, 20, 30]
    ]

    distractor_results = [
        report["experiments"][f"DISTRACTORS_{x}"]["aggregate"]
        for x in [10, 50, 100, 250]
    ]

    report["FINAL_SCORECARD"] = {
        "structured_world_discovery_rate": structured_discovery,
        "structured_world_mean_heldout_accuracy": structured_holdout,
        "complex_world_discovery_rate": complex_discovery,
        "null_false_discovery_rate": null_fdr,
        "noise_robustness": {
            str(x): noise_results[i]
            for i, x in enumerate([5, 10, 20, 30])
        },
        "distractor_robustness": {
            str(x): distractor_results[i]
            for i, x in enumerate([10, 50, 100, 250])
        },
        "distribution_shift": agg("DISTRIBUTION_SHIFT"),
        "out_of_range": agg("OUT_OF_RANGE"),
        "rule_stability": stability,
    }

    OUT.write_text(
        json.dumps(report, indent=2, default=str)
    )

    # --------------------------------------------------------
    # PRINT DECISIVE RESULTS
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("                    DEFINITIVE RESULT")
    print("=" * 80)

    print(
        f"Structured discovery rate : "
        f"{structured_discovery:.4f}"
    )

    print(
        f"Structured held-out accuracy: "
        f"{structured_holdout:.4f}"
    )

    print(
        f"Complex-world discovery rate: "
        f"{complex_discovery:.4f}"
    )

    print(
        f"NULL false-discovery rate  : "
        f"{null_fdr:.4f}"
    )

    print(
        f"Distribution-shift holdout : "
        f"{agg('DISTRIBUTION_SHIFT')['mean_held_out_accuracy']}"
    )

    print(
        f"Out-of-range holdout       : "
        f"{agg('OUT_OF_RANGE')['mean_held_out_accuracy']}"
    )

    print()
    print("REPORT:", OUT)
    print("=" * 80)


if __name__ == "__main__":
    run()
