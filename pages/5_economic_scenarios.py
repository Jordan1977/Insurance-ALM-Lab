from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header, metric_row

from src.analytics import base_analytics
from src.risk_engine import surplus_at_risk
from src.scenario_generator import (
    DETERMINISTIC_SCENARIOS,
    evaluate_deterministic_scenario,
    run_monte_carlo,
    surplus_distribution_from_mc,
)

page_header('Economic Scenarios & Monte Carlo', 'How do deterministic and stochastic market/claims shocks transmit to economic surplus and coverage?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

scenario = st.selectbox("Deterministic scenario", list(DETERMINISTIC_SCENARIOS), index=list(DETERMINISTIC_SCENARIOS).index(st.session_state.get("active_scenario", "Base")))
st.session_state.active_scenario = scenario
result = evaluate_deterministic_scenario(
    base["assets"],
    scenario,
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

s = DETERMINISTIC_SCENARIOS[scenario]
metric_row([
    ("Rates", f"{s['d_rate']*10_000:+.0f}bp", None),
    ("Equities", f"{s['equity_shock']:+.0%}", None),
    ("Spreads", f"{s['credit_spread_shock']*10_000:+.0f}bp", None),
    ("Inflation", f"{s['inflation_shock']:+.1%}", None),
    ("FX", f"{s['fx_shock']:+.0%}", None),
])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stressed Assets", f"€{result['stressed_assets']:,.0f}m", f"€{result['stressed_assets']-result['base_assets']:+,.0f}m")
c2.metric("Stressed Liabilities", f"€{result['stressed_liabilities']:,.0f}m", f"€{result['stressed_liabilities']-result['base_liabilities']:+,.0f}m", delta_color="inverse")
c3.metric("Stressed Surplus", f"€{result['surplus']:,.0f}m", f"€{result['delta_surplus']:+,.0f}m")
c4.metric("Economic A/L Coverage", f"{result['coverage']:.1%}", f"{result['coverage']-result['base_coverage']:+.1%}")

st.markdown("### ALM Decision Chain")
st.markdown("**Macro shock → market-factor shocks → asset P&L / claim revaluation → economic surplus → risk drivers → mitigation analytics**")

labels = ["Base surplus"] + list(result["attribution"]) + ["Stressed surplus"]
values = [result["base_surplus"]] + list(result["attribution"].values()) + [result["surplus"]]
measure = ["absolute"] + ["relative"] * len(result["attribution"]) + ["total"]
fig = go.Figure(go.Waterfall(x=labels, y=values, measure=measure))
fig.update_layout(title="Surplus attribution by risk driver", yaxis_title="EURm", height=450)
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Stochastic projection")
controls = st.columns(3)
n_sims = controls[0].select_slider("Simulations", options=[500, 1000, 2500, 5000], value=1000)
horizon = controls[1].slider("Projection horizon (years)", 3, 10, 5)
seed = controls[2].number_input("Random seed", min_value=1, max_value=100000, value=123, step=1)

if st.button("Run Monte Carlo", type="primary"):
    with st.spinner("Running correlated economic scenarios..."):
        mc = run_monte_carlo(n_sims=n_sims, horizon=horizon, seed=int(seed))
        dist = surplus_distribution_from_mc(
            mc,
            base["assets"],
            st.session_state.get("discount_rate", .03),
            st.session_state.get("claim_inflation", .025),
            horizon,
            st.session_state.get("fx_hedge_ratio", .5),
        )
        risk = surplus_at_risk(base["kpis"]["surplus"], dist.surplus.to_numpy(), .99)
        st.session_state["mc_dist"] = dist
        st.session_state["mc_risk"] = risk

if "mc_dist" in st.session_state:
    dist = st.session_state["mc_dist"]
    risk = st.session_state["mc_risk"]
    q01 = float(dist.surplus.quantile(.01))
    metric_row([
        ("Median Surplus", f"€{dist.surplus.median():,.0f}m", None),
        ("1% Surplus Quantile", f"€{q01:,.0f}m", None),
        ("SaR 99%", f"€{risk['surplus_at_risk']:,.0f}m", None),
        ("P(Coverage < 100%)", f"{(dist.economic_coverage_ratio < 1).mean():.1%}", None),
        ("P(Asset Sale)", f"{dist.liquidity_shortfall_flag.mean():.1%}", None),
    ], help_texts=[None, None, "Surplus-at-Risk at 99% confidence.", None,
        "Share of scenarios where annual net claim cash outflow exceeds the simulated cash bucket and non-cash assets must be sold."])
    fig = go.Figure(go.Histogram(x=dist.surplus, nbinsx=55))
    fig.add_vline(x=0, line_dash="dash")
    fig.update_layout(title="Distribution of horizon economic surplus", xaxis_title="EURm", yaxis_title="Scenario count")
    st.plotly_chart(fig, use_container_width=True)

st.caption("The stochastic model is a simplified dynamic closed-book projection with family-level Poisson claim frequency, lognormal severity, gross claim payments and lagged XoL recoveries. No future premiums, regulatory capital, tax, management-action optimisation or production calibration are modelled.")
