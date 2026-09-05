from __future__ import annotations

import streamlit as st

from src.data_loader import (
    load_asset_book_csv, load_instrument_book_csv, load_liability_cf_csv, load_yield_curve_csv,
)
from src.validation import full_data_quality_report, overall_status
from src.ui_helpers import inject_global_css

st.set_page_config(page_title="Insurance ALM Lab", page_icon="ALM", layout="wide", initial_sidebar_state="expanded")
inject_global_css()

DEFAULTS = {
    "discount_rate": .03, "claim_inflation": .025, "risk_free_rate": .025,
    "var_confidence": .99, "asset_weights": None, "active_scenario": "Base",
    "equity_hedge_ratio": 0.0, "fx_hedge_ratio": .50, "cash_min": .05,
    "cash_max": .20, "equity_max": .20, "illiquid_max": .20, "hy_max": .10,
    "duration_gap_tolerance": 1.0, "liquidity_target": 1.5,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

with st.sidebar:
    st.markdown(f"**Active Scenario:** {st.session_state.active_scenario}")
    st.caption("Model version: V6.3 — see CHANGELOG_V6.3.md")
    st.divider()

    st.markdown("#### Core assumptions")
    st.session_state.discount_rate = st.slider(
        "Base discount-rate level", 0.0, .08, st.session_state.discount_rate, .0025, format="percent"
    )
    st.session_state.claim_inflation = st.slider(
        "Base claims inflation", -.02, .08, st.session_state.claim_inflation, .0025, format="percent"
    )

    with st.expander("Advanced assumptions"):
        st.session_state.risk_free_rate = st.slider(
            "Risk-free rate", 0.0, .06, st.session_state.risk_free_rate, .0025, format="percent"
        )
        st.session_state.fx_hedge_ratio = st.slider(
            "FX hedge ratio", 0.0, 1.0, st.session_state.fx_hedge_ratio, .05, format="percent"
        )

    with st.expander("Illustrative internal ALM limits"):
        st.session_state.equity_max = st.slider("Maximum equity allocation", .05, .40, st.session_state.equity_max, .01, format="percent")
        st.session_state.illiquid_max = st.slider("Maximum illiquid allocation", .05, .40, st.session_state.illiquid_max, .01, format="percent")
        st.session_state.hy_max = st.slider("Maximum High Yield allocation", 0.0, .20, st.session_state.hy_max, .01, format="percent")
        st.session_state.duration_gap_tolerance = st.slider(
            "Duration-gap tolerance (years)", 0.0, 3.0, st.session_state.duration_gap_tolerance, .1
        )
        st.session_state.liquidity_target = st.slider(
            "12M claims coverage target", 1.0, 3.0, st.session_state.liquidity_target, .1
        )
    st.caption("All insurer balance-sheet data, limits and assumptions are synthetic.")

    with st.expander("Data quality"):
        report = full_data_quality_report(
            load_asset_book_csv(), load_instrument_book_csv(), load_liability_cf_csv(), load_yield_curve_csv()
        )
        status = overall_status(report)
        (st.success if status == "PASS" else st.error)(f"Data Quality: {status}")
        st.dataframe(report, use_container_width=True, hide_index=True)

# Seven business-oriented groups: the analytical modules remain separate for
# maintainability, while recruiter-facing navigation follows an ALM workflow.
pages = {
    "EXECUTIVE": [
        st.Page("pages/0_overview.py", title="Overview", default=True),
        st.Page("pages/1_executive_dashboard.py", title="Executive ALM Dashboard"),
        st.Page("pages/20_committee_pack.py", title="Investment Committee Pack"),
    ],
    "NON-LIFE LIABILITIES & ALM": [
        st.Page("pages/3_liabilities.py", title="Claims & Liabilities"),
        st.Page("pages/21_reinsurance.py", title="Reinsurance: Gross → Net"),
        st.Page("pages/4_alm_matching.py", title="Cash-Flow Matching & Liquidity"),
    ],
    "RISK & SCENARIOS": [
        st.Page("pages/15_sensitivity.py", title="Sensitivity / Tornado"),
        st.Page("pages/5_economic_scenarios.py", title="Economic Scenarios & Monte Carlo"),
        st.Page("pages/6_stress_testing.py", title="Stress Testing"),
        st.Page("pages/10_macro_transmission.py", title="Macro → ALM Transmission"),
    ],
    "INVESTMENT STRATEGY": [
        st.Page("pages/2_assets.py", title="Asset Portfolio"),
        st.Page("pages/16_performance_attribution.py", title="Performance Attribution"),
        st.Page("pages/8_strategic_allocation.py", title="Strategic Asset Allocation"),
        st.Page("pages/9_cantonment.py", title="Cantonment"),
        st.Page("pages/18_guidelines.py", title="Investment Guidelines"),
    ],
    "REINVESTMENT & HEDGING": [
        st.Page("pages/17_reinvestment.py", title="Reinvestment & Maturities"),
        st.Page("pages/7_hedging.py", title="Hedging Lab"),
    ],
    "MACRO & MONITORING": [
        st.Page("pages/12_macro_markets.py", title="Macro & Markets"),
        st.Page("pages/13_assumptions_hub.py", title="Assumptions Hub"),
        st.Page("pages/14_research_watch.py", title="Research & Regulatory Watch"),
    ],
    "GOVERNANCE & REPORTING": [
        st.Page("pages/11_reporting.py", title="ALM Reporting"),
        st.Page("pages/19_audit_trail.py", title="Analytical Audit Trail"),
    ],
}
pg = st.navigation(pages, position="sidebar")
pg.run()
