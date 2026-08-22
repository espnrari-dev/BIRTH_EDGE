"""
Simple scoring engine that can be extended with machine learning.
For now we use rule-based scores computed in filters.py.
The database stores token features and outcomes, which can later
be used to train a model to predict pumps/rugs.
"""
import sqlite3
from database import get_db, insert_token

def record_token(token_data: dict):
    """Store token data in DB for future learning."""
    insert_token({
        "addr": token_data.get("addr"),
        "chain": token_data.get("chain"),
        "symbol": token_data.get("symbol", ""),
        "discovered_at": token_data.get("discovered_at"),
        "liquidity_usd": token_data.get("liquidity_usd", 0),
        "holder_score": token_data.get("holder_score", 0),
        "dev_score": token_data.get("dev_score", 0),
        "lp_lock_score": token_data.get("lp_lock_score", 0),
        "tax_score": token_data.get("tax_score", 0),
        "overall_score": token_data.get("overall_score", 0),
    })

# Future: function to update outcomes and train model
