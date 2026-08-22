# BIRTH_EDGE / SIA v1 - Formal Novelty Claims

## Status: Candidate Historical Novelty - Internal Proof Complete, Prior-Art Search Required

### 1. Tripartite Memory Pipeline (Topology / Episodic / Belief)

**Problem:** LLM agents use single RAG vector DB blending immutable facts (contract, liquidity) with probabilistic beliefs (pump probability) -> context collapse, hallucinated market state.

**Implementation:**
- `birth_edge.db`: `tokens` table addr PK, chain, liquidity_usd, discovered_at - immutable topology
- `learning.db`: `learning_results` addr, initial_liquidity_usd, holder_score, dev_score, overall_score, final_price_usd, pumped, rug_pulled, price_change_24h - chronological episodic
- `cognition.db`: `events` token_birth {addr, liquidity, overall_score} + `memory_importance` - synthesized belief via importance weighting

Enforcement: `learning.record_token()` -> `cognition.record_event()` same tx (learning.py:51). Belief derived from topology+episodic.

**Claim Strength:** 7/10 candidate novel for token discovery hunter. Not unprecedented as pattern (CQRS/Event Sourcing), novel application to anti-hallucination market agent.

**Prior-Art Search Terms:** "token discovery cognition ledger importance", "solana mint base64 decode hunter sqlite", "market agent separate topology episodic belief stores"

### 2. Clone-Based Counterfactual Testing (LTEE-inspired) + Adversarial Augmentation

**Problem:** Unit tests `assert f(x)=y` inadequate for adaptive systems requiring `f(x|H_A) != f(x|H_B)`.

**Implementation V3 Fixed4:**
- Fresh clones: DELETE FROM learning_results, new OnlineLogisticRegression(FEATURE_NAMES) count 0
- H_A 15x PUMP_WIN 50k liq 95 holder 90 overall, H_B 15x RUG_LOSS 1k liq 10 holder 20 overall
- Same FUTURE TEST 20k liq 60 holder
- Real SGD `update([liq,holder,dev,lp,tax,overall],label)` `predict_proba([...])`

**Empirical Proof Commit 4b49fd6:**
Clone A weights [249.965,0.474,0.449,0.249,0.249,0.449] bias +0.0737 -> 0.5184171357035481
Clone B weights [-4.99,-0.049,-0.049,-0.249,-0.249,-0.099] bias -0.0737 -> 0.481582864296452
Diff 0.0368 divergence True hashes MODEL_A 83e06b2832be9e8c MODEL_B f8694fdecc748dae DIVERGENCE b5bea41b6c623f7c

**L6 Adversarial Extension Commit b5bfab6 + 219e8276:**
4 high-score rugs (85+ overall but rug_pulled=1 price_change -95) + 4 low-score pumps (55- overall but pumped=1 price_change +200)
Total 74 rows 14 pumped 5 rug, train 59 holdout 15 seed 0
Model 0.9333 tp2 fp1 tn12 fn0 vs baseline75 0.8 tp0 fp1 tn12 fn2 improvement +0.1333 PASS
Proves model catches low-score pumps baseline misses.

**Claim Strength:** 8/10 candidate novel methodology for financial agents. LTEE + concept drift testing exists, 4-part spec immediate+opposite-history+persistence+decision-path as formal harness novel.

**Prior-Art Search Terms:** "opposite history clone test adaptive market", "adversarial high score rug low score pump baseline", "card counting seed sweep improvement"

### 3. Cryptographic Audit Loop (INPUT->VERSION->CONFIG->EXECUTION->OUTPUT->HASH->INTERPRETATION)

**Problem:** Sense-Think-Act black box, cannot reconstruct state that triggered decision.

**Implementation:** `hash_logger.py` SHA256 every state change before action, `logs/hash_chain.jsonl` sequential.

Chain:
[HASH] H_A cddbc064c8261206 Input History A
[HASH] H_B 6f40a7d6333bfda6 Input History B
[HASH] PRED_A 3780bd62bbfecb77 0.5184
[HASH] PRED_B 35c23c2af47c8cf4 0.4815
[HASH] MODEL_A 83e06b2832be9e8c weights/bias/count
[HASH] MODEL_B f8694fdecc748dae
[HASH] DIVERGENCE b5bea41b6c623f7c true
[HASH] LEVEL6 219e82761550672fc8e89dd684d737084d1d8662d2708ec040734c830362ef1a PASS

**Claim Strength:** 6/10 impl (Merkle chain exists), 8/10 pedagogy (enforcement as evidence loop for financial agents).

**Prior-Art Search Terms:** "evidence-driven curriculum known gaps pedagogy", "hash chain market agent audit"
