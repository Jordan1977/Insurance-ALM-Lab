from src.asset_model import build_asset_portfolio, build_instrument_book
from src.liability_model import build_liability_cash_flows, total_liability_metrics
from src.reinvestment import (
    annual_cash_projection, compare_reinvestment_policies, select_candidate,
    REINVESTMENT_POLICIES, REINVESTMENT_UNIVERSE,
)


def _setup():
    A = build_asset_portfolio()
    B = build_instrument_book(A)
    cf = build_liability_cash_flows()
    L = total_liability_metrics()
    return A, B, cf, L


def test_cash_conservation_holds_exactly_every_year():
    """Section 30: Opening Cash + Inflows - Claims + Shortfall Funding -
    Investments = Ending Cash, with zero tolerance."""
    A, B, cf, L = _setup()
    ladder, _ = annual_cash_projection(B, cf, "Reinvest at same maturity", 3.7, L["modified_duration"], horizon=5)
    implied_ending = (
        ladder.opening_cash + ladder.coupon_income + ladder.bond_maturities + ladder.reinsurance_recoveries
        - ladder.gross_claims_paid + ladder.shortfall_funded_externally - ladder.amount_reinvested
    )
    assert (implied_ending - ladder.ending_cash).abs().max() < 1e-9


def test_ending_cash_never_negative():
    A, B, cf, L = _setup()
    for policy in REINVESTMENT_POLICIES:
        ladder, _ = annual_cash_projection(B, cf, policy, 3.7, L["modified_duration"], horizon=5)
        assert (ladder.ending_cash >= -1e-9).all()


def test_shortfall_and_investment_never_both_positive_same_year():
    """A year either needs external funding or has cash to reinvest -- never both."""
    A, B, cf, L = _setup()
    ladder, _ = annual_cash_projection(B, cf, "Hold cash", 3.7, L["modified_duration"], horizon=5)
    both_positive = (ladder.shortfall_funded_externally > 1e-9) & (ladder.amount_reinvested > 1e-9)
    assert not both_positive.any()


def test_all_five_policies_covered():
    A, B, cf, L = _setup()
    comparison = compare_reinvestment_policies(A, B, cf, L["modified_duration"])
    assert set(comparison.policy) == set(REINVESTMENT_POLICIES)
    assert len(REINVESTMENT_POLICIES) == 5  # Section 28 explicitly adds "Reinvest short" vs the V1 four


def test_select_candidate_hold_cash_is_none():
    assert select_candidate("Hold cash", 3.7, 4.0) is None


def test_select_candidate_reinvest_short_is_shortest_maturity():
    c = select_candidate("Reinvest short", 3.7, 4.0)
    assert c.name == "EUR Sovereign 2Y"


def test_select_candidate_extend_duration_is_longest():
    c = select_candidate("Extend duration", 3.7, 4.0)
    assert c.duration == max(u.duration for u in REINVESTMENT_UNIVERSE)


def test_select_candidate_liability_matching_targets_liability_duration():
    target = 6.0
    c = select_candidate("Liability-matching reinvestment", 3.7, target)
    # must be the closest available duration to the target, not just any instrument
    closest_gap = min(abs(u.duration - target) for u in REINVESTMENT_UNIVERSE)
    assert abs(c.duration - target) == closest_gap


def test_extend_duration_increases_asset_duration_vs_hold_cash():
    A, B, cf, L = _setup()
    comparison = compare_reinvestment_policies(A, B, cf, L["modified_duration"]).set_index("policy")
    assert comparison.loc["Extend duration", "asset_duration_after"] > comparison.loc["Hold cash", "asset_duration_after"]


def test_liability_matching_minimises_duration_gap_magnitude():
    A, B, cf, L = _setup()
    comparison = compare_reinvestment_policies(A, B, cf, L["modified_duration"]).set_index("policy")
    gaps = comparison.duration_gap_after.abs()
    assert gaps["Liability-matching reinvestment"] <= gaps["Extend duration"]
    assert gaps["Liability-matching reinvestment"] <= gaps["Hold cash"]


def test_reinvested_amount_matches_ladder_total_exactly():
    """The blended duration/yield calculation must use the ACTUAL amount
    invested from the cash ladder, not a separate heuristic figure."""
    A, B, cf, L = _setup()
    from src.reinvestment import policy_outcome
    outcome = policy_outcome(A, B, cf, "Extend duration", L["modified_duration"])
    assert abs(outcome["invested_total"] - outcome["ladder"].amount_reinvested.sum()) < 1e-9
