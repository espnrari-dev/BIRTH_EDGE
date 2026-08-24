#!/usr/bin/env python3
"""
REAL Birth Edge Learning System
===============================
100% real market data only. Zero fakes. Zero hardcoded fallbacks.
Zero invented prices.

Rules enforced:
- Initial price comes ONLY from live DexScreener API response (priceUsd).
- If the API returns no usable priceUsd (None, missing, 0, non-numeric),
  the token is SKIPPED. It is never stored with a synthetic value.
- Final price is also fetched live. Same strict rule.
- No "or 1e-05", no liquidity/1e6 guesses treated as price, nothing.
- Every stored row is verifiable against the public API at the time of insert.

Data source: https://api.dexscreener.com (public, no key required)
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "data" / "learning_real.db"
DEX_BASE = "https://api.dexscreener.com"
REQUEST_TIMEOUT = 15
USER_AGENT = "RealBirthEdge/1.0 (research; real-data-only)"

# Minimum liquidity (USD) to even consider a pair. Pure quality filter, not a price.
MIN_LIQUIDITY_USD = 500.0


# ---------------------------------------------------------------------------
# Database – pure real data schema
# ---------------------------------------------------------------------------
def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=DELETE")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_id        TEXT    NOT NULL,
                pair_address    TEXT    NOT NULL,
                token_address   TEXT    NOT NULL,
                symbol          TEXT,
                name            TEXT,
                discovered_at   TEXT    NOT NULL,
                initial_price_usd REAL  NOT NULL,
                final_price_usd   REAL,
                liquidity_usd   REAL,
                volume_h24      REAL,
                price_change_h24 REAL,
                overall_score   REAL,
                multiplier      REAL,
                notes           TEXT,
                raw_initial_json TEXT,
                UNIQUE(chain_id, pair_address)
            );

            CREATE INDEX IF NOT EXISTS idx_discovered
                ON learning_results(discovered_at);
            CREATE INDEX IF NOT EXISTS idx_score
                ON learning_results(overall_score);
            """
        )
    print(f"[DB] Initialized real database at {DB_PATH}")


# ---------------------------------------------------------------------------
# Strict real-price helpers
# ---------------------------------------------------------------------------
def _parse_real_price(value: Any) -> Optional[float]:
    """Return a positive float only if the value is a genuine usable price.
    Never invent, never default.
    """
    if value is None:
        return None
    try:
        p = float(value)
        if p > 0.0 and p == p:  # reject NaN / negative / zero
            return p
    except (TypeError, ValueError):
        pass
    return None


def fetch_pair(chain_id: str, pair_address: str) -> Optional[dict]:
    url = f"{DEX_BASE}/latest/dex/pairs/{chain_id}/{pair_address}"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        if not pairs:
            return None
        return pairs[0]
    except Exception as e:
        print(f"[API] fetch_pair error {chain_id}/{pair_address}: {e}")
        return None


def fetch_token_pairs(chain_id: str, token_address: str) -> list[dict]:
    url = f"{DEX_BASE}/tokens/v1/{chain_id}/{token_address}"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("pairs") or []
    except Exception as e:
        print(f"[API] fetch_token_pairs error: {e}")
        return []


def search_pairs(query: str, limit: int = 30) -> list[dict]:
    url = f"{DEX_BASE}/latest/dex/search"
    try:
        r = requests.get(
            url,
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        pairs = data.get("pairs") or []
        real = []
        for p in pairs[:limit]:
            price = _parse_real_price(p.get("priceUsd"))
            if price is None:
                continue
            liq = p.get("liquidity") or {}
            liq_usd = liq.get("usd")
            if liq_usd is not None:
                try:
                    if float(liq_usd) < MIN_LIQUIDITY_USD:
                        continue
                except (TypeError, ValueError):
                    pass
            real.append(p)
        return real
    except Exception as e:
        print(f"[API] search error: {e}")
        return []


def latest_token_profiles(limit: int = 20) -> list[dict]:
    url = f"{DEX_BASE}/token-profiles/latest/v1"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data[:limit]
        return []
    except Exception as e:
        print(f"[API] latest profiles error: {e}")
        return []


# ---------------------------------------------------------------------------
# Core real ingestion – no fakes allowed
# ---------------------------------------------------------------------------
def record_birth_from_pair(pair: dict) -> bool:
    price = _parse_real_price(pair.get("priceUsd"))
    if price is None:
        print(f"[SKIP] No real priceUsd for {pair.get('baseToken', {}).get('symbol')}")
        return False

    chain_id = pair.get("chainId")
    pair_addr = pair.get("pairAddress")
    base = pair.get("baseToken") or {}
    token_addr = base.get("address")
    symbol = base.get("symbol")
    name = base.get("name")

    if not all([chain_id, pair_addr, token_addr]):
        print("[SKIP] Missing identifiers")
        return False

    if symbol and (len(symbol) > 24 or len(symbol) < 1):
        print(f"[SKIP] Absurd symbol length: {str(symbol)[:40]}...")
        return False
    if name and len(name) > 80:
        print("[SKIP] Absurd name length")
        return False

    liq = pair.get("liquidity") or {}
    liq_usd = None
    try:
        liq_usd = float(liq.get("usd")) if liq.get("usd") is not None else None
    except (TypeError, ValueError):
        pass

    vol = pair.get("volume") or {}
    vol_h24 = None
    try:
        vol_h24 = float(vol.get("h24")) if vol.get("h24") is not None else None
    except (TypeError, ValueError):
        pass

    pc = pair.get("priceChange") or {}
    pc_h24 = None
    try:
        pc_h24 = float(pc.get("h24")) if pc.get("h24") is not None else None
    except (TypeError, ValueError):
        pass

    now = datetime.now(timezone.utc).isoformat()

    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO learning_results (
                chain_id, pair_address, token_address, symbol, name,
                discovered_at, initial_price_usd, liquidity_usd,
                volume_h24, price_change_h24, raw_initial_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chain_id,
                pair_addr,
                token_addr,
                symbol,
                name,
                now,
                price,          # REAL only
                liq_usd,
                vol_h24,
                pc_h24,
                json.dumps(pair, default=str),
            ),
        )
        conn.commit()
        print(
            f"[REAL BIRTH] {symbol} ({chain_id}) "
            f"price=\( {price:.10g}  liq= \){liq_usd or 0:.0f}"
        )
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        print(f"[DB ERR] {e}")
        return False
    finally:
        conn.close()


def discover_and_record(queries: list[str] | None = None) -> int:
    if queries is None:
        queries = [
            "pump fun", "meme", "BONK", "WIF", "PEPE",
            "new pair", "base meme", "solana meme",
        ]

    recorded = 0
    seen_pairs: set[str] = set()

    for q in queries:
        pairs = search_pairs(q, limit=12)
        for p in pairs:
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            try:
                if record_birth_from_pair(p):
                    recorded += 1
            except Exception as e:
                print(f"[RECORD ERR] {e}")
        time.sleep(0.6)

    profiles = latest_token_profiles(limit=10)
    for prof in profiles:
        chain = prof.get("chainId")
        addr = prof.get("tokenAddress")
        if not chain or not addr:
            continue
        pairs = fetch_token_pairs(chain, addr)
        for p in pairs[:3]:
            key = f"{p.get('chainId')}:{p.get('pairAddress')}"
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            try:
                if record_birth_from_pair(p):
                    recorded += 1
            except Exception as e:
                print(f"[RECORD ERR] {e}")
        time.sleep(0.5)

    print(f"[DISCOVER] Recorded {recorded} new real births")
    return recorded


def update_final_prices(max_age_hours: float = 48.0) -> int:
    updated = 0
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, chain_id, pair_address, symbol, initial_price_usd
            FROM learning_results
            WHERE final_price_usd IS NULL
            """
        ).fetchall()

    for row in rows:
        pair = fetch_pair(row["chain_id"], row["pair_address"])
        if not pair:
            continue
        price = _parse_real_price(pair.get("priceUsd"))
        if price is None:
            print(f"[SKIP FINAL] No real price for {row['symbol']}")
            continue

        multiplier = price / row["initial_price_usd"] if row["initial_price_usd"] > 0 else None
        score = None
        if multiplier is not None:
            score = min(100.0, max(0.0, 50.0 + 15.0 * (multiplier - 1.0)))

        conn = get_conn()
        try:
            conn.execute(
                """
                UPDATE learning_results
                SET final_price_usd = ?,
                    multiplier = ?,
                    overall_score = ?,
                    notes = COALESCE(notes, '') || ' | final updated live'
                WHERE id = ?
                """,
                (price, multiplier, score, row["id"]),
            )
            conn.commit()
            print(
                f"[REAL FINAL] {row['symbol']}  "
                f"${row['initial_price_usd']:.8g} → ${price:.8g}  "
                f"x{multiplier:.3f}  score={score:.1f}"
            )
            updated += 1
        except Exception as e:
            print(f"[UPDATE ERR] {e}")
        finally:
            conn.close()
        time.sleep(0.25)

    print(f"[UPDATE] Updated {updated} finals with real prices")
    return updated


def prove_all_real() -> None:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT symbol, discovered_at, initial_price_usd, final_price_usd,
                   overall_score, multiplier
            FROM learning_results
            ORDER BY discovered_at DESC
            LIMIT 30
            """
        ).fetchall()

        print("\n=== REAL DATA PROOF ===")
        print(f"{'SYMBOL':<12} {'DISCOVERED':<22} {'INITIAL':>14} {'FINAL':>14} {'MULT':>8} {'SCORE':>6}")
        print("-" * 80)
        for r in rows:
            fin = f"{r['final_price_usd']:.8g}" if r["final_price_usd"] is not None else "—"
            mult = f"{r['multiplier']:.3f}" if r["multiplier"] is not None else "—"
            sc = f"{r['overall_score']:.1f}" if r["overall_score"] is not None else "—"
            print(
                f"{(r['symbol'] or '?'):<12} {r['discovered_at'][:19]:<22} "
                f"{r['initial_price_usd']:>14.8g} {fin:>14} {mult:>8} {sc:>6}"
            )

        stats = conn.execute(
            """
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT initial_price_usd) as distinct_prices,
                   COUNT(CASE WHEN initial_price_usd = 1e-05 THEN 1 END) as fake_1e5
            FROM learning_results
            """
        ).fetchone()

        print("\n=== INTEGRITY ===")
        print(f"Total rows          : {stats['total']}")
        print(f"Distinct initial $  : {stats['distinct_prices']}")
        print(f"Rows with 1e-05     : {stats['fake_1e5']}  (must be 0)")
        if stats["fake_1e5"] > 0 or (
            stats["total"] > 5 and stats["distinct_prices"] < stats["total"] * 0.7
        ):
            print("WARNING: data looks suspicious – investigate!")
        else:
            print("PASS: all initial prices are real and varied.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Real Birth Edge – 100% real data")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--discover", action="store_true", help="Discover & record real births")
    parser.add_argument("--update", action="store_true", help="Update final prices from live API")
    parser.add_argument("--prove", action="store_true", help="Audit that everything is real")
    parser.add_argument("--loop", type=int, metavar="SECONDS",
                        help="Run discover+update in a loop")
    args = parser.parse_args()

    if args.init or not DB_PATH.exists():
        init_db()

    if args.discover:
        discover_and_record()

    if args.update:
        update_final_prices()

    if args.prove:
        prove_all_real()

    if args.loop:
        print(f"[LOOP] every {args.loop}s – Ctrl+C to stop")
        while True:
            discover_and_record()
            update_final_prices()
            prove_all_real()
            time.sleep(args.loop)

    if not any([args.init, args.discover, args.update, args.prove, args.loop]):
        init_db()
        discover_and_record()
        update_final_prices()
        prove_all_real()


if __name__ == "__main__":
    main()
