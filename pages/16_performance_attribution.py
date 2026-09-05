from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.performance_attribution import performance_attribution, return_vs_risk_contribution, SYNTHETIC_TRAILING_12M_SHOCK

page_header('Illustrative Factor-Based Return Attribution', 'Which market factors explain the synthetic portfolio P&L, and does the attribution reconcile to ending market value?', st.session_state.get("active_scenario", "Base"))
st.warning("This is NOT a Brinson allocation/selection attribution and NOT a report of actual historical performance. "
           "It applies one clearly-labelled **synthetic** trailing-12-month market shock through the same scenario "
           "engine used elsewhere in the app, so the return build-up is internally consistent rather than "
           "reverse-engineered from a fabricated 'historical return' number.")

with st.expander("Synthetic shock applied (illustrative, not observed)"):
    st.json(SYNTHETIC_TRAILING_12M_SHOCK)

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
detail, summary = performance_attribution(base["assets"], fx_hedge_ratio=st.session_state.get("fx_hedge_ratio", .5))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Beginning Market Value", f"€{summary['beginning_mv']:,.0f}m")
c2.metric("Ending Market Value", f"€{summary['ending_mv']:,.0f}m")
c3.metric("Total Portfolio Return", f"{summary['total_return']:.2%}")
c4.metric("Reconciliation check", f"{summary['reconciled_total']:.4%}",
          help="Sum of the waterfall channels below; must equal Total Portfolio Return to floating-point precision.")
assert abs(summary["total_return"] - summary["reconciled_total"]) < 1e-9  # same guarantee tests/ enforce

fig = go.Figure(go.Waterfall(
    x=["Beginning MV"] + list(summary["waterfall"].keys()) + ["Ending MV"],
    y=[summary["beginning_mv"]] + [v * summary["beginning_mv"] for v in summary["waterfall"].values()] + [0.0],
    measure=["absolute"] + ["relative"] * len(summary["waterfall"]) + ["total"],
))
fig.update_layout(title="Beginning MV -> Ending MV by factor (EURm)", yaxis_title="EURm", height=430)
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Contribution by asset class")
show = detail.copy()
for col in ["beginning_mv", "carry_pnl", "rate_pnl", "spread_pnl", "equity_real_pnl", "fx_pnl", "total_pnl", "ending_mv"]:
    show[col] = show[col].map(lambda v: f"€{v:,.1f}m")
for col in ["asset_class_return", "return_contribution"]:
    show[col] = detail[col].map(lambda v: f"{v:.2%}")
st.dataframe(show, use_container_width=True, hide_index=True)

st.markdown("### Return contribution vs. risk contribution")
st.caption("Analytical Observation, not an investment judgement: does an asset class earn its share of the risk taken?")
cmp = return_vs_risk_contribution(detail, base["risk_contribution"])
fig2 = go.Figure()
fig2.add_bar(x=cmp.asset_class, y=cmp.pct_of_total_return, name="Share of total return")
fig2.add_bar(x=cmp.asset_class, y=cmp.pct_of_total_risk, name="Share of total risk")
fig2.update_layout(barmode="group", yaxis_tickformat=".0%", height=400)
st.plotly_chart(fig2, use_container_width=True)

top_risk_row = cmp.sort_values("pct_of_total_risk", ascending=False).iloc[0]
st.info(f"**Analytical observation:** {top_risk_row.asset_class} represents {top_risk_row.weight:.0%} of assets, "
        f"contributes {top_risk_row.pct_of_total_return:.0%} of the illustrative return, and "
        f"{top_risk_row.pct_of_total_risk:.0%} of total modelled asset-volatility risk.")
