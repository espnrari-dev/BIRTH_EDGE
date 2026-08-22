#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"

echo "Restoring clean learning DB from backup"
cp data/learning.db.bak data/learning.db

echo "Injecting adversarial examples"
python3 prepare_l6_dataset.py

echo "Building L6 evidence (seed 0)"
SEED=0 python3 build_level6_fixed.py
