from src.asset_model import build_asset_portfolio
from src.scenario_generator import (
    apply_deterministic_scenario, deterministic_asset_attribution,
    evaluate_deterministic_scenario, DETERMINISTIC_SCENARIOS,
)


def test_named_scenario_still_works_after_refactor():
    """Regression test: passing a DETERMINISTIC_SCENARIOS key must behave
    exactly as before the dict-shock refactor."""
    A = build_asset_portfolio()
    stressed = apply_deterministic_scenario(A, "Rates +200bp")
    bonds = stressed[stressed.asset_class == "French Government Bonds"]
    assert (bonds.market_value_stressed < bonds.market_value).all()


def test_named_scenario_evaluate_matches_previous_semantics():
    A = build_asset_portfolio()
    result = evaluate_deterministic_scenario(A, "Stagflation")
    assert result["scenario"] == "Stagflation"
    # Surplus attribution must still reconcile exactly to delta surplus.
    total_attribution = sum(result["attribution"].values())
    assert abs(total_attribution - result["delta_surplus"]) < 1e-6


def test_custom_shock_dict_accepted():
    A = build_asset_portfolio()
    stressed = apply_deterministic_scenario(A, {"equity_shock": -.15})
    eq = stressed[stressed.asset_class == "Euro Equities"]
    assert (eq.market_value_stressed < eq.market_value).all()
    bonds = stressed[stressed.asset_class == "French Government Bonds"]
    assert (bonds.market_value_stressed == bonds.market_value).all()  # no rate shock applied


def test_real_estate_shock_key_isolated_and_backward_compatible():
    A = build_asset_portfolio()
    # Without real_estate_shock key: real assets fall back to 0.5x equity_shock (unchanged behaviour).
    default_behaviour = deterministic_asset_attribution(A, {"equity_shock": -.20})
    real_row = default_behaviour[default_behaviour.asset_class == "Real Estate"].iloc[0]
    re_mv = float(A.loc[A.asset_class == "Real Estate", "market_value"].iloc[0])
    assert abs(real_row.equity_real_pnl - re_mv * .5 * -.20) < 1e-9

    # With an explicit real_estate_shock key: isolated from equity_shock entirely.
    isolated = deterministic_asset_attribution(A, {"equity_shock": 0.0, "real_estate_shock": -.10})
    real_row2 = isolated[isolated.asset_class == "Real Estate"].iloc[0]
    assert abs(real_row2.equity_real_pnl - re_mv * -.10) < 1e-9
    equity_row = isolated[isolated.asset_class == "Euro Equities"].iloc[0]
    assert abs(equity_row.equity_real_pnl) < 1e-9


def test_severity_shock_isolated_from_inflation_shock():
    A = build_asset_portfolio()
    inflation_only = evaluate_deterministic_scenario(A, {}, extra_claim_inflation=.01)
    severity_only = evaluate_deterministic_scenario(A, {}, severity_shock=.10)
    # Both move liabilities up (surplus down) but via different, independent parameters.
    assert inflation_only["delta_surplus"] < 0
    assert severity_only["delta_surplus"] < 0
    assert inflation_only["stressed_liabilities"] != severity_only["stressed_liabilities"]


def test_frequency_shock_parameter_isolated_and_asset_side_unaffected():
    A = build_asset_portfolio()
    result = evaluate_deterministic_scenario(A, {}, frequency_shock=.10)
    assert result["stressed_assets"] == result["base_assets"]  # no asset-side shock applied
    assert result["stressed_liabilities"] > result["base_liabilities"]
    assert result["delta_surplus"] < 0


def test_all_named_scenarios_still_evaluate_without_error():
    A = build_asset_portfolio()
    for name in DETERMINISTIC_SCENARIOS:
        result = evaluate_deterministic_scenario(A, name)
        assert result["scenario"] == name
        assert result["stressed_assets"] > 0
        assert result["stressed_liabilities"] > 0
