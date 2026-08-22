#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"

echo "============================================================"
echo "BIRTH_EDGE — TEST SCHEMA INSPECTION"
echo "============================================================"

echo
echo "=== WORLD GENERATION ==="
grep -nE \
  -B 12 -A 80 \
  'MULTI_SIGNAL|def .*world|def .*generate|def .*make_' \
  "$ROOT/definitive_architecture_test.py" |
head -n 300

echo
echo "=== TARGET / LABEL REFERENCES ==="
grep -nE \
  -B 5 -A 8 \
  'target|label|outcome|y_true|y_pred|row\[' \
  "$ROOT/definitive_architecture_test.py" |
head -n 300

echo
echo "=== RULE EVALUATION ==="
grep -nE \
  -B 10 -A 25 \
  'evaluate|matches|rule.*row|predict|fitness' \
  "$ROOT/definitive_architecture_test.py" |
head -n 300

echo
echo "=== MINER RULE EVALUATION ==="
grep -nE \
  -B 8 -A 20 \
  'def .*eval|def .*match|def .*predict|rule.*evaluate|rule.*match' \
  "$ROOT/aegis_rule_miner.py" |
head -n 300

echo
echo "============================================================"
echo "NO FILES MODIFIED"
echo "============================================================"
