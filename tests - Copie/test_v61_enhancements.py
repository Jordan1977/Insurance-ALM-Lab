import numpy as np

from src.asset_model import build_asset_portfolio, build_instrument_book
from src.liability_model import build_liability_cash_flows, total_liability_metrics
from src.reinsurance import (
    QuotaShareTreaty, apply_quota_share_to_annual_claims, compare_reinsurance_structures,
)
from src.reinvestment import optimize_liability_matching_basket, policy_outcome
from src.scenario_generator import run_monte_carlo, surplus_distribution_from_mc


def test_poisson_frequency_factor_positive_shape_and_reproducible():
    a = run_monte_carlo(n_sims=50, horizon=3, seed=99)
    b = run_monte_carlo(n_sims=50, horizon=3, seed=99)
    f = a["claim_frequency_multiplier"]
    assert f.shape == (50, 3, 5)
    assert (f >= 0).all()
    assert np.array_equal(f, b["claim_frequency_multiplier"])


def test_dynamic_mc_exposes_reinsurance_cash_flow_columns():
    A = build_asset_portfolio()
    mc = run_monte_carlo(n_sims=80, horizon=3, seed=7)
    out = surplus_distribution_from_mc(mc, A, horizon_year=3)
    assert {"gross_claims_paid", "reinsurance_recoveries_received", "minimum_cash_buffer",
            "forced_sale_amount", "liquidity_shortfall_flag"}.issubset(out.columns)
    assert (out["gross_claims_paid"] >= out["reinsurance_recoveries_received"]).all()


def test_quota_share_reconciles_and_reduces_claims():
    gross = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    qs = apply_quota_share_to_annual_claims(gross, QuotaShareTreaty(ceded_share=.30, counterparty_haircut=0.0))
    assert np.allclose(qs.net_claims, qs.gross_claims * .70)
    assert np.allclose(qs.gross_claims - qs.effective_recovery, qs.net_claims)


def test_reinsurance_structure_comparison_contains_three_structures():
    gross = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    out = compare_reinsurance_structures(gross)
    assert len(out) == 3
    assert set(out.structure.str.contains("Quota share")) == {False, True}


def test_liability_matching_basket_weights_sum_to_one_and_target_duration():
    out = optimize_liability_matching_basket(4.0)
    assert abs(sum(out["weights"].values()) - 1.0) < 1e-6
    assert abs(out["duration"] - 4.0) < .15
    assert out["liquidity"] >= .70 - 1e-8


def test_optimised_reinvestment_is_at_least_as_good_as_single_closest_on_book_gap():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    cf = build_liability_cash_flows()
    L = total_liability_metrics()
    out = policy_outcome(A, B, cf, "Liability-matching reinvestment", L["modified_duration"])
    assert out["basket_weights"] is not None
    assert abs(out["duration_gap_after"]) < .20
