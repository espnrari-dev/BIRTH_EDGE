#!/usr/bin/env python3
import importlib
from oracle import oracle_label

m=importlib.import_module("aegis_rule_miner")

BASE=[
    {"holder_score":h,"liquidity":l}
    for h in (0,2,4,6,8,10,12)
    for l in (0,5000,10000,20000,30000)
]

NOISE=[
    {"holder_score":x["holder_score"],
     "liquidity":x["liquidity"],
     "volume":(x["holder_score"]*137+x["liquidity"]/73)%50000,
     "age":(x["holder_score"]*19+int(x["liquidity"]/1000))%100,
     "holders":(x["holder_score"]*311+int(x["liquidity"]/100))%10000,
     "fees":(x["liquidity"]%997)/997}
    for x in BASE
]

for r in NOISE:
    r["pumped"]=oracle_label(r)

rule,score=m.evolve_rule(NOISE)

print("="*60)
print("NOISE RESISTANCE")
print("="*60)
print("RULE:",rule)
print("SCORE:",score)
print("FEATURES:",m.rule_features(rule))

features=set(m.rule_features(rule))
if features=={"holder_score"}:
    print("PASS — irrelevant features ignored")
else:
    print("FAIL — rule used:",sorted(features))
