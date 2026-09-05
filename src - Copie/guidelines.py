"""Investment Guidelines & Limits Monitor.

All limits here are "Synthetic Internal Illustrative Limits" set by the user
via the sidebar / Assumptions Hub -- never presented as Thélem's real
guidelines. This module is deliberately generic: `check_compliance` takes
*computed* metrics (from the same engines every other page uses) and a limits
dict, so a proposed SAA weight vector or a reinvestment-adjusted duration can
both be tested against the same guideline set without re-deriving anything.
"""
from __future__ import annotations

import pandas as pd

from src.asset_model import EQUITY_CLASSES, ILLIQUID_CLASSES, CREDIT_CLASSES, fx_exposure


def portfolio_guideline_metrics(asset_df: pd.DataFrame, weight_col: str = "weight",
                                fx_hedge_ratio: float = 0.0) -> dict:
    """Compute the exposure metrics guidelines are checked against, from
    whatever weight column is passed in (current book or a proposed SAA /
    reinvestment weight vector) -- one function, reusable for any candidate
    allocation."""
    df = asset_df.copy()
    w = df[weight_col]
    equity_weight = float(w[df.asset_class.isin(EQUITY_CLASSES)].sum())
    illiquid_weight = float(w[df.asset_class.isin(ILLIQUID_CLASSES)].sum())
    hy_weight = float(w[df.asset_class.eq("High Yield Bonds")].sum())
    ig_weight = float(w[df.asset_class.isin(CREDIT_CLASSES) & ~df.asset_class.eq("High Yield Bonds")].sum())
    cash_weight = float(w[df.asset_class.eq("Cash / Money Market")].sum())
    fx = fx_exposure(df.assign(market_value=w * df.market_value.sum() / max(w.sum(), 1e-9)), fx_hedge_ratio)
    fx_weight = fx["net_fx_exposure"] / df.market_value.sum() if df.market_value.sum() else 0.0
    largest_weight = float(w.max())
    return {
        "equity_weight": equity_weight,
        "illiquid_weight": illiquid_weight,
        "hy_weight": hy_weight,
        "ig_weight": ig_weight,
        "cash_weight": cash_weight,
        "fx_weight": fx_weight,
        "largest_single_asset_class_weight": largest_weight,
    }


def check_compliance(metrics: dict, kpis: dict, liquidity_coverage: float, limits: dict) -> pd.DataFrame:
    """Compare current/candidate metrics against the illustrative internal
    limits and return one row per guideline with GREEN/AMBER/RED status."""
    def status(value, limit, higher_is_better):
        if higher_is_better:
            return "GREEN" if value >= limit else ("AMBER" if value >= limit * .85 else "RED")
        return "GREEN" if value <= limit else ("AMBER" if value <= limit * 1.15 else "RED")

    rows = [
        ("Maximum equity exposure", metrics["equity_weight"], limits["equity_max"], False),
        ("Maximum High Yield exposure", metrics["hy_weight"], limits["hy_max"], False),
        ("Maximum illiquid exposure", metrics["illiquid_weight"], limits["illiquid_max"], False),
        ("Maximum net FX exposure", metrics["fx_weight"], limits.get("fx_max", .15), False),
        ("Minimum cash", metrics["cash_weight"], limits["cash_min"], True),
        ("Maximum single asset-class weight", metrics["largest_single_asset_class_weight"], limits.get("concentration_max", .45), False),
        ("Maximum |duration gap|", abs(kpis["duration_gap"]), limits["duration_gap_tolerance"], False),
        ("Minimum 12M liquidity coverage", liquidity_coverage, limits["liquidity_target"], True),
        ("Minimum Economic A/L Coverage", kpis["economic_coverage_ratio"], limits.get("coverage_min", 1.0), True),
    ]
    out = pd.DataFrame(rows, columns=["guideline", "current", "limit", "higher_is_better"])
    out["status"] = [status(v, l, h) for v, l, h in zip(out.current, out.limit, out.higher_is_better)]
    # Headroom sign convention: ALWAYS positive = safe margin, negative = breach,
    # regardless of whether the guideline is a ceiling or a floor. (Earlier version
    # returned `current - limit` unconditionally, which for a floor like "minimum
    # cash" reads backwards -- positive headroom would have meant *less* cash than
    # required. Fixed and covered by tests/test_guidelines.py.)
    out["headroom"] = out.apply(lambda r: (r.limit - r.current) if not r.higher_is_better else (r.current - r.limit), axis=1)
    return out.drop(columns="higher_is_better")


def overall_compliance(check: pd.DataFrame) -> tuple[str, list[str]]:
    breaches = check.loc[check.status == "RED", "guideline"].tolist()
    if breaches:
        return "NON-COMPLIANT", breaches
    return "COMPLIANT", []
