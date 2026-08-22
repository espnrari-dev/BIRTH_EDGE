#!/usr/bin/env python3
"""
AEGIS RULE MINER V3 — FAST VALIDATED
Deterministic data-driven conjunction discovery.
"""

import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

FEATURES = [
    "liquidity_usd",
    "holder_score",
    "dev_score",
    "lp_lock_score",
    "tax_score",
    "overall_score",
]

@dataclass(frozen=True)
class Predicate:
    feature: str
    operator: str
    threshold: float

    def evaluate(self, values):
        x = float(values.get(self.feature, 0.0))
        return x > self.threshold if self.operator == ">" else x < self.threshold

    def to_string(self):
        return f"({self.feature} {self.operator} {self.threshold:.6g})"

@dataclass(frozen=True)
class Rule:
    predicates: Tuple[Predicate, ...]

    def evaluate(self, values):
        return all(p.evaluate(values) for p in self.predicates)

    def to_string(self):
        if len(self.predicates) == 1:
            return self.predicates[0].to_string()
        return "(" + " AND ".join(p.to_string() for p in self.predicates) + ")"

    @property
    def complexity(self):
        return len(self.predicates)

Expr = Rule

def extract_features(row):
    out = {}
    for f in FEATURES:
        v = row.get("initial_liquidity_usd", row.get("liquidity_usd", 0.0)) if f == "liquidity_usd" else row.get(f, 0.0)
        try:
            v = float(v)
        except (TypeError, ValueError):
            v = 0.0
        out[f] = v if math.isfinite(v) else 0.0
    return out

def _matrix(rows):
    names = list(FEATURES)
    cols = {f: [] for f in names}
    labels = []
    for row in rows:
        x = extract_features(row)
        for f in names:
            cols[f].append(x[f])
        labels.append(bool(row["pumped"]))
    return names, cols, labels

def _thresholds(values, limit=20):
    vals = sorted(set(values))
    if len(vals) < 2:
        return []
    mids = [(a+b)/2.0 for a,b in zip(vals, vals[1:]) if a != b]
    if len(mids) <= limit:
        return mids
    return [mids[round(i*(len(mids)-1)/(limit-1))] for i in range(limit)]

def _metrics(pred, labels):
    n = len(labels)
    if not n:
        return 0.0, 0.0, 0.0
    tp = tn = fp = fn = 0
    for p, y in zip(pred, labels):
        if y:
            if p: tp += 1
            else: fn += 1
        else:
            if p: fp += 1
            else: tn += 1
    acc = (tp + tn) / n
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    bal = (tpr + tnr) / 2.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    return acc, bal, prec

def _support(pred):
    return sum(pred) / len(pred) if pred else 0.0

def _candidate_score(pred, labels, complexity):
    acc, bal, prec = _metrics(pred, labels)
    support = _support(pred)
    penalty = 0.012 * max(0, complexity - 1)
    if support < 0.05:
        penalty += (0.05 - support) * 2.0
    return 0.45*acc + 0.40*bal + 0.15*prec - penalty, acc, bal

def _predicates(cols, active):
    out = []
    for f in active:
        for t in _thresholds(cols[f]):
            for op in (">", "<"):
                p = tuple(x > t if op == ">" else x < t for x in cols[f])
                out.append((Predicate(f, op, t), p))
    return out

def _discover(rows, seed):
    if len(rows) < 20 or not FEATURES:
        return None, 0.0

    names, cols, labels = _matrix(rows)
    active = [f for f in names if len(set(cols[f])) >= 2]
    if not active:
        return None, 0.0

    singles = _predicates(cols, active)
    ranked = []

    for pred_obj, pred in singles:
        score, acc, bal = _candidate_score(pred, labels, 1)
        ranked.append((score, bal, acc, Rule((pred_obj,)), pred))

    ranked.sort(key=lambda x: (-x[0], -x[1], x[3].to_string()))
    top = ranked[:24]

    candidates = list(top)

    # Only build pairs from the top 24 single predicates.
    # This is the major runtime reduction.
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            r1 = top[i][3]
            r2 = top[j][3]
            if r1.predicates[0].feature == r2.predicates[0].feature:
                continue
            pred1 = top[i][4]
            pred2 = top[j][4]
            pred = tuple(x and y for x, y in zip(pred1, pred2))
            rule = Rule((r1.predicates[0], r2.predicates[0]))
            score, acc, bal = _candidate_score(pred, labels, 2)
            candidates.append((score, bal, acc, rule, pred))

    candidates.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3].complexity, x[3].to_string()))

    if not candidates:
        return None, 0.0

    _, bal, acc, best, _ = candidates[0]

    # Gate on balanced performance, preventing majority-class tricks.
    if bal < 0.55:
        return None, bal

    return best, acc

def evolve_rule(rows, generations=60, population_size=100, max_depth=5):
    del generations, population_size, max_depth
    data = list(rows)
    state = random.getstate()
    try:
        seed = state[1][0]
    except Exception:
        seed = 0
    return _discover(data, seed)

def evaluate_rule(expr, rows):
    labels = [bool(r["pumped"]) for r in rows]
    pred = [bool(expr.evaluate(extract_features(r))) for r in rows]
    acc, bal, precision = _metrics(pred, labels)
    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "positive_precision": precision,
    }

def rule_features(expr):
    return sorted({p.feature for p in expr.predicates})

__all__ = [
    "FEATURES", "Expr", "Rule", "Predicate",
    "extract_features", "evolve_rule",
    "evaluate_rule", "rule_features",
]
