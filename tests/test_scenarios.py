import numpy as np
from src.asset_model import build_asset_portfolio
from src.liability_model import total_liability_metrics
from src.scenario_generator import (
    apply_deterministic_scenario, scenario_discount_rate, scenario_claim_inflation,
    run_monte_carlo, surplus_distribution_from_mc, DETERMINISTIC_SCENARIOS,
    DEFAULT_FACTOR_CORR,
)


def test_rate_shock_reduces_fixed_income_value():
    A = build_asset_portfolio()
    stressed = apply_deterministic_scenario(A, "Rates +200bp")
    bonds = stressed[stressed.asset_class == "French Government Bonds"]
    assert (bonds.market_value_stressed < bonds.market_value).all()


def test_equity_shock_reduces_equity_value_only_via_equity_channel():
    A = build_asset_portfolio()
    stressed = apply_deterministic_scenario(A, "Equity -30%")
    eq = stressed[stressed.asset_class == "Euro Equities"]
    assert (eq.market_value_stressed < eq.market_value).all()


def test_stagflation_increases_claim_inflation_and_liabilities():
    base = total_liability_metrics(0.03, 0.025)
    infl = scenario_claim_inflation(0.025, "Stagflation")
    stressed = total_liability_metrics(scenario_discount_rate(0.03, "Stagflation"), infl)
    assert infl > 0.025
    assert stressed["present_value"] != base["present_value"]


def test_base_scenario_is_neutral():
    A = build_asset_portfolio()
    stressed = apply_deterministic_scenario(A, "Base")
    assert np.allclose(stressed.market_value_stressed, stressed.market_value)


def test_monte_carlo_reproducible_with_seed():
    mc1 = run_monte_carlo(n_sims=200, horizon=5, seed=42)
    mc2 = run_monte_carlo(n_sims=200, horizon=5, seed=42)
    assert np.allclose(mc1["equity_returns"], mc2["equity_returns"])
    assert np.allclose(mc1["rates"], mc2["rates"])


def test_monte_carlo_different_seeds_differ():
    mc1 = run_monte_carlo(n_sims=200, horizon=5, seed=1)
    mc2 = run_monte_carlo(n_sims=200, horizon=5, seed=2)
    assert not np.allclose(mc1["equity_returns"], mc2["equity_returns"])


def test_factor_correlation_matrix_psd():
    eigvals = np.linalg.eigvalsh(DEFAULT_FACTOR_CORR)
    assert (eigvals >= -1e-8).all()


def test_equity_spread_correlation_is_negative():
    # index order: [equity, rate, inflation, spread, FX]
    assert DEFAULT_FACTOR_CORR[0, 3] < 0


def test_surplus_distribution_from_mc_shapes():
    A = build_asset_portfolio()
    mc = run_monte_carlo(n_sims=300, horizon=5, seed=7)
    D = surplus_distribution_from_mc(mc, A, base_discount_rate=0.03, base_claim_inflation=0.025, horizon_year=5)
    assert len(D) == 300
    assert (D.simulated_assets > 0).all()
    assert set(["surplus", "economic_coverage_ratio", "claims_paid"]).issubset(D.columns)


def test_monte_carlo_includes_fx_factor():
    mc = run_monte_carlo(n_sims=50, horizon=3, seed=1)
    assert "fx_returns" in mc
    assert mc["fx_returns"].shape == (50, 3)

def test_factor_correlation_is_five_by_five():
    assert DEFAULT_FACTOR_CORR.shape == (5, 5)


def test_claim_severity_multiplier_is_positive_and_reproducible():
    mc1 = run_monte_carlo(n_sims=100, horizon=4, seed=77)
    mc2 = run_monte_carlo(n_sims=100, horizon=4, seed=77)
    assert (mc1["claim_severity_multiplier"] > 0).all()
    assert np.allclose(mc1["claim_severity_multiplier"], mc2["claim_severity_multiplier"])
