from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.cantonment import cantonment_analysis

page_header('Synthetic Asset Cantonment by Liability Family', 'Can the synthetic asset book be allocated across liability pools without double use while preserving duration and liquidity coherence?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
summary, allocation = cantonment_analysis(
    base["assets"],
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
)

st.success(f"Allocation conservation check: €{summary.assets_assigned.sum():,.1f}m assigned / €{base['assets'].market_value.sum():,.1f}m available.")
st.dataframe(summary, use_container_width=True, hide_index=True)

fig = go.Figure()
fig.add_bar(x=summary.family, y=summary.asset_duration, name="Assigned asset duration")
fig.add_bar(x=summary.family, y=summary.liability_duration, name="Liability duration")
fig.update_layout(barmode="group", title="Duration compatibility by synthetic liability pool")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Asset allocation by liability family")
fig = px.bar(allocation, x="family", y="amount", color="asset_class", title="Constrained asset assignment — each euro used at most once")
st.plotly_chart(fig, use_container_width=True)

with st.expander("Detailed allocation matrix"):
    pivot = allocation.pivot_table(index="asset_class", columns="family", values="amount", aggfunc="sum", fill_value=0)
    pivot["Total assigned"] = pivot.sum(axis=1)
    st.dataframe(pivot, use_container_width=True)

st.caption("The optimiser minimises duration mismatch and penalises illiquid assets more heavily for short-tail / high-liquidity claim families. It is a transparent analytical prototype, not a production segmentation model.")
