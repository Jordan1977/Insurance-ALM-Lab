from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics
from src.scenario_generator import evaluate_deterministic_scenario
from src.risk_engine import liquidity_stress

page_header('Stress Testing', 'Which combined market and insurance stresses create the largest deterioration in the economic ALM position?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

stress_map = {
    "2008-style Financial Stress": ("Recession", {}),
    "2020-style Market Shock": ("Equity -30%", {}),
    "2022-style Inflation / Rate Shock": ("Inflation +2%", {}),
    "Stagflation": ("Stagflation", {}),
    "Recession": ("Recession", {}),
    "Credit / Sovereign Stress": ("Credit Spreads +100bp", {}),
    "Claims Inflation Shock": ("Base", {"extra_claim_inflation": .03}),
    "Large-Loss / Cat-like Shock": ("Base", {"frequency_shock": .30, "severity_shock": .80}),
    "Liquidity / Claims Stress": ("Liquidity / Claims Stress", {}),
}
rows = []
for label, (scenario, extra_kwargs) in stress_map.items():
    r = evaluate_deterministic_scenario(
        base["assets"], scenario,
        st.session_state.get("discount_rate", .03),
        st.session_state.get("claim_inflation", .025),
        st.session_state.get("fx_hedge_ratio", .5),
        **extra_kwargs,
    )
    rows.append({
        "Stress": label,
        "Scenario proxy": scenario,
        "Assets": r["stressed_assets"],
        "Liabilities (net)": r["stressed_liabilities"],
        "Surplus": r["surplus"],
        "Coverage": r["coverage"],
        "Δ Surplus": r["delta_surplus"],
    })
D = pd.DataFrame(rows)
st.caption("Stylised scenario — not exact historical replication. Liabilities shown are NET of reinsurance; "
           "the Large-Loss stress specifically triggers the reinsurance layer (see the dedicated comparison below).")
st.dataframe(D, use_container_width=True, hide_index=True, column_config={"Coverage": st.column_config.NumberColumn(format="%.1%%")})
fig = px.bar(D, x="Stress", y="Δ Surplus", title="Economic surplus deterioration by stress")
st.plotly_chart(fig, use_container_width=True)

selected = st.selectbox("Inspect stress", D.Stress.tolist())
row = D[D.Stress == selected].iloc[0]
st.markdown("### Before / after")
c1, c2, c3 = st.columns(3)
c1.metric("Economic Surplus", f"€{row['Surplus']:,.0f}m", f"€{row['Δ Surplus']:+,.0f}m")
c2.metric("Economic A/L Coverage", f"{row['Coverage']:.1%}", f"{row['Coverage']-base['kpis']['economic_coverage_ratio']:+.1%}")
c3.metric("12M Base Liquidity Coverage", f"{base['liquidity_coverage']:.2f}x")
st.info("Use the Hedging Lab to test first-order mitigation of rate, equity and FX exposures. Stress results remain analytical illustrations rather than recommendations.")


st.markdown("### Dedicated liquidity / claims stress")
LS = liquidity_stress(base["assets"], base["claims_12m"], claims_multiplier=1.20, liquid_haircut=.05, semi_liquid_haircut=.20)
cc = st.columns(4)
cc[0].metric("Base Available Liquidity", f"€{LS['base_available_liquidity']:,.0f}m")
cc[1].metric("Stressed Available Liquidity", f"€{LS['stressed_available_liquidity']:,.0f}m")
cc[2].metric("Stressed 12M Claims", f"€{LS['stressed_claims_12m']:,.0f}m")
cc[3].metric("Stressed Liquidity Coverage", f"{LS['stressed_coverage']:.2f}x")
st.caption("Illustrative stress: claims +20%, haircuts to monetisable assets and only 25% of semi-liquid assets assumed available. Not a regulatory liquidity metric.")

st.markdown("### Large-Loss / Cat-like Shock: gross vs. net of reinsurance (Section 15)")
st.caption("Stylised insurance claims shock — not a catastrophe model.")
from src.liability_model import build_liability_cash_flows
from src.reinsurance import reinsurance_summary

base_cf = build_liability_cash_flows(st.session_state.get("claim_inflation", .025))
stress_cf = build_liability_cash_flows(st.session_state.get("claim_inflation", .025), frequency_shock=.30, severity_shock=.80)
base_reins = reinsurance_summary(base_cf, base["treaty"])
stress_reins = reinsurance_summary(stress_cf, base["treaty"])
gross_stressed_assets = evaluate_deterministic_scenario(base["assets"], "Base", st.session_state.get("discount_rate", .03),
                                                        st.session_state.get("claim_inflation", .025), st.session_state.get("fx_hedge_ratio", .5))["stressed_assets"]
cc = st.columns(4)
cc[0].metric("Gross Claims (12M)", f"€{stress_reins['claims_12m_gross']:,.0f}m", f"€{stress_reins['claims_12m_gross']-base_reins['claims_12m_gross']:+,.0f}m")
cc[1].metric("Recoveries (12M)", f"€{stress_reins['recoveries_12m']:,.0f}m", f"€{stress_reins['recoveries_12m']-base_reins['recoveries_12m']:+,.0f}m")
cc[2].metric("Net Claims (12M)", f"€{stress_reins['claims_12m_net']:,.0f}m", f"€{stress_reins['claims_12m_net']-base_reins['claims_12m_net']:+,.0f}m")
gross_surplus = gross_stressed_assets - stress_reins["total_gross_claims"]
net_surplus = gross_stressed_assets - stress_reins["total_net_claims"]
cc[3].metric("Surplus Improvement from Reinsurance (ultimate)", f"€{net_surplus - gross_surplus:,.0f}m")
st.caption("Full annual detail, treaty controls and the interim-liquidity-vs-ultimate-cost distinction: Reinsurance page.")
