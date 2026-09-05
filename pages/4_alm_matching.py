from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.asset_model import build_instrument_book, instrument_cash_flows
from src.liability_model import build_liability_cash_flows
from src.reinsurance import net_liability_cash_flows
from src.alm_engine import cash_flow_matching_table, maturity_bucket_matching

page_header('Asset-Liability Cash-Flow Matching', 'Do contractual asset cash flows and available liquidity adequately cover projected net claim payments?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
book = build_instrument_book(base["assets"])
asset_cf = instrument_cash_flows(book, horizon=10)
gross_liab_cf = build_liability_cash_flows(st.session_state.get("claim_inflation", .025))
net_liab_cf = net_liability_cash_flows(gross_liab_cf, base["treaty"])
match = cash_flow_matching_table(asset_cf, net_liab_cf, contractual_only=True)
buckets = maturity_bucket_matching(asset_cf, net_liab_cf, contractual_only=True)

k = base["kpis"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Economic A/L Coverage (net)", f"{k['economic_coverage_ratio']:.1%}")
c2.metric("Duration Gap (net)", f"{k['duration_gap']:+.2f}y")
c3.metric("DV01 Gap (net)", f"€{k['dv01_gap']:+.4f}m/bp")
c4.metric("Years with Net CF Shortfall", f"{int(match.shortfall.sum())}")

fig = go.Figure()
fig.add_bar(x=match.year, y=match.asset_cf, name="Contractual asset cash flows")
fig.add_bar(x=match.year, y=match.liability_cf, name="Net claims (post-reinsurance)")
fig.update_layout(barmode="group", title="Contractual asset cash flows vs NET projected claims", yaxis_title="EURm")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Annual matching table (net)")
st.dataframe(match, use_container_width=True, hide_index=True)
first_deficit = match.loc[match.shortfall, "year"].min() if match.shortfall.any() else None
worst_gap = match.gap.min()
min_buffer = match.cumulative_gap.min()
c1, c2, c3 = st.columns(3)
c1.metric("First Deficit Year", f"Year {int(first_deficit)}" if pd.notna(first_deficit) else "None in horizon")
c2.metric("Worst Annual Gap", f"€{worst_gap:,.1f}m")
c3.metric("Minimum Cumulative Buffer", f"€{min_buffer:,.1f}m")

st.markdown("### Gross claims, recoveries and net claims by year")
gross_by_year = gross_liab_cf.groupby("year")["cash_flow"].sum().rename("gross_claims")
net_by_year = net_liab_cf.groupby("year")["cash_flow"].sum().rename("net_claims")
recovery_by_year = (gross_by_year - net_by_year).rename("effective_recovery")
gross_net_table = pd.concat([gross_by_year, recovery_by_year, net_by_year], axis=1).reset_index()
st.dataframe(gross_net_table, use_container_width=True, hide_index=True)

st.markdown("### Maturity-bucket matching (net)")
st.dataframe(buckets, use_container_width=True, hide_index=True)
st.caption("Equity, real-estate and infrastructure principal maturities are not invented. Their estimated income is excluded from the contractual matching view.")
