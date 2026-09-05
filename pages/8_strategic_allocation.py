from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.optimization import optimize_allocation
from src.formatting import fmt_pct, fmt_years, fmt_ratio
from src.ui_helpers import metric_row

page_header('Liability-Aware Strategic Asset Allocation', 'How does the preferred strategic allocation change once duration, liquidity and insurance constraints are considered?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
mode = st.selectbox("Objective", ["Liability-Aware", "Min Vol", "Max Sharpe"])
weights, metrics = optimize_allocation(
    base["assets"],
    base["corr"],
    base["liabilities"]["modified_duration"],
    mode=mode,
    cash_min=st.session_state.get("cash_min", .05),
    cash_max=st.session_state.get("cash_max", .20),
    equity_max=st.session_state.get("equity_max", .20),
    illiquid_max=st.session_state.get("illiquid_max", .20),
    hy_max=st.session_state.get("hy_max", .10),
    duration_gap_tolerance=st.session_state.get("duration_gap_tolerance", 1.0),
    liquidity_target=st.session_state.get("liquidity_target", 1.5),
    claims_12m=base["claims_12m"],
    total_assets=base["kpis"]["total_assets"],
    risk_free_rate=st.session_state.get("risk_free_rate", .025),
)

if not metrics["success"]:
    st.error(f"Optimisation failed; current weights retained. Solver message: {metrics['message']}")

metric_row([
    ("Expected Return", fmt_pct(metrics["expected_return"], 2), None),
    ("Volatility", fmt_pct(metrics["volatility"], 2), None),
    ("Sharpe", f"{metrics['sharpe']:.2f}", None),
    ("Duration Gap", fmt_years(metrics["duration_gap"], signed=True), None),
    ("12M Liquidity", fmt_ratio(metrics["liquidity_coverage"]), None),
])

fig = go.Figure()
fig.add_bar(x=weights.asset_class, y=weights.current_weight, name="Current")
fig.add_bar(x=weights.asset_class, y=weights.optimized_weight, name="Optimized")
fig.update_layout(barmode="group", yaxis_tickformat=".0%", title="Current vs optimized strategic allocation")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Constraint check")
st.write(f"Duration-gap limit: ±{st.session_state.get('duration_gap_tolerance',1.0):.1f}y — **actual {metrics['duration_gap']:+.2f}y**")
st.write(f"12M liquidity target: {st.session_state.get('liquidity_target',1.5):.2f}x — **actual {metrics['liquidity_coverage']:.2f}x**")
st.info("ALM principle demonstrated: the portfolio with the highest standalone Sharpe ratio is not necessarily the preferred allocation once claim timing, liquidity and duration constraints are imposed.")
