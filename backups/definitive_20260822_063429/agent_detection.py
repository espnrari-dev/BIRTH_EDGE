import os
import time
from datetime import datetime, timedelta
import requests
from utils import fetch_json_sync, now_str
import cognition

# Public endpoints
SOLSCAN_ACCOUNT_TOKENS_URL = "https://public-api.solscan.io/account/tokens?address={}&limit=10"
SOLSCAN_ACCOUNT_TXS_URL = "https://public-api.solscan.io/account/transactions?address={}&limit=10"

def get_creator_tokens(creator_addr):
    """Fetch recent tokens created by an address using Solscan."""
    try:
        data = fetch_json_sync(SOLSCAN_ACCOUNT_TOKENS_URL.format(creator_addr))
        if data:
            return [item.get("tokenAddress") for item in data if item.get("tokenAddress")]
    except:
        pass
    return []

def get_creator_recent_txs(creator_addr):
    """Fetch recent transactions for an address."""
    try:
        data = fetch_json_sync(SOLSCAN_ACCOUNT_TXS_URL.format(creator_addr))
        if data:
            return data
    except:
        pass
    return []

def classify_creator(creator_addr):
    """
    Classify a creator address as:
    - 'dev' if they have created 1+ tokens
    - 'sniper' if they have many early buys (heuristic)
    - 'unknown' otherwise
    """
    tokens = get_creator_tokens(creator_addr)
    if tokens:
        return 'dev'
    # Could add sniper detection based on transaction patterns later
    return 'unknown'

def update_agent_from_creator(creator_addr):
    """Register or update an agent based on creator address."""
    role = classify_creator(creator_addr)
    # Check existing agent
    agent = cognition.get_agent(creator_addr)
    if not agent:
        cognition.register_agent(creator_addr, role, success_count=0, fail_count=0)
        print(f"[{now_str()}] Registered new agent: {creator_addr[:8]}.. role={role}")
    else:
        # Update role if changed
        if agent['role'] != role:
            cognition.register_agent(creator_addr, role, success_count=0, fail_count=0)
            print(f"[{now_str()}] Updated agent role: {creator_addr[:8]}.. -> {role}")

def track_agent_behavior(agent_addr, outcome_type):
    """
    Update agent success/fail counts based on outcome_type.
    outcome_type: 'rug' or 'pump'
    """
    agent = cognition.get_agent(agent_addr)
    if not agent:
        return
    if outcome_type == 'pump':
        cognition.register_agent(agent_addr, agent['role'], success_count=1, fail_count=0)
    elif outcome_type == 'rug':
        cognition.register_agent(agent_addr, agent['role'], success_count=0, fail_count=1)

def scan_new_creators():
    """
    Scan recent births and update agent map with creators.
    This function would be called from the main filter loop when a new token appears.
    """
    from config import DEX_LATEST_URL
    r = fetch_json_sync(DEX_LATEST_URL)
    if not r:
        return
    for t in r[:10]:
        creator = t.get('creator')  # DexScreener may not provide creator; fallback to None
        if creator:
            update_agent_from_creator(creator)
        else:
            # Attempt to derive creator from pair data (usually not available)
            pass

# This function will be called from main loop after a token is discovered.
def process_creator_for_token(token_data):
    """Given token_data with possible creator, update agent map."""
    creator = token_data.get('creator')
    if creator:
        update_agent_from_creator(creator)
