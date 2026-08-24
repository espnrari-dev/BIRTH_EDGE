import json, shutil, os
ROOT="~/BIRTH_EDGE"
# lock the model that gave tp=6 tn=89
shutil.copy(os.path.expanduser(f"{ROOT}/data/ml_model.json"), os.path.expanduser(f"{ROOT}/data/ml_model_production.json"))
config={
  "mode": "logging",
  "model": "data/ml_model_production.json",
  "positive_examples_current": 6,
  "positive_examples_needed": 30,
  "note": "Collect real positives. No retrain until >=30. Lower labeling threshold only if you decide as business owner."
}
with open(os.path.expanduser(f"{ROOT}/data/production_config.json"),"w") as h:
    json.dump(config,h,indent=2)
print("Locked production model. Now in logging mode. Need 24 more real positives.")
