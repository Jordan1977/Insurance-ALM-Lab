# Quality Report — FINAL (V6.3)

Advanced educational non-life insurance ALM decision-support prototype for
an M2 apprenticeship application. **Not production-ready** — see
`limitations.md`. This document follows Part 125 of the V6.3 brief:
separate sections per quality dimension, each stating exactly what was
verified and how.

## What this final pass found and fixed

Per Part 1's instruction, the entire repository was audited before any
change was made. Two real issues were found:

| # | Finding | Severity | Fix | Test |
|---|---|---|---|---|
| 1 | The Investment Guidelines FX limit was labelled "Maximum **gross** FX exposure" while its underlying metric (`portfolio_guideline_metrics`) is computed from `net_fx_exposure` — a direct violation of Part 56 ("if the metric is NET FX exposure, do not call the limit Maximum Gross FX Exposure"). | P1 | Relabelled to "Maximum net FX exposure". | `tests/test_ui_robustness.py::test_guideline_metric_names_match_gross_vs_net_basis` |
| 2 | No permanent safeguard existed preventing a future page from reintroducing a `st.columns(5+)` KPI row (Part 70's hard rule), even though the currently-shipped pages already respect it. | P2 | Added a static test scanning every page file for `st.columns(5+)`. | `tests/test_ui_robustness.py::test_no_five_column_kpi_rows` |
| 3 | Verified but not previously tested: recovery lag never improves immediate liquidity (Part 20/29's explicit economic property). | — (verification gap, not a bug) | No code change — the property already held; added a permanent regression test. | `tests/test_reinsurance.py::test_recovery_lag_never_improves_immediate_liquidity` |

Everything else audited in this pass — the central calculation chain in
`src/analytics.py`, the frequency/severity/inflation independence, the
pathwise stochastic reinsurance in the Monte Carlo loop, the reinvestment
cash-conservation identity, the SAA constraint enforcement, the cantonment
conservation, the scenario-attribution reconciliation, and the terminology
around Solvency/LCR/IFRS 17/ORSA — was already correct, verified
independently rather than assumed from passing tests (Part 1's explicit
instruction).

## Financial Quality

- **Central calculation chain (Part 3)**: confirmed one authoritative path — `src/analytics.py::base_analytics` and `scenario_analytics` are the single entry point every page uses; no page independently recomputes assets, liabilities, claims, reinsurance or surplus.
- **Reconciliations verified this session** (not merely re-run from existing tests, independently re-derived): Asset book (Σ instrument MV = asset-class MV = total assets), gross claims (Exposure × Frequency × Severity, exact), reinsurance (Net = Gross − Effective Recovery, exact, every year), scenario P&L (Σ attribution = Δ surplus, exact, for every named scenario), performance attribution (Beginning MV + Σ P&L channels = Ending MV, exact), reinvestment cash (Opening + Inflows − Claims + Shortfall Funding − Investment = Ending, exact, every year), cantonment (no asset allocated twice).
- **Units**: EURm, %, bp, years and "x coverage" used consistently; DV01 is EURm of P&L per basis point throughout (`src/formatting.py::fmt_dv01`).
- **Final numerical reconciliation** (Part 121), base case: Assets €1,150.0m; Gross Liability PV €1,000.4m; Net Liability PV €1,000.4m (treaty deliberately does not bite the base case); Surplus €149.6m; Coverage 114.9%; Duration Gap +0.36y; DV01 Gap +€0.0921m/bp; 12M Gross Claims €260.8m; 12M Liquidity Coverage 3.44x.
- **Final scenario sweep** (Part 122), all economically correct in sign and plausible in magnitude: Rates +100bp → Surplus €140.8m (114.5%); Rates −100bp → €159.2m (115.4%); Credit +100bp → €132.8m (113.3%); Equity −20% → €99.0m (109.9%); Claim Inflation +1pp → €111.8m (110.8%); Frequency +10% and Severity +10% → identical €55.2m (105.0%, arithmetically equivalent by construction, documented in limitations.md); Large Loss → surplus turns negative (coverage 63.6%) under a persistent decade-long frequency+severity shock; Stagflation → €13.4m (101.3%, the most adverse named scenario).

## Non-Life Quality

Exposure × Frequency × Severity is explicit and derivable (`expected_gross_claims` in `src/liability_model.py`), with tail classification (Short/Short-Medium/Medium-Long/Long) driving a genuine Long-Tail vs Short-Tail PV split. Claim frequency is simulated per family via a Poisson process in the Monte Carlo engine, not a single portfolio-wide multiplier. Reinsurance is explicitly documented as a portfolio-level **annual aggregate** excess-of-loss layer (never called per-occurrence), with a separate quota-share comparison explicitly flagged as excluding ceded premium, commission and capital effects. Run-off is explicitly labelled "simplified ALM-oriented claims settlement model", never Chain-Ladder.

## ALM Quality

Net-of-reinsurance liabilities are the single headline balance-sheet figure everywhere (dashboard, scenarios, ALM matching, reporting, committee pack); gross figures remain separately available and are never silently mixed in (verified via `tests/test_analytics.py`). Cash-flow matching, duration/DV01 gap, and the 12M liquidity metric all use the same net basis. Liquidity distinguishes ultimate net cost from interim cash timing (a longer recovery lag never improves near-term liquidity — now permanently tested).

## Quantitative Quality

Correlated market factors (equity GBM, Vasicek-style rates, AR(1) inflation, mean-reverting spreads, FX) with a PSD-checked 5×5 correlation matrix; claim severity is lognormal, claim frequency is Poisson per family. Reinsurance is applied path-by-path inside the Monte Carlo loop (not an average expected-recovery ratio), tracking gross claims paid, recoveries received on the treaty's own lag, forced-sale amounts and a minimum-cash-buffer flag per path. All stochastic results are reproducible from a fixed seed (verified by test).

## Software Quality

149 tests passing; every Streamlit page (23 total) executes end-to-end with zero runtime exceptions via `streamlit.testing.v1.AppTest`. No wildcard imports, bare `except`, `TODO`/`FIXME` markers, or `st.columns(5+)` KPI rows anywhere in `pages/` or `src/` (each now has a permanent static test). Financial engines (`src/`) have no Streamlit import and are independently importable and testable.

## UX Quality

All 21 analytical pages use the shared `src/ui_helpers.py` (`page_header`, `metric_row`) and `src/formatting.py` (`fmt_eur_m`, `fmt_pct`, `fmt_bp`, `fmt_years`, `fmt_ratio`, `fmt_dv01`) helpers — confirmed by grep, not assumed. Navigation is consolidated into 7 business-oriented sections via `st.navigation`. The Executive Dashboard and Investment Committee Pack (the two flagship pages) were rebuilt to synthesise rather than list; Reinsurance, Guidelines, Hedging and Sensitivity use tabs/expanders to avoid presenting everything on one screen at once.

## Visual QA

**No browser or screenshot capability was available in this session.** Per Part 130's explicit instruction, this is stated plainly rather than glossed over: the pixel-level, multi-viewport review (1920×1080 / 1440×900 / 1366×768 / 1280×720), manual screenshot inspection, and click-through browser testing that Parts 98–101, 117 and 124 ask for were **not performed**. What was verified instead: every page's Python script executes to completion with no exception (via `AppTest`), which catches logic errors and missing-import crashes but cannot catch text clipping, label wrapping, legend overlap, or any other rendering-only issue. **No claim of pixel-perfect, fully responsive, or visually validated status is made anywhere in this repository.** A person with access to a browser should still click through all 23 pages at 1366×768 before using this for an actual interview, per Part 101's "laptop-first" guidance.

## Documentation

`README.md`, `methodology.md`, `assumptions.md`, `limitations.md`, `model_governance.md`, `MISSION_COVERAGE.md`, this file, and `CHANGELOG_FINAL.md` all describe the current code as of this pass — cross-checked against the actual `src/` and `pages/` contents rather than carried forward from an earlier version unchanged.

## Known Limitations (see `limitations.md` for the complete list)

Synthetic balance sheet; simplified (non-actuarial) claims engine; reinsurance is a single annual-aggregate excess-of-loss layer with quota-share only as a claims-side comparison; no reserving triangles, no catastrophe model, no full default model, no Solvency II SCR/MCR, no ORSA, no IFRS 17, no production data feeds; frequency and severity shocks are arithmetically equivalent at this aggregate level; **no browser/visual QA was performed in this session** (see above).

## Honest Scoring (Part 126 — nothing inflated; a score below 9 is explained, not hidden)

| Dimension | Score | Why not higher |
|---|---|---|
| Financial Correctness | 8/10 | Every reconciliation independently re-verified this session; one real mislabelling (FX guideline) was still found, showing continued vigilance is needed even on a mature codebase. |
| ALM Depth | 8/10 | Net-of-reinsurance consistency, interim-vs-ultimate liquidity, and cash-flow matching all verified coherent; still single-curve, single-country, closed-book. |
| Non-Life Relevance | 9/10 | Frequency × Severity, tail classification, Poisson frequency, and a genuine pathwise gross-to-net reinsurance mechanic form a coherent story; still no reserving triangles or catastrophe model. |
| Investment Relevance | 8/10 | Constrained SAA, hedging with correct direction/units, and an optimised reinvestment basket; no transaction costs or multi-period optimisation. |
| Quantitative Robustness | 8/10 | PSD-checked correlated factors, genuine pathwise stochastic claims and reinsurance; calibration remains illustrative rather than fitted. |
| Software Engineering | 9/10 | 149 tests, zero runtime exceptions across all pages, engines fully Streamlit-independent; two real issues (FX label, missing static safeguard) were still caught this session. |
| Model Governance | 8/10 | `model_governance.md` and a functioning (session-local) `update_assumption()` Audit Trail; explicitly not a regulatory audit trail. |
| Explainability | 8/10 | Consistent "not a Solvency ratio / not LCR / not Brinson / not a cat model" framing, extended to the corrected FX-guideline naming. |
| UX | 8/10 | Shared design system applied to every analytical page (up from 6 in the prior pass); Executive Dashboard and Committee Pack genuinely synthesise. |
| Visual Consistency | 7/10 | Code-level formatting and layout are now consistent app-wide; this is capped below 9 because it is **not backed by actual browser inspection** — see the Visual QA section above. Per Part 126's own rule, this score being below 9 means a further visual pass (with real browser access) is still warranted before claiming full visual completion. |
| Recruiter Impact | 8/10 | The gross-to-net reinsurance story, corrected performance-attribution honesty, and synthesised Committee Pack read as genuine understanding of the role; capped by the same unverified-rendering caveat above. |

Per Part 126: Visual Consistency is below 9, so **another visual refinement pass with actual browser access remains warranted** before this can honestly be called visually finished — this is stated directly rather than rounded up.
