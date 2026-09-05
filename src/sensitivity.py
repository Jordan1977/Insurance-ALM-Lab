"""ALM sensitivity / tornado analysis.

Every shock below is evaluated by calling `evaluate_deterministic_scenario`
(src/scenario_generator.py) with an isolated single-factor shock dict -- the
exact same function used by the Economic Scenarios and Stress Testing pages.
No formula is duplicated here: this module only defines *which* one-at-a-time
shocks to run and packages the results for a tornado chart.
"""
from __future__ import annotations

import pandas as pd

from src.scenario_generator import evaluate_deterministic_scenario

# (label, shock kwargs passed straight through to evaluate_deterministic_scenario)
SENSITIVITY_SHOCKS: list[tuple[str, dict]] = [
    ("Rates +100bp", dict(name_or_shock={"d_rate": .01})),
    ("Rates -100bp", dict(name_or_shock={"d_rate": -.01})),
    ("Claim inflation +1pp", dict(name_or_shock={}, extra_claim_inflation=.01)),
    ("Claim frequency +10%", dict(name_or_shock={}, frequency_shock=.10)),
    ("Claim severity +10%", dict(name_or_shock={}, severity_shock=.10)),
    ("Equity -10%", dict(name_or_shock={"equity_shock": -.10})),
    ("Equity -20%", dict(name_or_shock={"equity_shock": -.20})),
    ("Credit spreads +50bp", dict(name_or_shock={"credit_spread_shock": .005})),
    ("Credit spreads +100bp", dict(name_or_shock={"credit_spread_shock": .01})),
    ("EUR appreciation +10%", dict(name_or_shock={"fx_shock": -.10})),
    ("EUR depreciation -10%", dict(name_or_shock={"fx_shock": .10})),
    ("Real estate -10%", dict(name_or_shock={"real_estate_shock": -.10})),
]


def tornado_analysis(asset_df: pd.DataFrame, base_discount_rate: float = .03,
                     base_claim_inflation: float = .025, fx_hedge_ratio: float = .0) -> pd.DataFrame:
    """Run every single-factor shock in SENSITIVITY_SHOCKS and rank by absolute
    surplus impact. Each row also carries the asset-side and liability-side
    impact so a reader can see *why* a factor moves the surplus."""
    rows = []
    for label, kwargs in SENSITIVITY_SHOCKS:
        result = evaluate_deterministic_scenario(
            asset_df, base_discount_rate=base_discount_rate,
            base_claim_inflation=base_claim_inflation, fx_hedge_ratio=fx_hedge_ratio,
            label=label, **kwargs,
        )
        asset_impact = result["stressed_assets"] - result["base_assets"]
        liability_impact = result["stressed_liabilities"] - result["base_liabilities"]
        rows.append({
            "factor": label,
            "asset_impact": asset_impact,
            "liability_impact": liability_impact,
            "surplus_impact": result["delta_surplus"],
            "coverage_impact": result["coverage"] - result["base_coverage"],
        })
    out = pd.DataFrame(rows)
    out["abs_surplus_impact"] = out.surplus_impact.abs()
    return out.sort_values("abs_surplus_impact", ascending=False).reset_index(drop=True)


def top_risk_drivers(tornado: pd.DataFrame, n: int = 3) -> list[str]:
    """Plain-language top-N risk drivers, generated only from computed values
    (no hardcoded commentary) -- feeds both the Sensitivity page and the
    Investment Committee Pack (single source, per the no-duplication rule)."""
    out = []
    for _, row in tornado.head(n).iterrows():
        direction = "reduces" if row.surplus_impact < 0 else "increases"
        out.append(f"{row.factor} {direction} economic surplus by €{abs(row.surplus_impact):,.0f}m (coverage {row.coverage_impact:+.1%}).")
    return out
