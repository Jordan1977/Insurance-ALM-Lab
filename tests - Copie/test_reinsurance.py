import numpy as np
import pytest

from src.liability_model import build_liability_cash_flows
from src.reinsurance import (
    ExcessOfLossTreaty, apply_reinsurance_to_annual_claims,
    net_liability_cash_flows, liquidity_impact, reinsurance_summary,
)


def test_net_claims_equals_gross_minus_effective_recovery():
    cf = build_liability_cash_flows()
    gross_by_year = cf.groupby("year")["cash_flow"].sum()
    result = apply_reinsurance_to_annual_claims(gross_by_year)
    residual = (result.net_claims - (result.gross_claims - result.effective_recovery)).abs()
    assert (residual < 1e-9).all()


def test_no_recovery_below_retention():
    treaty = ExcessOfLossTreaty(retention=1_000.0, limit=500.0)  # retention above any single year's claims
    cf = build_liability_cash_flows()
    gross_by_year = cf.groupby("year")["cash_flow"].sum()
    result = apply_reinsurance_to_annual_claims(gross_by_year, treaty)
    assert (result.effective_recovery == 0).all()
    assert np.allclose(result.net_claims, result.gross_claims)


def test_recovery_capped_at_limit():
    treaty = ExcessOfLossTreaty(retention=0.0, limit=50.0, recovery_rate=1.0, counterparty_haircut=0.0)
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    result = apply_reinsurance_to_annual_claims(gross_by_year, treaty)
    assert (result.gross_recovery <= 50.0 + 1e-9).all()


def test_higher_recovery_rate_reduces_net_claims():
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    low = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(retention=150.0, limit=300.0, recovery_rate=.5))
    high = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(retention=150.0, limit=300.0, recovery_rate=1.0))
    assert high.net_claims.sum() < low.net_claims.sum()


def test_counterparty_haircut_reduces_effective_recovery():
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    active_treaty_kwargs = dict(retention=150.0, limit=300.0, recovery_rate=1.0)
    no_haircut = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(counterparty_haircut=0.0, **active_treaty_kwargs))
    with_haircut = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(counterparty_haircut=.20, **active_treaty_kwargs))
    assert with_haircut.effective_recovery.sum() < no_haircut.effective_recovery.sum()
    assert with_haircut.net_claims.sum() > no_haircut.net_claims.sum()


def test_net_liability_cash_flows_reconcile_to_annual_net():
    cf = build_liability_cash_flows()
    treaty = ExcessOfLossTreaty()
    net_cf = net_liability_cash_flows(cf, treaty)
    gross_by_year = cf.groupby("year")["cash_flow"].sum()
    treaty_result = apply_reinsurance_to_annual_claims(gross_by_year, treaty).set_index("year")
    net_by_year = net_cf.groupby("year")["cash_flow"].sum()
    for year in gross_by_year.index:
        assert abs(net_by_year[year] - treaty_result.loc[year, "net_claims"]) < 1e-6


def test_net_liability_cash_flows_never_exceed_gross():
    cf = build_liability_cash_flows()
    net_cf = net_liability_cash_flows(cf)
    assert (net_cf["cash_flow"] <= net_cf["gross_cash_flow"] + 1e-9).all()


def test_recovery_lag_shifts_cash_receipt_not_ultimate_cost():
    """Section 13: a longer recovery lag must not change the ultimate net
    claim cost, only when the offsetting cash is actually received."""
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    fast = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(recovery_lag=0))
    slow = apply_reinsurance_to_annual_claims(gross_by_year, ExcessOfLossTreaty(recovery_lag=3))
    assert np.allclose(fast.net_claims, slow.net_claims)  # ultimate cost unchanged
    assert not np.array_equal(fast.recovery_received_year, slow.recovery_received_year)  # timing changed


def test_liquidity_impact_shows_temporary_gap_before_recovery_arrives():
    treaty = ExcessOfLossTreaty(retention=100.0, limit=1000.0, recovery_rate=1.0, recovery_lag=2, counterparty_haircut=0.0)
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    result = apply_reinsurance_to_annual_claims(gross_by_year, treaty)
    liq = liquidity_impact(result)
    # The very first year a recovery is earned, no cash can have arrived yet
    # (recovery_lag=2), so that year must show a full, unmitigated outflow.
    first_earning_year = result.loc[result.effective_recovery > 0, "year"].min()
    row = liq.loc[liq.year == first_earning_year].iloc[0]
    assert row.cash_inflow_this_year == 0.0
    assert row.net_liquidity_impact_this_year == row.gross_claims
    # But the ultimate net claim cost for that same year IS reduced by the
    # (not-yet-received) recovery -- this is exactly the point of Section 13:
    # a treaty can lower the ultimate loss while still leaving a temporary gap.
    treaty_row = result.loc[result.year == first_earning_year].iloc[0]
    assert treaty_row.net_claims < treaty_row.gross_claims


def test_recovery_lag_never_improves_immediate_liquidity():
    """Sanity test (V6.3, Part 20/29 of the brief): a longer recovery lag
    must never improve the immediate (year-1) liquidity impact -- it can
    only leave it unchanged or worse, never better, since cash cannot
    arrive before it is received."""
    gross_by_year = build_liability_cash_flows().groupby("year")["cash_flow"].sum()
    impacts = []
    for lag in [0, 1, 3]:
        treaty = ExcessOfLossTreaty(retention=100.0, limit=1000.0, recovery_rate=1.0, recovery_lag=lag, counterparty_haircut=0.0)
        result = apply_reinsurance_to_annual_claims(gross_by_year, treaty)
        liq = liquidity_impact(result)
        impacts.append(float(liq.loc[liq.year == 1, "net_liquidity_impact_this_year"].iloc[0]))
    assert impacts == sorted(impacts)  # non-decreasing as lag increases


def test_invalid_treaty_parameters_rejected():
    with pytest.raises(ValueError):
        ExcessOfLossTreaty(retention=-1.0)
    with pytest.raises(ValueError):
        ExcessOfLossTreaty(recovery_rate=1.5)
    with pytest.raises(ValueError):
        ExcessOfLossTreaty(counterparty_haircut=-.1)
    with pytest.raises(ValueError):
        ExcessOfLossTreaty(recovery_lag=-1)


def test_reinsurance_summary_shape():
    cf = build_liability_cash_flows()
    summary = reinsurance_summary(cf)
    assert summary["total_net_claims"] == pytest.approx(summary["total_gross_claims"] - summary["total_effective_recovery"], abs=1e-6)
    assert summary["claims_12m_net"] <= summary["claims_12m_gross"] + 1e-9


def test_default_treaty_barely_touches_base_case_but_bites_under_large_loss_stress():
    """Calibration regression test: the default treaty is deliberately set
    above ordinary base-case claims (an XoL layer should protect against a
    tail year, not everyday claims), so the base-case Economic A/L Coverage
    stays close to its historical ~115% calibration. A large-loss / cat-like
    stress (higher frequency and severity) must push claims into the layer
    and trigger materially larger recoveries."""
    from src.reinsurance import DEFAULT_TREATY

    base_cf = build_liability_cash_flows()
    base_summary = reinsurance_summary(base_cf, DEFAULT_TREATY)
    assert base_summary["total_effective_recovery"] < base_summary["total_gross_claims"] * .02  # negligible

    stress_cf = build_liability_cash_flows(frequency_shock=.20, severity_shock=.50)
    stress_summary = reinsurance_summary(stress_cf, DEFAULT_TREATY)
    assert stress_summary["recoveries_12m"] > base_summary["recoveries_12m"] + 50.0
