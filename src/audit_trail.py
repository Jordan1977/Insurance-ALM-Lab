"""Prototype Analytical Audit Trail.

Explicitly NOT a regulatory audit trail -- it is a session-local log of
assumption and decision changes, kept so the app can demonstrate the *idea*
of traceability that a real ALM governance process would need. Log entries
live in `st.session_state["audit_trail"]` (a plain list of dicts) so the
functions here stay pure and testable without Streamlit.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

AUDIT_TRAIL_KEY = "audit_trail"


def new_entry(parameter: str, previous_value, new_value, reason: str,
             source: str = "User (sidebar)", affected_modules: str = "", scenario: str = "Base") -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "parameter": parameter,
        "previous_value": previous_value,
        "new_value": new_value,
        "reason": reason,
        "source": source,
        "affected_modules": affected_modules,
        "scenario": scenario,
    }


def update_assumption(log: list[dict], parameter: str, previous_value, new_value,
                      reason: str, affected_modules: str = "", scenario: str = "Base",
                      validator=None) -> list[dict]:
    """The single place an assumption change should go through:

    1. validate the new value (optional `validator(value) -> bool`);
    2. no-op if the value did not actually change;
    3. append one Audit Trail entry recording old -> new value and why.

    Returns the (mutated) log for convenience; callers still hold their own
    reference (e.g. st.session_state["audit_trail"]).
    """
    if validator is not None and not validator(new_value):
        raise ValueError(f"Rejected new value for {parameter!r}: {new_value!r} failed validation.")
    if previous_value == new_value:
        return log
    log.append(new_entry(parameter, previous_value, new_value, reason, affected_modules=affected_modules, scenario=scenario))
    return log


def audit_trail_dataframe(log: list[dict]) -> pd.DataFrame:
    if not log:
        return pd.DataFrame(columns=["timestamp", "parameter", "previous_value", "new_value", "reason", "source", "affected_modules", "scenario"])
    df = pd.DataFrame(log)
    df["_seq"] = range(len(df))  # tiebreaker so same-timestamp entries stay in insertion order
    return df.sort_values(["timestamp", "_seq"], ascending=False).drop(columns="_seq").reset_index(drop=True)
