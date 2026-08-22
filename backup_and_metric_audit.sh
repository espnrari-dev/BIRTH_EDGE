#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="$ROOT/backups/definitive_$STAMP"

mkdir -p "$BACKUP"

echo "============================================================"
echo "BIRTH_EDGE — PRE-AUDIT BACKUP"
echo "============================================================"
echo "Backup: $BACKUP"
echo

# Core source
for f in \
    aegis_rule_miner.py \
    definitive_architecture_test.py \
    definitive_architecture_test_v2.log
do
    if [ -f "$ROOT/$f" ]; then
        cp -p "$ROOT/$f" "$BACKUP/"
        echo "BACKUP  $f"
    fi
done

# All Python source files involved in the current architecture
find "$ROOT" -maxdepth 1 -type f -name '*.py' -print0 |
while IFS= read -r -d '' f; do
    cp -p "$f" "$BACKUP/"
done

# Existing logs/results
find "$ROOT" -maxdepth 1 -type f \
    \( -name '*.log' -o -name '*.json' -o -name '*.txt' \) \
    -print0 |
while IFS= read -r -d '' f; do
    cp -p "$f" "$BACKUP/" 2>/dev/null || true
done

# Record exact source hashes
(
    cd "$ROOT"
    sha256sum *.py *.log 2>/dev/null || true
) > "$BACKUP/SOURCE_HASHES.sha256"

echo
echo "Backup complete."
echo

echo "============================================================"
echo "BALANCED-ACCURACY AUDIT"
echo "============================================================"

echo
echo "[1] Locate every balanced-accuracy implementation:"
grep -RniE \
    'balanced_accuracy|balanced.?acc|recall_score|confusion_matrix' \
    "$ROOT" \
    --include='*.py' \
    --exclude-dir=backups \
    2>/dev/null || true

echo
echo "[2] Locate metric aggregation/reporting:"
grep -RniE \
    'mean_held_out_balanced|held_out_balanced|balanced' \
    "$ROOT" \
    --include='*.py' \
    --exclude-dir=backups \
    2>/dev/null || true

echo
echo "[3] Inspect relevant test sections:"
grep -nE \
    -B 8 -A 18 \
    'balanced_accuracy|held_out_balanced_accuracy' \
    "$ROOT/definitive_architecture_test.py" \
    2>/dev/null || true

echo
echo "============================================================"
echo "BACKUP LOCATION"
echo "============================================================"
echo "$BACKUP"

echo
echo "============================================================"
echo "AUDIT COMPLETE — NO SOURCE MODIFIED"
echo "============================================================"
