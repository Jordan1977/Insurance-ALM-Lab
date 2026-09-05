# Changelog: V6.1 -> V6.2

A UI/UX refinement release, per the brief's own instruction not to expand
functional scope. Every item below corresponds to an actual modified file
and a passing test where applicable.

## Audit performed before any change

Read the entire V6.1 codebase, including the stochastic engine additions
(Poisson claim frequency, pathwise reinsurance in the Monte Carlo loop,
quota-share comparison, liability-matching reinvestment basket optimiser)
and the navigation consolidation (`st.navigation` with 7 grouped sections).
**Finding: this model-depth and navigation work was already correctly
implemented** — the V6.2 brief's Sections 22-29 and Section 53 asks were
already satisfied. This pass therefore focused on the remaining UI/UX
sections (3-20, 30-60) and the final red-team/visual-QA sections (61-71).

## 1. Shared formatting and layout infrastructure (Sections 7, 52)

- Added `src/formatting.py`: `fmt_eur_m`, `fmt_pct`, `fmt_signed_pct`,
  `fmt_bp`, `fmt_years`, `fmt_ratio`, `fmt_weight`, `fmt_dv01`,
  `fmt_delta_eur_m` — one place controlling how a number is displayed,
  independent of the full-precision internal computation. 9 tests.
- Added `src/ui_helpers.py`: `page_header` (title + business question +
  always-visible active-scenario badge, Sections 15-16), `metric_row`
  (auto-wraps to a new row after 4 metrics instead of cramming 5-6 into one,
  Section 5), `status_badge` (text-first status labels, Section 57),
  `compact_expander`.

## 2. Executive Dashboard rebuilt (Section 18)

First screen now shows exactly the 6 KPIs specified in the brief (Economic
Assets, Net Liability PV, Economic Surplus, Coverage, Duration Gap, 12M
Liquidity Coverage), watchpoints capped at 3, and the ALM health monitor /
scenario waterfall moved into expanders so they don't compete with the
headline numbers on first load.

## 3. Investment Committee Pack rebuilt (Sections 20-21)

Replaced a 13-section page-by-page copy of every other page with the
requested 7-section synthesis (A. Position, B. Claims & Reinsurance,
C. Top Risks, D. Active Scenario, E. Guidelines, F. Strategy,
G. Committee Watchpoints). The watchpoint engine now follows an
OBSERVATION -> WHY IT MATTERS -> ANALYSIS TO CONSIDER structure and is
ranked by a severity/impact score, replacing a fixed if/elif ordering.

## 4. Red-team pass — 2 real bugs found and fixed (Section 61)

| # | Finding | Severity | Fix |
|---|---|---|---|
| 1 | `pages/0_overview.py` used bare `st.session_state.asset_weights` attribute access instead of `.get()` — raises an `AttributeError` (a raw traceback shown to the user) if the page is reached before `app.py`'s defaults are set. | HIGH | Switched to `.get()` with defaults, matching every other page. |
| 2 | `pages/18_guidelines.py` and `pages/20_committee_pack.py` called `optimize_allocation` without checking the returned `success` flag — a failed solve's fallback weights would have been silently shown as an optimised proposal (Section 59 violation). | HIGH | Added explicit failure messaging in both pages, matching the pattern already correct on `pages/8_strategic_allocation.py`. |

Both fixes have regression tests in `tests/test_ui_robustness.py`, including
a test that scans every page file for the same anti-pattern so it cannot
silently reappear.

## 5. Page-level UX changes (Sections 36, 40-43, 47)

- **Reinsurance page**: 4 stacked sections converted to tabs (Gross→Net /
  Liquidity Timing / Large-Loss Stress / Structure Comparison).
- **Investment Guidelines page**: rows sort RED-first/AMBER/GREEN-last;
  added a Base-vs-Active-Scenario compliance comparison that highlights
  newly-breached constraints — this view did not exist before.
- **Hedging Lab**: split into Interest-Rate / Equity / FX tabs, each using
  `metric_row` instead of a flat 4-5 column row.
- **Sensitivity/Tornado**: chart title states the base surplus figure; the
  full data table moved behind an expander.

## 6. Sidebar restructure (Sections 13-14)

Reordered into Active Scenario + Model Version at top, "Core assumptions",
then "Advanced assumptions" / "Illustrative internal ALM limits" / "Data
quality" as separate expanders. All rate/percentage sliders now display as
"3.00%" using Streamlit's built-in `format="percent"` option — verified via
`AppTest` that the underlying stored decimal (e.g. `discount_rate == 0.03`)
is completely unchanged, so no financial engine is affected.

## What was NOT done in this pass

- **No pixel-level, multi-viewport visual QA.** This session has no browser
  or screenshot tool. Sections 4 and 66 of the brief ask for actual rendered
  screenshots at four viewport sizes; this was not performed and is not
  claimed. Every page was instead verified by full script execution via
  `streamlit.testing.v1.AppTest`, which catches Python-level errors but not
  rendering/layout issues.
- **Only 6 of ~20 analytical pages received the full UX treatment**
  (Executive Dashboard, Committee Pack, Reinsurance, Guidelines, Hedging,
  Sensitivity, plus the sidebar). Assets, Liabilities, ALM Matching,
  Economic Scenarios, Stress Testing, Strategic Allocation, Cantonment,
  Reinvestment, Macro & Markets, Assumptions Hub, Audit Trail, Research
  Watch, Reporting, Performance Attribution and Macro Transmission still use
  their V6 layouts. This is the largest remaining gap — see
  `QUALITY_REPORT.md` for the explicit UX/Visual Consistency scores this
  produced and why a further pass is warranted per the brief's own Section
  71 rule.
- **No "Recruiter / Demo Mode"** was added (Section 63) — the brief allows
  skipping this if it would add fragility; the default landing path
  (Overview -> Executive -> Committee Pack) already covers the same ground.
- **No screenshots** were produced (Section 66).

## Test count

142 tests, all passing (up from 131 at V6.1) — 9 new formatting tests plus 2
new UI-robustness regression tests (the bugs found in Section 4 above), and
1 removed obsolete assertion updated for the new page structure. All 23
Streamlit pages verified with zero runtime exceptions via
`streamlit.testing.v1.AppTest`.
