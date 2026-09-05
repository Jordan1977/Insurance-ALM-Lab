from src.asset_model import build_asset_portfolio, build_correlation_matrix, risk_contribution
from src.performance_attribution import performance_attribution, return_vs_risk_contribution, SYNTHETIC_TRAILING_12M_SHOCK


def test_performance_attribution_reconciles_to_total_return():
    A = build_asset_portfolio()
    detail, summary = performance_attribution(A)
    assert abs(summary["reconciled_total"] - summary["total_return"]) < 1e-9


def test_beginning_plus_total_pnl_equals_ending_mv():
    A = build_asset_portfolio()
    detail, summary = performance_attribution(A)
    assert abs(summary["beginning_mv"] + summary["total_pnl"] - summary["ending_mv"]) < 1e-6


def test_per_row_beginning_plus_pnl_equals_ending():
    A = build_asset_portfolio()
    detail, _ = performance_attribution(A)
    residual = (detail.beginning_mv + detail.total_pnl - detail.ending_mv).abs()
    assert (residual < 1e-9).all()


def test_per_row_pnl_components_sum_to_total_pnl():
    A = build_asset_portfolio()
    detail, _ = performance_attribution(A)
    components = detail.carry_pnl + detail.rate_pnl + detail.spread_pnl + detail.equity_real_pnl + detail.fx_pnl
    assert (components - detail.total_pnl).abs().max() < 1e-9


def test_no_field_named_historical_return_exists():
    """Regression test for the V6 'major correction': no attribute in the
    asset book or attribution output should claim to be a historical
    observation when it is actually synthetic."""
    A = build_asset_portfolio()
    assert "historical_return_1y" not in A.columns
    detail, summary = performance_attribution(A)
    assert not any("historical" in c.lower() for c in detail.columns)
    assert not any("historical" in k.lower() for k in summary.keys())


def test_shock_is_clearly_labelled_and_not_random_noise():
    """The synthetic shock must be a fixed, documented dict -- not sampled
    noise -- so results are exactly reproducible without a seed."""
    A = build_asset_portfolio()
    _, summary1 = performance_attribution(A)
    _, summary2 = performance_attribution(A)
    assert summary1["total_return"] == summary2["total_return"]
    assert summary1["shock_applied"] == SYNTHETIC_TRAILING_12M_SHOCK


def test_return_vs_risk_contribution_shapes_and_sums():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    rc = risk_contribution(A, C)
    detail, _ = performance_attribution(A)
    cmp = return_vs_risk_contribution(detail, rc)
    assert abs(cmp.pct_of_total_return.sum() - 1.0) < 1e-6
    assert abs(cmp.pct_of_total_risk.sum() - 1.0) < 1e-6
