from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.formatting import fmt_eur_m, fmt_delta_eur_m
from src.liability_model import build_liability_cash_flows
from src.reinsurance import (ExcessOfLossTreaty, QuotaShareTreaty, DEFAULT_TREATY,
                             reinsurance_summary, compare_reinsurance_structures)
from src.ui_helpers import page_header, metric_row

page_header("Reinsurance: Gross -> Net Claims",
           "How much of the ultimate claim cost does reinsurance actually absorb, and when does the cash arrive?")
st.caption("Modelled as a single portfolio-level ANNUAL AGGREGATE excess-of-loss layer, for tractability -- a real "
           "treaty attaches per claim occurrence, not to the sum of a year's claims. See methodology.md.")

with st.expander("Treaty parameters", expanded=False):
    c = st.columns(3)
    retention = c[0].number_input("Retention (EURm/yr)", 0.0, 1000.0, DEFAULT_TREATY.retention, 10.0)
    limit = c[1].number_input("Limit (EURm/yr)", 0.0, 1000.0, DEFAULT_TREATY.limit, 10.0)
    recovery_rate = c[2].slider("Recovery rate", 0.0, 1.0, DEFAULT_TREATY.recovery_rate, .05)
    c2 = st.columns(2)
    recovery_lag = c2[0].number_input("Recovery lag (yrs)", 0, 5, DEFAULT_TREATY.recovery_lag, 1)
    haircut = c2[1].slider("Counterparty haircut", 0.0, .30, DEFAULT_TREATY.counterparty_haircut, .01)
treaty = ExcessOfLossTreaty(retention=retention, limit=limit, recovery_rate=recovery_rate,
                            recovery_lag=int(recovery_lag), counterparty_haircut=haircut)

claim_inflation = st.session_state.get("claim_inflation", .025)
cf = build_liability_cash_flows(claim_inflation)
summary = reinsurance_summary(cf, treaty)

tab_gross_net, tab_liquidity, tab_stress, tab_structure = st.tabs(
    ["Gross → Net", "Liquidity Timing", "Large-Loss Stress", "Structure Comparison"])

with tab_gross_net:
    metric_row([
        ("Gross Claims (10Y)", fmt_eur_m(summary["total_gross_claims"]), None),
        ("Effective Recoveries", fmt_eur_m(summary["total_effective_recovery"]), None),
        ("Ultimate Net Claims", fmt_eur_m(summary["total_net_claims"]), None),
    ])
    fig = go.Figure()
    fig.add_bar(x=summary["annual_detail"].year, y=summary["annual_detail"].gross_claims, name="Gross claims")
    fig.add_bar(x=summary["annual_detail"].year, y=summary["annual_detail"].net_claims, name="Net claims")
    fig.update_layout(barmode="group", title="Gross vs. net claims by year", yaxis_title="EURm", height=420,
                      margin=dict(t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Annual detail table"):
        st.dataframe(summary["annual_detail"], use_container_width=True, hide_index=True)

with tab_liquidity:
    st.caption("Ultimate cost vs. cash timing (Section 13): a treaty can lower the ultimate net loss while still "
              "leaving a temporary liquidity gap if the recovery lags the claim payment.")
    metric_row([
        ("12M Interim Liquidity Need", fmt_eur_m(summary["liquidity_detail"].iloc[0].net_liquidity_impact_this_year), None),
    ], help_texts=["Gross claims paid this year, less any recovery cash actually received this year. This is what "
                  "the Executive Dashboard's 12M liquidity metric uses -- not the ultimate net claim cost."])
    st.dataframe(summary["liquidity_detail"][["year", "cash_outflow_this_year", "cash_inflow_this_year", "net_liquidity_impact_this_year"]],
                 use_container_width=True, hide_index=True)

with tab_stress:
    st.caption("Stylised insurance claims shock -- not a catastrophe model.")
    stress_cols = st.columns(2)
    freq_shock = stress_cols[0].slider("Claim frequency shock", 0.0, .50, .20, .05)
    sev_shock = stress_cols[1].slider("Claim severity shock", 0.0, 1.0, .50, .05)
    stress_cf = build_liability_cash_flows(claim_inflation, frequency_shock=freq_shock, severity_shock=sev_shock)
    stress_summary = reinsurance_summary(stress_cf, treaty)
    metric_row([
        ("Stressed Gross (12M)", fmt_eur_m(stress_summary["claims_12m_gross"]), fmt_delta_eur_m(stress_summary["claims_12m_gross"] - summary["claims_12m_gross"])),
        ("Stressed Recoveries (12M)", fmt_eur_m(stress_summary["recoveries_12m"]), fmt_delta_eur_m(stress_summary["recoveries_12m"] - summary["recoveries_12m"])),
        ("Stressed Net (12M)", fmt_eur_m(stress_summary["claims_12m_net"]), fmt_delta_eur_m(stress_summary["claims_12m_net"] - summary["claims_12m_net"])),
    ])
    st.info("By design, the default treaty is calibrated above ordinary base-case claims so it barely bites day to "
           "day, and triggers materially larger recoveries precisely under a large-loss stress.")

with tab_structure:
    st.caption("Illustrative only: this comparison ignores ceded premium, commissions, reinstatements and capital "
              "effects. It is a claims-side analytical comparison, not a placement or pricing recommendation.")
    qs_share = st.slider("Illustrative quota-share ceded share", 0.0, .60, .30, .05)
    qs = QuotaShareTreaty(ceded_share=qs_share, recovery_lag=0, counterparty_haircut=.02)
    st.markdown("**Base-case claims**")
    st.dataframe(compare_reinsurance_structures(cf.groupby("year")["cash_flow"].sum(), treaty, qs),
                use_container_width=True, hide_index=True)
    st.markdown("**Large-loss stress**")
    stress_cf_for_compare = build_liability_cash_flows(claim_inflation, frequency_shock=.20, severity_shock=.50)
    st.dataframe(compare_reinsurance_structures(stress_cf_for_compare.groupby("year")["cash_flow"].sum(), treaty, qs),
                use_container_width=True, hide_index=True)
    st.caption("Quota share reduces ordinary and stressed claims proportionally; XoL is deliberately calibrated to "
              "provide little ordinary-course relief and materially more protection in tail years.")
