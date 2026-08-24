#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

cd "$HOME/BIRTH_EDGE"

python3 - <<'PY'
import json
import os
import sqlite3

dbs = [
    "data/birth_edge.db",
    "data/learning.db",
    "data/cognition.db",
]

print("=" * 72)
print("BIRTH_EDGE RECONVERGENCE SCHEMA DISCOVERY")
print("=" * 72)

for db in dbs:
    print()
    print("#" * 72)
    print("DATABASE:", db)
    print("#" * 72)

    if not os.path.exists(db):
        print("MISSING")
        continue

    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    tables = con.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    for table_row in tables:
        table = table_row["name"]

        print()
        print("-" * 72)
        print("TABLE:", table)

        cols = con.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()

        print("COLUMNS:")

        for col in cols:
            print(
                f"  {col['name']} | "
                f"{col['type'] or 'UNKNOWN'}"
            )

        count = con.execute(
            f'SELECT COUNT(*) AS n FROM "{table}"'
        ).fetchone()["n"]

        print("ROW_COUNT:", count)

        if count > 0:
            rows = con.execute(
                f'SELECT * FROM "{table}" LIMIT 3'
            ).fetchall()

            print("SAMPLE_ROWS:")

            for index, row in enumerate(rows, 1):
                print(
                    f"  ROW_{index}:",
                    json.dumps(
                        dict(row),
                        default=str,
                        sort_keys=True,
                    )
                )

    con.close()

print()
print("#" * 72)
print("JSON STRUCTURE")
print("#" * 72)

for path in [
    "data/ml_model.json",
    "data/ml_memory.json",
    "data/ml_reflection.json",
]:
    print()
    print("FILE:", path)

    if not os.path.exists(path):
        print("MISSING")
        continue

    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if isinstance(payload, dict):
            print("TOP_LEVEL_KEYS:", sorted(payload.keys()))

            for key, value in payload.items():
                if isinstance(value, list):
                    print(
                        f"LIST {key}:",
                        len(value)
                    )

                    if value:
                        print(
                            "FIRST_ITEM:",
                            json.dumps(
                                value[0],
                                default=str,
                                sort_keys=True,
                            )[:3000]
                        )

                elif isinstance(value, dict):
                    print(
                        f"DICT {key}:",
                        "keys=",
                        sorted(value.keys())
                    )

                else:
                    print(
                        f"VALUE {key}:",
                        repr(value)[:500]
                    )

        elif isinstance(payload, list):
            print("LIST_LENGTH:", len(payload))

            if payload:
                print(
                    "FIRST_ITEM:",
                    json.dumps(
                        payload[0],
                        default=str,
                        sort_keys=True,
                    )[:3000]
                )

        else:
            print(
                "TYPE:",
                type(payload).__name__
            )

    except Exception as exc:
        print(
            "READ_ERROR:",
            repr(exc)
        )

print()
print("=" * 72)
print("DISCOVERY COMPLETE — NO DATA MODIFIED")
print("=" * 72)
PY
