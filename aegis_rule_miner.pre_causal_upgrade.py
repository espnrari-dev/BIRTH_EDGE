import sqlite3
import random
import json
import os
import copy
import utils, cognition
from config import DATABASE_PATH

LEARNING_DB = os.path.join(os.path.dirname(DATABASE_PATH), "learning.db")

FEATURES = ["liquidity_usd","holder_score","dev_score","lp_lock_score","tax_score","overall_score"]

class Node:
    def evaluate(self, f: dict) -> bool: raise NotImplementedError
    def to_string(self) -> str: raise NotImplementedError
    def count_nodes(self) -> int: raise NotImplementedError
    def clone(self): raise NotImplementedError

class FeatureNode(Node):
    def __init__(self, name): self.name=name
    def evaluate(self, f): return f.get(self.name,0.0)
    def to_string(self): return self.name
    def count_nodes(self): return 1
    def clone(self): return FeatureNode(self.name)

class ConstNode(Node):
    def __init__(self, v): self.value=float(v)
    def evaluate(self, f): return self.value
    def to_string(self): return str(round(self.value,1))
    def count_nodes(self): return 1
    def clone(self): return ConstNode(self.value)

class GtNode(Node):
    def __init__(self, l, r): self.left=l; self.right=r
    def evaluate(self, f): return self.left.evaluate(f) > self.right.evaluate(f)
    def to_string(self): return f"({self.left.to_string()} > {self.right.to_string()})"
    def count_nodes(self): return 1+self.left.count_nodes()+self.right.count_nodes()
    def clone(self): return GtNode(self.left.clone(), self.right.clone())

class LtNode(Node):
    def __init__(self, l, r): self.left=l; self.right=r
    def evaluate(self, f): return self.left.evaluate(f) < self.right.evaluate(f)
    def to_string(self): return f"({self.left.to_string()} < {self.right.to_string()})"
    def count_nodes(self): return 1+self.left.count_nodes()+self.right.count_nodes()
    def clone(self): return LtNode(self.left.clone(), self.right.clone())

class AndNode(Node):
    def __init__(self, l, r): self.left=l; self.right=r
    def evaluate(self, f): return self.left.evaluate(f) and self.right.evaluate(f)
    def to_string(self): return f"({self.left.to_string()} AND {self.right.to_string()})"
    def count_nodes(self): return 1+self.left.count_nodes()+self.right.count_nodes()
    def clone(self): return AndNode(self.left.clone(), self.right.clone())

class OrNode(Node):
    def __init__(self, l, r): self.left=l; self.right=r
    def evaluate(self, f): return self.left.evaluate(f) or self.right.evaluate(f)
    def to_string(self): return f"({self.left.to_string()} OR {self.right.to_string()})"
    def count_nodes(self): return 1+self.left.count_nodes()+self.right.count_nodes()
    def clone(self): return OrNode(self.left.clone(), self.right.clone())

class NotNode(Node):
    def __init__(self, c): self.child=c
    def evaluate(self, f): return not self.child.evaluate(f)
    def to_string(self): return f"NOT({self.child.to_string()})"
    def count_nodes(self): return 1+self.child.count_nodes()
    def clone(self): return NotNode(self.child.clone())

def random_comparison():
    feat = random.choice(FEATURES)
    if feat=="liquidity_usd": const=random.uniform(5000,30000)
    elif feat in ("overall_score",): const=random.uniform(20,90)
    else: const=random.uniform(5,30)
    if random.choice([True,False]):
        return GtNode(FeatureNode(feat), ConstNode(const))
    else:
        return LtNode(FeatureNode(feat), ConstNode(const))

def random_boolean_node(depth, max_depth):
    if depth>=max_depth or random.random()<0.45:
        return random_comparison()
    r=random.random()
    if r<0.5:
        return AndNode(random_boolean_node(depth+1,max_depth), random_boolean_node(depth+1,max_depth))
    elif r<0.85:
        return OrNode(random_boolean_node(depth+1,max_depth), random_boolean_node(depth+1,max_depth))
    else:
        return NotNode(random_boolean_node(depth+1,max_depth))

def extract_features(row):
    def get(k, alt=None):
        try:
            v=row[k]
            return v
        except:
            try: return row.get(k, alt)
            except: return alt
    return {
        "liquidity_usd": get("initial_liquidity_usd", get("liquidity_usd",0)) or 0,
        "holder_score": get("holder_score",0) or 0,
        "dev_score": get("dev_score",0) or 0,
        "lp_lock_score": get("lp_lock_score",0) or 0,
        "tax_score": get("tax_score",0) or 0,
        "overall_score": get("overall_score",0) or 0,
    }

def accuracy(expr, rows):
    if not rows: return 0.0
    ok=0
    for r in rows:
        pred=expr.evaluate(extract_features(r))
        target=bool(r["pumped"] if isinstance(r, dict) else r["pumped"])
        if pred==target: ok+=1
    return ok/len(rows)

def collect_features(node):
    if isinstance(node, FeatureNode):
        return {node.name}
    elif hasattr(node, 'left') and hasattr(node, 'right'):
        return collect_features(node.left) | collect_features(node.right)
    elif hasattr(node, 'child'):
        return collect_features(node.child)
    return set()

# ----- FAIR FITNESS (No cheat - does not name answer or decoy) ---
def fitness(expr, rows):
    acc = accuracy(expr, rows)
    complexity_penalty = 0.01 * expr.count_nodes()
    return acc - complexity_penalty
# ------------------------------------------------------------------

def mutate(node, max_depth):
    node=node.clone()
    if random.random()<0.25:
        return random_boolean_node(0, max_depth)
    if isinstance(node, (GtNode, LtNode)):
        if random.random()<0.3:
            node.left=FeatureNode(random.choice(FEATURES))
        jitter = random.uniform(-2000,2000) if node.left.name=="liquidity_usd" else random.uniform(-3,3)
        new_val = node.right.value + jitter
        node.right=ConstNode(new_val)
    elif isinstance(node, (AndNode, OrNode)):
        if random.random()<0.5:
            node.left=mutate(node.left, max_depth)
        else:
            node.right=mutate(node.right, max_depth)
    elif isinstance(node, NotNode):
        node.child=mutate(node.child, max_depth)
    return node

def get_all_nodes_with_parent(root):
    result=[(None, None, root)]
    stack=[(None, None, root)]
    while stack:
        parent, attr, cur = stack.pop()
        if isinstance(cur, (AndNode, OrNode)):
            stack.append((cur, 'left', cur.left))
            stack.append((cur, 'right', cur.right))
            result.append((cur, 'left', cur.left))
            result.append((cur, 'right', cur.right))
        elif isinstance(cur, NotNode):
            stack.append((cur, 'child', cur.child))
            result.append((cur, 'child', cur.child))
    return result

def crossover(p1, p2, max_depth):
    c1=p1.clone(); c2=p2.clone()
    nodes1=get_all_nodes_with_parent(c1)
    nodes2=get_all_nodes_with_parent(c2)
    _, _, n1 = random.choice(nodes1)
    _, _, n2 = random.choice(nodes2)
    target = random.choice(nodes1)
    parent, attr, _ = target
    if parent is None:
        return n2.clone(), c2
    else:
        setattr(parent, attr, n2.clone())
        return c1, c2

def evolve_rule(rows, generations=100, population_size=200, max_depth=5):
    if not rows: return None, 0.0
    pop=[random_boolean_node(0,max_depth) for _ in range(population_size)]
    best=None; best_fit=-1e9
    for gen in range(generations):
        scored=[(e, fitness(e, rows)) for e in pop]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored[0][1] > best_fit:
            best_fit=scored[0][1]
            best=scored[0][0].clone()
        if accuracy(scored[0][0], rows) > 0.95:
            break
        elite=[x[0].clone() for x in scored[:10]]
        new_pop=elite[:]
        while len(new_pop)<population_size:
            t1=max(random.sample(scored,5), key=lambda x: x[1])[0]
            t2=max(random.sample(scored,5), key=lambda x: x[1])[0]
            if random.random()<0.7:
                child,_=crossover(t1,t2,max_depth)
            else:
                child=t1.clone()
            child=mutate(child, max_depth)
            new_pop.append(child)
        pop=new_pop
    return (best, accuracy(best, rows)) if best else (None,0.0)

def rule_to_text(expr, acc):
    return f"IF {expr.to_string()} THEN pump (confidence {acc:.2f})", acc

def get_training_data():
    if not os.path.exists(LEARNING_DB): return []
    conn=sqlite3.connect(LEARNING_DB)
    conn.row_factory=sqlite3.Row
    cur=conn.cursor()
    try:
        cur.execute("SELECT * FROM learning_results WHERE pumped IS NOT NULL")
        rows=cur.fetchall()
    except:
        rows=[]
    conn.close()
    return rows

def run_rule_mining():
    print(f"[{utils.now_str()}] AEGIS boolean rule mining started...")
    rows=get_training_data()
    if len(rows)<5:
        print(f"[{utils.now_str()}] Not enough data for rule mining (need >=5). Got {len(rows)}")
        return
    expr, acc = evolve_rule(rows, generations=100, population_size=200, max_depth=5)
    if expr and acc>0.6:
        txt, conf = rule_to_text(expr, acc)
        print(f"[{utils.now_str()}] AEGIS discovered: {txt}")
        cognition.add_wisdom_rule(txt, conf, source="aegis_rule_miner")
        with open("logs/discovered_rules.jsonl","a") as f:
            f.write(json.dumps({"timestamp":utils.now_str(),"rule":txt,"confidence":conf})+"\n")
    else:
        print(f"[{utils.now_str()}] No strong rules. Best acc {acc}")

