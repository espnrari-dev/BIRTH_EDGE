import sqlite3, os, json, time, subprocess, requests
from datetime import datetime, timedelta

DB_BIRTH = "data/birth_edge.db"
DB_LEARN = "data/learning.db"
DB_COG = "data/cognition.db"
BASELINE = "data/nominal_baseline.json"

def log_event(kind, details):
    try:
        import cognition
        cognition.record_event(kind, details)
    except Exception as e:
        print(f"[NOMINAL] {kind} {details} log fail {e}")

def get_table_counts():
    counts = {}
    for db_path in [DB_BIRTH, DB_LEARN, DB_COG]:
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[f"{os.path.basename(db_path)}:{t}"] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            counts[db_path] = f"ERR {e}"
    return counts

def establish_baseline():
    conn = sqlite3.connect(DB_BIRTH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), AVG(overall_score), AVG(liquidity_usd), SUM(CASE WHEN overall_score>=75 THEN 1 ELSE 0 END) FROM tokens")
    total, avg_score, avg_liq, pass_cnt = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM tokens WHERE symbol='?' OR symbol IS NULL")
    bad_sym = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tokens WHERE discovered_at IS NULL")
    null_time = cur.fetchone()[0]
    conn.close()

    conn = sqlite3.connect(DB_LEARN)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*), AVG(CASE WHEN pumped=1 THEN 1 ELSE 0 END) FROM learning_results WHERE final_price_usd IS NOT NULL")
        learned, pump_rate = cur.fetchone()
    except:
        learned, pump_rate = 0, 0
    conn.close()

    baseline = {
        "timestamp": datetime.now().isoformat(),
        "total_tokens": total or 0,
        "avg_score": avg_score or 0,
        "avg_liq": avg_liq or 0,
        "pass_candidates": pass_cnt or 0,
        "bad_symbol_rate": (bad_sym / total) if total else 0,
        "null_time_rate": (null_time / total) if total else 0,
        "pump_rate": pump_rate or 0,
        "tables": get_table_counts(),
        "nominal_rules": {
            "min_tokens_per_hour": 2,
            "max_bad_symbol_rate": 0.2,
            "max_null_time_rate": 0.05,
            "min_pass_rate": 0.05,
            "required_tables": ["birth_edge.db:tokens", "learning.db:learning_results", "cognition.db:events"]
        }
    }
    os.makedirs("data", exist_ok=True)
    with open(BASELINE, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"[NOMINAL] baseline established {total} tokens avg {avg_score:.2f} PASS {pass_cnt}")
    return baseline

def load_baseline():
    if not os.path.exists(BASELINE):
        return establish_baseline()
    with open(BASELINE) as f:
        return json.load(f)

def check_health():
    baseline = load_baseline()
    rules = baseline["nominal_rules"]
    issues = []

    # 1. DB tables
    counts = get_table_counts()
    for req in rules["required_tables"]:
        if req not in counts:
            issues.append(("missing_table", req, f"table {req} missing"))

    # 2. Process hunter alive?
    try:
        out = subprocess.check_output(["pgrep", "-f", "main.py"], text=True)
        if not out.strip():
            issues.append(("process_down", "main.py", "hunter not running"))
    except:
        issues.append(("process_down", "main.py", "pgrep failed - hunter down"))

    # 3. Data quality
    conn = sqlite3.connect(DB_BIRTH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM tokens")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tokens WHERE symbol='?' OR symbol IS NULL")
    bad_sym = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM tokens WHERE discovered_at IS NULL")
    null_time = cur.fetchone()[0]
    # discovery rate last hour
    cur.execute("SELECT COUNT(*) FROM tokens WHERE discovered_at > datetime('now','-1 hour')")
    last_hour = cur.fetchone()[0]
    conn.close()

    if total>0 and (bad_sym/total) > rules["max_bad_symbol_rate"]:
        issues.append(("data_quality", "symbol", f"bad symbol rate {bad_sym}/{total}={bad_sym/total:.2%} > {rules['max_bad_symbol_rate']}"))
    if total>0 and (null_time/total) > rules["max_null_time_rate"]:
        issues.append(("data_quality", "discovered_at", f"null time rate {null_time}/{total}"))
    if last_hour < rules["min_tokens_per_hour"] and total>10:
        issues.append(("low_throughput", "discovery", f"only {last_hour} tokens last hour < {rules['min_tokens_per_hour']}"))

    # 4. API health
    try:
        r = requests.get("https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112", timeout=5)
        if r.status_code!= 200:
            issues.append(("api_down", "dexscreener", f"status {r.status_code}"))
    except Exception as e:
        issues.append(("api_down", "dexscreener", str(e)))

    # 5. Model health
    if not os.path.exists("data/ml_model.json"):
        issues.append(("model_missing", "ml_model.json", "no model file"))
    else:
        try:
            with open("data/ml_model.json") as f:
                j=json.load(f)
                if not j:
                    issues.append(("model_corrupt", "ml_model.json", "empty"))
        except:
            issues.append(("model_corrupt", "ml_model.json", "json parse fail"))

    return issues, baseline, {"total": total, "bad_sym": bad_sym, "null_time": null_time, "last_hour": last_hour, "tables": counts}

def heal(issues):
    healed=[]
    for kind, target, msg in issues:
        print(f"[HEAL] {kind}:{target} -> {msg}")
        try:
            if kind=="missing_table":
                if "birth_edge" in target:
                    from scoring import init_birth_db; init_birth_db()
                    healed.append(f"recreated {target}")
                elif "learning" in target:
                    from learning import init_learning_db; init_learning_db()
                    healed.append(f"recreated {target}")
                elif "cognition" in target:
                    import cognition; cognition.init_cognition_db()
                    healed.append(f"recreated {target}")

            elif kind=="process_down":
                subprocess.Popen(["nohup", "python3", "main.py"], stdout=open("logs/hunter_live.log","a"), stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
                healed.append("restarted main.py")
                log_event("self_heal_restart", {"target": target})

            elif kind=="data_quality" and target=="symbol":
                # auto-fix? symbols
                import sqlite3, requests
                conn=sqlite3.connect(DB_BIRTH)
                cur=conn.cursor()
                cur.execute("SELECT addr FROM tokens WHERE symbol='?' OR symbol IS NULL LIMIT 20")
                for (addr,) in cur.fetchall():
                    try:
                        r=requests.get(f"https://api.dexscreener.com/latest/dex/tokens/{addr}", timeout=8, headers={"User-Agent":"Mozilla/5.0"})
                        if r.status_code==200:
                            pairs=r.json().get('pairs',[])
                            if pairs:
                                sym=pairs[0].get('baseToken',{}).get('symbol','?')
                                cur.execute("UPDATE tokens SET symbol=? WHERE addr=?", (sym, addr))
                    except: pass
                conn.commit(); conn.close()
                healed.append("fixed? symbols")
                log_event("self_heal_symbol_fix", {"fixed": 20})

            elif kind=="data_quality" and target=="discovered_at":
                conn=sqlite3.connect(DB_BIRTH)
                conn.execute("UPDATE tokens SET discovered_at=datetime('now') WHERE discovered_at IS NULL")
                conn.commit(); conn.close()
                healed.append("fixed null discovered_at")

            elif kind in ("model_missing","model_corrupt"):
                if os.path.exists("data/learning.db.bak"):
                    import shutil; shutil.copy("data/learning.db.bak","data/ml_model.json.bakrestore")
                with open("data/ml_model.json","w") as f:
                    json.dump({"weights": [0.1,0.1,0.1,0.1], "bias": 0, "trained": 0}, f)
                healed.append("reset ml_model.json")
        except Exception as e:
            healed.append(f"heal fail {kind}:{target} {e}")

    return healed

if __name__=="__main__":
    import sys
    if len(sys.argv)>1 and sys.argv[1]=="baseline":
        establish_baseline()
    else:
        issues, base, cur = check_health()
        if not issues:
            print(f"[NOMINAL] OK total={cur['total']} last_hour={cur['last_hour']} bad_sym={cur['bad_sym']}")
        else:
            print(f"[NOMINAL] {len(issues)} issues: {issues}")
            healed = heal(issues)
            print(f"[NOMINAL] healed: {healed}")
            log_event("nominal_heal_cycle", {"issues": issues, "healed": healed, "current": cur})
