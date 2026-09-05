from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.asset_model import (
    build_asset_portfolio,
    build_correlation_matrix,
    build_instrument_book,
    fx_exposure,
    portfolio_expected_return,
    portfolio_modified_duration,
    portfolio_volatility,
    risk_contribution,
)
from src.risk_engine import concentration_report, classify_liquidity

page_header('Asset Book & Investment Risk Analytics', 'How is the synthetic investment portfolio allocated, valued and exposed to market, credit and liquidity risks?', st.session_state.get("active_scenario", "Base"))

assets = build_asset_portfolio(st.session_state.get("asset_weights"))
corr = build_correlation_matrix(assets.asset_class.tolist())
book = build_instrument_book(assets)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Assets", f"€{assets.market_value.sum():,.0f}m")
c2.metric("Expected Return", f"{portfolio_expected_return(assets):.2%}")
c3.metric("Modelled Volatility", f"{portfolio_volatility(assets, corr):.2%}")
c4.metric("Modified Duration", f"{portfolio_modified_duration(assets):.2f}y")

left, right = st.columns(2)
with left:
    fig = px.bar(assets, x="asset_class", y="weight", title="Strategic allocation")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
with right:
    rc = risk_contribution(assets, corr)
    fig = px.bar(rc, x="asset_class", y="pct_of_total_risk", title="Contribution to asset volatility risk")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Rate, spread and liquidity sensitivities")
show = assets[["asset_class", "market_value", "yield", "modified_duration", "dv01", "spread_duration", "liquidity_score", "rating", "currency"]].copy()
st.dataframe(show, use_container_width=True, hide_index=True)

l, r = st.columns(2)
with l:
    fig = px.imshow(corr, text_auto=".2f", aspect="auto", title="Asset-class correlation matrix")
    st.plotly_chart(fig, use_container_width=True)
with r:
    conc = concentration_report(assets)
    st.markdown("#### Concentration monitor")
    st.dataframe(conc, use_container_width=True, hide_index=True)
    fx = fx_exposure(assets, st.session_state.get("fx_hedge_ratio", .5))
    st.metric("Gross foreign-currency exposure", f"€{fx['gross_fx_exposure']:,.1f}m")
    st.metric("Net exposure after configured hedge", f"€{fx['net_fx_exposure']:,.1f}m")

with st.expander("Instrument-level synthetic book"):
    st.caption("Contractual assets have calibrated face values; market value is not treated as principal.")
    st.dataframe(book, use_container_width=True, hide_index=True)

with st.expander("Liquidity classification"):
    st.dataframe(classify_liquidity(assets), use_container_width=True, hide_index=True)
