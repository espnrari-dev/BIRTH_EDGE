import json, shutil, tempfile, sqlite3
from pathlib import Path
import hash_logger

ROOT = Path(__file__).parent
import sys
sys.path.insert(0, str(ROOT))
import ml_model

FEATURE_NAMES = ["liquidity_usd","holder_score","dev_score","lp_lock_score","tax_score","overall_score"]

def clone_root_fresh():
    tmp = Path(tempfile.mkdtemp(prefix="birth_edge_causal_v3_"))
    (tmp / "data").mkdir(parents=True)
    # Fresh DB - don't copy old 67 rows
    db_path = tmp / "data" / "learning.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_results (
            addr TEXT PRIMARY KEY, chain TEXT, symbol TEXT,
            initial_price_usd REAL, initial_liquidity_usd REAL,
            overall_score INTEGER, holder_score REAL, dev_score REAL,
            lp_lock_score REAL, tax_score REAL, discovered_at TEXT,
            final_price_usd REAL, rug_pulled INTEGER DEFAULT 0,
            pumped INTEGER DEFAULT 0, updated_at TEXT, price_change_24h REAL
        )
    """)
    conn.commit()
    conn.close()
    return tmp

def train_history_real(clone, history):
    db_path = clone / "data" / "learning.db"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    conn.execute("DELETE FROM learning_results")
    for h in history:
        cur.execute("""INSERT OR REPLACE INTO learning_results
        (addr, chain, symbol, initial_price_usd, initial_liquidity_usd,
         overall_score, holder_score, dev_score, lp_lock_score, tax_score,
         pumped, rug_pulled, discovered_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (h["address"], "sol", h["symbol"], 0.01, h["liq"],
         h["overall"], h["holder_score"], h.get("dev_score",50), 50, 50,
         1 if "PUMP" in h["symbol"] else 0,
         1 if "RUG" in h["symbol"] else 0,
         "2026-08-22T00:00:00"))
    conn.commit()
    conn.close()

    model_path = clone / "ml_model.json"
    model = ml_model.OnlineLogisticRegression(FEATURE_NAMES)

    for h in history:
        feat_list = [h["liq"], h["holder_score"], h.get("dev_score",50), 50, 50, h["overall"]]
        label = 1 if "PUMP" in h["symbol"] else 0
        model.update(feat_list, label)

    model.save(str(model_path))
    print(f"Clone {clone.name} trained {len(history)} rows -> weights {model.weights[:3]} bias {model.bias:.4f} count {model.count}")

def predict_real(clone, future):
    model = ml_model.OnlineLogisticRegression.load(str(clone / "ml_model.json"))
    preds = []
    for token in future:
        feat_list = [token["liq"], token["holder_score"], token.get("dev_score",50), 50, 50, token["overall"]]
        prob = model.predict_proba(feat_list)
        preds.append(float(prob))
    return preds, model

H_A = [{"symbol":"PUMP_WIN","liq":50000,"holder_score":95,"overall":90,"address":"0xAAA_PUMP","dev_score":90}] * 15
H_B = [{"symbol":"RUG_LOSS","liq":1000,"holder_score":10,"overall":20,"address":"0xBBB_RUG","dev_score":10}] * 15
FUTURE = [{"symbol":"TEST","liq":20000,"holder_score":60,"overall":60,"dev_score":50}]

clone_a = clone_root_fresh()
clone_b = clone_root_fresh()

print("\n=== Clone A pump history ===")
train_history_real(clone_a, H_A)
pred_a, model_a = predict_real(clone_a, FUTURE)

print("\n=== Clone B rug history ===")
train_history_real(clone_b, H_B)
pred_b, model_b = predict_real(clone_b, FUTURE)

print(f"\nClone A pred: {pred_a} weights: {model_a.weights}")
print(f"Clone B pred: {pred_b} weights: {model_b.weights}")
divergence = abs(pred_a[0]-pred_b[0]) > 0.01
print(f"DIVERGENCE: {divergence} diff={abs(pred_a[0]-pred_b[0]):.4f}")

hash_logger.log_hash("H_A", H_A)
hash_logger.log_hash("H_B", H_B)
hash_logger.log_hash("PRED_A", pred_a)
hash_logger.log_hash("PRED_B", pred_b)
hash_logger.log_hash("MODEL_A", {"weights": model_a.weights, "bias": model_a.bias, "count": model_a.count})
hash_logger.log_hash("MODEL_B", {"weights": model_b.weights, "bias": model_b.bias, "count": model_b.count})
hash_logger.log_hash("DIVERGENCE", divergence)

if divergence:
    print("\nVERDICT: ADAPTIVE BEHAVIOR DEMONSTRATED - real learning code, opposite histories, same future, different prediction")
else:
    print("\nVERDICT: BEHAVIOR NOT DEMONSTRATED")
