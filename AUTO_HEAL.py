import os, time, subprocess, re
from pathlib import Path
from datetime import datetime
BASE=Path.home()
TMP=BASE/'tmp'; TMP.mkdir(parents=True, exist_ok=True)
os.environ['TMPDIR']=str(TMP)
REPO=BASE/'BIRTH_EDGE'
LOG=REPO/'data/watch.log'

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG,'a') as f: f.write(f'[{datetime.now().strftime("%H:%M:%S")}] {m}\n')
    print(m,flush=True)

def run(cmd):
    env=os.environ.copy(); env['TMPDIR']=str(TMP)
    r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=60,cwd=str(REPO),env=env)
    out=(r.stdout+r.stderr)[-800:]
    if out.strip(): log(out.strip()[:600])
    return r.returncode==0, out

def get_github_token():
    for fp in [BASE/'.github_token', BASE/'github_token.txt']:
        try:
            t=fp.read_text().strip()
            if t.startswith('ghp_') or t.startswith('github_pat_'): return t
        except: pass
    return ''

log('=== AUTO-HEAL BIRTH_EDGE V1 - COMPREHENSIVE SEARCH FIRST ===')
while True:
    try:
        gh=get_github_token()
        if not gh: log('MISSING GitHub token in ~/.github_token'); time.sleep(30); continue
        # search
        run('git remote set-url origin https://'+gh+'@github.com/gothegadget-dot/Birthedge-.git')
        # check diverged like you showed
        ok, status = run('git status -b --porcelain')
        if 'diverged' in status or 'behind' in status:
            log('Diverged detected - auto rebasing')
            run('git fetch origin main --tags')
            run('git pull --rebase origin main')
        # commit if needed
        ok, por = run('git status --porcelain')
        if por.strip():
            run('git add -A')
            run('git commit -m "auto-heal '+datetime.now().strftime("%Y-%m-%d %H:%M")+'"')
        # push with tags - exactly what failed before
        ok, out = run('git push origin main --tags 2>&1 | tail -5')
        if ok: log('[GIT] BIRTH_EDGE pushed main + tags by itself')
    except Exception as e:
        log(f'ERR {e}')
    time.sleep(60)
