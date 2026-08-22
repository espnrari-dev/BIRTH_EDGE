#!/data/data/com.termux/files/usr/bin/python
import random
import statistics
import importlib
import aegis_rule_miner as arm

# Import the exact test module so we use its existing world generators
import definitive_architecture_test as dat

SEEDS = dat.SEEDS

def metric_from_predictions(y_true, y_pred):
    tp = tn = fp = fn = 0

    for yt, yp in zip(y_true, y_pred):
        if yt == 1 and yp == 1:
            tp += 1
        elif yt == 0 and yp == 0:
            tn += 1
        elif yt == 0 and yp == 1:
            fp += 1
        elif yt == 1 and yp == 0:
            fn += 1

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total else 0.0

    tpr = tp / (tp + fn) if (tp + fn) else 0.0
    tnr = tn / (tn + fp) if (tn + fp) else 0.0
    balanced = (tpr + tnr) / 2.0

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "tpr": tpr,
        "tnr": tnr,
        "balanced": balanced,
        "positive_rate": (tp + fn) / total if total else 0.0,
    }


def extract_prediction(rule, row):
    """
    Evaluate the discovered rule using the miner's own evaluator
    where available. Fall back to the test module's evaluator.
    """
    for name in (
        "evaluate_rule",
        "eval_rule",
        "rule_matches",
        "matches_rule",
        "evaluate",
    ):
        fn = getattr(arm, name, None)
        if callable(fn):
            try:
                return bool(fn(rule, row))
            except TypeError:
                try:
                    return bool(fn(row, rule))
                except Exception:
                    pass
            except Exception:
                pass

    fn = getattr(dat, "evaluate_rule", None)
    if callable(fn):
        try:
            return bool(fn(rule, row))
        except TypeError:
            try:
                return bool(fn(row, rule))
            except Exception:
                pass

    raise RuntimeError(
        "Could not locate a rule evaluator. "
        "No source files were modified."
    )


print("=" * 80)
print("BIRTH_EDGE — MULTI_SIGNAL FORENSIC METRIC AUDIT")
print("=" * 80)
print("Miner:", arm.__file__)
print("Test :", dat.__file__)
print()

results = []

for seed in SEEDS:
    random.seed(seed)

    # Use the test's own generator exactly.
    generator = getattr(dat, "make_world", None)

    if generator is None:
        generator = getattr(dat, "generate_world", None)

    if generator is None:
        raise RuntimeError(
            "Could not locate world generator in definitive_architecture_test.py"
        )

    try:
        rows = generator("MULTI_SIGNAL", seed)
    except TypeError:
        try:
            rows = generator("MULTI_SIGNAL", seed=seed)
        except TypeError:
            rows = generator("MULTI_SIGNAL")

    # Preserve the test's train/test split if available.
    split = getattr(dat, "split_rows", None)

    if callable(split):
        try:
            train, held = split(rows, seed)
        except TypeError:
            train, held = split(rows)
    else:
        n = len(rows)
        cut = int(n * 0.8)
        train = rows[:cut]
        held = rows[cut:]

    result = arm.evolve_rule(
        train,
        generations=60,
        population_size=100,
        max_depth=5,
    )

    rule = result[0] if isinstance(result, tuple) else result

    if rule is None:
        print(f"Seed {seed:02d} | NO RULE")
        continue

    y_true = []
    y_pred = []

    for row in held:
        y_true.append(int(row["target"]))
        y_pred.append(int(extract_prediction(rule, row)))

    m = metric_from_predictions(y_true, y_pred)

    print(
        f"Seed {seed:02d} | "
        f"acc={m['accuracy']:.4f} | "
        f"bal={m['balanced']:.4f} | "
        f"TP={m['tp']} TN={m['tn']} FP={m['fp']} FN={m['fn']} | "
        f"TPR={m['tpr']:.4f} TNR={m['tnr']:.4f} | "
        f"positive_rate={m['positive_rate']:.4f}"
    )
    print(f"         rule={rule}")

    results.append(m)

print()
print("=" * 80)
print("AGGREGATE FORENSIC RESULT")
print("=" * 80)

if results:
    print("Runs:", len(results))
    print(
        "Mean accuracy:",
        f"{statistics.mean(x['accuracy'] for x in results):.6f}"
    )
    print(
        "Mean balanced:",
        f"{statistics.mean(x['balanced'] for x in results):.6f}"
    )
    print(
        "Mean TPR:",
        f"{statistics.mean(x['tpr'] for x in results):.6f}"
    )
    print(
        "Mean TNR:",
        f"{statistics.mean(x['tnr'] for x in results):.6f}"
    )
    print(
        "Mean positive prevalence:",
        f"{statistics.mean(x['positive_rate'] for x in results):.6f}"
    )

    print()
    print("Interpretation:")
    print("- If TPR is low while TNR is high, the miner is missing positives.")
    print("- If TNR is low while TPR is high, it is over-predicting positives.")
    print("- If both are high but the aggregate is low, the original")
    print("  reporting path is inconsistent with the direct confusion matrix.")
    print("- If MULTI_SIGNAL genuinely produces asymmetric sensitivity,")
    print("  that is a real structural property worth preserving.")

print()
print("NO SOURCE FILES MODIFIED.")
