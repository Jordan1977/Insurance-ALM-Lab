"""Illustrative macro regime classification and mapping to ALM scenarios.

The shipped macro series is synthetic and used only to demonstrate the workflow.
It is not a forecast and is not presented as observed ECB/market history.
"""
from __future__ import annotations

import pandas as pd

REGIMES = ["Growth", "Slowdown", "Disinflation", "Inflation", "Stagflation", "Recession"]
REGIME_TO_SCENARIO = {
    "Growth": "Risk-on",
    "Slowdown": "Equity -20%",
    "Disinflation": "Rates -100bp",
    "Inflation": "Inflation +2%",
    "Stagflation": "Stagflation",
    "Recession": "Recession",
}


def classify_regime(macro_df: pd.DataFrame, window: int = 12) -> pd.DataFrame:
    d = macro_df.sort_values("date").reset_index(drop=True).copy()
    d["inflation_trend"] = d["euro_inflation_pct"] - d["euro_inflation_pct"].shift(window)
    d["equity_momentum"] = d["eurostoxx50"].pct_change(window)
    d["spread_trend"] = d["credit_spread_ig_pct"] - d["credit_spread_ig_pct"].rolling(window).mean()

    def regime(row):
        if pd.isna(row.inflation_trend) or pd.isna(row.equity_momentum):
            return None
        infl_up = row.inflation_trend > .15
        eq_down = row.equity_momentum < -.08
        spread_up = (0.0 if pd.isna(row.spread_trend) else row.spread_trend) > .10
        if infl_up and eq_down:
            return "Stagflation"
        if eq_down and spread_up:
            return "Recession"
        if infl_up:
            return "Inflation"
        if eq_down:
            return "Slowdown"
        if row.inflation_trend < -.10:
            return "Disinflation"
        return "Growth"

    d["regime"] = d.apply(regime, axis=1)
    return d


def latest_regime(macro_df: pd.DataFrame, window: int = 12) -> str:
    d = classify_regime(macro_df, window)
    valid = d.dropna(subset=["regime"])
    return str(valid.iloc[-1].regime) if len(valid) else "Insufficient history"


def scenario_for_regime(regime: str) -> str:
    return REGIME_TO_SCENARIO.get(regime, "Base")
