"""Illustrative Factor-Based Return Attribution.

V6 correction (see CHANGELOG_V6.md): the V5 version derived a "realised"
return as `expected_return + random noise` and called it `historical_return`,
which was misleading -- nothing in that number came from an actual
observation. This version instead applies a single, explicitly-labelled
SYNTHETIC_TRAILING_12M_SHOCK through the exact same central engine used
everywhere else in the app (`deterministic_asset_attribution` in
`src/scenario_generator.py`), so no second P&L formula is created. This is
explicitly NOT a Brinson allocation/selection attribution -- there is still
no separate benchmark or policy-weight return series in this dataset to
support that decomposition.

Beginning MV + Carry + Rate P&L + Spread P&L + Equity/Real-asset P&L + FX P&L
= Ending MV, by construction, for every row.
"""
from __future__ import annotations

import pandas as pd

from src.scenario_generator import deterministic_asset_attribution

# An illustrative, moderate "trailing 12 months" market move -- picked to be
# plausible and easy to sanity-check, NOT fitted to any real observed period.
# Label kept in every output so a reader never mistakes this for history.
SYNTHETIC_TRAILING_12M_SHOCK: dict = {
    "d_rate": -.0020,             # rates drifted 20bp lower over the period
    "equity_shock": .06,          # equities +6%
    "credit_spread_shock": -.0010,  # spreads tightened 10bp
    "fx_shock": .02,               # USD +2% vs EUR
    "real_estate_shock": .015,     # real assets +1.5%
}


def performance_attribution(asset_df: pd.DataFrame, shock: dict | None = None,
                            fx_hedge_ratio: float = 0.0) -> tuple[pd.DataFrame, dict]:
    """Return (per-asset-class detail, summary dict with total_return, waterfall,
    beginning/ending market value and a reconciliation check)."""
    shock = SYNTHETIC_TRAILING_12M_SHOCK if shock is None else shock
    attribution = deterministic_asset_attribution(asset_df, shock, fx_hedge_ratio)

    df = asset_df[["asset_class", "market_value", "weight", "yield"]].copy().reset_index(drop=True)
    df["carry_pnl"] = df.market_value * df["yield"]
    df = df.merge(attribution, on="asset_class", how="left")
    df["total_pnl"] = df.carry_pnl + df.rate_pnl + df.spread_pnl + df.equity_real_pnl + df.fx_pnl
    df["beginning_mv"] = df.market_value
    df["ending_mv"] = df.beginning_mv + df.total_pnl
    df["asset_class_return"] = df.total_pnl / df.beginning_mv
    total_mv = float(df.beginning_mv.sum())
    df["return_contribution"] = df.total_pnl / total_mv

    total_pnl = float(df.total_pnl.sum())
    total_return = total_pnl / total_mv
    waterfall = {
        "Carry / income": float(df.carry_pnl.sum()) / total_mv,
        "Rate effect": float(df.rate_pnl.sum()) / total_mv,
        "Credit spread effect": float(df.spread_pnl.sum()) / total_mv,
        "Equity / real-asset effect": float(df.equity_real_pnl.sum()) / total_mv,
        "FX effect": float(df.fx_pnl.sum()) / total_mv,
    }
    reconciled_total = sum(waterfall.values())
    return df[["asset_class", "weight", "beginning_mv", "carry_pnl", "rate_pnl", "spread_pnl",
               "equity_real_pnl", "fx_pnl", "total_pnl", "ending_mv", "asset_class_return",
               "return_contribution"]], {
        "shock_applied": shock,
        "beginning_mv": total_mv,
        "ending_mv": total_mv + total_pnl,
        "total_pnl": total_pnl,
        "total_return": total_return,
        "waterfall": waterfall,
        "reconciled_total": reconciled_total,
    }


def return_vs_risk_contribution(performance_detail: pd.DataFrame, risk_contribution_df: pd.DataFrame) -> pd.DataFrame:
    """Join return contribution (this module) with market-risk contribution
    (src/asset_model.risk_contribution) so an Investment Committee can see,
    e.g., 'equities explain 25% of return but 42% of market risk' -- framed
    as an Analytical Observation, never as a buy/sell judgement."""
    left = performance_detail.set_index("asset_class")["return_contribution"]
    right = risk_contribution_df.set_index("asset_class")[["weight", "pct_of_total_risk"]]
    out = right.copy()
    out["return_contribution"] = left.reindex(out.index).fillna(0.0)
    total_return = out.return_contribution.sum()
    out["pct_of_total_return"] = out.return_contribution / total_return if total_return else 0.0
    return out.reset_index().rename(columns={"index": "asset_class"})
