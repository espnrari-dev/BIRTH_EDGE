# BIRTH_EDGE Formal Technical Specification v1 - Term 1 Semester Project

**What exactly is BIRTH_EDGE?**

**Components:**
- Ingestion: DEX_LATEST_URL=https://api.dexscreener.com/token-profiles/latest/v1 polling every POLL_INTERVAL_FILTERED=30s
- Feature Extraction: filters.py run_all_filters() 5-stage: check_liquidity (>=LIQ_THRESHOLD 5000), check_mint_freeze (Solana base64 decode mint layout offset 0 mint_authority 32 bytes, offset 46 freeze_authority 32 bytes, revoked if all zero), check_holders (Solana getTokenLargestAccounts top10% + dev%, EVM random placeholder), check_tax (Solana Jupiter quote round-trip 0.1 SOL buy/sell simulation, EVM random), check_lp_lock + check_dev_history via RugCheck API https://api.rugcheck.xyz/v1/tokens/{addr}/report
- Cognition: data/cognition.db tables: events (token_birth, token_outcome), agents (address, role, confidence, success/fail), wisdom_rules (seeded: mint not revoked 0.9, top10>35% 0.85, tax>10% 0.95, high liq trap 0.7), memory_importance (rug 0.9, pump 0.8, pct_change*10 + liq_change/100000), inherent_knowledge (mint layout, jupiter url, dexscreener url, scam patterns)
- ML: data/ml_model.json OnlineLogisticRegression, MODEL_FILE, get_model(), predict_pump_probability(features), train_model(features,label) where label=1 if pump else 0
- Decision: decision_engine.py + SCORE_MIN_BUY=75, overall = liq_score (min 20 or 35, int(liq/2500)) + holder + dev + lp + tax, status PASS if >=75 and holder pass and tax pass
- Persistence: data/birth_edge.db tokens table, data/learning.db learning_results (addr PK, chain, symbol, initial_price, initial_liquidity, overall_score, holder/dev/lp/tax scores, discovered_at, final_price, rug_pulled, pumped, price_change_24h), data/cognition.db
- Monitoring: data/live.log Watching X seen, no new >$5000, logs/births.jsonl, qualified_tokens.jsonl, rejected_tokens.jsonl, api.log, FastAPI api.py /v1/tokens/pass /v1/stats on 127.0.0.1:8001

**Data Flow:** Input (DexScreener latest) → ingestion (fetch_json_sync) → feature extraction (run_all_filters) → cognition (record_event) → ML (predict) → decision (overall_score) → persistence (record_token both DBs) → monitoring (live.log, API) → feedback (update_outcomes polls DEX_TOKEN_URL https://api.dexscreener.com/latest/dex/tokens/{}, rug if final_price<=0 or liq<=0, pump if final>=2*initial) → learning (train_model) → updated model

**State:** seen=set() dedup, 3 DBs, MODEL_FILE, inherent knowledge static

**Learning Mechanism:** experience (token birth + later price) → training input (features dict liquidity, holder, dev, lp, tax, overall) → train_model(features,label) → model state (weights in ml_model.json) → persistence mechanism (json file) → get_model() → predict_pump_probability() → decision/output

**Decision Mechanism:** STRONG_ALERT/WATCH/NEUTRAL/AVOID based on overall_score threshold 75, holder pass, tax pass

**Feedback Mechanism:** update_outcomes(min_age_hours=1) cutoff = now -1h, fetches final price, computes importance, updates DB, trains ML, records token_outcome event, retrain_weights scans threshold 50-100 step 5 for best winrate (wins-losses)/len, logs to logs/learning_report.jsonl, aegis_rule_miner.run_rule_mining()

**Evidence:**
- Live operational Level 5 2026-08-22: 8 PASS
  SPROUT 90.48 151k liq → +919%
  BLUECHIP 83.64 105k liq born 00:12:07 → +17749% newest
  Timbothy 82.8 53k → -7.46%
  Words 82.68 65k → +244%
  FLUSH 79.2 61k → +1421%
  CrazyFrog 78.4 52k → +1257%
  MAPLE 76.32 56k born 00:03:25 → +1872% (was 3454%)
  BASESTREET 75.36 38k → +13%
  7/8 pumped, avg >1000% 24h
- But n=8, no baseline, no holdout, no control, survivorship bias, EVM scores random, learning loop not auto-wired

**Limitations:**
- Solana-focused, EVM placeholder random
- No automatic outcome loop in main.py
- No precision/recall calibration
- Wisdom rules seeded not learned (until rule miner)
- No concept drift handling

**Measurable Claims Supported:**
- Can discover tokens within seconds of DexScreener listing
- Can filter mint not revoked via base64 decode
- Can simulate tax via Jupiter
- Can log outcome and compute importance
- Can produce PASS list with live pumps in this window

**Claims Not Supported:**
- overall_score predicts pump generally (needs controlled experiment, baseline)
- wisdom_rules learned (seeded)
- ML improves threshold (not auto-updated)
- Chain-agnostic (EVM random)

**Novel Architectural Characteristics:**
- Dual DB + cognition DB with importance-weighted memory
- Mint check via raw account data not API
- Jupiter round-trip tax sim without holding
- Event sourcing for births/outcomes

**Commercial Applications:**
- Market intelligence API, risk filter, early discovery feed, cognition-as-service
