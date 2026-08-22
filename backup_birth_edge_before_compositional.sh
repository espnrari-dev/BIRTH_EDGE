#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$HOME/BIRTH_EDGE"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT/backups/pre_compositional_$STAMP"

mkdir -p "$BACKUP_DIR"

FILES=(
    "aegis_rule_miner.py"
    "definitive_architecture_test.py"
)

echo "================================================================"
echo "BIRTH_EDGE — PRE-UPGRADE BACKUP"
echo "================================================================"
echo "Backup directory:"
echo "$BACKUP_DIR"
echo

for file in "${FILES[@]}"; do
    src="$ROOT/$file"

    if [ ! -f "$src" ]; then
        echo "ERROR: Missing required file: $src"
        exit 1
    fi

    cp -p "$src" "$BACKUP_DIR/$file"

    if ! cmp -s "$src" "$BACKUP_DIR/$file"; then
        echo "ERROR: Backup verification FAILED: $file"
        exit 1
    fi

    sha256sum "$src" "$BACKUP_DIR/$file"
    echo "VERIFIED: $file"
    echo
done

{
    echo "BIRTH_EDGE PRE-UPGRADE BACKUP"
    echo "Timestamp: $STAMP"
    echo "Source: $ROOT"
    echo "Backup: $BACKUP_DIR"
    echo
    sha256sum "$BACKUP_DIR"/*
} > "$BACKUP_DIR/BACKUP_MANIFEST.txt"

echo "================================================================"
echo "BACKUP VERIFIED"
echo "================================================================"
echo "Location:"
echo "$BACKUP_DIR"
echo
echo "Files:"
find "$BACKUP_DIR" -maxdepth 1 -type f -printf '%f\n' | sort
echo
echo "No source files were modified."
echo "================================================================"
