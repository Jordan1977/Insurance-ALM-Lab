import numpy as np
from src.liability_model import (
    build_liability_cash_flows, build_liability_summary, discount_curve,
    total_liability_metrics, LIABILITY_FAMILIES,
)


def test_liability_cash_flows_non_negative():
    cf = build_liability_cash_flows()
    assert (cf.cash_flow >= 0).all()


def test_payout_patterns_sum_to_one_per_family():
    for name, f in LIABILITY_FAMILIES.items():
        total = sum(f["payout"])
        assert abs(total - 1.0) < 1e-6, f"{name} payout sums to {total}, expected 1.0"


def test_discounted_pv_below_undiscounted_sum_for_positive_rates():
    cf = build_liability_cash_flows()
    curve = discount_curve(0.03)
    total_undiscounted = cf.groupby("year").cash_flow.sum()
    rates = curve.set_index("year").spot_rate
    pv = (total_undiscounted / (1 + rates) ** total_undiscounted.index).sum()
    assert pv < total_undiscounted.sum()


def test_higher_claim_inflation_increases_pv():
    low = total_liability_metrics(discount_rate=0.03, claim_inflation=0.01)
    high = total_liability_metrics(discount_rate=0.03, claim_inflation=0.06)
    assert high["present_value"] > low["present_value"]


def test_higher_discount_rate_decreases_pv():
    low_rate = total_liability_metrics(discount_rate=0.01, claim_inflation=0.025)
    high_rate = total_liability_metrics(discount_rate=0.06, claim_inflation=0.025)
    assert high_rate["present_value"] < low_rate["present_value"]


def test_liability_duration_positive():
    m = total_liability_metrics()
    assert m["modified_duration"] > 0


def test_liability_summary_per_family_positive_pv():
    s = build_liability_summary()
    assert (s.present_value > 0).all()
    assert (s.modified_duration > 0).all()
