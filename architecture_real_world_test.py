#!/usr/bin/env python3

import json
import random
import statistics
from pathlib import Path

import aegis_rule_miner as arm


OUT = Path("birth_edge_architecture_real_world_report.json")


FEATURES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]


def make_row(rng):
    return {
        "liquidity_usd": rng.uniform(0, 30000),
        "holder_score": rng.uniform(0, 30),
        "dev_score": rng.uniform(0, 30),
        "lp_lock_score": rng.uniform(0, 30),
        "tax_score": rng.uniform(0, 30),
        "overall_score": rng.uniform(0, 100),
    }


def run_world(name, rule_fn, n=300, seed=42):
    rng = random.Random(seed)

    rows = []

    for _ in range(n):
        row = make_row(rng)
        row["pumped"] = bool(rule_fn(row))
        rows.append(row)

    discovered, discovery_score = arm.evolve_rule(rows)

    result = {
        "world": name,
        "seed": seed,
        "samples": n,
        "discovered": discovered is not None,
        "discovery_score": discovery_score,
        "rule": discovered.to_string() if discovered else None,
        "features": arm.rule_features(discovered) if discovered else [],
    }

    if discovered is not None:
        metrics = arm.evaluate_rule(discovered, rows)
        result["metrics"] = metrics
        result["complexity"] = discovered.complexity
    else:
        result["metrics"] = None
        result["complexity"] = 0

    return result


WORLDS = {
    "SINGLE_LIQUIDITY":
        lambda r: r["liquidity_usd"] > 15000,

    "REVERSE_HOLDER":
        lambda r: r["holder_score"] < 8,

    "TWO_FEATURE_AND":
        lambda r:
            r["liquidity_usd"] > 15000
            and r["holder_score"] > 15,

    "DEV_THRESHOLD":
        lambda r: r["dev_score"] > 20,

    "LP_LOCK_THRESHOLD":
        lambda r: r["lp_lock_score"] > 18,

    "OVERALL_THRESHOLD":
        lambda r: r["overall_score"] > 70,

    "NULL_REALITY":
        lambda r: False,
}


def main():
    print("=" * 80)
    print("BIRTH_EDGE — REAL ARCHITECTURE DISCOVERY TEST")
    print("=" * 80)
    print()

    all_results = []

    seeds = [0, 1, 2, 3, 4]

    for world_name, rule_fn in WORLDS.items():

        print("=" * 80)
        print("WORLD:", world_name)
        print("=" * 80)

        world_results = []

        for seed in seeds:
            result = run_world(
                world_name,
                rule_fn,
                n=300,
                seed=seed,
            )

            world_results.append(result)
            all_results.append(result)

            print(
                f"Seed {seed:02d} | "
                f"discovered={result['discovered']} | "
                f"score={result['discovery_score']:.4f} | "
                f"rule={result['rule']}"
            )

        discovered_count = sum(
            r["discovered"] for r in world_results
        )

        scores = [
            r["discovery_score"]
            for r in world_results
            if r["discovered"]
        ]

        accuracies = [
            r["metrics"]["accuracy"]
            for r in world_results
            if r["metrics"] is not None
        ]

        print()
        print(
            "Discovery rate:",
            f"{discovered_count}/{len(seeds)}"
        )

        if scores:
            print(
                "Mean discovery score:",
                f"{statistics.mean(scores):.4f}"
            )

        if accuracies:
            print(
                "Mean accuracy:",
                f"{statistics.mean(accuracies):.4f}"
            )

        print()

    report = {
        "system": "BIRTH_EDGE",
        "test": "REAL_ARCHITECTURE_DISCOVERY",
        "version": 1,
        "features": FEATURES,
        "seeds": seeds,
        "worlds": list(WORLDS.keys()),
        "results": all_results,
    }

    OUT.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
    )

    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    print("Total experiments:", len(all_results))
    print("Report:", OUT)
    print("=" * 80)


if __name__ == "__main__":
    main()
