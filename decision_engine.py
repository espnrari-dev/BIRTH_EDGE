import json
import os
import time
from datetime import datetime
from utils import now_str, log_jsonl
import cognition
import ml_model

# Decision thresholds (configurable via config.py later)
DECISION_LOG = "logs/decisions.jsonl"

def get_agent_confidence(creator_addr):
    """Return agent confidence and role if known, else default."""
    agent = cognition.get_agent(creator_addr)
    if agent:
        return {
            "role": agent.get("role", "unknown"),
            "confidence": agent.get("confidence", 0.5),
            "success_count": agent.get("success_count", 0),
            "fail_count": agent.get("fail_count", 0),
        }
    return {"role": "unknown", "confidence": 0.5, "success_count": 0, "fail_count": 0}

def get_relevant_wisdom(token_data):
    """Retrieve wisdom rules that are relevant based on token features."""
    rules = cognition.get_wisdom_rules(min_confidence=0.6, limit=10)
    relevant = []
    for r in rules:
        rule = r["rule"].lower()
        if "liquidity" in rule and token_data.get("liquidity_usd", 0) < 10000:
            relevant.append(r)
        elif "holder" in rule and token_data.get("holder_score", 0) < 15:
            relevant.append(r)
        elif "tax" in rule and token_data.get("tax_score", 0) < 10:
            relevant.append(r)
        elif "mint" in rule and token_data.get("dev_score", 0) < 10:
            relevant.append(r)
    return relevant

def make_decision(token_data: dict) -> dict:
    """
    Combine:
    - overall_score (from filters)
    - ml_pump_probability (if available)
    - agent confidence (if creator known)
    - relevant wisdom rules
    Produce a final decision score and label.
    """
    # Base score = overall filter score (0-100)
    base = token_data.get("overall_score", 0)

    # ML probability (0-1) scaled to 0-100, but only if model trained
    ml_prob = token_data.get("ml_pump_probability", None)
    if ml_prob is not None and ml_prob != 0.5:
        ml_score = ml_prob * 100
    else:
        ml_score = 50  # neutral

    # Agent confidence factor: if known bad agent, reduce; if good, boost
    creator = token_data.get("creator")
    agent_info = get_agent_confidence(creator) if creator else {"role": "unknown", "confidence": 0.5}
    if agent_info["role"] == "dev":
        # Developers are risky; scale down if low success
        agent_factor = agent_info["confidence"] * 20  # 0-20
    elif agent_info["role"] == "sniper":
        agent_factor = agent_info["confidence"] * 30  # snipers can be good early
    else:
        agent_factor = 10  # neutral

    # Wisdom rules impact
    relevant_wisdom = get_relevant_wisdom(token_data)
    wisdom_bonus = 0
    wisdom_penalty = 0
    for r in relevant_wisdom:
        conf = r["confidence"]
        if "rug" in r["rule"] or "danger" in r["rule"] or "trap" in r["rule"]:
            wisdom_penalty += conf * 5
        else:
            wisdom_bonus += conf * 3

    # Combine
    final_score = 0.35 * base + 0.25 * ml_score + 0.15 * agent_factor + 0.25 * (50 + wisdom_bonus - wisdom_penalty)
    final_score = max(0, min(100, final_score))

    # Decision label
    if final_score >= 80:
        label = "STRONG_ALERT"
    elif final_score >= 65:
        label = "WATCH"
    elif final_score >= 50:
        label = "NEUTRAL"
    else:
        label = "AVOID"

    decision = {
        "timestamp": now_str(),
        "addr": token_data.get("addr"),
        "chain": token_data.get("chain"),
        "symbol": token_data.get("symbol", "?"),
        "overall_score": base,
        "ml_pump_probability": ml_prob,
        "agent_role": agent_info["role"],
        "agent_confidence": agent_info["confidence"],
        "relevant_wisdom_count": len(relevant_wisdom),
        "final_decision_score": round(final_score, 2),
        "label": label,
    }
    log_jsonl("decisions.jsonl", decision)
    return decision

def print_decision(decision):
    """Pretty-print decision to console."""
    print(f"[{now_str()}] 🧠 DECISION: {decision['label']} | {decision['symbol']} on {decision['chain']} | Score {decision['final_decision_score']:.1f} | ML {decision['ml_pump_probability']:.2f} | Agent {decision['agent_role']}")
