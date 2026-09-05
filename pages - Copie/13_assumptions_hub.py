from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui_helpers import page_header

from src.asset_model import ASSET_ASSUMPTIONS
from src.audit_trail import AUDIT_TRAIL_KEY, update_assumption
from src.liability_model import LIABILITY_FAMILIES, discount_curve, expected_gross_claims
from src.scenario_generator import DETERMINISTIC_SCENARIOS

page_header('Financial Assumptions Hub', 'Which assumptions drive the model, where do they come from and which modules do they affect?', st.session_state.get("active_scenario", "Base"))

st.session_state.setdefault(AUDIT_TRAIL_KEY, [])
st.session_state.setdefault("_assumption_history", {})

TRACKED = [
    ("discount_rate", "Discount-rate level", "User Input", "Liability PV, duration, deterministic scenarios"),
    ("claim_inflation", "Base claims inflation", "User Input", "Projected claims, liability PV, Monte Carlo"),
    ("risk_free_rate", "Risk-free rate", "User Input", "Sharpe / allocation analytics"),
    ("fx_hedge_ratio", "FX hedge ratio", "User Input", "Deterministic scenario P&L, Monte Carlo, hedging"),
    ("equity_max", "Maximum equity allocation limit", "Synthetic", "SAA constraint, Investment Guidelines"),
    ("illiquid_max", "Maximum illiquid allocation limit", "Synthetic", "SAA constraint, Investment Guidelines"),
    ("hy_max", "Maximum High Yield allocation limit", "Synthetic", "SAA constraint, Investment Guidelines"),
    ("duration_gap_tolerance", "Duration-gap tolerance", "Synthetic", "SAA constraint, Investment Guidelines"),
    ("liquidity_target", "12M liquidity coverage target", "Synthetic", "SAA constraint, Investment Guidelines"),
]

rows = []
for key, label, value_type, modules in TRACKED:
    current = st.session_state.get(key)
    previous = st.session_state["_assumption_history"].get(key, current)
    if previous != current:
        update_assumption(
            st.session_state[AUDIT_TRAIL_KEY], label, previous, current,
            reason="Changed via sidebar control", affected_modules=modules,
            scenario=st.session_state.get("active_scenario", "Base"),
        )
    st.session_state["_assumption_history"][key] = current
    rows.append({"Parameter": label, "Previous": previous, "Current": current, "Change": "Yes" if previous != current else "No",
                 "Type": value_type, "Source": "Sidebar slider", "Affected Modules": modules})

st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
st.caption("Changes are picked up the moment you move a sidebar slider; open the Audit Trail page to see the logged history.")

if st.button("Reset base case"):
    for key, _, _, _ in TRACKED:
        st.session_state.pop(key, None)
    st.session_state["_assumption_history"] = {}
    st.rerun()

st.markdown("### Synthetic EUR discount curve")
st.dataframe(discount_curve(st.session_state.get("discount_rate", .03)), use_container_width=True, hide_index=True)

st.markdown("### Strategic asset assumptions")
asset_rows = []
for name, a in ASSET_ASSUMPTIONS.items():
    asset_rows.append({"Asset Class": name, "Expected Return": a["exp_ret"], "Volatility": a["vol"], "Yield": a["yield_"],
                        "Duration": a["duration"], "Spread Duration": a["spread_duration"], "Liquidity Score": a["liquidity"]})
st.dataframe(pd.DataFrame(asset_rows), use_container_width=True, hide_index=True)
st.caption("Strategic asset-class parameters are versioned in code (`src/asset_model.py`), not exposed as sliders here, "
           "since editing them redefines the synthetic book rather than adjusting a scenario assumption.")

st.markdown("### Non-life liability-family assumptions (frequency x severity)")
liab_rows = []
for name, f in LIABILITY_FAMILIES.items():
    liab_rows.append({
        "Family": name, "Exposure (policies)": f["exposure_units"], "Frequency": f["frequency"],
        "Severity (EURm/claim)": f["severity"], "Expected Gross Claims (EURm)": expected_gross_claims(f),
        "Tail": f["tail"], "Liquidity Requirement": f["liquidity_requirement"],
        "Inflation Sensitivity": f["inflation_sensitivity"], "Payout Sum": sum(f["payout"]),
    })
st.dataframe(pd.DataFrame(liab_rows), use_container_width=True, hide_index=True)
st.caption("Expected Gross Claims = Exposure x Frequency x Severity, by construction -- see methodology.md section 6.")

st.markdown("### Deterministic scenario calibration")
st.dataframe(pd.DataFrame(DETERMINISTIC_SCENARIOS).T.reset_index(names="Scenario"), use_container_width=True, hide_index=True)
