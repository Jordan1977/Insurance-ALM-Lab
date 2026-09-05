from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.data_loader import load_macro_data, load_public_macro_snapshot
from src.macro_engine import classify_regime, latest_regime, scenario_for_regime

page_header('Macro & Markets', 'Which public observations and synthetic research assumptions feed the ALM scenario framework?', st.session_state.get("active_scenario", "Base"))
st.info(
    "The compact snapshot below contains dated public observations from ECB / Eurostat. "
    "The longer charts remain a synthetic, reproducible research history and are explicitly labelled as such. "
    "Public observations are context only: they are never silently injected into the insurer model."
)

snapshot = load_public_macro_snapshot()
st.markdown("### Dated public macro snapshot")
show = snapshot.copy()
show["observation_date"] = show["observation_date"].dt.date.astype(str)
show["as_of_date"] = show["as_of_date"].dt.date.astype(str)
st.dataframe(show[["category", "series", "value", "unit", "observation_date", "source", "status"]],
             use_container_width=True, hide_index=True)
st.caption("Sources and URLs are stored in data/public_macro_snapshot.csv for traceability. Snapshot as-of 5 September 2026.")

st.markdown("### Synthetic research history")
st.warning("Charts below are synthetic and are NOT observed ECB, index, spread or FX history.")
macro = load_macro_data()
regime_df = classify_regime(macro)
regime = latest_regime(macro)
scenario = scenario_for_regime(regime)

c1, c2 = st.columns(2)
c1.metric("Illustrative Current Regime", regime)
c2.metric("Mapped ALM Scenario", scenario)
st.caption("Rule-based classification from inflation trend, equity momentum and credit-spread trend. It is descriptive, not predictive.")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_scatter(x=macro.date, y=macro.ecb_deposit_rate_pct, name="Policy-rate proxy (%)")
    fig.add_scatter(x=macro.date, y=macro.euro_10y_pct, name="EUR 10Y proxy (%)")
    fig.update_layout(title="Synthetic policy-rate and long-end yield series", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = go.Figure()
    fig.add_scatter(x=macro.date, y=macro.euro_inflation_pct, name="Inflation proxy (%)")
    fig.update_layout(title="Synthetic euro-area inflation series", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_scatter(x=macro.date, y=macro.eurostoxx50, name="Euro equity proxy")
    fig.add_scatter(x=macro.date, y=macro.sp500, name="US equity proxy", yaxis="y2")
    fig.update_layout(title="Synthetic equity index series", yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)
with right:
    fig = go.Figure()
    fig.add_scatter(x=macro.date, y=macro.credit_spread_ig_pct, name="IG spread proxy (%)")
    fig.add_scatter(x=macro.date, y=macro.eurusd, name="EUR/USD proxy", yaxis="y2")
    fig.update_layout(title="Synthetic credit-spread and FX series", yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Regime history"):
    st.dataframe(regime_df[["date", "inflation_trend", "equity_momentum", "spread_trend", "regime"]], use_container_width=True, hide_index=True)
