from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.asset_model import build_instrument_book
from src.guidelines import check_compliance, overall_compliance, portfolio_guideline_metrics
from src.liability_model import build_liability_cash_flows
from src.formatting import fmt_eur_m, fmt_ratio, fmt_years, fmt_pct
from src.ui_helpers import metric_row
from src.reinvestment import (
    REINVESTMENT_POLICIES, REINVESTMENT_UNIVERSE, annual_cash_projection,
    compare_reinvestment_policies, policy_outcome,
)

page_header('Reinvestment & Maturity Management', 'As assets mature and claims are paid, how should available cash be reinvested to improve ALM matching without hiding trade-offs?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
horizon = st.slider("Horizon (years)", 1, 5, 5)
book = build_instrument_book(base["assets"])
gross_cf = build_liability_cash_flows(st.session_state.get("claim_inflation", .025))

with st.expander("Reinvestment universe (Section 27)"):
    st.dataframe([{"Candidate": c.name, "Yield": f"{c.yield_:.2%}", "Duration": f"{c.duration:.1f}y",
                   "Spread": f"{c.spread:.2%}", "Rating": c.rating, "Liquidity": c.liquidity,
                   "Maturity": f"{c.maturity:.0f}y"} for c in REINVESTMENT_UNIVERSE],
                 use_container_width=True, hide_index=True)

st.markdown("### Annual cash account (Section 26)")
policy_for_ladder = st.selectbox("Policy to inspect", REINVESTMENT_POLICIES, index=4)
ladder, candidate = annual_cash_projection(book, gross_cf, policy_for_ladder,
                                           base["kpis"]["asset_duration"], base["liabilities"]["modified_duration"],
                                           base["treaty"], horizon)
st.caption(f"Selected candidate for reinvested cash under **{policy_for_ladder}**: **{candidate.name if candidate else 'Cash / money market'}**")

fig = go.Figure()
fig.add_bar(x=ladder.year, y=ladder.coupon_income, name="Coupon income")
fig.add_bar(x=ladder.year, y=ladder.bond_maturities, name="Bond maturities")
fig.add_bar(x=ladder.year, y=ladder.reinsurance_recoveries, name="Reinsurance recoveries")
fig.add_bar(x=ladder.year, y=-ladder.gross_claims_paid, name="Gross claims paid (outflow)")
fig.add_scatter(x=ladder.year, y=ladder.amount_reinvested, name="Amount reinvested", mode="lines+markers", yaxis="y2")
fig.update_layout(barmode="relative", height=440, yaxis_title="EURm (year)",
                  yaxis2=dict(title="Reinvested (EURm)", overlaying="y", side="right"),
                  title="Cash inflows/outflows and reinvestment by year")
st.plotly_chart(fig, use_container_width=True)
with st.expander("Annual cash-account detail"):
    st.dataframe(ladder, use_container_width=True, hide_index=True)
st.caption("`shortfall_funded_externally` is the amount that year's own coupon/maturity/recovery inflows could not "
           "cover, assumed drawn from the insurer's other liquid assets -- not carried forward as a growing "
           "negative cash balance. `ending_cash` is therefore always >= 0 by construction.")

st.markdown("### Reinvestment policy comparison")
comparison = compare_reinvestment_policies(base["assets"], book, gross_cf, base["liabilities"]["modified_duration"], base["treaty"], horizon)
focus = comparison.set_index("policy").loc["Liability-matching reinvestment"]
metric_row([
    ("Asset Duration After", fmt_years(float(focus.asset_duration_after)), None),
    ("Duration Gap After", fmt_years(float(focus.duration_gap_after), signed=True), None),
    ("Expected Yield", fmt_pct(float(focus.expected_yield), 2) if "expected_yield" in focus.index else "n/a", None),
])
with st.expander("Compare all reinvestment policies", expanded=True):
    st.dataframe(comparison.drop(columns=["basket_weights"], errors="ignore"), use_container_width=True, hide_index=True)

liability_row = comparison.set_index("policy").loc["Liability-matching reinvestment"]
if liability_row.get("basket_weights"):
    st.markdown("#### Optimised liability-matching basket")
    basket_df = [{"Instrument": k, "Weight": v} for k, v in liability_row["basket_weights"].items()]
    st.dataframe(basket_df, use_container_width=True, hide_index=True)
    st.caption("The optimiser targets the duration required on new money for the *whole* asset book to move toward the net-liability duration, subject to a minimum liquidity constraint. It is an analytical allocation, not a trade recommendation.")

fig2 = go.Figure()
fig2.add_bar(x=comparison.policy, y=comparison.asset_duration_after, name="Asset duration after")
fig2.add_hline(y=base["liabilities"]["modified_duration"], line_dash="dash", annotation_text="Liability duration (net)")
fig2.update_layout(title="Asset duration by reinvestment policy", yaxis_title="Years", height=400)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### Guideline check on the selected policy")
policy = st.selectbox("Policy to test against Investment Guidelines", comparison.policy.tolist(), index=4)
row = comparison.set_index("policy").loc[policy]
kpis_after = dict(base["kpis"])
kpis_after["duration_gap"] = float(row.duration_gap_after)
limits = dict(
    equity_max=st.session_state.get("equity_max", .20), hy_max=st.session_state.get("hy_max", .10),
    illiquid_max=st.session_state.get("illiquid_max", .20), cash_min=st.session_state.get("cash_min", .05),
    duration_gap_tolerance=st.session_state.get("duration_gap_tolerance", 1.0),
    liquidity_target=st.session_state.get("liquidity_target", 1.5),
)
metrics = portfolio_guideline_metrics(base["assets"])
check = check_compliance(metrics, kpis_after, base["liquidity_coverage"], limits)
status, breaches = overall_compliance(check)
(st.success if status == "COMPLIANT" else st.error)(f"**{policy}** is **{status}** with current Investment Guidelines" + (f" — breaches: {', '.join(breaches)}" if breaches else "."))
st.caption("Extending duration can improve the duration gap while doing nothing for (or worsening) liquidity or "
           "credit-quality concentration -- the guideline check surfaces that trade-off explicitly rather than only "
           "reporting the metric the policy was designed to improve.")
