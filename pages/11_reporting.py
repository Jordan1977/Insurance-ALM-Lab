from __future__ import annotations

import streamlit as st

from src.ui_helpers import page_header

from src.analytics import base_analytics, scenario_analytics
from src.reporting import build_html_report, executive_summary

page_header('Automated Executive ALM Reporting', 'Can the core ALM analysis be converted into a concise, internally consistent executive report?', st.session_state.get("active_scenario", "Base"))

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
active = st.session_state.get("active_scenario", "Base")
stress = scenario_analytics(
    base,
    active,
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

summary = executive_summary(
    base["kpis"],
    base["liquidity_coverage"],
    base["equity_risk_contribution"],
    active,
    stress if active != "Base" else None,
)

st.markdown("### Executive Summary")
for line in summary:
    st.write(f"• {line}")

sections = [
    ("Economic Balance Sheet (net of reinsurance)", [
        f"Economic assets: €{base['kpis']['total_assets']:.1f}m.",
        f"Net PV modelled liabilities: €{base['kpis']['total_liabilities']:.1f}m (gross: €{base['liabilities_gross']['present_value']:.1f}m).",
        f"Economic surplus: €{base['kpis']['surplus']:.1f}m; A/L coverage: {base['kpis']['economic_coverage_ratio']:.1%}.",
    ]),
    ("Non-Life Claims", [
        f"Gross claims next 12M: €{base['claims_12m_gross']:.1f}m.",
        f"Long-tail liability share (gross PV): {base['liabilities_gross']['long_tail_share']:.0%}.",
        f"Claims beyond 5 years (gross): €{base['liabilities_gross']['claims_beyond_5y']:.1f}m.",
    ]),
    ("Reinsurance", [
        f"Ultimate gross claims (10Y undiscounted): €{base['reinsurance']['total_gross_claims']:.1f}m.",
        f"Effective recoveries: €{base['reinsurance']['total_effective_recovery']:.1f}m.",
        f"Ultimate net claims: €{base['reinsurance']['total_net_claims']:.1f}m.",
        f"Treaty: retention €{base['treaty'].retention:.0f}m, limit €{base['treaty'].limit:.0f}m, "
        f"recovery rate {base['treaty'].recovery_rate:.0%}, lag {base['treaty'].recovery_lag}y.",
    ]),
    ("ALM Matching", [
        f"Asset modified duration: {base['kpis']['asset_duration']:.2f}y; net liability modified duration: {base['kpis']['liability_duration']:.2f}y.",
        f"Duration gap: {base['kpis']['duration_gap']:+.2f}y; DV01 gap: €{base['kpis']['dv01_gap']:+.4f}m/bp.",
    ]),
    ("Liquidity & Risk", [
        f"12M liquid-assets / interim-claims-need coverage: {base['liquidity_coverage']:.2f}x.",
        f"Gross FX exposure: €{base['fx']['gross_fx_exposure']:.1f}m; net after configured hedge: €{base['fx']['net_fx_exposure']:.1f}m.",
        f"Equity contribution to modelled volatility risk: {base['equity_risk_contribution']:.1%}.",
    ]),
]
if active != "Base":
    sections.append((f"Active Scenario — {active}", [
        f"Stressed assets: €{stress['stressed_assets']:.1f}m; stressed liabilities: €{stress['stressed_liabilities']:.1f}m.",
        f"Stressed surplus: €{stress['surplus']:.1f}m; stressed coverage: {stress['coverage']:.1%}.",
        f"Change in economic surplus: €{stress['delta_surplus']:+.1f}m.",
    ]))

sections.append(("Model Boundary", [
    "Synthetic non-life closed-book balance sheet; no future premiums.",
    "No SCR/ORSA, IFRS 17, tax, management-action or production derivative-pricing engine.",
    "Internal limits and all insurer-specific values are illustrative and not Thélem data.",
]))

st.markdown("### Report Preview")
for heading, lines in sections:
    st.markdown(f"#### {heading}")
    for line in lines:
        st.write(f"• {line}")

html = build_html_report("Insurance ALM Lab — Executive ALM Report", sections)
st.download_button("Download Executive ALM Report (.html)", html, file_name="insurance_alm_executive_report.html", mime="text/html")
text = "\n".join(summary)
st.download_button("Download Executive Summary (.txt)", text, file_name="alm_executive_summary.txt", mime="text/plain")
