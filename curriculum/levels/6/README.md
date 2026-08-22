# Level 6 - Scientist - BILLED

**Date:** 2026-08-22
**Rows:** 66 labeled (pumped/rug_pulled), 52 train 14 holdout seed 42
**Model:** OnlineLogisticRegression FEATURE_NAMES 6, count 52, weights [-0.031,-0.365,-0.361,-0.176,-0.142,-0.334] bias -0.28
**Baseline:** overall_score >=75
**Holdout:** acc model 0.5 (tp0 fp7 tn7 fn0) vs baseline 0.8571 (tp0 fp2 tn12 fn0)
**Improvement:** -0.3571
**Hash:** d61450cc5d1eef65c2ba73da562af8c201ebcb98157c2b2c0c8483a9f2cc5a21
**Verdict:** FAIL - baseline beats model. Honest Level 6 - shows model needs more pump samples, currently over-predicts pumps on all-rug holdout.
**Next:** Need balanced dataset, more pumped labels from update_outcomes with 2x criteria, retrain with l2 tuning.

Evidence: logs/evidence/level6/LEVEL6_2026-08-22_021018.json, docs/evidence/LEVEL6_2026-08-22_021018.json
