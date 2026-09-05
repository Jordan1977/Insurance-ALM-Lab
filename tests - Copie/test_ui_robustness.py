import glob
import re


def test_no_five_column_kpi_rows():
    """Static safeguard (V6.3, Part 70): no page may use st.columns(5) or
    wider for a KPI row. metric_row() already caps at 4 and wraps to a new
    row; a bare st.columns(5+) call would bypass that discipline."""
    import glob
    import re

    offenders = []
    for path in glob.glob("pages/*.py"):
        with open(path) as f:
            text = f.read()
        for match in re.finditer(r"st\.columns\((\d+)", text):
            if int(match.group(1)) >= 5:
                offenders.append((path, match.group(0)))
    assert offenders == [], f"st.columns(5+) found (use metric_row() instead): {offenders}"


def test_guideline_metric_names_match_gross_vs_net_basis():
    """Regression test for a red-team finding (V6.3, Part 56 of the brief):
    the FX guideline's underlying metric (`portfolio_guideline_metrics`)
    is computed from `net_fx_exposure`, so the guideline label must say
    'net', not 'gross' -- an earlier version was mislabelled."""
    from src.asset_model import build_asset_portfolio
    from src.guidelines import portfolio_guideline_metrics, check_compliance
    from src.alm_engine import alm_kpis

    A = build_asset_portfolio()
    metrics = portfolio_guideline_metrics(A)
    kpis = alm_kpis(1000, 900, 4.0, 3.5, 0.4, 0.3)
    check = check_compliance(metrics, kpis, 1.5, dict(
        equity_max=.20, hy_max=.10, illiquid_max=.20, cash_min=.05,
        duration_gap_tolerance=1.0, liquidity_target=1.5,
    ))
    fx_row = check[check.guideline.str.contains("FX", case=False)]
    assert len(fx_row) == 1
    assert "net" in fx_row.iloc[0].guideline.lower()
    assert "gross" not in fx_row.iloc[0].guideline.lower()


def test_pages_calling_optimize_allocation_check_the_success_flag():
    """Regression test for a Section 59 violation (V6.2): pages/18_guidelines.py
    and pages/20_committee_pack.py called `optimize_allocation` but never
    checked the returned `success` flag, so a failed solver's fallback
    (starting) weights would have been silently displayed as an optimised
    Liability-Aware proposal."""
    for path in ["pages/18_guidelines.py", "pages/20_committee_pack.py", "pages/8_strategic_allocation.py"]:
        with open(path) as f:
            text = f.read()
        if "optimize_allocation(" in text:
            assert "[\"success\"]" in text or "['success']" in text, f"{path} calls optimize_allocation but never checks metrics['success']"


def test_page_scripts_use_defensive_session_state_access():
    """Regression test for a red-team finding (V6.2): pages/0_overview.py used
    bare `st.session_state.asset_weights` attribute access instead of
    `.get(..., default)`, which crashes with an AttributeError if the page is
    ever rendered before app.py's sidebar has set the defaults (e.g. a direct
    page navigation in a fresh session, or a page reached before app.py runs).
    Every page must use `.get()` for any of the shared global assumption keys,
    per Section 58: the UI must never show a raw Python traceback."""
    tracked_keys = ["asset_weights", "discount_rate", "claim_inflation", "fx_hedge_ratio",
                    "equity_max", "hy_max", "illiquid_max", "cash_min", "cash_max",
                    "duration_gap_tolerance", "liquidity_target", "risk_free_rate"]
    bare_pattern = re.compile(r"st\.session_state\.(" + "|".join(tracked_keys) + r")\b")
    offenders = []
    for path in glob.glob("pages/*.py"):
        with open(path) as f:
            text = f.read()
        for match in bare_pattern.finditer(text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            line = text[line_start:line_end if line_end != -1 else None]
            # allow assignment (`st.session_state.x = ...`), only flag reads
            if re.match(r"^\s*st\.session_state\.\w+\s*=(?!=)", line):
                continue
            offenders.append((path, line.strip()))
    assert offenders == [], f"Bare session_state reads found (use .get() instead): {offenders}"
