"""Market, liquidity, concentration and surplus-risk metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from src.utils import status_flag


def parametric_var(mu: float, sigma: float, confidence: float, horizon_years: float = 1.0) -> float:
    z = norm.ppf(confidence)
    return max(-(mu * horizon_years - z * sigma * np.sqrt(horizon_years)), 0.0)


def parametric_cvar(mu: float, sigma: float, confidence: float, horizon_years: float = 1.0) -> float:
    z = norm.ppf(confidence)
    return max(-(mu * horizon_years - sigma * np.sqrt(horizon_years) * norm.pdf(z) / (1 - confidence)), 0.0)


def sharpe_ratio(mu: float, sigma: float, rf: float = .025) -> float:
    return (mu - rf) / sigma if sigma else 0.0


def sortino_ratio(mu: float, downside: float, rf: float = .025) -> float:
    return (mu - rf) / downside if downside else 0.0


def liquidity_coverage_ratio(liquid_assets: float, claims_12m: float) -> float:
    return liquid_assets / claims_12m if claims_12m else np.inf


def classify_liquidity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["liquidity_bucket"] = out.liquidity_score.apply(
        lambda x: "Highly Liquid" if x >= .85 else "Liquid" if x >= .60 else "Semi-Liquid" if x >= .30 else "Illiquid"
    )
    return out


def liquidity_stress(asset_df: pd.DataFrame, claims_12m: float,
                     claims_multiplier: float = 1.20,
                     liquid_haircut: float = .05,
                     semi_liquid_haircut: float = .20) -> dict[str, float]:
    """Illustrative one-year liquidity stress, not a regulatory liquidity metric."""
    liq = classify_liquidity(asset_df)
    highly_liquid = float(liq.loc[liq.liquidity_bucket == "Highly Liquid", "market_value"].sum())
    liquid = float(liq.loc[liq.liquidity_bucket == "Liquid", "market_value"].sum())
    semi = float(liq.loc[liq.liquidity_bucket == "Semi-Liquid", "market_value"].sum())
    base_available = highly_liquid + liquid
    stressed_available = highly_liquid * (1 - liquid_haircut) + liquid * (1 - liquid_haircut) + semi * .25 * (1 - semi_liquid_haircut)
    stressed_claims = claims_12m * claims_multiplier
    return {
        "base_available_liquidity": base_available,
        "stressed_available_liquidity": stressed_available,
        "base_claims_12m": claims_12m,
        "stressed_claims_12m": stressed_claims,
        "base_coverage": base_available / claims_12m if claims_12m else np.inf,
        "stressed_coverage": stressed_available / stressed_claims if stressed_claims else np.inf,
        "liquidity_buffer": stressed_available - stressed_claims,
    }


def surplus_at_risk(base_surplus: float, simulated_surplus, confidence: float = .99) -> dict[str, float]:
    sims = np.asarray(simulated_surplus, dtype=float)
    q = float(np.quantile(sims, 1 - confidence))
    tail = sims[sims <= q]
    tail_mean = float(tail.mean()) if len(tail) else q
    return {
        "quantile": q,
        "surplus_at_risk": max(base_surplus - q, 0.0),
        "expected_shortfall": max(base_surplus - tail_mean, 0.0),
    }


def alm_audit_score(kpis: dict, equity_risk: float, lcr: float,
                    largest_weight: float = .25, illiquid_weight: float = 0.0,
                    equity_weight: float = 0.0, hy_weight: float = 0.0,
                    fx_weight: float = 0.0) -> pd.DataFrame:
    rows = [
        ("Economic Coverage", "A/L Coverage", kpis["economic_coverage_ratio"], 1.10, status_flag(kpis["economic_coverage_ratio"], 1.15, 1.05, True), "Economic assets / PV modelled liabilities; not a Solvency II ratio."),
        ("Duration Matching", "|Duration Gap|", abs(kpis["duration_gap"]), 1.0, status_flag(abs(kpis["duration_gap"]), .5, 1.0, False), "Parallel-rate sensitivity mismatch."),
        ("Liquidity", "12M Claims Coverage", lcr, 1.5, status_flag(lcr, 1.5, 1.2, True), "Illustrative internal indicator; not regulatory LCR."),
        ("Market Risk", "Equity Risk Contribution", equity_risk, .40, status_flag(equity_risk, .40, .50, False), "Share of total modelled asset volatility contributed by equities."),
        ("Concentration", "Largest Asset-Class Weight", largest_weight, .30, status_flag(largest_weight, .25, .30, False), "Largest strategic asset-class weight."),
    ]
    if illiquid_weight:
        rows.append(("Liquidity", "Illiquid Asset Weight", illiquid_weight, .20, status_flag(illiquid_weight, .15, .20, False), "Real estate, infrastructure and private-debt allocation."))
    if hy_weight:
        rows.append(("Credit", "High Yield Weight", hy_weight, .10, status_flag(hy_weight, .07, .10, False), "Synthetic High Yield allocation."))
    if fx_weight:
        rows.append(("FX", "Gross FX Weight", fx_weight, .10, status_flag(fx_weight, .08, .12, False), "Gross USD plus 50% proxy of mixed-currency global equities."))
    out = pd.DataFrame(rows, columns=["dimension", "metric", "value", "target", "status", "comment"])
    return out


def herfindahl_index(weights) -> float:
    w = np.asarray(weights, dtype=float)
    total = w.sum()
    if total <= 0:
        return 0.0
    w = w / total
    return float((w**2).sum())


def concentration_report(asset_df: pd.DataFrame) -> pd.DataFrame:
    dims = [("asset_class", "Asset class"), ("rating", "Rating"), ("currency", "Currency"), ("geography", "Geography")]
    rows = []
    for col, label in dims:
        if col not in asset_df.columns:
            continue
        grouped = asset_df.groupby(col).market_value.sum()
        rows.append({
            "dimension": label,
            "hhi": herfindahl_index(grouped.values),
            "largest_bucket": grouped.idxmax(),
            "largest_bucket_weight": float(grouped.max() / grouped.sum()),
        })
    return pd.DataFrame(rows)
