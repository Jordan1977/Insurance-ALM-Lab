# Model Limitations

The prototype is intentionally transparent about what it does not model.

## Insurance / actuarial limitations

- Synthetic projected claim cash flows, not actuarial reserving.
- A simplified stochastic frequency/severity layer is included (Poisson family frequency + lognormal aggregate severity), but it is not a reserving or catastrophe model.
- No catastrophe model.
- No premium inflows or new business.
- No reinsurance cash flows.
- No tax or expenses.

## Regulatory / accounting limitations

- No Solvency II SCR calculation.
- No ORSA.
- No IFRS 17 measurement or accounting.
- Economic A/L Coverage is not a solvency ratio.
- 12M liquidity coverage is not Basel LCR and not a regulatory insurance liquidity ratio.

## Investment limitations

- Synthetic expected returns, volatilities, correlations, spreads and liquidity scores.
- Simplified asset classes and issuer concentration.
- No transaction costs, taxes or implementation lag.
- No derivative valuation, collateral, basis risk or hedge accounting.
- No alternative-asset cash-flow model beyond simplified income / amortisation assumptions.

## Scenario limitations

- Deterministic scenarios are stylised, not exact historical replications.
- Monte Carlo factors are deliberately parsimonious and not calibrated to production market data.
- No management actions or dynamic strategic rebalancing in stochastic paths.
- Yield-curve dynamics are simplified to a rate factor rather than a full multi-factor term-structure model.

## Macro / regulatory-watch limitations

- The shipped macro dataset is synthetic demonstration data, not observed history.
- The Research & Regulatory Watch page is a workflow template and does not auto-fetch or interpret publications.
- Any production use would require validated data sources, governance, change control and human review.

## Purpose

These limitations are deliberate. The project is designed to demonstrate financial reasoning, ALM understanding, Python architecture, quantitative modelling and decision-support communication — not to create false production precision.

## New-module limitations (V5)

- **Reinvestment policies** model only the first-order effect of redirecting the actually-invested cash (V6: from an explicit annual cash account, not a heuristic sum) into a new blended duration/yield; they do not simulate interest-rate-path-dependent reinvestment timing.
- **Sensitivity / tornado shocks** are one-at-a-time, round illustrative magnitudes; they do not capture joint/correlated moves (that is what the stochastic Monte Carlo engine on the Economic Scenarios page is for), and are not a Value-at-Risk decomposition.
- **Investment Guidelines Monitor** limits are entirely synthetic and user-editable; breach thresholds and AMBER bands are illustrative round numbers, not calibrated risk-appetite statements.
- **Audit Trail** is session-local (lost on browser refresh) and is explicitly not a regulatory or immutable audit log — see `model_governance.md`.
- **Investment Committee Pack** is a UI convenience that reuses existing engine outputs; it introduces no new financial model and inherits every limitation listed above.

## New-module limitations (V6)

- **Performance attribution** applies one fixed, explicitly-labelled synthetic "trailing 12 months" market shock (`SYNTHETIC_TRAILING_12M_SHOCK`) through the same scenario engine used elsewhere — it is not a genuine Brinson allocation/selection attribution (no benchmark or policy-weight series exists in this dataset to support that), and it is not a report of any actual historical period.
- **Reinsurance** is modelled as a single *annual aggregate* excess-of-loss layer, not a per-claim-occurrence layer — a real treaty attaches to individual large losses, not to the sum of a year's claims. The central ALM basis uses one annual-aggregate XoL treaty; a simplified quota-share is available only as a claims-side analytical comparison, not as a second central liability basis. There is no reinstatement provision, no multi-year aggregate deductible, and no reinsurer default/insolvency beyond the flat counterparty haircut.
- **Frequency × severity** is a deterministic decomposition (Exposure × Frequency × Severity), not a stochastic frequency/severity convolution — a pure frequency shock and a pure severity shock therefore have an identical arithmetic effect on aggregate claims at this level, which a full actuarial model would not assume (it would differentiate their contribution to the *tail* of the claims distribution). The Monte Carlo engine combines family-level Poisson frequency simulation with a lognormal aggregate severity multiplier; it still does not constitute a full actuarial frequency/severity convolution, reserving model or catastrophe model.
- **Non-life claim families** use illustrative exposure/frequency/severity combinations chosen to reproduce the original portfolio scale, not real insurer or market claims data.
- **Navigation** was not consolidated into fewer top-level sections in this pass (a planned V6 UX improvement); the app remains organised as 22 individual pages rather than the 6-8 grouped sections outlined in the V6 brief's Section 53.

