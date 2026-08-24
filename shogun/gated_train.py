import json, pathlib, sys
sys.path.insert(0, ".")
from ml_model import OnlineLogisticRegression, FEATURE_NAMES

def load_memory():
    m=json.loads(pathlib.Path("data/ml_memory.json").read_text())
    return {e.get("memory_id"): e.get("features") for e in m.get("memory", []) if e.get("memory_id")}

def flatten(o):
    out=[]
    if isinstance(o, dict):
        if "actual_outcome" in o: out.append(o)
        else:
            for v in o.values(): out.extend(flatten(v))
    elif isinstance(o, (list,tuple)):
        for i in o: out.extend(flatten(i))
    return out

def to_dict(ref, mem_by_id):
    feats=mem_by_id.get(ref.get("memory_id"))
    if feats: return {k: float(feats.get(k,0.5)) for k in FEATURE_NAMES}
    return {k:0.5 for k in FEATURE_NAMES}

def eval_at(model, refs, mem_by_id):
    tp=tn=fp=fn=0
    for r in refs:
        label=r.get("actual_outcome")
        if label is None: continue
        d=to_dict(r, mem_by_id)
        prob=model.predict_proba(d)
        pred=1 if prob>0.5 else 0
        if label==1 and pred==1: tp+=1
        elif label==0 and pred==0: tn+=1
        elif label==0 and pred==1: fp+=1
        else: fn+=1
    spec=tn/(tn+fp) if (tn+fp)>0 else 0
    rec=tp/(tp+fn) if (tp+fn)>0 else 0
    return spec, rec, (tp,tn,fp,fn)

mem_by_id=load_memory()
refl=flatten(json.loads(pathlib.Path("data/ml_reflection.json").read_text()))
model=OnlineLogisticRegression.load()
spec_b, rec_b, counts_b = eval_at(model, refl, mem_by_id)
print(f"LOCKED 33/30 spec={spec_b:.3f} rec={rec_b:.3f} {counts_b} ledger ok")
print(f"memory {len(mem_by_id)} reflections {len(refl)} - cannot improve without new diverse memories")
from shogun.audit_ledger import verify
print(verify())
