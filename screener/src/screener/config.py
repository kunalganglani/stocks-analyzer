"""Central config: env vars + every tunable threshold.

DB-stored settings (equity, risk_pct, ...) override these defaults at runtime;
these constants are the single source for anything not worth a DB round-trip.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# --- env ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
ALERT_FROM = os.environ.get("ALERT_FROM", "stocks-analyzer <onboarding@resend.dev>")
ALERT_TO = os.environ.get("ALERT_TO", "kunalganglani@gmail.com")


@dataclass(frozen=True)
class Thresholds:
    # Universe / liquidity (Minervini trades liquid names only)
    min_price: float = 10.0
    min_avg_dollar_volume: float = 5_000_000.0  # 50d avg

    # Quality gate (Buffett/Munger)
    min_roe: float = 0.15
    min_roic: float = 0.12          # alternative to ROE
    max_debt_to_equity: float = 1.5
    min_gross_margin_stability: float = 0.06  # max stdev of gross margin over years

    # Trend template
    rs_min_percentile: float = 70.0
    min_pct_above_52w_low: float = 0.30
    max_pct_off_52w_high: float = 0.25
    ma200_rising_lookback: int = 21  # trading days (~1 month)

    # RS weighting (IBD-style): 0.4*r63 + 0.2*r126 + 0.2*r189 + 0.2*r252
    rs_windows: tuple[int, ...] = (63, 126, 189, 252)
    rs_weights: tuple[float, ...] = (0.4, 0.2, 0.2, 0.2)

    # VCP / entry trigger
    vcp_lookback: int = 90                  # trading days to scan for the base
    vcp_swing_window: int = 5               # bars each side for swing hi/lo detection
    vcp_min_contractions: int = 2
    vcp_step_tolerance: float = 1.10        # adjacent contraction may be <= 1.1x previous
    vcp_contraction_decay: float = 0.75     # but final must be <= decay * first (overall tightening)
    vcp_max_final_contraction: float = 0.12
    vcp_dryup_ratio: float = 0.8            # 10d avg vol < ratio * 50d avg vol
    vcp_breakout_volume_mult: float = 1.4   # breakout vol >= mult * 50d avg
    vcp_max_extension: float = 0.05         # close <= pivot * (1 + this) — no chasing
    vcp_pivot_near_pct: float = 0.05        # within 5% below pivot => pivot_near

    # Buy management
    max_stop_pct: float = 0.08              # stop never wider than 8% below buy point
    buy_cooldown_days: int = 20             # no repeat BUY for same ticker within N trading days

    # Sell rules
    sell_strength_gain: float = 0.20
    climax_gain: float = 0.25
    climax_window: int = 15                 # trading days
    climax_extension_vs_ma200: float = 1.7

    # Sizing defaults (overridden by DB settings)
    equity: float = 100_000.0
    risk_pct: float = 1.25
    max_position_pct: float = 25.0

    # Fundamentals refresh
    fundamentals_stale_days: int = 21


T = Thresholds()
