from datetime import datetime

def maybe_buy(token_data: dict):
    """Public version: only log qualified tokens, no auto-trade."""
    if token_data.get("pass"):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ QUALIFIED: {token_data.get('symbol','?')} on {token_data.get('chain')} – Score {token_data['overall_score']}")
        # In future, could send Telegram alert or store in DB.
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ REJECTED: {token_data.get('symbol','?')} – Reason: {token_data.get('reason','unknown')}")
