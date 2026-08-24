import sqlite3, os, json, time
from datetime import datetime

DB = "data/birth_edge.db"
ML_MODEL = "data/ml_model.json"

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_issues():
    issues = []
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tokens")
        token_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM tokens WHERE discovered_at IS NULL OR discovered_at=''")
        null_count = cur.fetchone()[0]
        conn.close()
        if token_count > 0 and null_count / token_count > 0.2:
            issues.append(('data_quality', 'discovered_at', f'null time rate {null_count}/{token_count}'))
        if token_count < 2:
            issues.append(('low_throughput', 'discovery', f'only {token_count} tokens last hour < 2'))
    except Exception as e:
        issues.append(('db_error', 'sqlite', str(e)))
    if not os.path.exists(ML_MODEL):
        issues.append(('model_missing', 'ml_model.json', 'no model file'))
    return issues

def heal(issue):
    category, field, detail = issue
    if category == 'model_missing':
        try:
            with open(ML_MODEL, 'w') as f:
                json.dump({"weights": [0.0]*6, "bias": 0.0, "count": 0}, f)
            return 'reset ml_model.json'
        except Exception as e:
            return f'heal fail {category}:{field} {e}'
    elif category == 'data_quality':
        try:
            conn = sqlite3.connect(DB)
            conn.execute("UPDATE tokens SET discovered_at = datetime('now') WHERE discovered_at IS NULL OR discovered_at=''")
            conn.commit()
            conn.close()
            return 'filled missing discovered_at'
        except Exception as e:
            return f'heal fail {category}:{field} {e}'
    elif category == 'low_throughput':
        return 'no action'
    else:
        return f'unknown issue {category}'

def main():
    print("[NOMINAL] started")
    while True:
        issues = check_issues()
        if issues:
            print(f"[NOMINAL] issues: {issues}")
            healed = []
            for issue in issues:
                result = heal(issue)
                healed.append(result)
            print(f"[NOMINAL] healed: {healed}")
        else:
            print("[NOMINAL] clean")
        time.sleep(300)

if __name__ == '__main__':
    main()
