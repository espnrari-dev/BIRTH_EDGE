# Controlled Causal Test V3 FIXED - Real Code

Date: 2026-08-22 02:02:48
Harness: decisive_adaptive_test_v3_fixed4.py
Fix: Fresh clones (no 67-row copy), feature list [liq, holder, dev, lp, tax, overall], update(list) not dict

H_A: 15x PUMP_WIN 50k liq 95 holder
H_B: 15x RUG_LOSS 1k liq 10 holder
FUTURE: TEST 20k liq 60 holder identical for both

Result:
Clone A weights [249.96, 0.474, 0.449] bias +0.0737 -> 0.5184
Clone B weights [-4.99, -0.049, -0.049] bias -0.0737 -> 0.4815
Diff 0.0368 divergence True

Hashes:
MODEL_A 83e06b2832be9e8c
MODEL_B f8694fdecc748dae
DIVERGENCE b5bea41b6c623f7c true

Verdict: ADAPTIVE BEHAVIOR DEMONSTRATED with real ml_model.py
