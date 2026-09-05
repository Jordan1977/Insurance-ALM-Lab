"""Convenience assembly layer for UI pages.

Keeps Streamlit pages declarative while all calculations remain in testable
financial-engine modules.
"""
from __future__ import annotations

from src.asset_model import (
    build_asset_portfolio,
    build_correlation_matrix,
    portfolio_modified_duration,
    portfolio_asset_dv01,
    portfolio_expected_return,
    portfolio_volatility,
    risk_contribution,
    fx_exposure,
)
from src.liability_model import total_liability_metrics, projected_claims_12m, build_liability_cash_flows
from src.alm_engine import alm_kpis
from src.risk_engine import classify_liquidity, liquidity_coverage_ratio
from src.scenario_generator import evaluate_deterministic_scenario
from src.reinsurance import DEFAULT_TREATY, ExcessOfLossTreaty, total_net_liability_metrics, reinsurance_summary


def base_analytics(asset_weights=None, discount_rate=.03, claim_inflation=.025,
                   fx_hedge_ratio=.5, treaty: ExcessOfLossTreaty = DEFAULT_TREATY):
    """Central assembly used by every page. The headline economic balance
    sheet (`kpis`) is NET of reinsurance (Section 4 of the V6 brief); GROSS
    figures remain available under `liabilities_gross` / `reinsurance` for
    the Reinsurance and Non-Life Liabilities pages, and are never silently
    mixed with the net headline numbers."""
    assets = build_asset_portfolio(asset_weights)
    corr = build_correlation_matrix(assets.asset_class.tolist())
    liabilities_gross = total_liability_metrics(discount_rate, claim_inflation)
    liabilities_net = total_net_liability_metrics(discount_rate, claim_inflation, treaty)
    kpis = alm_kpis(
        float(assets.market_value.sum()),
        liabilities_net["present_value"],
        portfolio_modified_duration(assets),
        liabilities_net["modified_duration"],
        portfolio_asset_dv01(assets),
        liabilities_net["dv01"],
    )
    gross_cf = build_liability_cash_flows(claim_inflation)
    reins = reinsurance_summary(gross_cf, treaty)
    liq = classify_liquidity(assets)
    liquid_assets = float(liq.loc[liq.liquidity_bucket.isin(["Highly Liquid", "Liquid"]), "market_value"].sum())
    # Liquidity coverage uses the year-1 INTERIM liquidity requirement (gross
    # claims paid out this year, less any recovery cash actually received
    # this year) rather than the ultimate net claim cost -- Section 13/22:
    # a treaty can lower the ultimate loss while still leaving a near-term
    # cash gap if recoveries lag the claim payment.
    claims_12m_liquidity = float(reins["liquidity_detail"].loc[reins["liquidity_detail"].year == reins["liquidity_detail"].year.min(), "net_liquidity_impact_this_year"].iloc[0])
    lcr = liquidity_coverage_ratio(liquid_assets, claims_12m_liquidity)
    rc = risk_contribution(assets, corr)
    eq_risk = float(rc.loc[rc.asset_class.isin({"Euro Equities", "US Equities", "Global Equities"}), "pct_of_total_risk"].sum())
    return {
        "assets": assets,
        "corr": corr,
        "liabilities": liabilities_net,
        "liabilities_gross": liabilities_gross,
        "reinsurance": reins,
        "treaty": treaty,
        "kpis": kpis,
        "liquid_assets": liquid_assets,
        "claims_12m": claims_12m_liquidity,
        "claims_12m_gross": reins["claims_12m_gross"],
        "claims_12m_net_ultimate": reins["claims_12m_net"],
        "liquidity_coverage": lcr,
        "risk_contribution": rc,
        "equity_risk_contribution": eq_risk,
        "expected_return": portfolio_expected_return(assets),
        "volatility": portfolio_volatility(assets, corr),
        "fx": fx_exposure(assets, fx_hedge_ratio),
    }


def scenario_analytics(base: dict, scenario: str, discount_rate=.03,
                       claim_inflation=.025, fx_hedge_ratio=.5):
    if scenario == "Base":
        return {
            "scenario": "Base",
            "stressed_assets": base["kpis"]["total_assets"],
            "stressed_liabilities": base["kpis"]["total_liabilities"],
            "surplus": base["kpis"]["surplus"],
            "coverage": base["kpis"]["economic_coverage_ratio"],
            "delta_surplus": 0.0,
            "attribution": {},
        }
    return evaluate_deterministic_scenario(base["assets"], scenario, discount_rate, claim_inflation, fx_hedge_ratio)
