#!/usr/bin/env python3
"""
Homeostatic Controller
----------------------
Deterministic feedback that couples internal state
(entropy, KL, integrity belief) back into the
NominalRecognizer thresholds.

This closes the loop required for deterministic
emergent behavior.
"""

from __future__ import annotations
import json
import pathlib
from dataclasses import dataclass, asdict
from typing import Dict

STATE_FILE = pathlib.Path("data/homeostasis_state.json")

@dataclass
class Thresholds:
    max_symbol_len: int = 24
    min_liquidity: float = 300.0
    max_z: float = 4.5
    min_entropy_symbol: float = 1.1

@dataclass
class ControllerState:
    thresholds: Thresholds
    last_entropy: float = 0.0
    last_kl: float = 0.0
    integrity: float = 1.0
    mode: str = "nominal"          # nominal | tight | relaxed

def load_state() -> ControllerState:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text())
        th = Thresholds(**data.get("thresholds", {}))
        return ControllerState(
            thresholds=th,
            last_entropy=data.get("last_entropy", 0.0),
            last_kl=data.get("last_kl", 0.0),
            integrity=data.get("integrity", 1.0),
            mode=data.get("mode", "nominal"),
        )
    return ControllerState(thresholds=Thresholds())

def save_state(state: ControllerState) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(asdict(state), indent=2))

def deterministic_update(
    entropy: float,
    kl: float,
    integrity: float,
) -> ControllerState:
    """
    Pure function. Same inputs always produce the same new thresholds.
    This is the deterministic core required for emergence.
    """
    state = load_state()
    state.last_entropy = entropy
    state.last_kl = kl
    state.integrity = integrity

    # Fixed deterministic policy
    if entropy > 4.4 and kl > 0.40 and integrity < 0.75:
        # Stress → tighten
        state.mode = "tight"
        state.thresholds.min_liquidity = 600.0
        state.thresholds.max_z = 3.2
        state.thresholds.min_entropy_symbol = 1.4
        state.thresholds.max_symbol_len = 18
    elif entropy < 3.6 and kl < 0.15 and integrity > 0.90:
        # Calm → slight relaxation
        state.mode = "relaxed"
        state.thresholds.min_liquidity = 200.0
        state.thresholds.max_z = 5.0
        state.thresholds.min_entropy_symbol = 0.9
        state.thresholds.max_symbol_len = 28
    else:
        # Hold nominal
        state.mode = "nominal"
        state.thresholds = Thresholds()          # reset to defaults

    save_state(state)
    return state
