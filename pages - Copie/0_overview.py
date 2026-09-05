from __future__ import annotations

import streamlit as st

from src.analytics import base_analytics
from src.formatting import fmt_eur_m, fmt_pct
from src.ui_helpers import metric_row

st.title("Insurance ALM Lab")
st.subheader("Asset-Liability, Risk & Strategic Allocation Analytics")
st.info(
    "Independent educational ALM prototype built around the analytical responsibilities of a non-life insurer. "
    "All insurer portfolios, claims, limits and assumptions are synthetic and do not represent Thélem assurances "
    "or any other institution. Outputs are analytical illustrations, not recommendations."
)

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

metric_row([
    ("Economic Assets", fmt_eur_m(base["kpis"]["total_assets"]), None),
    ("Net Liability PV", fmt_eur_m(base["kpis"]["total_liabilities"]), None),
    ("Economic Surplus", fmt_eur_m(base["kpis"]["surplus"]), None),
    ("Economic A/L Coverage", fmt_pct(base["kpis"]["economic_coverage_ratio"]), None),
])

st.markdown("### Decision architecture")
st.markdown(
    "**Macro backdrop → Economic scenario → Asset repricing → Claims / liability repricing → "
    "Economic surplus → Risk drivers → Hedging / allocation analytics → Reporting**"
)

st.markdown("### How the prototype maps to a non-life ALM role")
mission_rows = [
    ("Investment strategy / strategic asset allocation", "Strategic Allocation", "Constrained, liability-aware SAA with duration, liquidity and risk limits"),
    ("Model financial assets and performance", "Assets / Performance Attribution", "Strategic asset book, instrument-level contractual cash flows, risk contribution, DV01, spread duration and return-vs-risk attribution"),
    ("Model insurance liabilities", "Liabilities", "Five synthetic non-life claim families, payout patterns, claims inflation, PV and duration"),
    ("Analyse financial risks", "Dashboard / Sensitivity / Stress Testing", "Rates, spreads, equity, FX, concentration, liquidity, surplus risk and a one-at-a-time tornado analysis"),
    ("Explore hedging strategies", "Hedging Lab", "DV01-based swap sizing, equity futures proxy and FX hedge overlay"),
    ("Economic Scenario Generator", "Economic Scenarios", "Deterministic scenarios plus correlated Monte Carlo closed-book projection"),
    ("Asset cantonment by product family", "Cantonment", "Linear-programme allocation where each euro of synthetic assets is assigned at most once"),
    ("Macro / financial market monitoring", "Macro & Markets / Transmission / Research Watch", "Regime classification, explicit macro-to-ALM scenario mapping and a monitoring workflow template"),
    ("Financial reporting / risk monitoring", "Reporting / Investment Guidelines / Committee Pack", "Executive ALM report, guideline compliance checks and a condensed committee synthesis"),
    ("Reinvestment of maturing assets", "Reinvestment & Maturity Management", "Maturity ladder and comparison of four reinvestment policies against duration and liquidity"),
    ("Assumption governance / traceability", "Assumptions Hub / Audit Trail", "Central update_assumption() mechanism logging every assumption change"),
]
st.dataframe(
    {"Mission": [x[0] for x in mission_rows], "Module": [x[1] for x in mission_rows], "Demonstration": [x[2] for x in mission_rows]},
    use_container_width=True,
    hide_index=True,
)

st.markdown("### Model boundary")
st.caption(
    "Closed-book analytical framework: no future premiums, no full SCR/ORSA, no IFRS 17 engine, no tax, "
    "no derivative collateral/accounting and no production calibration. These exclusions are deliberate and documented."
)
