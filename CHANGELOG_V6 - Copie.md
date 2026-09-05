# Changelog: V5 -> V6

This is a substantive, code-level change log, not a marketing summary. Every
item below corresponds to actual modified/added files and a passing test.

## Audit performed before any change (Section 2 of the V6 brief)

Read every `src/` and `pages/` file in the delivered V5. Findings: the
instrument-level face-value calibration, the linear-programme cantonment
engine, and the scenario P&L attribution reconciliation were all genuinely
correct and were kept unchanged. Two real problems were found and form the
basis of the changes below.

## 1. Reinsurance / Gross-to-Net claims (new module, Sections 12-16)

- Added `src/reinsurance.py`: a portfolio-level annual-aggregate
  excess-of-loss structure (`ExcessOfLossTreaty`: retention, limit, recovery
  rate, recovery lag, counterparty haircut).
- Distinguishes **Ultimate Net Claim Cost** from **Interim Liquidity
  Requirement** (Section 13): a treaty can lower the ultimate loss while
  still leaving a temporary cash gap if the recovery lags the claim payment.
- `net_liability_cash_flows()` allocates each year's recovery back to
  families pro-rata to their share of that year's gross claims — no double
  counting, reconciles exactly (`tests/test_reinsurance.py`).
- Default treaty calibrated **above** ordinary base-case claims so it
  barely bites day to day and triggers materially larger recoveries under a
  Large-Loss / Cat-like stress — verified with a dedicated regression test.
- New page: `pages/21_reinsurance.py`.
- **12 new tests**, all passing.

## 2. Net claims propagated through the central balance sheet (Sections 4, 16, 43, 64)

- `src/analytics.py::base_analytics` now reports **NET-of-reinsurance**
  liabilities as the headline `kpis` (Economic Surplus, Coverage, Duration
  Gap, DV01 Gap); GROSS figures remain available under `liabilities_gross`
  and `reinsurance`, never silently mixed with net figures.
- **Bug found and fixed:** `evaluate_deterministic_scenario` (used by the
  Economic Scenarios, Stress Testing and Macro Transmission pages) was still
  computing liabilities on a GROSS basis after `base_analytics` switched to
  NET — meaning the "Base" view and "Active Scenario" view would have shown
  inconsistent liability bases. Fixed so both paths use the identical net
  liability engine; a dedicated integration test in
  `tests/test_analytics.py` pins a direct-call vs assembly-layer comparison
  to catch any future divergence (Section 64: Active Scenario Consistency).
- 12M Liquidity Coverage now uses the **interim** liquidity requirement
  (gross claims paid less recoveries actually received that year), not the
  ultimate net claim cost — the two differ materially whenever
  `recovery_lag > 0`, which is exactly the point Section 13 asks to
  demonstrate.
- ALM Matching (`pages/4_alm_matching.py`) now matches asset cash flows
  against NET claims, with a separate gross/recovery/net table so the two
  bases are never conflated (Section 21).

## 3. Non-life claims engine: explicit Frequency x Severity (Sections 6-11)

- `LIABILITY_FAMILIES` (`src/liability_model.py`) now defines
  `exposure_units`, `frequency` and `severity` per family; `base_claims` is
  **derived** as their product rather than a free-standing number.
  Calibration reproduces the original figures exactly (320/180/260/140/100),
  so the balance-sheet scale is unchanged.
- Added `tail` classification (Short / Short-Medium / Medium-Long / Long)
  and `liquidity_requirement` per family; `total_liability_metrics()` now
  reports `long_tail_share` / `short_tail_share` and `claims_beyond_5y`.
- Added isolated `frequency_shock` and `severity_shock` parameters
  throughout the liability and scenario engines, and a "Claim frequency
  +10%" row in the Tornado module alongside the existing severity shock.
- **Bug found and fixed:** a DataFrame column named `tail` silently shadowed
  pandas' built-in `.tail()` method, causing an `AttributeError` the moment
  it was accessed as `summary.tail`. Renamed to `tail_classification`
  everywhere and accessed via bracket notation as a defensive habit.
- **8 new tests.**

## 4. Performance Attribution: the "major correction" (Section 23)

- Removed `historical_return_1y = expected_return + random noise` entirely
  from `src/asset_model.py` — nothing in that number came from an actual
  observation, and naming it "historical" was misleading.
- Rebuilt `src/performance_attribution.py` around one explicitly-labelled
  `SYNTHETIC_TRAILING_12M_SHOCK`, applied through the same
  `deterministic_asset_attribution` function used by every scenario and
  tornado calculation — no second P&L formula was created.
- `Beginning MV + Carry + Rate/Spread/Equity/FX P&L = Ending MV` now
  reconciles exactly, per row and in total (`tests/test_performance_attribution.py`,
  including a regression test that no field anywhere is named "historical"
  when it is actually synthetic).
- Rewrote `pages/16_performance_attribution.py` to match.

## 5. Reinvestment & Maturity Management V2 (Sections 26-30)

- Replaced the V1 first-order "blend from the sum of positive cash-flow
  years" with an explicit **year-by-year cash account**
  (`src/reinvestment.py::annual_cash_projection`): Opening Cash + Coupon
  Income + Bond Maturities + Reinsurance Recoveries − Gross Claims Paid =
  Cash Available; the actually-invested amount (not a heuristic) then feeds
  the resulting blended duration/yield.
- **Bug found and fixed during development:** the first version of this
  loop let a negative cash balance compound across years, reaching
  -€452m by year 4 — economically nonsensical (an insurer draws on its
  other liquid assets each year rather than running an ever-larger
  overdraft on this one cash-flow stream). Fixed by explicitly tracking
  `shortfall_funded_externally` each year and resetting to a floored
  balance, so `ending_cash >= 0` always holds.
- Added a fifth named policy, **"Reinvest short"** (Section 28), and a
  concrete `REINVESTMENT_UNIVERSE` of six synthetic candidate instruments
  (Section 27), replacing the previous abstract "new instrument duration"
  numbers.
- **11 new/rewritten tests**, including an exact cash-conservation check.

## 6. Investment Committee Pack V2 (Section 49)

- Expanded from 10 to 13 sections, adding **"Non-Life Claims Outlook"** and
  **"Gross vs Net Claims / Reinsurance"** as their own sections rather than
  folding them into the executive summary.
- Fixed a leftover reference to the removed `maturity_ladder` function
  (would have raised an `ImportError` on page load) as part of wiring in
  the V2 reinvestment engine.
- "Items for Committee Review" now use "Key Watchpoint" / "Analytical
  Observation" / "item for review" language throughout (Section 50).

## 7. Reporting and Stress Testing updates

- `pages/11_reporting.py`: added dedicated "Non-Life Claims" and
  "Reinsurance" report sections; balance-sheet section now states net vs
  gross explicitly.
- `pages/6_stress_testing.py`: added a "Large-Loss / Cat-like Shock" stress
  (frequency +30%, severity +80%) with an explicit gross-vs-net-of-reinsurance
  comparison (Section 15), and a "Claims Inflation Shock" entry.

## What was NOT done in this pass

- **Navigation was not consolidated** into the 6-8 grouped sections outlined
  in Section 53 of the brief. The app remains 22 individual pages. This is
  the single largest deferred item — Streamlit's `st.navigation`/`st.Page`
  API (available in the pinned Streamlit version) would support this
  without touching page logic, but it was not implemented in this session.
- A full stochastic frequency (Poisson) process was **not** added to the
  Monte Carlo engine; only the deterministic frequency/severity split and
  the existing lognormal severity multiplier are stochastic-adjacent. See
  limitations.md.
- No simplified quota-share reinsurance structure was added alongside the
  excess-of-loss layer (the brief explicitly said this was optional and to
  avoid overcomplicating).

## Test count

V5 shipped with 88 tests. V6 adds a reinsurance test module, a
frequency/severity test module, a new analytics-integration test module, and
substantially rewrites the performance-attribution and reinvestment test
modules against their rebuilt engines. Net result: **125 tests, all
passing**, plus every page verified with zero runtime exceptions via
`streamlit.testing.v1.AppTest`. See QUALITY_REPORT.md for the full red-team
log and honest scoring.


## V6.1 refinement

- Grouped the Streamlit navigation into seven business-oriented sections instead of a flat 20+ page menu.
- Added explicit Poisson claim-frequency simulation by non-life family and integrated it into stochastic claims.
- Rebuilt stochastic asset evolution row-by-row; claims are paid gross, reinsurance recoveries arrive with lag, and cash is used first.
- Added a dated public ECB/Eurostat macro snapshot while preserving the reproducible synthetic history as explicitly synthetic.
- Added an analytical quota-share comparison alongside the default tail-oriented annual-aggregate XoL illustration.
- Upgraded liability-matching reinvestment from a single closest bond to a constrained optimised basket targeting the duration required on new money.
- Added regression tests for frequency simulation, reinsurance structure comparison, dynamic MC cash-flow columns and the reinvestment basket.
