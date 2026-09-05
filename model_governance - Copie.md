# Model Governance

This note documents the prototype the way a model-risk / model-governance
function would expect a real model to be documented — at prototype depth,
not production depth. It complements `methodology.md`, `assumptions.md` and
`limitations.md` rather than repeating them.

## Model purpose

Decision-support and educational prototype demonstrating how an ALM analyst
in a non-life insurer can connect asset allocation, liability cash flows,
economic scenarios, financial risk, hedging, and investment governance in one
coherent, testable framework. It is built for a job application, not for
production use.

## Scope

In scope: economic balance-sheet construction, instrument-level asset cash
flows, non-life liability cash-flow projection, deterministic and stochastic
economic scenarios, sensitivity/tornado analysis, cash-flow and duration
matching, liquidity analytics, hedging sizing, liability-aware strategic
allocation, cantonment, reinvestment policy comparison, investment guideline
monitoring, an analytical audit trail, and automated reporting.

Out of scope (see `limitations.md` for the full list): Solvency II SCR/MCR,
ORSA, IFRS 17, actuarial best-estimate reserving, regulatory capital, tax,
derivative pricing/collateral/hedge accounting, production data feeds,
management-action modelling.

## Version

V5 (this document accompanies the V5 delivery). Prior versions: V3, V4.

## Inputs

- Synthetic strategic asset-class assumptions (`src/asset_model.py`).
- Synthetic non-life liability-family assumptions (`src/liability_model.py`).
- A synthetic, offline macro/market dataset (`data/macro_data.csv`) —
  explicitly not real observed history (see the Macro & Markets page banner).
- User-adjustable global assumptions (discount rate, claims inflation,
  hedge ratios, illustrative internal limits) via the sidebar / Assumptions
  Hub, tracked in the Audit Trail.

## Outputs

Economic balance sheet, ALM KPIs (coverage, duration gap, DV01 gap),
cash-flow matching tables, liquidity coverage, deterministic and stochastic
scenario results with surplus attribution, tornado sensitivity ranking,
hedge sizing, strategic allocation comparisons, cantonment pool summaries,
reinvestment policy comparisons, guideline compliance status, and an
automated HTML/CSV report / Investment Committee Pack.

## Assumptions

See `assumptions.md`. All balance-sheet, liability, macro and limit data
are synthetic; none represent Thélem assurances or any other institution.

## Limitations

See `limitations.md`.

## Validation performed

- 88 automated pytest tests covering formula correctness, sign coherence,
  reconciliation identities (scenario attribution, performance attribution,
  cantonment conservation), constraint satisfaction (SAA, guidelines), and
  regression tests for two bugs found in this pass (see `QUALITY_REPORT.md`).
- Every Streamlit page executed end-to-end via `streamlit.testing.v1.AppTest`
  with no runtime exceptions.
- A structured red-team pass (Section 58-style) checking for unit confusion
  (bp vs %), Market Value vs Face Value confusion, double counting, broken
  reconciliations, non-conservative cantonment, inconsistent active-scenario
  state across pages, and incorrect regulatory terminology. Findings and
  fixes are logged in `QUALITY_REPORT.md`.

## Model risk & change control

- All formulas live in `src/`, called once from each Streamlit page — the
  prototype's version of "a formula must exist in exactly one place."
- Assumption changes made through the Assumptions Hub page are logged via
  `src/audit_trail.update_assumption()`, which validates the new value,
  records the previous value, and stamps the affected modules and active
  scenario. This is a **prototype analytical audit trail**, not a
  regulatory or immutable one: it is session-local (lost on refresh) and
  has no user-authentication or dual-control concept.
- Any change to a core financial formula should be accompanied by an
  updated or new test in `tests/`, per the existing pattern (each fixed bug
  in this project has a named regression test referencing it).

## Last updated

This document was last updated alongside the V5 delivery described in
`QUALITY_REPORT.md`.
