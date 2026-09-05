from __future__ import annotations

import streamlit as st

from src.analytics import base_analytics, scenario_analytics
from src.guidelines import check_compliance, overall_compliance, portfolio_guideline_metrics
from src.optimization import optimize_allocation
from src.ui_helpers import page_header, metric_row

STATUS_ORDER = {"RED": 0, "AMBER": 1, "GREEN": 2}


def _sorted(check):
    """Section 40: RED first, AMBER second, GREEN last -- so a reviewer never
    has to scan every row to find what matters."""
    return check.assign(_order=check.status.map(STATUS_ORDER)).sort_values("_order").drop(columns="_order")


active_scenario = st.session_state.get("active_scenario", "Base")
page_header("Investment Guidelines & Limits Monitor",
           "Is the current book, and any proposed change, within the insurer's own illustrative limits?",
           scenario=active_scenario)
st.warning("All limits below are **Synthetic Internal Illustrative Limits**, editable from the sidebar. "
          "They are not Thélem assurances' real investment guidelines.")

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
limits = dict(
    equity_max=st.session_state.get("equity_max", .20), hy_max=st.session_state.get("hy_max", .10),
    illiquid_max=st.session_state.get("illiquid_max", .20), cash_min=st.session_state.get("cash_min", .05),
    duration_gap_tolerance=st.session_state.get("duration_gap_tolerance", 1.0),
    liquidity_target=st.session_state.get("liquidity_target", 1.5),
)

tab_current, tab_saa = st.tabs(["Current Book (Base vs. Active Scenario)", "Test a Proposed Allocation"])

with tab_current:
    metrics = portfolio_guideline_metrics(base["assets"])
    check = check_compliance(metrics, base["kpis"], base["liquidity_coverage"], limits)
    status, breaches = overall_compliance(check)
    (st.success if status == "COMPLIANT" else st.error)(f"**Base: {status}**" + (f" — breaches: {', '.join(breaches)}" if breaches else "."))

    if active_scenario != "Base":
        stress = scenario_analytics(base, active_scenario, st.session_state.get("discount_rate", .03),
                                    st.session_state.get("claim_inflation", .025), st.session_state.get("fx_hedge_ratio", .5))
        stressed_kpis = dict(base["kpis"])
        stressed_kpis["economic_coverage_ratio"] = stress["coverage"]
        stressed_check = check_compliance(metrics, stressed_kpis, base["liquidity_coverage"], limits)
        stressed_status, stressed_breaches = overall_compliance(stressed_check)
        (st.success if stressed_status == "COMPLIANT" else st.error)(
            f"**{active_scenario}: {stressed_status}**" + (f" — breaches: {', '.join(stressed_breaches)}" if stressed_breaches else "."))
        newly_breached = set(stressed_check.loc[stressed_check.status == "RED", "guideline"]) - set(check.loc[check.status == "RED", "guideline"])
        if newly_breached:
            st.error(f"Newly breached under {active_scenario}: {', '.join(newly_breached)}")

    n_red, n_amber = int((check.status == "RED").sum()), int((check.status == "AMBER").sum())
    metric_row([("Breaches (RED)", str(n_red), None), ("Watchlist (AMBER)", str(n_amber), None), ("Guidelines checked", str(len(check)), None)])
    st.dataframe(_sorted(check), use_container_width=True, hide_index=True)

with tab_saa:
    st.caption("Section 43: any SAA output is automatically checked here, using the exact same compliance function.")
    mode = st.selectbox("SAA objective to test", ["Liability-Aware", "Min Vol", "Max Sharpe"])
    weights, saa_metrics = optimize_allocation(
        base["assets"], base["corr"], base["liabilities"]["modified_duration"], mode=mode,
        cash_min=st.session_state.get("cash_min", .05), cash_max=st.session_state.get("cash_max", .20),
        equity_max=limits["equity_max"], illiquid_max=limits["illiquid_max"], hy_max=limits["hy_max"],
        duration_gap_tolerance=limits["duration_gap_tolerance"], liquidity_target=limits["liquidity_target"],
        claims_12m=base["claims_12m"], total_assets=base["kpis"]["total_assets"],
        risk_free_rate=st.session_state.get("risk_free_rate", .025),
    )
    if not saa_metrics["success"]:
        st.error(f"Feasible solution not found under current constraints — solver message: {saa_metrics['message']}. "
                "Showing the current book's weights instead; do not read this as an optimised proposal.")
    proposed = base["assets"].assign(weight=weights.optimized_weight.to_numpy())
    proposed_metrics = portfolio_guideline_metrics(proposed)
    proposed_kpis = dict(base["kpis"])
    proposed_kpis["duration_gap"] = saa_metrics["duration_gap"]
    proposed_check = check_compliance(proposed_metrics, proposed_kpis, saa_metrics["liquidity_coverage"], limits)
    proposed_status, proposed_breaches = overall_compliance(proposed_check)
    (st.success if proposed_status == "COMPLIANT" else st.error)(
        f"**{mode}** allocation is **{proposed_status}**" + (f" — breaches: {', '.join(proposed_breaches)}" if proposed_breaches else "."))
    st.dataframe(_sorted(proposed_check), use_container_width=True, hide_index=True)
