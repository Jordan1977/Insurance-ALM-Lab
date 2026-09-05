from src.asset_model import build_asset_portfolio, build_instrument_book, instrument_cash_flows, portfolio_modified_duration, portfolio_asset_dv01
from src.liability_model import build_liability_cash_flows, total_liability_metrics
from src.alm_engine import (
    economic_coverage_ratio, surplus, duration_gap, alm_kpis,
    cash_flow_matching_table, maturity_bucket_matching,
)


def test_economic_coverage_ratio_basic():
    assert economic_coverage_ratio(120, 100) == 1.2


def test_surplus_basic():
    assert surplus(120, 100) == 20


def test_duration_gap_sign():
    assert duration_gap(5.0, 7.0) == -2.0


def test_alm_kpis_internally_consistent():
    K = alm_kpis(1150, 1000, 6.0, 7.0, 0.5, 0.6)
    assert K["surplus"] == 150
    assert abs(K["economic_coverage_ratio"] - 1.15) < 1e-9
    assert K["duration_gap"] == -1.0
    assert abs(K["dv01_gap"] - (-0.1)) < 1e-9


def test_cash_flow_matching_table_shape_and_gap():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    ACF = instrument_cash_flows(B)
    LCF = build_liability_cash_flows()
    T = cash_flow_matching_table(ACF, LCF)
    assert set(["asset_cf", "liability_cf", "coverage_ratio", "gap", "shortfall"]).issubset(T.columns)
    assert (T.gap == T.asset_cf - T.liability_cf).all()


def test_maturity_bucket_matching_covers_all_buckets():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    ACF = instrument_cash_flows(B)
    LCF = build_liability_cash_flows()
    M = maturity_bucket_matching(ACF, LCF)
    from src.utils import BUCKET_ORDER
    assert list(M.bucket) == BUCKET_ORDER


def test_coverage_matches_base_case_target_range():
    """The synthetic book is designed to start at ~115-120% coverage
    (a deliberate pedagogical buffer for stress testing)."""
    A = build_asset_portfolio()
    L = total_liability_metrics()
    cov = A.market_value.sum() / L["present_value"]
    assert 1.05 < cov < 1.35
