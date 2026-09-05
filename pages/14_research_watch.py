from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui_helpers import page_header

page_header('Research, Market & Regulatory Watch', 'How could relevant publications be captured, summarised and translated into ALM assumptions without inventing live news?', st.session_state.get("active_scenario", "Base"))

watch = pd.DataFrame([
    {"Watch Area": "Monetary policy", "Typical Source": "ECB / central-bank publications", "ALM Question": "Has the expected rate path or curve shape changed?", "Model Link": "Discount curve, bond valuation, DV01, SAA"},
    {"Watch Area": "Inflation", "Typical Source": "Official statistics / macro research", "ALM Question": "Does claims-inflation calibration need review?", "Model Link": "Projected claims, liability PV, scenarios"},
    {"Watch Area": "Insurance regulation", "Typical Source": "EIOPA / supervisory publications", "ALM Question": "Does a change affect investment governance, liquidity or risk monitoring?", "Model Link": "Governance / methodology note only; no pseudo-SCR"},
    {"Watch Area": "Credit markets", "Typical Source": "Market data / research", "ALM Question": "Have spreads or liquidity conditions materially changed?", "Model Link": "Spread duration, stress testing, SAA"},
    {"Watch Area": "Equity / FX markets", "Typical Source": "Market data / research", "ALM Question": "Has risk contribution or foreign-currency exposure changed?", "Model Link": "Risk contribution, FX hedge, scenarios"},
])
st.dataframe(watch, use_container_width=True, hide_index=True)

st.markdown("### Publication synthesis template")
source = st.text_input("Source / publication")
date = st.text_input("Observation date")
message = st.text_area("Key message", placeholder="Two or three factual lines only")
impact = st.selectbox("Primary ALM transmission", ["Rates", "Inflation / claims", "Credit spreads", "Equity", "FX", "Liquidity", "Governance / regulation"])
assumption = st.text_input("Assumption or monitor to review")
if source or message:
    st.markdown("#### Structured note")
    st.write(f"**Source:** {source or '—'}  |  **Date:** {date or '—'}")
    st.write(f"**Key message:** {message or '—'}")
    st.write(f"**ALM transmission:** {impact}")
    st.write(f"**Model / assumption to review:** {assumption or '—'}")
    st.info("A professional workflow would validate facts, retain source links and require human judgement before changing assumptions. This prototype deliberately does not auto-interpret regulatory text.")
