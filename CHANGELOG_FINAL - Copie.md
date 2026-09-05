# Changelog: V6.3 -> Final

A final-polish release, per the brief's own instruction not to expand
functional scope. Every item below corresponds to an actual modified file
and a passing test.

## Audit performed before any change

Read the entire V6.3 repository (Part 1). Finding: the shared design-system
adoption that the previous pass (V6.2) had flagged as its largest gap —
applying `page_header` / `metric_row` / `src/formatting.py` helpers to every
page, not just 6 — was **already done**. All 21 analytical pages import and
use `src/ui_helpers.py`, and no page contains a `st.columns(5+)` KPI row.
This pass therefore focused on a genuine financial/terminology red-team
pass (Part 118) and closing the remaining verification gaps, rather than
redoing UX work that was already complete.

## 1. Red-team finding: FX guideline mislabelled gross vs. net (Part 56)

`src/guidelines.py::check_compliance` labelled a limit "Maximum **gross**
FX exposure" while the metric feeding it (`portfolio_guideline_metrics`) is
computed from `net_fx_exposure`. Fixed to "Maximum **net** FX exposure".
Regression test: `tests/test_ui_robustness.py::test_guideline_metric_names_match_gross_vs_net_basis`.

## 2. Permanent static safeguard against `st.columns(5+)` (Part 70)

The current codebase already respects the "no 5-column KPI row" rule, but
nothing prevented a future page from reintroducing one. Added
`tests/test_ui_robustness.py::test_no_five_column_kpi_rows`, which scans
every page file and fails the build if any `st.columns(5)` or wider appears.

## 3. Verified and permanently tested: recovery lag never improves immediate liquidity (Parts 20, 29, 64)

This economic property already held in the reinsurance engine but had no
dedicated test. Independently re-derived (lag=0 gives a €100m year-1
liquidity outflow; lag=1 and lag=3 both give the full €260.8m unmitigated
outflow — non-decreasing as lag increases, exactly as required) and added
`tests/test_reinsurance.py::test_recovery_lag_never_improves_immediate_liquidity`.

## 4. Full financial audit (Parts 6-65) — no further issues found

Independently re-verified, not merely re-run from existing tests:

- Central calculation chain (Part 3): confirmed `src/analytics.py` is the single source every page consumes; no page independently recomputes assets, liabilities, claims, reinsurance or surplus.
- Frequency/severity/claim-inflation independence (Part 16): confirmed the three shock channels are distinct parameters (`frequency_shock`, `severity_shock`, `extra_claim_inflation`) that do not double-apply.
- Pathwise stochastic reinsurance (Part 21): confirmed the Monte Carlo loop applies the XoL formula to each simulated path's gross losses individually, with recovery cash arriving on the treaty's own lag — not an average expected-recovery ratio applied to the whole distribution.
- Reinvestment cash conservation (Part 49): confirmed exact every year, including the "shortfall funded externally" term (functionally the brief's "Asset Sales" line).
- SAA/reinvestment optimizer failure handling (Part 48): confirmed every page calling `optimize_allocation` checks the `success` flag before displaying results as optimised (this was already fixed in the V6.2 pass; re-verified here).
- Terminology (Part 113): no misuse of SCR/MCR/ORSA/IFRS 17/Solvency Ratio/regulatory LCR found anywhere in `src/` or `pages/`.
- Final numerical reconciliation and scenario sweep (Parts 121-122): run and manually reviewed for economic plausibility — see `QUALITY_REPORT_FINAL.md`.

## What was NOT done in this pass

- **No browser or screenshot QA was performed** (Parts 98-101, 117, 124). This session has no browser or screenshot capability. Per Part 130's explicit instruction, this is stated directly: no claim of pixel-perfect, fully responsive, or visually validated status is made. Every page was verified only by full Python script execution via `streamlit.testing.v1.AppTest`, which catches logic/import errors but not rendering issues (text clipping, label wrapping, legend overlap, etc.).
- **No 3-minute demo script** was written as a separate document (Part 116) — the existing 5-minute demo path in `README.md` can be compressed by a presenter by skipping the Model Controls / Limitations step, but no dedicated shorter script was authored.
- **No `screenshots/` directory** was produced (Part 129), for the same reason as the browser QA gap above.

## Test count

149 tests, all passing (up from 146 at the start of this session) — 3 new
regression tests for the findings above. All 23 Streamlit pages verified
with zero runtime exceptions via `streamlit.testing.v1.AppTest`.

## Recommended next step

Per `QUALITY_REPORT_FINAL.md`'s honest scoring, Visual Consistency scored
7/10 (below the brief's own 9/10 completion bar) specifically because it is
not backed by actual browser inspection. The single highest-value next step
is a real browser walkthrough of all 23 pages at 1366×768, 1440×900 and
1920×1080, with screenshots taken and manually inspected per Part 100's
checklist — not further code changes.
