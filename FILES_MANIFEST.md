# BIRTH_EDGE – Canonical File Manifest
## Core files
| File | Purpose |
|------|---------|
| main.py | Entry point: filter loop, realtime Pump.fun, learning, ML, cognition, agent detection, decision engine |
| config.py | Public API endpoints, thresholds, scoring weights |
| filters.py | On-chain safety checks |
| scanners.py | Legacy DexScreener scanners |
| learning.py | Closed-loop outcome tracking and ML training trigger |
| ml_model.py | Online logistic regression model |
| cognition.py | World map, agent map, memory importance, wisdom, inherent knowledge |
| agent_detection.py | Automatically classify and track creators/agents |
| decision_engine.py | Combines signals into actionable decisions |
| realtime_pumpfun.py | Sub-second Pump.fun token detection via PumpPortal WebSocket |
| aegis_rule_miner.py | Symbolic regression for discovering trading rules from data |
| utils.py | Shared helpers |
| execution.py | Optional trade signal logger |
| requirements.txt | Dependencies |
| FILES_MANIFEST.md | This manifest |
| CURRICULUM.md | Educational curriculum for the whole system |

## Data & Logs
- logs/births.jsonl, filtered.jsonl, katana_targets.jsonl, beacon_gaps.jsonl
- logs/realtime_births.jsonl (Pump.fun realtime events)
- logs/qualified_tokens.jsonl, rejected_tokens.jsonl, learning_report.jsonl
- logs/decisions.jsonl (decision engine output)
- logs/discovered_rules.jsonl (AEGIS rule miner output)
- data/learning.db (outcome database)
- data/cognition.db (world events, agents, memory, wisdom)
- data/ml_model.json (trained ML model weights)
