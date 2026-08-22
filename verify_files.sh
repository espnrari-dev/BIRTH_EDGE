#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for f in main.py config.py filters.py scanners.py learning.py ml_model.py cognition.py agent_detection.py decision_engine.py realtime_pumpfun.py aegis_rule_miner.py utils.py execution.py requirements.txt FILES_MANIFEST.md CURRICULUM.md; do
    if [ -f "$f" ]; then
        echo "OK   $f"
    else
        echo "MISS $f"
    fi
done
