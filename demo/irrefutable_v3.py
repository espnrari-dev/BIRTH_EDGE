import os, sys, json, shutil, subprocess, tempfile, pathlib
# Use real BIRTH_EDGE ml_model
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) if os.path.basename(os.getcwd())=='demo' else '.')
import ml_model

MODEL_ORIG = ml_model.MODEL_FILE
print(f"[V3] MODEL_FILE={MODEL_ORIG}")
print(f"[V3] API: {dir(ml_model)}")

# Histories - opposite
H_A = [
    {"liquidity_usd": 80000, "holder_score": 28, "dev_score": 18, "lp_lock_score": 18, "tax_score": 14, "overall_score": 85},
    {"liquidity_usd": 90000, "holder_score": 27, "dev_score": 19, "lp_lock_score": 17, "tax_score": 15, "overall_score": 88},
]
H_B = [
    {"liquidity_usd": 6000, "holder_score": 5, "dev_score": 2, "lp_lock_score": 3, "tax_score": 2, "overall_score": 30},
    {"liquidity_usd": 5500, "holder_score": 4, "dev_score": 1, "lp_lock_score": 2, "tax_score": 1, "overall_score": 25},
]
FUTURE = [
    {"liquidity_usd": 50000, "holder_score": 20, "dev_score": 15, "lp_lock_score": 12, "tax_score": 10, "overall_score": 75},
]

def clone_worker(model_path, history_json, future_json):
    """Worker that receives future as list[dict] - FIXED: no double json.loads"""
    # This code runs in subprocess
    code = f'''
import sys, json, os
sys.path.insert(0, "{os.getcwd()}")
import ml_model
ml_model.MODEL_FILE = "{model_path}"
# Ensure clean
if os.path.exists("{model_path}"):
    os.remove("{model_path}")
# Load future - outer loads gives list[dict], inner x IS dict, do NOT json.loads(x)
future = json.loads(sys.argv[1]) # list of dicts - FIXED
history = json.loads(sys.argv[2])
for feat in history:
    ml_model.train_model(feat, 1 if feat["overall_score"]>70 else 0)
preds = [ml_model.predict_pump_probability(f) for f in future]
print(json.dumps({{"preds": preds, "model_path": "{model_path}"}}))
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tf:
        tf.write(code)
        tf_path = tf.name
    result = subprocess.run([sys.executable, tf_path, future_json, history_json], capture_output=True, text=True, timeout=15)
    os.unlink(tf_path)
    if result.returncode!= 0:
        print(f"CLONE FAILED stderr: {result.stderr}")
        print(f"stdout: {result.stdout}")
        return None
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except Exception as e:
        print(f"Parse failed: {e} stdout={result.stdout}")
        return None

# 1. Immediate adaptation - same clone
print("\n=== 1. Immediate adaptation ===")
tmp1 = tempfile.mktemp(suffix='.json')
if os.path.exists(MODEL_ORIG):
    shutil.copy(MODEL_ORIG, tmp1)
ml_model.MODEL_FILE = tmp1
if os.path.exists(tmp1):
    os.remove(tmp1)
pred_before = ml_model.predict_pump_probability(FUTURE[0])
for feat in H_A:
    ml_model.train_model(feat, 1)
pred_after_A = ml_model.predict_pump_probability(FUTURE[0])
print(f"before={pred_before} after training H_A={pred_after_A} changed={pred_before!=pred_after_A}")

# Reset
ml_model.MODEL_FILE = tmp1
if os.path.exists(tmp1):
    os.remove(tmp1)
pred_before2 = ml_model.predict_pump_probability(FUTURE[0])
for feat in H_B:
    ml_model.train_model(feat, 0)
pred_after_B = ml_model.predict_pump_probability(FUTURE[0])
print(f"before={pred_before2} after training H_B={pred_after_B} changed={pred_before2!=pred_after_B}")

# 2. Opposite-history effect - isolated clones
print("\n=== 2. Opposite-history effect (isolated clones) ===")
modelA = tempfile.mktemp(suffix='.json')
modelB = tempfile.mktemp(suffix='.json')
future_json = json.dumps(FUTURE)
resA = clone_worker(modelA, json.dumps(H_A), future_json)
resB = clone_worker(modelB, json.dumps(H_B), future_json)
print(f"Clone A (trained pump) preds: {resA}")
print(f"Clone B (trained rug) preds: {resB}")
if resA and resB:
    print(f"A!= B? {resA['preds']!= resB['preds']} STRONGEST EVIDENCE")

# 3. Persistence across process boundary
print("\n=== 3. Persistence ===")
modelP = tempfile.mktemp(suffix='.json')
# Train in one process
train_code = f'''
import sys, json, os
sys.path.insert(0, "{os.getcwd()}")
import ml_model
ml_model.MODEL_FILE="{modelP}"
if os.path.exists("{modelP}"): os.remove("{modelP}")
for feat in {H_A}:
    ml_model.train_model(feat, 1)
print("trained")
'''
subprocess.run([sys.executable, "-c", train_code], check=True)
# Load in fresh process
load_code = f'''
import sys, json, os
sys.path.insert(0, "{os.getcwd()}")
import ml_model
ml_model.MODEL_FILE="{modelP}"
pred = ml_model.predict_pump_probability({FUTURE[0]})
print(json.dumps({{"pred": pred}}))
'''
r = subprocess.run([sys.executable, "-c", load_code], capture_output=True, text=True)
print(f"Persistence load result: {r.stdout} err: {r.stderr}")
if r.stdout:
    persisted_pred = json.loads(r.stdout.strip().splitlines()[-1])["pred"]
    print(f"Persisted pred after destroy/reload: {persisted_pred} vs pred_after_A={pred_after_A} match={persisted_pred==pred_after_A}")

# Restore
ml_model.MODEL_FILE = MODEL_ORIG
print("\n=== V3 DONE ===")
