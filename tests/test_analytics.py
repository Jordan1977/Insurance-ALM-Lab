from src.analytics import base_analytics, scenario_analytics


def test_base_analytics_headline_liabilities_are_net_of_reinsurance():
    """Section 4: the headline economic balance sheet must be NET, with
    GROSS still separately available and never silently mixed in."""
    b = base_analytics()
    assert b["kpis"]["total_liabilities"] == b["liabilities"]["present_value"]
    assert b["liabilities"]["present_value"] <= b["liabilities_gross"]["present_value"] + 1e-6


def test_base_analytics_coverage_close_to_historical_calibration():
    """Regression test for the treaty recalibration: base-case coverage
    should stay close to the ~115% figure the app was originally calibrated
    around for stress-testing headroom, not jump materially higher just
    because a reinsurance layer was introduced."""
    b = base_analytics()
    assert 1.05 < b["kpis"]["economic_coverage_ratio"] < 1.25


def test_base_analytics_liquidity_uses_interim_not_ultimate_claims():
    """Section 13: the 12M liquidity figure must reflect the *interim* cash
    requirement (gross claims paid less recoveries actually received that
    year), not the ultimate net claim cost, since the two can differ a lot
    when recovery_lag > 0."""
    b = base_analytics()
    assert abs(b["claims_12m"] - b["claims_12m_gross"]) < 1e-6  # lag=1 -> nothing received in year 1
    assert b["claims_12m_net_ultimate"] < b["claims_12m_gross"] or b["claims_12m_net_ultimate"] == b["claims_12m_gross"]


def test_base_analytics_reinsurance_block_present_and_consistent():
    b = base_analytics()
    reins = b["reinsurance"]
    assert reins["total_net_claims"] == reins["total_gross_claims"] - reins["total_effective_recovery"]


def test_scenario_analytics_base_case_is_neutral():
    b = base_analytics()
    s = scenario_analytics(b, "Base")
    assert s["delta_surplus"] == 0.0
    assert s["stressed_assets"] == b["kpis"]["total_assets"]


def test_scenario_analytics_named_scenario_matches_direct_engine_call():
    """Section 64: there must be exactly one way to evaluate a scenario --
    the page-level assembly must agree with a direct call to the same
    underlying function, for the SAME inputs. (Note: `scenario_analytics`
    and `evaluate_deterministic_scenario` have different fx_hedge_ratio
    *defaults* -- .5 vs 0.0 -- so this test pins the value explicitly rather
    than relying on both functions defaulting the same way.)"""
    from src.scenario_generator import evaluate_deterministic_scenario

    b = base_analytics(fx_hedge_ratio=.5)
    via_analytics = scenario_analytics(b, "Stagflation", fx_hedge_ratio=.5)
    direct = evaluate_deterministic_scenario(b["assets"], "Stagflation", fx_hedge_ratio=.5)
    assert via_analytics["surplus"] == direct["surplus"]
    assert via_analytics["coverage"] == direct["coverage"]
