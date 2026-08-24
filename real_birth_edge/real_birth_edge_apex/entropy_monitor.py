#!/usr/bin/env python3
"""
Entropy Monitor for Birth-Price Distribution
--------------------------------------------
Novel signal: Shannon entropy + KL divergence of the empirical
distribution of real birth prices (log-space).

Academic basis:
- Shannon entropy as measure of uncertainty / novelty in the price field
- KL divergence as information gain / regime shift detector
- Online Bayesian update of system confidence from these quantities
"""

from __future__ import annotations
import math
import sqlite3
from collections import deque
from pathlib import Path
from typing import Deque, List, Tuple

import numpy as np

DB = Path("data/apex.db")
COG_DB = Path("data/cognition.db")

# Rolling window of log-prices
WINDOW = 300
N_BINS = 24
LOG_PRICE_RANGE = (-18.0, 2.0)          # covers \~1e-8 to \~7 USD

class BirthPriceEntropy:
    def __init__(self):
        self.log_prices: Deque[float] = deque(maxlen=WINDOW)
        self.ref_hist: np.ndarray | None = None
        self.ref_count = 0

    def _bin_index(self, log_p: float) -> int:
        lo, hi = LOG_PRICE_RANGE
        if log_p <= lo:
            return 0
        if log_p >= hi:
            return N_BINS - 1
        return int((log_p - lo) / (hi - lo) * (N_BINS - 1))

    def add(self, price: float) -> None:
        if price <= 0:
            return
        self.log_prices.append(math.log(price))

    def entropy_and_kl(self) -> Tuple[float, float]:
        if len(self.log_prices) < 30:
            return 0.0, 0.0

        hist = np.zeros(N_BINS, dtype=float)
        for lp in self.log_prices:
            hist[self._bin_index(lp)] += 1.0
        hist /= hist.sum()

        # Shannon entropy (bits)
        ent = -np.sum(hist * np.log2(hist + 1e-12))

        # Reference distribution (slowly adapting)
        if self.ref_hist is None:
            self.ref_hist = hist.copy()
            self.ref_count = 1
            kl = 0.0
        else:
            # Exponential moving update of reference
            alpha = 0.02
            self.ref_hist = (1 - alpha) * self.ref_hist + alpha * hist
            self.ref_hist /= self.ref_hist.sum()
            kl = float(np.sum(hist * np.log2((hist + 1e-12) / (self.ref_hist + 1e-12))))
            self.ref_count += 1

        return float(ent), float(kl)

def update_cognition_from_entropy(entropy: float, kl: float) -> None:
    """Bayesian-style update of integrity / novelty beliefs."""
    import cognition
    # High entropy or sudden KL jump → treat as novelty / possible stress
    novelty = min(1.0, kl * 3.0)
    integrity_success = entropy < 4.2          # empirically calm range
    cognition.update_belief("data_integrity", success=integrity_success, weight=0.08)
    cognition.update_belief("heal_success", success=(kl < 0.35), weight=0.10)
    cognition.record_episode(
        "entropy_signal",
        {"entropy": entropy, "kl": kl, "novelty": novelty},
        integrity=cognition.get_belief("data_integrity")
    )

def process_new_birth(price: float) -> dict:
    """Call this after every accepted real birth."""
    mon = BirthPriceEntropy()
    # load recent prices from DB to warm the window
    try:
        with sqlite3.connect(DB) as conn:
            rows = conn.execute(
                "SELECT initial_price FROM births ORDER BY id DESC LIMIT ?", (WINDOW,)
            ).fetchall()
            for (p,) in reversed(rows):
                mon.add(p)
    except Exception:
        pass

    mon.add(price)
    ent, kl = mon.entropy_and_kl()
    update_cognition_from_entropy(ent, kl)
    return {"entropy": ent, "kl": kl}
