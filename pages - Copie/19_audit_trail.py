from __future__ import annotations

import streamlit as st

from src.ui_helpers import page_header

from src.audit_trail import AUDIT_TRAIL_KEY, audit_trail_dataframe

page_header('Prototype Analytical Audit Trail', 'What assumptions changed, why did they change and which analytical modules are affected?', st.session_state.get("active_scenario", "Base"))

st.session_state.setdefault(AUDIT_TRAIL_KEY, [])
log = audit_trail_dataframe(st.session_state[AUDIT_TRAIL_KEY])

if log.empty:
    st.info("No assumption changes logged yet this session. Change a value on the Financial Assumptions Hub page "
            "(or a sidebar slider) and it will appear here automatically.")
else:
    st.dataframe(log, use_container_width=True, hide_index=True)
    st.download_button("Download audit trail (.csv)", log.to_csv(index=False), file_name="alm_lab_audit_trail.csv", mime="text/csv")

st.markdown("### How entries are created")
st.write(
    "Every tracked assumption change goes through a single `update_assumption()` function "
    "(`src/audit_trail.py`): it validates the new value, records the previous value, and appends one entry here "
    "with a reason and the modules it affects. This centralises change-tracking in one place rather than "
    "scattering ad-hoc logging across pages."
)
