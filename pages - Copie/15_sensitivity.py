from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.analytics import base_analytics
from src.formatting import fmt_eur_m
from src.sensitivity import tornado_analysis, top_risk_drivers
from src.ui_helpers import page_header

page_header("ALM Sensitivity Analysis (Tornado)",
           "Which single factor threatens the economic surplus the most?")
st.caption("Every shock below calls the same `evaluate_deterministic_scenario` engine used by the Economic Scenarios "
           "and Stress Testing pages, applied one factor at a time — no sensitivity is computed independently.")

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

tornado = tornado_analysis(
    base["assets"],
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
st.session_state["tornado_result"] = tornado  # single source for the Committee Pack (Section 45: no recompute)

fig = go.Figure(go.Bar(
    x=tornado.surplus_impact, y=tornado.factor, orientation="h",
    marker_color=["#b23b3b" if v < 0 else "#1e7f4f" for v in tornado.surplus_impact],
))
fig.update_layout(title=f"Surplus impact by risk factor — base surplus {fmt_eur_m(base['kpis']['surplus'])}",
                  xaxis_title="EURm", height=460, margin=dict(t=40, b=10),
                  yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.markdown("##### Top 3 ALM risk drivers")
for line in top_risk_drivers(tornado, 3):
    st.write(f"• {line}")

with st.expander("Full sensitivity table"):
    st.dataframe(
        tornado[["factor", "asset_impact", "liability_impact", "surplus_impact", "coverage_impact"]],
        use_container_width=True, hide_index=True,
    )
    st.caption("Each row shocks exactly one factor from the base case; combined scenarios (e.g. Stagflation) are on "
              "the Economic Scenarios and Stress Testing pages.")
