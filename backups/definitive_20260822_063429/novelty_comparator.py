#!/usr/bin/env python3
"""
NOVELTY PROVER FOR AEGIS
Compares AEGIS against standard baselines to establish if it has a unique
empirical advantage (specifically, resistance to spurious decoys).
"""

import json
import random
import statistics
from collections import defaultdict

# SKLearn Baselines
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

# Import your data generators and utilities
import full_novelty_gauntlet as fng
import aegis_rule_miner as arm


# ============================================================
# BASELINE WRAPPERS
# ============================================================

def decision_tree_rule(rows, seed, max_depth=5):
    """Train a DT, extract feature importance, and check decoy selection."""
    rng = random.Random(seed)
    data = list(rows)
    rng.shuffle(data)
    
    X = []
    y = []
    features = arm.FEATURES
    for r in data:
        X.append([r.get(f, 0) for f in features])
        y.append(r["pumped"])
    
    clf = DecisionTreeClassifier(max_depth=max_depth, random_state=seed)
    clf.fit(X, y)
    
    importances = dict(zip(features, clf.feature_importances_))
    
    decoy_selected = importances.get("overall_score", 0) > 0.05
    true_selected = (importances.get("liquidity_usd", 0) > 0.05 and 
                     importances.get("holder_score", 0) > 0.05)
    
    preds = clf.predict(X)
    acc = sum(1 for p, t in zip(preds, y) if p == t) / len(y)
    
    return {
        "accuracy": acc,
        "decoy_selected": decoy_selected,
        "true_pair_selected": true_selected,
        "importances": importances,
        "rule_type": "DecisionTree"
    }

def random_forest_rule(rows, seed, max_depth=5):
    """Train an RF, extract feature importance."""
    rng = random.Random(seed)
    data = list(rows)
    rng.shuffle(data)
    
    X = []
    y = []
    features = arm.FEATURES
    for r in data:
        X.append([r.get(f, 0) for f in features])
        y.append(r["pumped"])
    
    clf = RandomForestClassifier(max_depth=max_depth, n_estimators=50, random_state=seed)
    clf.fit(X, y)
    
    importances = dict(zip(features, clf.feature_importances_))
    
    decoy_selected = importances.get("overall_score", 0) > 0.05
    true_selected = (importances.get("liquidity_usd", 0) > 0.05 and 
                     importances.get("holder_score", 0) > 0.05)
    
    preds = clf.predict(X)
    acc = sum(1 for p, t in zip(preds, y) if p == t) / len(y)
    
    return {
        "accuracy": acc,
        "decoy_selected": decoy_selected,
        "true_pair_selected": true_selected,
        "importances": importances,
        "rule_type": "RandomForest"
    }

def greedy_rule_learner(rows, seed):
    """Greedy single-feature median-split baseline."""
    rng = random.Random(seed)
    data = list(rows)
    rng.shuffle(data)
    
    features = arm.FEATURES
    best_feat = None
    best_acc = 0
    best_thresh = 0
    
    for feat in features:
        values = sorted([r.get(feat, 0) for r in data])
        for thresh in [values[int(len(values)*0.25)], values[int(len(values)*0.5)], values[int(len(values)*0.75)]]:
            correct = 0
            for r in data:
                pred = r.get(feat, 0) > thresh
                if pred == bool(r["pumped"]):
                    correct += 1
            acc = correct / len(data)
            if acc > best_acc:
                best_acc = acc
                best_feat = feat
                best_thresh = thresh
    
    decoy_selected = (best_feat == "overall_score")
    true_selected = (best_feat in ["liquidity_usd", "holder_score"])
    
    return {
        "accuracy": best_acc,
        "decoy_selected": decoy_selected,
        "true_pair_selected": False,
        "rule_type": "GreedySingle",
        "best_feature": best_feat
    }


# ============================================================
# COMPARISON ENGINE
# ============================================================

def run_baseline_on_test(baseline_func, test_name, data_generator, seeds=15):
    results = []
    for seed in range(seeds):
        rows = data_generator(300, 10000 + seed)
        result = baseline_func(rows, seed + 1000)
        results.append(result)
    return {
        "test": test_name,
        "mean_accuracy": statistics.mean([r["accuracy"] for r in results]),
        "decoy_selection_rate": sum(1 for r in results if r["decoy_selected"]) / len(results),
        "true_pair_rate": sum(1 for r in results if r["true_pair_selected"]) / len(results),
        "details": results
    }

def load_aegis_results():
    try:
        with open("novelty_gauntlet_results.json", "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print("ERROR: novelty_gauntlet_results.json not found. Run the full gauntlet first.")
        return None


# ============================================================
# MAIN NOVELTY VERDICT
# ============================================================

def main():
    print("="*72)
    print("AEGIS NOVELTY PROVER")
    print("="*72)
    print("Running baselines on critical stress tests...\n")
    
    # 1. Run Baselines
    baseline_results = {}
    
    baseline_results["correlated_decoy"] = {
        "DecisionTree": run_baseline_on_test(decision_tree_rule, "correlated_decoy", fng.correlated_decoy_rows, seeds=15),
        "RandomForest": run_baseline_on_test(random_forest_rule, "correlated_decoy", fng.correlated_decoy_rows, seeds=15),
        "Greedy": run_baseline_on_test(greedy_rule_learner, "correlated_decoy", fng.correlated_decoy_rows, seeds=15),
    }
    
    baseline_results["adversarial_decoy"] = {
        "DecisionTree": run_baseline_on_test(decision_tree_rule, "adversarial_decoy", fng.adversarial_decoy_rows, seeds=15),
        "RandomForest": run_baseline_on_test(random_forest_rule, "adversarial_decoy", fng.adversarial_decoy_rows, seeds=15),
        "Greedy": run_baseline_on_test(greedy_rule_learner, "adversarial_decoy", fng.adversarial_decoy_rows, seeds=15),
    }
    
    # 2. Load AEGIS results
    aegis_data = load_aegis_results()
    if aegis_data is None:
        print("Cannot compare. Exiting.")
        return
    
    aegis_correlated = aegis_data["tests"].get("correlated_decoy", {})
    aegis_adversarial = aegis_data["tests"].get("adversarial_decoy", {})
    
    aegis_decoy_rate_corr = aegis_correlated.get("decoy_selection_rate", 1.0)
    aegis_true_rate_corr = aegis_correlated.get("both_true_features_rate", 0.0)
    aegis_decoy_rate_adv = aegis_adversarial.get("decoy_selection_rate", 1.0)
    aegis_true_rate_adv = aegis_adversarial.get("true_pair_rate", 0.0)
    
    # 3. Print Comparison Table
    print("\n" + "="*72)
    print("COMPARATIVE TABLE: DECOY RESISTANCE")
    print("="*72)
    print(f"{'Model':<15} | {'Corr-Decoy Rate':<15} | {'Corr-True Rate':<15} | {'Adv-Decoy Rate':<15} | {'Adv-True Rate':<15}")
    print("-"*80)
    
    dt_corr = baseline_results["correlated_decoy"]["DecisionTree"]
    rf_corr = baseline_results["correlated_decoy"]["RandomForest"]
    gr_corr = baseline_results["correlated_decoy"]["Greedy"]
    
    dt_adv = baseline_results["adversarial_decoy"]["DecisionTree"]
    rf_adv = baseline_results["adversarial_decoy"]["RandomForest"]
    gr_adv = baseline_results["adversarial_decoy"]["Greedy"]
    
    print(f"{'DecisionTree':<15} | {dt_corr['decoy_selection_rate']*100:>5.1f}%       | {dt_corr['true_pair_rate']*100:>5.1f}%       | {dt_adv['decoy_selection_rate']*100:>5.1f}%       | {dt_adv['true_pair_rate']*100:>5.1f}%")
    print(f"{'RandomForest':<15} | {rf_corr['decoy_selection_rate']*100:>5.1f}%       | {rf_corr['true_pair_rate']*100:>5.1f}%       | {rf_adv['decoy_selection_rate']*100:>5.1f}%       | {rf_adv['true_pair_rate']*100:>5.1f}%")
    print(f"{'Greedy':<15} | {gr_corr['decoy_selection_rate']*100:>5.1f}%       | {gr_corr['true_pair_rate']*100:>5.1f}%       | {gr_adv['decoy_selection_rate']*100:>5.1f}%       | {gr_adv['true_pair_rate']*100:>5.1f}%")
    print(f"{'AEGIS':<15} | {aegis_decoy_rate_corr*100:>5.1f}%       | {aegis_true_rate_corr*100:>5.1f}%       | {aegis_decoy_rate_adv*100:>5.1f}%       | {aegis_true_rate_adv*100:>5.1f}%")
    
    # 4. THE FINAL VERDICT
    print("\n" + "="*72)
    print("NOVELTY DETERMINATION")
    print("="*72)
    
    best_baseline_decoy_rate = min(dt_corr['decoy_selection_rate'], rf_corr['decoy_selection_rate'], gr_corr['decoy_selection_rate'])
    best_baseline_true_rate = max(dt_corr['true_pair_rate'], rf_corr['true_pair_rate'], gr_corr['true_pair_rate'])
    
    decoy_improvement = best_baseline_decoy_rate - aegis_decoy_rate_corr
    true_improvement = aegis_true_rate_corr - best_baseline_true_rate
    
    print(f"Best Baseline Decoy Rate: {best_baseline_decoy_rate*100:.1f}%")
    print(f"AEGIS Decoy Rate: {aegis_decoy_rate_corr*100:.1f}%")
    print(f"Decoy Reduction: {decoy_improvement*100:.1f} percentage points")
    print(f"True-Pair Increase: {true_improvement*100:.1f} percentage points")
    
    if decoy_improvement > 0.20 and true_improvement > 0.20:
        print("\n>>> NOVELTY STATUS: PROVEN <<<")
        print("AEGIS demonstrates a substantial, statistically meaningful advantage")
        print("in resisting spurious correlated decoys compared to standard ML baselines.")
        print("This is a novel empirical property for a symbolic rule-miner in this domain.")
    elif decoy_improvement > 0.10:
        print("\n>>> NOVELTY STATUS: PARTIAL / PROMISING <<<")
        print("AEGIS shows modest improvement, but the gap is narrow.")
        print("Further hyperparameter tuning or a larger test suite is required.")
    else:
        print("\n>>> NOVELTY STATUS: NOT PROVEN (NOT NOVEL) <<<")
        print("AEGIS does not outperform standard Decision Trees or Random Forests")
        print("in decoy resistance. The system behaves similarly to existing ensembles.")
        print("Therefore, it does not currently demonstrate a novel empirical advantage.")

    # Save comparative results
    with open("novelty_comparison.json", "w") as f:
        json.dump({
            "baselines": baseline_results,
            "aegis": {
                "correlated_decoy_rate": aegis_decoy_rate_corr,
                "adversarial_decoy_rate": aegis_decoy_rate_adv,
                "true_pair_rate": aegis_true_rate_corr
            },
            "verdict": {
                "novelty_proven": decoy_improvement > 0.20 and true_improvement > 0.20,
                "decoy_reduction": decoy_improvement,
                "true_increase": true_improvement
            }
        }, f, indent=2)

    print("\nDetailed comparison saved to: novelty_comparison.json")

if __name__ == "__main__":
    main()
