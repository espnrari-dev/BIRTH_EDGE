import os, time, shutil, subprocess, fcntl, sys
BASE="/data/data/com.termux/files/home/BIRTH_EDGE"
DATA=f"{BASE}/data"
BACKUP=f"{BASE}/.backup"
os.makedirs(BACKUP, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

# singleton
LOCK=f"{DATA}/GUARDIAN.lock"
lf=open(LOCK,"w")
try: fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
except: print("guardian already running"); sys.exit(0)

# backup
for f in ["engine.py","HARDCODED_RULE.py","LOCKED_GUARDIAN.py"]:
    try: shutil.copy(f"{BASE}/{f}", f"{BACKUP}/{f}.bak")
    except: pass

while True:
    try:
        os.makedirs(DATA, exist_ok=True)
        for f in ["engine.py","HARDCODED_RULE.py","LOCKED_GUARDIAN.py"]:
            p=f"{BASE}/{f}"; b=f"{BACKUP}/{f}.bak"
            if not os.path.exists(p) and os.path.exists(b):
                shutil.copy(b,p)
                print(f"RESTORED {f}")

        for f in [f"{DATA}/balance.json", f"{DATA}/treasury.jsonl"]:
            if not os.path.exists(f): open(f,"a").close()

        # keep alive - no chattr inside loop
        for pat, target in [("BIRTH_EDGE/engine.py", f"{BASE}/engine.py"), ("HARDCODED_RULE.py", f"{BASE}/HARDCODED_RULE.py")]:
            out=subprocess.run(["pgrep","-f",pat], capture_output=True, text=True)
            if not out.stdout.strip():
                subprocess.Popen(["nohup","python3","-u",target], stdout=open(f"{DATA}/{pat.split('/')[-1].split('.')[0]}.log","a"), stderr=open(f"{DATA}/{pat.split('/')[-1].split('.')[0]}.log","a"), preexec_fn=os.setpgrp)
    except: pass
    time.sleep(10)
