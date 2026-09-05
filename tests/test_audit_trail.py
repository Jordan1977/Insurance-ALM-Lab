import pytest

from src.audit_trail import update_assumption, audit_trail_dataframe


def test_update_assumption_appends_entry_on_change():
    log = []
    update_assumption(log, "Discount rate", 0.03, 0.04, reason="Rate rise assumption")
    assert len(log) == 1
    assert log[0]["previous_value"] == 0.03
    assert log[0]["new_value"] == 0.04


def test_update_assumption_no_op_when_unchanged():
    log = []
    update_assumption(log, "Discount rate", 0.03, 0.03, reason="No change")
    assert len(log) == 0


def test_update_assumption_validator_rejects_bad_value():
    log = []
    with pytest.raises(ValueError):
        update_assumption(log, "Discount rate", 0.03, -5.0, reason="Bad input", validator=lambda v: -0.05 <= v <= 0.15)
    assert len(log) == 0


def test_audit_trail_dataframe_sorted_most_recent_first():
    log = []
    update_assumption(log, "A", 1, 2, reason="first")
    update_assumption(log, "B", 1, 2, reason="second")
    df = audit_trail_dataframe(log)
    assert list(df.parameter) == ["B", "A"]


def test_audit_trail_dataframe_empty_has_expected_columns():
    df = audit_trail_dataframe([])
    assert list(df.columns) == ["timestamp", "parameter", "previous_value", "new_value", "reason", "source", "affected_modules", "scenario"]
