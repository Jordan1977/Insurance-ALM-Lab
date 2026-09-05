# Quality Gate Report — V6

Advanced educational non-life insurance ALM decision-support prototype.
**Not production-ready** — see limitations.md. This report records what was
actually run, not what was intended.

## Test count

| | Count |
|---|---|
| Tests collected | 131 |
| Passed | 131 |
| Failed | 0 |
| Current V6.1 Python compile check | PASS |
| Current V6.1 Streamlit runtime smoke test | NOT RUN in this environment (Streamlit package unavailable) |

## Financial reconciliations (all verified, not assumed)

- **Asset book reconciliation:** instrument-level market values sum exactly to the strategic asset-class book (`tests/test_assets.py`).
- **Gross claims reconciliation:** Expected Gross Claims = Exposure × Frequency × Severity, exactly, for every family (`tests/test_frequency_severity.py`).
- **Reinsurance reconciliation:** Net Claims = Gross Claims − Effective Recovery, exactly, every year; family-level net cash flows sum to the year-level net figure (`tests/test_reinsurance.py`).
- **Net liability reconciliation:** the net-of-reinsurance liability PV/duration/DV01 uses the identical `pv_duration_metrics` formula as the gross engine — no second PV formula exists (`src/liability_model.py`, `src/reinsurance.py`).
- **Scenario P&L reconciliation:** Σ(attribution channels) = Δ Surplus, exactly, for every named scenario, including under the net-of-reinsurance basis (`tests/test_scenario_refactor.py`, `tests/test_analytics.py`).
- **Performance attribution reconciliation:** Beginning MV + Σ(P&L channels) = Ending MV, exactly, per asset class and in total (`tests/test_performance_attribution.py`).
- **Reinvestment cash conservation:** Opening Cash + Inflows − Claims + Shortfall Funding − Investments = Ending Cash, exactly, every year, for every policy (`tests/test_reinvestment.py`).
- **Cantonment conservation:** every euro of assets is allocated at most once (`tests/test_optimization_cantonment.py`).
- **Active scenario consistency:** a scenario evaluated via `src.analytics` and the same scenario evaluated by calling `evaluate_deterministic_scenario` directly produce identical surplus and coverage (`tests/test_analytics.py`).

## Integration tests (Section 63 of the V6 brief)

`tests/test_analytics.py` exercises the full assembly layer used by every
page (`base_analytics`, `scenario_analytics`), not just the underlying
formulas in isolation — this is what caught the gross/net inconsistency
described below.

## Red-team pass — findings and fixes

Every item below was found by independently re-deriving a number and
comparing it to the code's output, not by trusting an existing test.

| # | Finding | Severity | Fix | Regression test |
|---|---|---|---|---|
| 1 | `evaluate_deterministic_scenario` (used by Economic Scenarios / Stress Testing / Macro Transmission) still computed liabilities on a GROSS basis after `src.analytics.base_analytics` switched to NET-of-reinsurance as the headline figure — meaning "Base" and "Active Scenario" views would have silently used different liability bases. | **HIGH** | Both paths now call the identical net liability engine (`total_net_liability_metrics`). | `tests/test_analytics.py::test_scenario_analytics_named_scenario_matches_direct_engine_call` |
| 2 | The first version of the V2 reinvestment cash account let a negative cash balance compound across years (reaching −€452m by year 4) instead of being funded from the insurer's other liquid assets each year — economically nonsensical. | **HIGH** | Added an explicit `shortfall_funded_externally` line so `ending_cash >= 0` always holds; the shortfall is reported, not hidden or compounded. | `tests/test_reinvestment.py::test_ending_cash_never_negative` |
| 3 | A DataFrame column named `tail` silently shadowed pandas' built-in `.tail()` method, raising an `AttributeError` the moment it was accessed as an attribute. | **MEDIUM** | Renamed to `tail_classification` everywhere; accessed via bracket notation as a defensive habit going forward. | `tests/test_frequency_severity.py::test_every_family_has_tail_and_liquidity_classification` |
| 4 | The default reinsurance treaty (initial calibration: retention €150m, limit €300m) recovered enough of ordinary base-case claims to lift Economic A/L Coverage from ~115% to ~136% — undermining the balance sheet's original calibration for stress-testing headroom, and behaving unlike a real excess-of-loss layer (which should barely touch ordinary claims). | **MEDIUM** | Recalibrated the default treaty (retention €280m, limit €400m) to sit above ordinary base-case claims, restoring ~115% base coverage while still triggering materially larger recoveries under a Large-Loss stress. | `tests/test_reinsurance.py::test_default_treaty_barely_touches_base_case_but_bites_under_large_loss_stress` |
| 5 | `pages/20_committee_pack.py` and `pages/4_alm_matching.py` referenced the removed V1 `maturity_ladder` function after the reinvestment engine was rebuilt — would have raised an `ImportError` on page load. | **HIGH** (would have broken the app) | Rewired both pages to the V2 `annual_cash_projection` / `net_liability_cash_flows` API. | Caught by `streamlit.testing.v1.AppTest` full-page execution, not just static import checks. |
| 6 | Two functions with the same conceptual role (`scenario_analytics` wrapper vs. `evaluate_deterministic_scenario` itself) had different default `fx_hedge_ratio` values (.5 vs 0.0) — a latent inconsistency that would only surface if a caller relied on the default rather than passing an explicit value. | **LOW** | Aligned both defaults to .5; added a test that pins explicit values so future default drift is caught immediately rather than silently. | `tests/test_analytics.py::test_scenario_analytics_named_scenario_matches_direct_engine_call` |
| 7 | Checked for and found none: bp/% unit confusion, Market-Value/Face-Value confusion (already fixed in a prior pass), double counting of claims or reinsurance recoveries, incorrect hedge direction, non-PSD correlation matrices, unused imports, wildcard imports, bare `except`, `TODO`/`FIXME`/placeholder markers, hardcoded displayed figures. | — | — | Existing tests + a targeted `grep` sweep across the full codebase |

## Economic sanity checks (Section 62 of the V6 brief) — all verified in this session

- Rates ↑ → fixed-rate bond value ↓; Rates ↓ → value ↑ (verified both directions).
- Credit spreads ↑ → credit-asset value ↓.
- Claim inflation ↑, claim frequency ↑, and claim severity ↑ each independently → gross and net claims ↑, surplus ↓ (frequency and severity produce an identical aggregate impact by construction — documented, not hidden, in limitations.md).
- Effective reinsurance recovery ↑ → net claims ↓; the default treaty demonstrably barely bites the base case (0% of base-case claims) and absorbs 46% of a large-loss shock's incremental claims.
- Equities ↓ → assets ↓, isolated from real-estate/credit/rate channels.
- A completed rate hedge reduces the targeted DV01 gap (verified via `rate_hedge`).
- Liability-matching reinvestment produces a smaller |duration gap| than either "Hold cash" or "Extend duration" alone.
- Cantonment and reinvestment cash both conserve exactly (see reconciliations above).
- Stagflation remains the most adverse tested named scenario (coverage 114.9% → 101.3%); the Large-Loss stress is more severe still on the claims side specifically (net claims +26% at the 12-month horizon).

## Known limitations / out-of-scope items

See `limitations.md` for the full list. Headline V6-specific items: the central reinsurance basis is a single annual-aggregate excess-of-loss layer (not per-occurrence, no reinstatement), with quota-share included only as a claims-side comparison; frequency and severity shocks are arithmetically equivalent at this aggregate level (no distributional convolution); claim frequency is now simulated by family with a Poisson process; navigation is now consolidated into seven recruiter-facing groups via `st.navigation`. Reinsurance remains deliberately simplified and the stochastic model is still an educational closed-book engine rather than an actuarial/catastrophe production model.

## Honest scoring (out of 10 — never defaulted to 10, and a score below 9 is explained)

| Dimension | Score | Why not higher |
|---|---|---|
| Financial Correctness | 8/10 | Core formulas, reconciliations and the gross/net reinsurance mechanic all verified independently; the fact that 3 HIGH-severity bugs (gross/net scenario inconsistency, compounding negative cash, a stale import) were found in this session shows real defects can still slip past a large, growing codebase even with 88 pre-existing tests. |
| ALM Depth | 8/10 | Now covers matching, liquidity (interim vs. ultimate), reinvestment, cantonment and guidelines on a consistent net-of-reinsurance basis; still single-curve, single-country, closed-book. |
| Non-Life Insurance Relevance | 9/10 | Frequency × Severity, tail classification, Poisson frequency risk, gross-to-net XoL and quota-share comparison now form a coherent non-life story; still no real reserving triangles or catastrophe model. |
| Investment Relevance | 8/10 | Constrained SAA, hedging and a concrete reinvestment universe now include an optimised liability-matching new-money basket; still no transaction costs or full multi-period optimisation. |
| Actuarial Relevance | 6/10 | Frequency × Severity × Exposure and a simplified run-off/payout pattern are genuine actuarial concepts applied correctly at ALM level; this is explicitly not a reserving engine and does not attempt Chain-Ladder, GLM frequency/severity fitting, or IBNR estimation. |
| Quantitative Robustness | 8/10 | PSD-checked correlated market factors, explicit Poisson claim frequency, lognormal severity, dynamic row-level asset evolution and lagged reinsurance cash flows materially deepen the stochastic engine; calibration remains illustrative. |
| Software Engineering | 9/10 | Modular, typed, 131 passing tests and CI workflow; navigation is now grouped into seven business sections while underlying modules remain separate for maintainability. |
| Model Governance | 8/10 | `model_governance.md`, `CHANGELOG_V6.md` and a session-local but genuinely functioning Audit Trail via a single `update_assumption()` entry point. |
| Explainability | 8/10 | Consistent "not a Solvency ratio / not LCR / not Brinson / not a regulatory audit trail / not a cat model" framing maintained and extended to the new reinsurance and performance-attribution language. |
| UX | 8/10 | The same analytical depth is now organised under seven business-oriented navigation groups; a final pixel-level runtime review remains advisable before recruiter distribution. |
| Recruiter Impact | 9/10 | The non-life claims/reinsurance chain, optimised reinvestment, grouped navigation and public-macro traceability now make the project read much more like a response to an ALM job description than a generic dashboard. |

## What remains intentionally limited

The next gains should come from **visual/runtime polish and interview preparation**, not from adding more modules. If another technical pass is made, priority should be limited to: (1) pixel-level Streamlit review on the deployed runtime; (2) optional calibration of the synthetic market/claims assumptions; and (3) deeper multi-period reinvestment only if it can be explained clearly in interview. Full reserving, catastrophe modelling, Solvency II SCR, IFRS 17 and production data infrastructure remain deliberately out of scope.


## V6.1 incremental validation

The V6.1 pass adds tests for stochastic claim frequency, quota-share reconciliation, dynamic Monte Carlo reinsurance cash timing and optimised reinvestment. **Final local result: 131/131 tests passed**, plus `python -m compileall` passed for `src/`, `pages/`, `app.py` and `tests/`. Streamlit itself is not installed in this execution environment, so the grouped-navigation UI was syntax-checked and aligned with the documented `st.Page` / `st.navigation` API but not pixel-level runtime-tested here.

---

# V6.2 — Model Quality and Visual/UX Quality (Section 70)

V6.2 is a refinement release: the brief explicitly asked not to expand functional scope. Streamlit **was** installed and available in this session, so — unlike the V6.1 note above — every page was actually executed end-to-end via `streamlit.testing.v1.AppTest`, not merely syntax-checked.

## Model Quality

### Audit finding: the model-depth work was already done

Before changing any code, the entire V6.1 codebase was read. The Poisson per-family claim-frequency model, the pathwise (not expected-ratio) application of the excess-of-loss treaty inside the Monte Carlo loop, the quota-share comparison, and the liability-matching reinvestment basket optimiser were all already correctly implemented — no double counting was found between base claims, claim inflation, the frequency multiplier and the severity multiplier (they multiply through the cash-flow build-up in the intended order, in `src/scenario_generator.py::surplus_distribution_from_mc`).

### Red-team findings and fixes (Section 61)

| # | Finding | Severity | Fix | Regression test |
|---|---|---|---|---|
| 1 | `pages/0_overview.py` used bare `st.session_state.asset_weights` attribute access (and three siblings) instead of `.get(key, default)`. This raises an `AttributeError` — a raw Python traceback shown to the user — if the page is ever reached before `app.py`'s sidebar has set its defaults. | **HIGH** (violates Section 58: never show a traceback) | Switched to `.get()` with the correct default, matching every other page's pattern. | `tests/test_ui_robustness.py::test_page_scripts_use_defensive_session_state_access` — scans every page file for the same anti-pattern. |
| 2 | `pages/18_guidelines.py` and `pages/20_committee_pack.py` both called `optimize_allocation` but never checked the returned `success` flag. A failed solve silently falls back to the starting weights, which would have been displayed as if they were an optimised Liability-Aware proposal — a direct Section 59 violation ("do not silently return fallback results as optimal"). | **HIGH** | Added an explicit `if not saa_metrics["success"]:` warning/error message in both pages, matching the pattern already correctly used on `pages/8_strategic_allocation.py`. | `tests/test_ui_robustness.py::test_pages_calling_optimize_allocation_check_the_success_flag` |
| 3 | Checked for and found none in this pass: gross/net confusion, claim or reinsurance double counting, recovery-timing errors, rate/spread double counting, MV/face confusion, wrong hedge direction, cash-conservation failure, optimizer artefacts silently accepted elsewhere, scenario mismatch, stale macro data, or fabricated "real" data labels. | — | — | Existing 131 tests + a targeted manual trace through the dynamic Monte Carlo cash-flow build-up |

### Error-state testing (Section 58)

Manually exercised: extreme claim inflation (+30%, coverage falls to 45.6% — no crash, no NaN/inf), negative claim inflation (-2%, coverage rises to 135.1% — no crash), zero FX hedge ratio, full (100%) FX hedge ratio (net exposure correctly goes to zero). All returned finite, sign-correct results with no unhandled exception.

## Visual / UX Quality

**Tested viewport sizes: none.** This session has no browser or screenshot tool available, so the pixel-level, multi-resolution visual QA that Sections 4 and 66 of the brief ask for (1920×1080 / 1440×900 / 1366×768 / 1280×720, actual rendered screenshots) was **not performed** and is not claimed. What follows is code-level layout discipline, verified by running every page's script to completion (catching Python-level errors, not rendering issues).

### What was changed

- **Shared infrastructure** (`src/formatting.py`, `src/ui_helpers.py`): central `fmt_eur_m` / `fmt_pct` / `fmt_bp` / `fmt_years` / `fmt_ratio` / `fmt_dv01` functions (Section 7) and a `page_header` / `metric_row` layout system (Sections 16, 52) so pages stop each inventing their own precision and spacing. `metric_row` automatically wraps to a new row after 4 metrics (Section 5) instead of the 5-6 column rows some pages previously used.
- **Executive Dashboard rebuilt** (Section 18): first screen now shows exactly the 6 KPIs the brief specifies, watchpoints limited to 3, methodology moved to a closing expander, ALM health monitor and scenario waterfall moved into `st.expander`s so they don't compete with the headline numbers.
- **Investment Committee Pack rebuilt** (Section 20): replaced a 13-section page-by-page copy with the requested 7-section synthesis (A. Position → G. Watchpoints). The watchpoint engine now follows the OBSERVATION → WHY IT MATTERS → ANALYSIS TO CONSIDER structure from Section 21, ranked by a severity/impact score rather than a fixed if/elif order.
- **Reinsurance page**: 4 stacked sections converted to tabs (Gross→Net / Liquidity Timing / Large-Loss Stress / Structure Comparison) per Section 43.
- **Investment Guidelines page**: rows now sort RED-first/AMBER-second/GREEN-last (Section 40); added an explicit Base-vs-Active-Scenario compliance comparison highlighting newly-breached constraints (Section 41), which did not exist before.
- **Hedging Lab**: split into Interest-Rate / Equity / FX tabs (Section 47), each using `metric_row` instead of a flat 4-5 column row.
- **Sensitivity/Tornado**: chart title now states the base surplus figure (Section 36); full table moved behind an expander so the tornado chart and top-3 drivers are what a reader sees first.
- **Sidebar**: restructured into the requested hierarchy — Active Scenario + Model Version at top, a small "Core assumptions" section, then "Advanced assumptions", "Illustrative internal ALM limits" and "Data quality" as separate expanders (Section 13). All rate/percentage sliders now display as "3.00%" rather than a bare decimal, using Streamlit's built-in `format="percent"` slider option — verified via `AppTest` that the underlying stored decimal value is completely unchanged (e.g. `discount_rate` still reads `0.03` in session state), so no downstream financial engine is affected by this purely-cosmetic change (Section 14).

### What was NOT changed in this pass

Of the app's ~20 analytical pages, **6** (Executive Dashboard, Committee Pack, Reinsurance, Guidelines, Hedging, Sensitivity, plus the shared sidebar) received the full Section 3-55 treatment described above. The remaining pages (Assets, Liabilities, ALM Matching, Economic Scenarios, Stress Testing, Strategic Allocation, Cantonment, Reinvestment, Macro & Markets, Assumptions Hub, Audit Trail, Research Watch, Reporting, Performance Attribution, Macro Transmission) still use their V6 layouts and have not yet been passed through the shared `metric_row`/`fmt_*` helpers or restructured into tabs. This is the largest remaining gap for a future pass — the highest-traffic pages were prioritised given the time available, not all pages.

No screenshots were produced (Section 66 not attempted, for the reason stated above).

## Final score (Section 71 — updated for V6.2, nothing defaulted to 10)

| Dimension | Score | Why not higher |
|---|---|---|
| Financial Correctness | 8/10 | Unchanged from V6 — verified again in this pass, no new issues found. |
| ALM Depth | 8/10 | Unchanged from V6. |
| Non-Life Insurance Relevance | 9/10 | Unchanged from V6.1. |
| Investment Relevance | 8/10 | Unchanged from V6.1. |
| Quant Robustness | 8/10 | Unchanged from V6.1. |
| Software Engineering | 9/10 | Two real bugs (Section 61 table above) were caught by this pass's tests, showing the test suite is doing real work rather than just tracking existing behaviour. |
| Model Governance | 8/10 | Unchanged from V6. |
| UX | 7/10 | Genuinely improved on the 6 pages redesigned (fewer columns, consistent formatting, RED-first sorting, tabs instead of stacked sections) but **not yet applied app-wide** — per Section 71's own rule, a score below 9 here means another refinement pass is warranted, and the highest-priority target for it is named above. |
| Visual Consistency | 6/10 | The `src/formatting.py` / `src/ui_helpers.py` helpers now exist and are used consistently on the redesigned pages, but most pages still format numbers ad hoc. No actual browser rendering was inspected — this score reflects code-level consistency only, not verified pixel output. |
| Explainability | 8/10 | Unchanged from V6, extended with the OBSERVATION/WHY/ANALYSIS watchpoint structure. |
| Recruiter Impact | 8/10 | The flagship Executive Dashboard and Committee Pack are now materially cleaner and better synthesised; overall impact is capped by the remaining pages not yet receiving the same treatment. |

**Per Section 71's own instruction ("If UX or Visual Consistency < 9: perform another refinement pass"): both are below 9, so a further pass is warranted before this is considered visually finished.** The concrete next steps are listed in "What was NOT changed" above.



## V6.3 visual / UX refinement

- Shared responsive layout guardrails: **implemented**.
- Common page-header system across analytical pages: **implemented**.
- Five-column KPI/control rows: **removed from analytical pages**.
- Sidebar version reference: **corrected to V6.3**.
- Reinvestment / scenario information hierarchy: **further refined**.
- Browser screenshot QA at 1920×1080 / 1440×900 / 1366×768 / 1280×720: **NOT EXECUTED in this build environment because Streamlit is not installed**.

Therefore V6.3 is code-level responsive-hardened, but it is **not claimed pixel-perfect**. A final browser screenshot pass remains a deployment QA step, not a model-development task.
