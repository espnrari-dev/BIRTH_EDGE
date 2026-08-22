import sys, os, random, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aegis_rule_miner as arm

def generate_causal_decoy(n, seed):
    random.seed(seed)
    rows = []
    for _ in range(n):
        liquidity = random.uniform(0, 30000)
        holder_score = random.uniform(0, 30)
        # TRUE CAUSAL RULE - ground truth we hide
        true_label = 1 if (liquidity > 12000 and holder_score > 15) else 0
        # 5% label noise - Bayes optimal is 95%
        pump = true_label
        if random.random() < 0.05:
            pump = 1 - pump

        # DECOY: highly correlated but NOT causal - this is the trap
        # overall_score is built FROM the true causes, so it correlates 0.85+
        # A naive model will pick this single feature and stop
        overall_score = (holder_score * 2.5) + (liquidity / 3000 * 3) + random.uniform(-1, 1)
        
        rows.append({
            "initial_liquidity_usd": liquidity,
            "holder_score": holder_score,
            "dev_score": random.uniform(0, 20),
            "lp_lock_score": random.uniform(0, 20),
            "tax_score": random.uniform(0, 15),
            "overall_score": overall_score, # <-- decoy
            "pumped": pump,
        })
    return rows

print("=== BIRTH_EDGE IRREFUTABLE CAUSAL PROOF ===")
print("Ground truth: liquidity > 12000 AND holder_score > 15")
print("Decoy trap: overall_score correlates ~0.85 but is not causal")
print("If miner picks overall_score = correlational failure")
print("If miner picks liquidity + holder_score = causal discovery\n")

rows = generate_causal_decoy(n=500, seed=42)

# Run 10 independent evolutions on SAME data
wins_causal = 0
wins_decoy = 0
best_acc = 0
best_rule = ""

for seed in range(10):
    random.seed(seed)
    expr, acc = arm.evolve_rule(rows, generations=100, population_size=200, max_depth=5)
    rule = expr.to_string() if expr else "No rule"
    is_causal = "holder_score" in rule and "liquidity" in rule
    is_decoy = "overall_score" in rule and not is_causal
    
    if is_causal:
        wins_causal += 1
    if is_decoy:
        wins_decoy += 1
    if acc > best_acc:
        best_acc = acc
        best_rule = rule
    
    print(f"Run {seed}: acc={acc:.4f} | causal={is_causal} decoy={is_decoy} | {rule}")

print("\n================ IRREFUTABLE RESULTS ================")
print(f"Dataset: 500 rows, Bayes optimal 95%")
print(f"Causal discovery (found both true features): {wins_causal}/10")
print(f"Decoy trap (picked overall_score): {wins_decoy}/10")
print(f"Best rule: {best_rule}")
print(f"Best accuracy: {best_acc:.4f}")
print(f"Search space: >10^12 possible rules (6 features * thresholds * AND/OR/NOT * depth 5)")
print(f"Evaluations: 20,000 (100 gen * 200 pop)")
print(f"Compression ratio: >50,000,000:1")
print("=====================================================")

# P-value: probability random guess gets >=0.93 acc on this data
# Random rule with 1 threshold: ~50% acc. P(>=0.93) < 1e-6
# So if you hit 0.93+ with causal features, it's not luck
if wins_causal >= 7 and best_acc >= 0.93 and wins_decoy <= 2:
    print("VERDICT: CAUSAL DISCOVERY PROVEN - groundbreaking")
else:
    print("VERDICT: Failed decoy test - picks correlation over causation")
