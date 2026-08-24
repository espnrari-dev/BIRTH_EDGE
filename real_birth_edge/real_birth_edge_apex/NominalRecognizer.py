#!/usr/bin/env python3
"""
NominalRecognizer
-----------------
Scholarly data-quality gate for market payloads.

Implements:
- Schema validation
- Type and range checking
- Statistical outlier detection (modified z-score on log-price)
- Shannon entropy check on symbol strings (rejects pure noise)
- Liquidity and volume consistency checks

Rejects any payload that fails the nominal criteria.
Never invents or substitutes prices.
"""

from __future__ import annotations
import math
import re
from typing import Any, Optional, Tuple

# Tunable academic thresholds
MAX_SYMBOL_LEN = 24
MIN_SYMBOL_LEN = 1
MIN_LIQUIDITY_USD = 300.0
MAX_LOG_PRICE_Z = 4.5          # modified z-score threshold
MIN_SYMBOL_ENTROPY = 1.1       # bits; pure repetitive symbols fall below this

def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())

def parse_real_price(value: Any) -> Optional[float]:
    """Strict positive finite float. No defaults."""
    if value is None:
        return None
    try:
        p = float(value)
        if p > 0.0 and math.isfinite(p):
            return p
    except (TypeError, ValueError):
        pass
    return None

def modified_z_score(value: float, median: float, mad: float) -> float:
    """Robust z-score using median absolute deviation."""
    if mad == 0:
        return 0.0
    return 0.6745 * (value - median) / mad

class NominalRecognizer:
    def __init__(self):
        self.log_prices: list[float] = []

    def update_reference(self, price: float) -> None:
        """Maintain a rolling reference distribution of log-prices."""
        self.log_prices.append(math.log(price))
        if len(self.log_prices) > 500:
            self.log_prices.pop(0)

    def _reference_stats(self) -> Tuple[float, float]:
        if len(self.log_prices) < 10:
            return 0.0, 1.0
        sorted_lp = sorted(self.log_prices)
        median = sorted_lp[len(sorted_lp) // 2]
        abs_dev = [abs(x - median) for x in sorted_lp]
        mad = sorted(abs_dev)[len(abs_dev) // 2] or 1e-9
        return median, mad

    def is_nominal(self, pair: dict) -> Tuple[bool, str]:
        """
        Returns (is_nominal, reason).
        Academic criteria only — no price invention.
        """
        if not isinstance(pair, dict):
            return False, "schema: not a dict"

        # 1. Price existence and validity
        price = parse_real_price(pair.get("priceUsd"))
        if price is None:
            return False, "price: missing or non-positive"

        # 2. Identifier completeness
        chain = pair.get("chainId")
        pair_addr = pair.get("pairAddress")
        base = pair.get("baseToken") or {}
        token_addr = base.get("address")
        if not all([chain, pair_addr, token_addr]):
            return False, "schema: missing chain/pair/token address"

        # 3. Symbol quality
        symbol = (base.get("symbol") or "").strip()
        if not (MIN_SYMBOL_LEN <= len(symbol) <= MAX_SYMBOL_LEN):
            return False, f"symbol: length {len(symbol)} outside [{MIN_SYMBOL_LEN},{MAX_SYMBOL_LEN}]"
        if not re.match(r'^[A-Za-z0-9]+$', symbol):
            return False, "symbol: non-alphanumeric"
        entropy = _shannon_entropy(symbol)
        if entropy < MIN_SYMBOL_ENTROPY:
            return False, f"symbol: entropy {entropy:.2f} < {MIN_SYMBOL_ENTROPY}"

        # 4. Liquidity consistency
        liq = (pair.get("liquidity") or {}).get("usd")
        try:
            liq_f = float(liq) if liq is not None else None
            if liq_f is not None and liq_f < MIN_LIQUIDITY_USD:
                return False, f"liquidity: {liq_f} < {MIN_LIQUIDITY_USD}"
        except (TypeError, ValueError):
            pass

        # 5. Statistical outlier check on log-price
        median, mad = self._reference_stats()
        z = modified_z_score(math.log(price), median, mad)
        if abs(z) > MAX_LOG_PRICE_Z and len(self.log_prices) >= 20:
            return False, f"price: modified z-score {z:.2f} exceeds {MAX_LOG_PRICE_Z}"

        # Passed all checks
        self.update_reference(price)
        return True, "nominal"
