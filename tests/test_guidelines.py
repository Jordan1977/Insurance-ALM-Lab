from src.asset_model import build_asset_portfolio, build_correlation_matrix, portfolio_modified_duration, portfolio_asset_dv01
from src.liability_model import total_liability_metrics, projected_claims_12m
from src.alm_engine import alm_kpis
from src.risk_engine import classify_liquidity, liquidity_coverage_ratio
from src.guidelines import portfolio_guideline_metrics, check_compliance, overall_compliance
from src.optimization import optimize_allocation

LIMITS = dict(equity_max=.20, hy_max=.10, illiquid_max=.20, cash_min=.05,
              duration_gap_tolerance=1.0, liquidity_target=1.5)


def _base_kpis_and_lcr():
    A = build_asset_portfolio()
    L = total_liability_metrics()
    K = alm_kpis(A.market_value.sum(), L["present_value"], portfolio_modified_duration(A),
                 L["modified_duration"], portfolio_asset_dv01(A), L["dv01"])
    liq = classify_liquidity(A)
    liquid = liq.loc[liq.liquidity_bucket.isin(["Highly Liquid", "Liquid"]), "market_value"].sum()
    lcr = liquidity_coverage_ratio(liquid, projected_claims_12m())
    return A, K, lcr


def test_base_case_is_compliant_with_default_limits():
    A, K, lcr = _base_kpis_and_lcr()
    metrics = portfolio_guideline_metrics(A)
    check = check_compliance(metrics, K, lcr, LIMITS)
    status, breaches = overall_compliance(check)
    assert status == "COMPLIANT"
    assert breaches == []


def test_tight_equity_limit_produces_breach():
    A, K, lcr = _base_kpis_and_lcr()
    metrics = portfolio_guideline_metrics(A)
    tight_limits = {**LIMITS, "equity_max": .05}  # base equity weight is 15%
    check = check_compliance(metrics, K, lcr, tight_limits)
    status, breaches = overall_compliance(check)
    assert status == "NON-COMPLIANT"
    assert "Maximum equity exposure" in breaches


def test_headroom_sign_convention_positive_means_safe_for_both_ceilings_and_floors():
    """Regression test for a red-team finding: headroom must read the same way
    (positive = safe margin, negative = breach) whether the guideline is a
    ceiling (e.g. max equity) or a floor (e.g. min cash)."""
    A, K, lcr = _base_kpis_and_lcr()
    metrics = portfolio_guideline_metrics(A)
    check = check_compliance(metrics, K, lcr, LIMITS).set_index("guideline")
    # Base case is compliant everywhere, so every guideline's headroom must be >= 0.
    assert (check.headroom >= -1e-9).all(), check[check.headroom < 0]
    # A breach must show negative headroom.
    tight_limits = {**LIMITS, "cash_min": .50}  # base cash weight is 8%, well below this floor
    breach_check = check_compliance(metrics, K, lcr, tight_limits).set_index("guideline")
    assert breach_check.loc["Minimum cash", "headroom"] < 0


def test_saa_output_can_be_tested_against_guidelines():
    A = build_asset_portfolio()
    C = build_correlation_matrix(A.asset_class.tolist())
    L = total_liability_metrics()
    weights, saa_metrics = optimize_allocation(A, C, L["modified_duration"], mode="Liability-Aware",
                                                equity_max=LIMITS["equity_max"], hy_max=LIMITS["hy_max"],
                                                illiquid_max=LIMITS["illiquid_max"])
    proposed = A.assign(weight=weights.optimized_weight.to_numpy())
    metrics = portfolio_guideline_metrics(proposed)
    # The optimiser itself enforces equity/HY/illiquid caps, so the proposal must respect them here too.
    assert metrics["equity_weight"] <= LIMITS["equity_max"] + 1e-6
    assert metrics["hy_weight"] <= LIMITS["hy_max"] + 1e-6
    assert metrics["illiquid_weight"] <= LIMITS["illiquid_max"] + 1e-6
