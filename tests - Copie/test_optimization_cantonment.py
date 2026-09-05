import numpy as np

from src.asset_model import build_asset_portfolio, build_correlation_matrix
from src.cantonment import cantonment_analysis
from src.liability_model import total_liability_metrics, projected_claims_12m
from src.optimization import optimize_allocation


def test_liability_aware_optimizer_respects_duration_and_liquidity_constraints():
    assets = build_asset_portfolio()
    corr = build_correlation_matrix(assets.asset_class.tolist())
    liab = total_liability_metrics()
    _, metrics = optimize_allocation(
        assets, corr, liab["modified_duration"], mode="Liability-Aware",
        duration_gap_tolerance=.75, liquidity_target=1.5,
        claims_12m=projected_claims_12m(), total_assets=assets.market_value.sum(),
    )
    assert metrics["success"]
    assert abs(metrics["duration_gap"]) <= .75 + 1e-6
    assert metrics["liquidity_coverage"] >= 1.5 - 1e-6


def test_cantonment_conserves_every_asset_class():
    assets = build_asset_portfolio()
    summary, allocation = cantonment_analysis(assets)
    assigned = allocation.groupby("asset_class").amount.sum()
    available = assets.set_index("asset_class").market_value
    assert np.allclose(assigned.reindex(available.index).fillna(0), available, atol=1e-7)
    assert abs(summary.assets_assigned.sum() - assets.market_value.sum()) < 1e-7


def test_cantonment_pool_liquidity_floor():
    assets = build_asset_portfolio()
    summary, _ = cantonment_analysis(assets, liquidity_target=1.2)
    assert (summary.liquidity_coverage_12m >= 1.2 - 1e-6).all()
