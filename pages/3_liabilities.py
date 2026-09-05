from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.liability_model import (
    build_liability_cash_flows, build_liability_summary, total_liability_metrics,
    LIABILITY_FAMILIES, expected_claim_count, expected_severity, expected_gross_claims,
)
from src.reinsurance import DEFAULT_TREATY, net_liability_cash_flows, total_net_liability_metrics

page_header('Non-Life Liability Cash-Flow Engine', 'When and why are modelled non-life claims expected to be paid, and how sensitive are they to inflation and settlement timing?', st.session_state.get("active_scenario", "Base"))

discount_rate = st.session_state.get("discount_rate", .03)
claim_inflation = st.session_state.get("claim_inflation", .025)
cf = build_liability_cash_flows(claim_inflation)
summary = build_liability_summary(discount_rate, claim_inflation)
total_gross = total_liability_metrics(discount_rate, claim_inflation)
total_net = total_net_liability_metrics(discount_rate, claim_inflation, DEFAULT_TREATY)

st.markdown("### Frequency x Severity x Exposure (Section 6)")
freq_rows = []
for name, a in LIABILITY_FAMILIES.items():
    freq_rows.append({
        "Family": name, "Exposure (policies)": a["exposure_units"], "Frequency": f"{a['frequency']:.1%}",
        "Expected Claim Count": f"{expected_claim_count(a):,.0f}", "Severity (EURm/claim)": f"{expected_severity(a):.4f}",
        "Expected Gross Claims (EURm)": f"{expected_gross_claims(a):.1f}", "Tail": a["tail"],
        "Liquidity Requirement": a["liquidity_requirement"],
    })
st.dataframe(freq_rows, use_container_width=True, hide_index=True)

st.markdown("### Gross vs. net-of-reinsurance economic position")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Gross PV of Modelled Claims", f"€{total_gross['present_value']:,.1f}m")
c2.metric("Net PV of Modelled Claims", f"€{total_net['present_value']:,.1f}m",
          f"€{total_net['present_value']-total_gross['present_value']:+,.1f}m")
c3.metric("Gross Modified Duration", f"{total_gross['modified_duration']:.2f}y")
c4.metric("Net Modified Duration", f"{total_net['modified_duration']:.2f}y",
          f"{total_net['modified_duration']-total_gross['modified_duration']:+.2f}y")
st.caption("Full gross -> recoveries -> net detail and treaty controls: Reinsurance page.")

c5, c6, c7 = st.columns(3)
c5.metric("Next 12M Claims (gross)", f"€{total_gross['claims_12m']:,.1f}m")
c6.metric("Next 3Y Claims (gross)", f"€{total_gross['claims_3y']:,.1f}m")
c7.metric("Long-Tail Liability Share (gross PV)", f"{total_gross['long_tail_share']:.0%}")

fig = px.bar(cf, x="year", y="cash_flow", color="family", title="Projected GROSS claim cash flows by non-life family")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Family-level economics (gross)")
st.dataframe(summary, use_container_width=True, hide_index=True)

st.markdown("### Short-tail vs. long-tail (Section 7)")
long_tail = summary[summary.tail_classification.isin(["Long", "Medium/Long"])]
short_tail = summary[~summary.tail_classification.isin(["Long", "Medium/Long"])]
fig2 = go.Figure(go.Pie(labels=["Long / Medium-Long tail", "Short / Short-Medium tail"],
                        values=[long_tail.present_value.sum(), short_tail.present_value.sum()], hole=.5))
fig2.update_layout(title="PV share by tail classification", height=380)
st.plotly_chart(fig2, use_container_width=True)
st.caption("Long-tail branches (e.g. General Liability) carry greater inflation uncertainty, greater discount-rate "
           "sensitivity and a longer ALM horizon than short-tail branches (e.g. Home) -- this is why they dominate "
           "liability duration even when their share of near-term (12M) claims is smaller.")

st.markdown("### Claims inflation transmission")
low = build_liability_summary(discount_rate, max(claim_inflation - .01, -.02)).present_value.sum()
high = build_liability_summary(discount_rate, claim_inflation + .01).present_value.sum()
base = summary.present_value.sum()
cols = st.columns(3)
cols[0].metric("Inflation -100bp", f"€{low:,.1f}m", f"€{low-base:+,.1f}m", delta_color="inverse")
cols[1].metric("Base", f"€{base:,.1f}m")
cols[2].metric("Inflation +100bp", f"€{high:,.1f}m", f"€{high-base:+,.1f}m", delta_color="inverse")
st.caption("Claim-family sensitivities differ by tail length and are synthetic, documented assumptions.")
