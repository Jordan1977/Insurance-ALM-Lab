import numpy as np
from src.asset_model import build_asset_portfolio, build_correlation_matrix, portfolio_asset_dv01
from src.liability_model import total_liability_metrics
from src.risk_engine import (
    parametric_var, parametric_cvar, sharpe_ratio, liquidity_coverage_ratio,
    surplus_at_risk, herfindahl_index, concentration_report, liquidity_stress,
)
from src.hedging_engine import rate_hedge, equity_hedge, fx_hedge
from src.optimization import optimize_allocation
from src.cantonment import cantonment_analysis
from src.validation import full_data_quality_report, overall_status
from src.data_loader import DATA_DIR
import pandas as pd
import os


def test_var_non_negative():
    assert parametric_var(0.05, 0.15, 0.99) >= 0


def test_cvar_greater_than_or_equal_to_var():
    v = parametric_var(0.05, 0.15, 0.99)
    cv = parametric_cvar(0.05, 0.15, 0.99)
    assert cv >= v


def test_sharpe_ratio_basic():
    assert abs(sharpe_ratio(0.06, 0.10, 0.025) - 0.35) < 1e-9


def test_liquidity_coverage_ratio():
    assert liquidity_coverage_ratio(150, 100) == 1.5


def test_surplus_at_risk_non_negative_and_floored():
    sims = np.random.default_rng(0).normal(100, 20, 5000)
    r = surplus_at_risk(base_surplus=100, simulated_surplus=sims, confidence=0.99)
    assert r["surplus_at_risk"] >= 0
    assert r["expected_shortfall"] >= r["surplus_at_risk"] - 1e-6


def test_hhi_bounds():
    assert herfindahl_index([1, 0, 0, 0]) == 1.0
    assert abs(herfindahl_index([1, 1, 1, 1]) - 0.25) < 1e-9


def test_concentration_report_shape():
    A = build_asset_portfolio()
    rep = concentration_report(A)
    assert "hhi" in rep.columns
    assert (rep.hhi > 0).all()


def test_rate_hedge_reduces_dv01_gap():
    A = build_asset_portfolio()
    L = total_liability_metrics()
    adv = portfolio_asset_dv01(A)
    H = rate_hedge(adv, L["dv01"])
    assert abs(H["after_gap"]) <= abs(H["before_gap"]) + 1e-9


def test_equity_hedge_improves_stress_pnl():
    E = equity_hedge(equity_exposure=100, hedge_ratio=0.5, shock=-0.30)
    assert E["stress_pnl_after"] > E["stress_pnl_before"]


def test_fx_hedge_reduces_net_exposure_and_improves_pnl_on_adverse_move():
    F = fx_hedge(gross_fx_exposure=100, hedge_ratio=0.5, fx_shock=-0.10)
    assert F["net_exposure"] < F["gross_exposure"]
    assert F["stress_pnl_after"] > F["stress_pnl_before"]


def test_optimized_weights_sum_to_one():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    L = total_liability_metrics()
    W, M = optimize_allocation(A, C, L["modified_duration"], mode="Liability-Aware")
    assert abs(W.optimized_weight.sum() - 1.0) < 1e-4


def test_cantonment_assets_sum_to_total():
    A = build_asset_portfolio()
    D, allocation = cantonment_analysis(A)
    assert abs(D.assets_assigned.sum() - A.market_value.sum()) < 1e-3
    # every strategic asset-class euro is conserved across liability pools
    assigned = allocation.groupby("asset_class").amount.sum()
    available = A.set_index("asset_class").market_value
    assert np.allclose(assigned.reindex(available.index).fillna(0).values, available.values, atol=1e-6)


def test_data_quality_passes_on_shipped_csv_snapshots():
    asset_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_assets.csv"))
    instr_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_instrument_book.csv"))
    liab_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_liabilities.csv"))
    curve_df = pd.read_csv(os.path.join(DATA_DIR, "synthetic_yield_curve.csv"))
    report = full_data_quality_report(asset_df, instr_df, liab_df, curve_df)
    assert overall_status(report) == "PASS", report[report.status == "FAIL"]


def test_liquidity_stress_increases_claims_and_remains_finite():
    A = build_asset_portfolio()
    out = liquidity_stress(A, 250.0, claims_multiplier=1.2)
    assert out["stressed_claims_12m"] == 300.0
    assert np.isfinite(out["stressed_coverage"])

def test_rate_hedge_notional_is_realistic_order_of_magnitude():
    A = build_asset_portfolio()
    L = total_liability_metrics()
    H = rate_hedge(portfolio_asset_dv01(A), L["dv01"], hedge_ratio=1.0)
    assert 50 < H["notional_m"] < 250
    assert abs(H["after_gap"]) < 1e-9
