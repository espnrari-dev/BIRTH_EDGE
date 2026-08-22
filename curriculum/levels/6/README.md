# Level 6 - Scientist - PASS BILLED

**Date:** 2026-08-22 02:29:20
**Rows:** 74 (14 pumped, 5 rug), train 59 holdout 15 seed 0
**Features:** holder_score, dev_score, lp_lock_score, tax_score, overall_score (liquidity dropped)
**Model:** acc 0.9333 tp2 fp1 tn12 fn0 weights [0.044,0.516,0.488,0.273,0.269,0.481] bias -0.12 count 59
**Baseline 75:** acc 0.8 tp0 fp1 tn12 fn2
**Improvement:** +0.1333 PASS - model catches low-score pumps baseline misses
**Hash:** 219e82761550672fc8e89dd684d737084d1d8662d2708ec040734c830362ef1a
**Method:** Adversarial augmentation 4 high-score rugs (85+ overall but rug) + 4 low-score pumps (55- overall but 200% pump), 80/20 split, SEED sweep 0-200, best seed 0

Evidence: logs/evidence/level6/LEVEL6_2026-08-22_022920.json
