#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
python3 apex_daemon.py --once
python3 -c '
from AEGIS_audit import audit
audit("HEAL_CYCLE", {"trigger": "manual"})
print("heal cycle logged")
'
