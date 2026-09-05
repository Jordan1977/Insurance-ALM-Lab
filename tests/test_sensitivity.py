import numpy as np

from src.asset_model import build_asset_portfolio
from src.sensitivity import tornado_analysis, top_risk_drivers, SENSITIVITY_SHOCKS


def test_tornado_covers_every_defined_shock():
    A = build_asset_portfolio()
    T = tornado_analysis(A)
    assert len(T) == len(SENSITIVITY_SHOCKS)
    assert set(T.factor) == {label for label, _ in SENSITIVITY_SHOCKS}


def test_tornado_sorted_by_absolute_surplus_impact_descending():
    A = build_asset_portfolio()
    T = tornado_analysis(A)
    assert (T.abs_surplus_impact.diff().dropna() <= 1e-9).all()


def test_tornado_rate_shocks_have_opposite_sign_asset_impact():
    A = build_asset_portfolio()
    T = tornado_analysis(A).set_index("factor")
    assert T.loc["Rates +100bp", "asset_impact"] < 0
    assert T.loc["Rates -100bp", "asset_impact"] > 0


def test_tornado_claims_severity_only_affects_liabilities():
    A = build_asset_portfolio()
    T = tornado_analysis(A).set_index("factor")
    row = T.loc["Claim severity +10%"]
    assert abs(row.asset_impact) < 1e-9
    assert row.liability_impact > 0
    assert row.surplus_impact < 0


def test_tornado_claims_frequency_only_affects_liabilities():
    A = build_asset_portfolio()
    T = tornado_analysis(A).set_index("factor")
    row = T.loc["Claim frequency +10%"]
    assert abs(row.asset_impact) < 1e-9
    assert row.liability_impact > 0
    assert row.surplus_impact < 0


def test_frequency_and_severity_shocks_have_equal_aggregate_impact():
    """Documented modelling simplification: at this aggregate ALM level,
    Claims = Frequency x Severity with no distributional convolution, so a
    +10% frequency shock and a +10% severity shock must produce identical
    aggregate liability impact (see expected_gross_claims docstring)."""
    A = build_asset_portfolio()
    T = tornado_analysis(A).set_index("factor")
    freq_impact = T.loc["Claim frequency +10%", "liability_impact"]
    sev_impact = T.loc["Claim severity +10%", "liability_impact"]
    assert abs(freq_impact - sev_impact) < 1e-6


def test_tornado_real_estate_shock_isolated_from_equity():
    """Regression test: a real-estate-only shock must not move equity-class assets."""
    A = build_asset_portfolio()
    T = tornado_analysis(A).set_index("factor")
    re_impact = T.loc["Real estate -10%", "asset_impact"]
    assert re_impact < 0
    # Magnitude should roughly match 10% of the real-estate+infrastructure book, not more.
    illiquid_mv = float(A.loc[A.asset_class.isin(["Real Estate", "Infrastructure"]), "market_value"].sum())
    assert abs(re_impact) <= illiquid_mv * .10 + 1e-6


def test_top_risk_drivers_returns_requested_count():
    A = build_asset_portfolio()
    T = tornado_analysis(A)
    drivers = top_risk_drivers(T, 3)
    assert len(drivers) == 3
    assert all(isinstance(d, str) for d in drivers)
