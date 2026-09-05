from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.analytics import base_analytics, scenario_analytics
from src.formatting import fmt_eur_m, fmt_pct, fmt_years, fmt_ratio, fmt_delta_eur_m, fmt_signed_pct
from src.risk_engine import alm_audit_score
from src.ui_helpers import page_header, metric_row, compact_expander

active = st.session_state.get("active_scenario", "Base")
page_header("Executive ALM Dashboard",
           "What is the current economic position of the insurer, and how would it change under the active scenario?",
           scenario=active)

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
view = st.radio("View", ["Base", "Active Scenario"], horizontal=True, label_visibility="collapsed")
scenario = active if view == "Active Scenario" else "Base"
stress = scenario_analytics(
    base, scenario,
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

base_k = base["kpis"]
shown_assets, shown_liab = stress["stressed_assets"], stress["stressed_liabilities"]
shown_surplus, shown_cov = stress["surplus"], stress["coverage"]
is_stressed = scenario != "Base"

# ---- First screen: exactly the six figures a reader needs in 20 seconds (Section 18) ----
metric_row([
    ("Economic Assets", fmt_eur_m(shown_assets), fmt_delta_eur_m(shown_assets - base_k["total_assets"]) if is_stressed else None),
    ("Net Liability PV", fmt_eur_m(shown_liab), fmt_delta_eur_m(shown_liab - base_k["total_liabilities"]) if is_stressed else None),
    ("Economic Surplus", fmt_eur_m(shown_surplus), fmt_delta_eur_m(stress["delta_surplus"]) if is_stressed else None),
    ("Economic A/L Coverage", fmt_pct(shown_cov), fmt_signed_pct(shown_cov - base_k["economic_coverage_ratio"]) if is_stressed else None),
], help_texts=[
    "Sum of instrument market values across the synthetic strategic book.",
    "Present value of projected NET-of-reinsurance claim cash flows.",
    "Economic Assets minus Net Liability PV.",
    "Economic Assets / Net Liability PV. Not a Solvency II solvency ratio.",
])
metric_row([
    ("Duration Gap", fmt_years(base_k["duration_gap"], signed=True), None),
    ("12M Liquidity Coverage", fmt_ratio(base["liquidity_coverage"]), None),
], help_texts=[
    "Asset modified duration minus net liability modified duration, in years.",
    "Liquid assets / next-12-month interim claims need. Illustrative internal metric, not regulatory LCR.",
])

st.markdown("### Top ALM watchpoints")
watchpoints = []
if shown_cov < 1.05:
    watchpoints.append("Economic coverage falls close to the synthetic internal red zone under the selected view.")
if abs(base_k["duration_gap"]) > st.session_state.get("duration_gap_tolerance", 1.0):
    watchpoints.append("Asset and liability modified durations exceed the configured mismatch tolerance.")
if base["liquidity_coverage"] < st.session_state.get("liquidity_target", 1.5):
    watchpoints.append("12M liquid-assets / projected-claims coverage is below the configured internal target.")
if base["equity_risk_contribution"] > .40:
    watchpoints.append("Equities contribute a disproportionate share of modelled asset volatility risk.")
if not watchpoints:
    watchpoints.append("No configured ALM limit is breached in the current base view; scenario and concentration risks still require monitoring.")
for item in watchpoints[:3]:
    st.write(f"• {item}")

st.markdown("### Asset allocation vs. contribution to volatility risk")
rc = base["risk_contribution"]
fig = go.Figure()
fig.add_bar(x=rc.asset_class, y=rc.weight, name="Portfolio weight")
fig.add_bar(x=rc.asset_class, y=rc.pct_of_total_risk, name="Risk contribution")
fig.update_layout(barmode="group", yaxis_tickformat=".0%", height=420, margin=dict(t=30, b=10),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig, use_container_width=True)

if is_stressed:
    with st.expander("Scenario P&L attribution (waterfall)", expanded=False):
        attr = stress["attribution"]
        labels = ["Base surplus"] + list(attr) + ["Stressed surplus"]
        values = [base_k["surplus"]] + list(attr.values()) + [stress["surplus"]]
        measure = ["absolute"] + ["relative"] * len(attr) + ["total"]
        fig2 = go.Figure(go.Waterfall(x=labels, y=values, measure=measure))
        fig2.update_layout(height=420, yaxis_title="EURm", margin=dict(t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)

with st.expander("ALM health monitor (detailed status table)"):
    audit = alm_audit_score(
        base_k, base["equity_risk_contribution"], base["liquidity_coverage"],
        largest_weight=float(base["assets"].weight.max()),
    )
    st.dataframe(audit[["dimension", "metric", "value", "target", "status", "comment"]], use_container_width=True, hide_index=True)

with compact_expander():
    st.write("Economic A/L Coverage = Economic Assets / Net Liability PV (not a Solvency II ratio). "
             "Net Liability PV is post-reinsurance. Full formulas: methodology.md. Full limitations: limitations.md.")
