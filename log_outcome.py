import json, os, sys, datetime
ROOT=os.path.expanduser("~/BIRTH_EDGE")
REF=os.path.join(ROOT,"data/ml_reflection.json")
CFG=os.path.join(ROOT,"data/production_config.json")
MODEL=os.path.join(ROOT,"data/ml_model_production.json")

def load_json(p):
    with open(p) as f: return json.load(f)

def save_json(p, data):
    with open(p,'w') as f: json.dump(data,f,indent=2)

# Usage: python3 log_outcome.py '<source_features_json>' wisdom_score actual_outcome [symbol]
# example: python3 log_outcome.py '[0.8,0.2,0.5,0.9]' 0.75 1 SPROUT

if len(sys.argv) < 4:
    print("usage: log_outcome.py '[f1,f2,f3,f4]' wisdom_score actual_outcome [symbol]")
    sys.exit(1)

source_features=json.loads(sys.argv[1])
wisdom=float(sys.argv[2])
actual=float(sys.argv[3])
symbol=sys.argv[4] if len(sys.argv)>4 else ""

# load model to get model prediction
m=load_json(MODEL)
# simple dot product if model is logistic: uses weights
try:
    import math
    w=m.get('weights', m.get('coefficients', []))
    b=m.get('bias', m.get('intercept', 0))
    if w:
        logit=sum(float(a)*float(b) for a,b in zip(source_features,w))+float(b)
        prob=1/(1+math.exp(-logit))
    else:
        prob=float(m.get('predict',0))
except:
    prob=0.0

entry={
  "timestamp": datetime.datetime.utcnow().isoformat()+"Z",
  "symbol": symbol,
  "model_replay": {"source_features": source_features, "model_prediction": prob},
  "wisdom_score": wisdom,
  "actual_outcome": actual,
  "source": "manual_log"
}

data=load_json(REF)
if isinstance(data, dict) and 'reflections' in data:
    data['reflections'].append(entry)
else:
    data.append(entry)
save_json(REF, data)

# update counter
cfg=load_json(CFG)
positives=sum(1 for r in (data['reflections'] if isinstance(data,dict) else data) if float(r.get('actual_outcome',0))>=0.5)
cfg['positive_examples_current']=positives
cfg['remaining']=max(0,30-positives)
save_json(CFG, cfg)

print(f"logged {symbol} actual={actual} model={prob:.3f} wisdom={wisdom} -> positives {positives}/30 remaining {cfg['remaining']}")
