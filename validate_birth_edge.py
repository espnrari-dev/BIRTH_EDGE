#!/usr/bin/env python3
import importlib
import json
from oracle import oracle_label

TRAIN=[
    {"holder_score":h,"liquidity":l}
    for h in (0,2,4,6,8,10,12)
    for l in (0,5000,10000,20000,30000)
]

TEST=[
    {"holder_score":h,"liquidity":l}
    for h in (1,3,5,7,9,11,13)
    for l in (2500,7500,15000,25000,35000)
]

def main():
    m=importlib.import_module("aegis_rule_miner")

    train=[dict(x,pumped=oracle_label(x)) for x in TRAIN]

    print("="*72)
    print("BIRTH_EDGE RULE VALIDATION")
    print("="*72)

    result=m.evolve_rule(train)

    if isinstance(result,tuple):
        rule=result[0]
        discovered_score=result[1] if len(result)>1 else None
    else:
        rule=result
        discovered_score=None

    print("DISCOVERED RULE:")
    print(rule)

    if discovered_score is not None:
        print("DISCOVERY SCORE:",discovered_score)

    def predict(row):
        features=m.extract_features(row)
        return int(bool(rule.evaluate(features)))

    def score(rows):
        good=0
        for row in rows:
            good += predict(row)==oracle_label(row)
        return good/len(rows)

    train_acc=score(TRAIN)
    test_acc=score(TEST)

    print()
    print("TRAIN ACCURACY   :",f"{train_acc:.4f}")
    print("HELD-OUT ACCURACY:",f"{test_acc:.4f}")

    tp=tn=fp=fn=0
    for row in TEST:
        p=predict(row)
        t=oracle_label(row)
        if t and p: tp+=1
        elif not t and not p: tn+=1
        elif not t and p: fp+=1
        else: fn+=1

    print(f"TP={tp} TN={tn} FP={fp} FN={fn}")

    print()
    print("DISCOVERED FEATURES:",m.rule_features(rule))

    print()
    print("="*72)
    print("VERDICT")
    print("="*72)

    if test_acc>=0.95:
        print("PASS — strong held-out recovery")
    elif test_acc>=0.80:
        print("PARTIAL — meaningful held-out recovery")
    else:
        print("FAIL — insufficient recovery")

if __name__=="__main__":
    main()
