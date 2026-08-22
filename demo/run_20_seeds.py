import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random
import aegis_rule_miner as arm

results = []
correct_rule_count = 0
total_runs = 20

print(f"Running {total_runs} seeds...\n")

for seed in range(total_runs):
    random.seed(seed)
    rows = []
    for _ in range(200):
        liquidity = random.uniform(0, 30000)
        holder_score = random.uniform(0, 30)
        if liquidity > 12000 and holder_score > 15:
            pump = 1 if random.random() < 0.95 else 0
        else:
            pump = 0 if random.random() < 0.95 else 1
        rows.append({
            "initial_liquidity_usd": liquidity,
            "holder_score": holder_score,
            "dev_score": random.uniform(0, 20),
            "lp_lock_score": random.uniform(0, 20),
            "tax_score": random.uniform(0, 15),
            "overall_score": random.uniform(0, 100),
            "pumped": pump,
        })
    best_expr, acc = arm.evolve_rule(rows, generations=100, population_size=200, max_depth=5)
    if best_expr:
        rule_str = best_expr.to_string()
        results.append((seed, acc, rule_str))
        if "holder_score" in rule_str and "liquidity_usd" in rule_str:
            correct_rule_count += 1
        print(f"Seed {seed:2d}: acc={acc:.4f} | {rule_str}")
    else:
        results.append((seed, 0.0, "No rule"))
        print(f"Seed {seed:2d}: no rule evolved")

accs = [r[1] for r in results]
mean_acc = sum(accs) / len(accs)
std_acc = (sum((a - mean_acc)**2 for a in accs) / len(accs)) ** 0.5
min_acc = min(accs)
max_acc = max(accs)

print("\n================ SUMMARY ================")
print(f"Runs: {total_runs}")
print(f"Mean accuracy: {mean_acc:.4f}")
print(f"Std deviation: {std_acc:.4f}")
print(f"Min accuracy: {min_acc:.4f}")
print(f"Max accuracy: {max_acc:.4f}")
print(f"Runs that found both key features: {correct_rule_count}/{total_runs}")
print("=========================================")
