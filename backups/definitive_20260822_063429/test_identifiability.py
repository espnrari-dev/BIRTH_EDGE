#!/usr/bin/env python3
import importlib
from oracle import oracle_label

m=importlib.import_module("aegis_rule_miner")

SETS=[
("A",range(0,13,2),[0,5000,10000,20000,30000]),
("B",range(1,14,2),[2500,7500,15000,25000,35000]),
("C",[0,1,3,5,7,9,11,13],[1000,6000,12000,18000,26000,34000]),
("D",[2,4,6,8,10,12],[3000,9000,14000,22000,32000]),
]

for name,hs,ls in SETS:
    rows=[
        {"holder_score":h,"liquidity":l,"pumped":oracle_label(
            {"holder_score":h,"liquidity":l}
        )}
        for h in hs for l in ls
    ]

    result=m.evolve_rule(rows)
    rule=result[0] if isinstance(result,tuple) else result
    score=result[1] if isinstance(result,tuple) and len(result)>1 else None

    print("="*60)
    print("SET",name)
    print("RULE:",rule)
    print("SCORE:",score)
    print("FEATURES:",m.rule_features(rule))
