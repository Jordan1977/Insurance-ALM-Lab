from src.liability_model import (
    LIABILITY_FAMILIES, expected_claim_count, expected_severity, expected_gross_claims,
    build_liability_cash_flows, total_liability_metrics,
)

ORIGINAL_BASE_CLAIMS = {
    "Auto": 320, "Habitation": 180, "Responsabilité Civile": 260,
    "Professionnels": 140, "Autres": 100,
}


def test_expected_gross_claims_matches_original_calibration():
    """Regression test: the frequency x severity refactor must reproduce the
    original base_claims figures exactly (to rounding), so the balance-sheet
    scale (~1.15bn assets, ~115% coverage) is unchanged."""
    for name, assumptions in LIABILITY_FAMILIES.items():
        assert abs(expected_gross_claims(assumptions) - ORIGINAL_BASE_CLAIMS[name]) < 0.05


def test_expected_gross_claims_equals_count_times_severity():
    for assumptions in LIABILITY_FAMILIES.values():
        count = expected_claim_count(assumptions)
        severity = expected_severity(assumptions)
        assert abs(count * severity - expected_gross_claims(assumptions)) < 1e-9


def test_frequency_shock_scales_claim_count_only():
    for assumptions in LIABILITY_FAMILIES.values():
        base_count = expected_claim_count(assumptions)
        shocked_count = expected_claim_count(assumptions, frequency_shock=.10)
        assert abs(shocked_count - base_count * 1.10) < 1e-9
        # severity itself must not move
        assert expected_severity(assumptions) == expected_severity(assumptions, severity_shock=0.0)


def test_severity_shock_scales_severity_only():
    for assumptions in LIABILITY_FAMILIES.values():
        base_severity = expected_severity(assumptions)
        shocked_severity = expected_severity(assumptions, severity_shock=.10)
        assert abs(shocked_severity - base_severity * 1.10) < 1e-9


def test_every_family_has_tail_and_liquidity_classification():
    for name, assumptions in LIABILITY_FAMILIES.items():
        assert assumptions["tail"] in {"Short", "Short/Medium", "Medium/Long", "Long"}
        assert assumptions["liquidity_requirement"] in {"Very High", "High", "Medium", "Low"}


def test_long_tail_share_between_zero_and_one():
    m = total_liability_metrics()
    assert 0.0 <= m["long_tail_share"] <= 1.0
    assert abs(m["long_tail_share"] + m["short_tail_share"] - 1.0) < 1e-9


def test_general_liability_is_classified_long_tail_and_motor_is_not():
    assert LIABILITY_FAMILIES["Responsabilité Civile"]["tail"] == "Long"
    assert LIABILITY_FAMILIES["Auto"]["tail"] != "Long"


def test_frequency_shock_propagates_to_cash_flows():
    base = build_liability_cash_flows()
    shocked = build_liability_cash_flows(frequency_shock=.20)
    assert shocked.cash_flow.sum() > base.cash_flow.sum()
