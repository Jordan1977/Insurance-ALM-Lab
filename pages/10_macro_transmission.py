from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.ui_helpers import page_header, metric_row

from src.analytics import base_analytics
from src.macro_engine import REGIME_TO_SCENARIO
from src.scenario_generator import DETERMINISTIC_SCENARIOS, evaluate_deterministic_scenario

page_header('Macro → Markets → Non-Life ALM Transmission', 'How does a macro regime translate into market factors, claim dynamics and the insurer economic surplus?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
regime = st.selectbox("Illustrative macro regime", list(REGIME_TO_SCENARIO))
scenario = REGIME_TO_SCENARIO[regime]
s = DETERMINISTIC_SCENARIOS[scenario]

st.markdown(f"### Implied illustrative ALM scenario: **{scenario}**")
metric_row([
    ("Rates", f"{s['d_rate']*10_000:+.0f}bp", None),
    ("Equities", f"{s['equity_shock']:+.0%}", None),
    ("Credit Spreads", f"{s['credit_spread_shock']*10_000:+.0f}bp", None),
    ("Inflation", f"{s['inflation_shock']:+.1%}", None),
    ("FX", f"{s['fx_shock']:+.0%}", None),
])

transmission = {
    "Growth": "Growth resilient → risk assets supported → spreads contained → asset surplus may improve, while concentration risk can rise.",
    "Slowdown": "Activity slows → equities weaken → claims inflation may moderate → asset losses dominate unless lower rates support bonds/liability valuation.",
    "Disinflation": "Inflation eases → claims severity pressure moderates → rates decline → fixed-income assets rise while lower discounting can increase liability PV.",
    "Inflation": "Inflation rises → claim cash flows rise → rates can rise → bond prices fall; the net effect depends on A-L rate sensitivity and claims-inflation sensitivity.",
    "Stagflation": "Inflation and claims severity rise while equities weaken and spreads widen → both sides of the balance sheet can move adversely.",
    "Recession": "Equities fall and spreads widen while rates may decline → risky-asset losses are partly offset by rate effects; long-tail liabilities can revalue upward.",
}
st.write(transmission[regime])

result = evaluate_deterministic_scenario(
    base["assets"],
    scenario,
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

c1, c2, c3 = st.columns(3)
c1.metric("Economic Surplus", f"€{result['surplus']:,.0f}m", f"€{result['delta_surplus']:+,.0f}m")
c2.metric("Economic A/L Coverage", f"{result['coverage']:.1%}", f"{result['coverage']-result['base_coverage']:+.1%}")
c3.metric("Asset P&L", f"€{result['stressed_assets']-result['base_assets']:+,.0f}m")

labels = ["Base surplus"] + list(result["attribution"]) + ["Scenario surplus"]
values = [result["base_surplus"]] + list(result["attribution"].values()) + [result["surplus"]]
measure = ["absolute"] + ["relative"] * len(result["attribution"]) + ["total"]
fig = go.Figure(go.Waterfall(x=labels, y=values, measure=measure))
fig.update_layout(title="Macro regime → economic surplus attribution", yaxis_title="EURm")
st.plotly_chart(fig, use_container_width=True)

if st.button("Set this as active scenario"):
    st.session_state.active_scenario = scenario
    st.success(f"Active scenario set to {scenario}. Open the Executive Dashboard to compare base vs active scenario.")
