import numpy as np
from src.asset_model import (
    build_asset_portfolio, build_instrument_book, instrument_cash_flows,
    build_correlation_matrix, portfolio_expected_return, portfolio_volatility,
)


def test_weights_sum_to_one():
    A = build_asset_portfolio()
    assert abs(A.weight.sum() - 1.0) < 1e-9


def test_market_values_positive_and_sum_to_total():
    A = build_asset_portfolio(total_assets=1000.0)
    assert (A.market_value >= 0).all()
    assert abs(A.market_value.sum() - 1000.0) < 1e-6


def test_duration_non_negative():
    A = build_asset_portfolio()
    assert (A.duration >= 0).all()
    assert (A.modified_duration >= 0).all()


def test_dv01_sign_and_magnitude_consistent_with_duration():
    A = build_asset_portfolio()
    # DV01 should be (near) zero exactly where duration is zero (equities/real assets)
    zero_dur = A[A.duration == 0]
    assert (zero_dur.dv01.abs() < 1e-9).all()
    # and strictly positive wherever duration is positive
    pos_dur = A[A.duration > 0]
    assert (pos_dur.dv01 > 0).all()


def test_convexity_meaningfully_positive_for_bonds():
    """Regression test for the fixed convexity formula: a 5+ year modified-duration
    bond should have convexity of the right order of magnitude (years^2), not a
    near-zero placeholder."""
    A = build_asset_portfolio()
    govt = A[A.asset_class == "French Government Bonds"].iloc[0]
    assert govt.convexity > 10  # was ~0.56 under the old (duration**2)/100 bug


def test_instrument_book_sums_to_asset_book():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    assert abs(B.market_value.sum() - A.market_value.sum()) < 1e-6


def test_instrument_book_ids_unique():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    assert B.instrument_id.is_unique


def test_private_debt_cash_flows_decline_with_amortisation():
    """Regression test: private debt coupon must be charged on the declining
    balance, so cash flow should not be flat/increasing across years for a
    single instrument (interest component shrinks each year)."""
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    pd_instr = B[B.instrument_type == "Private debt"]
    assert len(pd_instr) > 0
    row = pd_instr.iloc[0]
    cf = instrument_cash_flows(B[B.instrument_id == row.instrument_id])
    cf = cf.sort_values("year")
    if len(cf) > 1:
        # interest portion shrinks -> total cash flow should be non-increasing
        assert (cf.cash_flow.diff().dropna() <= 1e-9).all()


def test_correlation_matrix_positive_semi_definite():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    eigvals = np.linalg.eigvalsh(C.values)
    assert (eigvals >= -1e-8).all()


def test_correlation_matrix_symmetric_unit_diagonal():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    assert np.allclose(C.values, C.values.T)
    assert np.allclose(np.diag(C.values), 1.0)


def test_portfolio_metrics_reasonable():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    er = portfolio_expected_return(A)
    vol = portfolio_volatility(A, C)
    assert 0 < er < 0.20
    assert 0 < vol < 0.30


def test_contractual_instrument_market_values_reconcile_by_class():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    by_book = B.groupby("asset_class").market_value.sum().sort_index()
    by_asset = A.set_index("asset_class").market_value.sort_index()
    assert np.allclose(by_book.reindex(by_asset.index).values, by_asset.values, atol=1e-8)

def test_bond_face_values_are_positive_and_not_forced_equal_to_market_value():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    bonds = B[B.instrument_type.isin(["Bond", "Private debt"])]
    assert (bonds.face_value > 0).all()
    assert (np.abs(bonds.face_value - bonds.market_value) > 1e-8).any()
