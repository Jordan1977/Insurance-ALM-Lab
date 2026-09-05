# Insurance ALM Lab

**Asset-Liability, Risk & Strategic Allocation Analytics for a synthetic non-life insurer**

Insurance ALM Lab is an independent Python/Streamlit prototype exploring how a non-life insurer can connect investment strategy, claim cash flows, economic scenarios and financial risk within one analytical framework.

The application models a **fully synthetic closed-book non-life insurance balance sheet** and provides asset-liability matching, deterministic and stochastic economic scenarios, stress testing, first-order hedging analytics, liability-aware strategic asset allocation, asset cantonment, macro-to-ALM transmission and automated executive reporting.

Its purpose is **not** to replicate a production ALM, reserving, IFRS 17 or Solvency II engine. It demonstrates how Python can support ALM analysis, risk monitoring, investment decision support and reporting.

> **Disclaimer** — All insurer portfolios, liabilities, limits and assumptions are synthetic. They do not represent Thélem assurances or any other institution. The project is educational and analytical and does not constitute investment, actuarial, accounting or regulatory advice.

---

### V6.1 recruiter-facing navigation

The analytical modules remain separate in code, but Streamlit navigation is grouped into seven business sections: **Executive; Non-Life Liabilities & ALM; Risk & Scenarios; Investment Strategy; Reinvestment & Hedging; Macro & Monitoring; Governance & Reporting.** This preserves modularity while avoiding a flat 20+ page recruiter experience.

## Why ALM matters

An insurer does not optimise an asset portfolio in isolation. Investment decisions must remain compatible with the timing, liquidity, inflation sensitivity and rate sensitivity of future claims.

The core decision chain in this project is:

**Macro backdrop → Economic scenario → Asset repricing → Claims / liability repricing → Economic surplus → Risk drivers → Hedging / allocation analytics → Reporting**

The key balance-sheet quantity is therefore **economic surplus**, not standalone portfolio return.

---

## Role-to-project mapping

| Typical non-life ALM responsibility | Prototype demonstration |
|---|---|
| Participate in investment strategy and strategic asset allocation | Liability-aware SAA under duration, liquidity and risk limits |
| Model financial assets and performance | Strategic asset book + coherent instrument-level contractual cash flows |
| Model insurer liabilities | Five synthetic non-life claim families with payout patterns and claims inflation |
| Analyse financial risks | Rates, spread, equity, FX, concentration, liquidity and surplus-risk analytics |
| Explore hedging strategies | DV01-based swap sizing, equity-futures proxy and FX overlay |
| Contribute to an Economic Scenario Generator | Deterministic scenario library + correlated Monte Carlo closed-book projection |
| Study asset cantonment by product family | Constrained optimisation where every euro of synthetic assets is assigned once |
| Monitor macro / financial trends | Offline research dataset, regime classification and explicit macro-to-ALM mapping |
| Improve financial reporting and risk monitoring | Executive dashboard, traffic-light monitor, HTML reporting and data-quality controls |
| Monitor publications and synthesize implications | Structured research / regulatory-watch workflow template |

---

## Main modules

1. **Executive ALM Dashboard** — base vs active scenario, economic assets/liabilities/surplus, duration, liquidity and risk watchpoints.
2. **Asset Book & Risk Analytics** — allocation, instrument book, correlations, risk contribution, concentration, DV01, spread duration and FX exposure.
3. **Non-Life Liability Engine** — Motor, Home, General Liability, Professional and Other claim families, modelled as Exposure x Frequency x Severity, with tail classification and gross-vs-net-of-reinsurance PV.
4. **ALM Cash-Flow Matching** — contractual asset cash flows vs NET-of-reinsurance projected claims by year and maturity bucket.
5. **Economic Scenario Generator** — rate, equity, spread, inflation, FX and claims frequency/severity shocks plus stochastic factor simulation.
6. **Stress Testing** — stylised financial, inflation, credit, liquidity/claims and Large-Loss / Cat-like stresses, with an explicit gross-vs-net-of-reinsurance comparison.
7. **Hedging Lab** — interest-rate, equity and FX mitigation analytics.
8. **Strategic Asset Allocation** — Liability-Aware, Minimum Volatility and Maximum Sharpe comparisons under explicit constraints.
9. **Asset Cantonment** — constrained analytical segregation across non-life claim families.
10. **Macro Transmission** — macro regime → calibrated scenario → balance-sheet result.
11. **Automated Reporting** — deterministic executive narrative (now including dedicated Non-Life Claims and Reinsurance sections) and downloadable HTML report.
12. **Macro & Markets** — dated ECB/Eurostat public snapshot for current context plus a clearly-labelled offline synthetic research history.
13. **Assumptions Hub** — transparent model assumptions and scenario calibration; every change is logged to the Audit Trail.
14. **Research & Regulatory Watch** — structured publication-synthesis workflow.
15. **ALM Sensitivity Analysis (Tornado)** — one-at-a-time ranking of the factors most threatening economic surplus, including isolated claim frequency and claim severity shocks.
16. **Performance Attribution** — factor-based return build-up (Carry + Rate + Spread + Equity + FX P&L) through a single explicitly-labelled synthetic shock; not a Brinson attribution, and no field pretends to be a historical observation.
17. **Reinvestment & Maturity Management** — an explicit year-by-year cash-conservation account and five policies, including a constrained liability-matching bond basket optimiser.
18. **Investment Guidelines Monitor** — synthetic internal limits, COMPLIANT/NON-COMPLIANT status, tested automatically against SAA and reinvestment proposals.
19. **Audit Trail** — prototype analytical log of every assumption change, with CSV export.
20. **Investment Committee Pack** — a 13-section synthesis of the whole application, including a Non-Life Claims Outlook and a Gross vs Net / Reinsurance section, with an HTML export.
21. **Reinsurance** — a portfolio-level annual-aggregate XoL default with editable retention/limit/recovery-rate/lag/haircut, a claims-side quota-share comparison, explicit ultimate-net-cost vs. interim-liquidity timing, and a Large-Loss stress test.

---

## V6 additions and what they demonstrate

V6 audited the entire V5 codebase before changing anything, kept everything that was already correct (the instrument-level face-value calibration, the linear-programme cantonment engine, the scenario attribution reconciliation), and focused on financial correctness and non-life insurance realism rather than adding pages for their own sake:

- **Reinsurance (the main new module)** — a genuine gross-to-net claims mechanic, calibrated so it barely affects the base case and demonstrably absorbs 46% of a Large-Loss stress's incremental claims.
- **Explicit Frequency x Severity claims engine**, replacing flat claim numbers with `Exposure x Frequency x Severity`, plus a Short-Tail/Long-Tail classification.
- **Performance Attribution rebuilt** to remove a genuinely misleading field (`historical_return_1y`, which was actually `expected_return + random noise`) and replace it with a clearly-labelled, formula-consistent factor decomposition.
- **Reinvestment rebuilt** around an explicit, exactly-conserving annual cash account rather than a first-order heuristic.
- Net-of-reinsurance liabilities wired through as the **single** headline balance-sheet figure everywhere — this surfaced and fixed a real cross-module inconsistency (see `QUALITY_REPORT.md`, finding #1) where the scenario engine had silently kept using gross figures after the dashboard switched to net.

Three further real bugs were found and fixed in the red-team pass: a compounding-negative-cash error in an early version of the reinvestment engine, a pandas column-name collision (`tail` shadowing `.tail()`), and a stale import that would have crashed two pages after the reinvestment API changed. All are documented with regression tests — see `CHANGELOG_V6.md` and `QUALITY_REPORT.md`.

**Not done in this pass:** navigation was not consolidated into fewer grouped sections (the app remains 22 individual pages) — this is the single largest gap between this delivery and the brief's own UX ambition, and is flagged as the top priority for any further pass.

## Previous release: V5

V5 added six modules the brief called out as high-value: Sensitivity/Tornado, Performance Attribution, Reinvestment & Maturity Management, Investment Guidelines Monitor, Audit Trail, and the Investment Committee Pack, each reusing the existing scenario/liability/risk engines. See `CHANGELOG_V6.md` for the full V5→V6 diff.

## 5-minute recruiter demo flow

1. **Executive Dashboard** — "the synthetic economic position of the insurer, net of reinsurance."
2. **Liabilities** — "when and why non-life claims are paid — frequency x severity, by tail."
3. **Reinsurance** — "how much of that ultimate cost reinsurance actually absorbs, and when the cash arrives."
4. **ALM Matching** — "how well asset cash flows line up with those NET claims."
5. **Sensitivity (Tornado)** — "which single factor threatens the surplus most."
6. **Stress Testing → Large-Loss shock** — "how reinsurance changes the picture precisely when it matters."
7. **Reinvestment & Maturity Management** — "what to do with the next few years of maturing bonds and recoveries."
8. **Investment Guidelines Monitor** — "limits, breaches and headroom."
9. **Investment Committee Pack** — "how it all comes together for a decision."

---

## Financial-engine highlights


### Internally coherent contractual assets

Contractual instruments have a **face value, coupon, maturity and synthetic yield**. Face value is calibrated so discounted contractual cash flows reconcile to market value. This avoids treating market value as principal.

### Non-life claim liabilities

Each claim family has an undiscounted base amount, payout pattern, claims-inflation sensitivity and volatility proxy. The engine projects claim payments and discounts them through a synthetic EUR spot curve.

### Economic A/L Coverage

`Economic Assets / PV of Modelled Liabilities`

This is an analytical balance-sheet metric only. It is **not** a Solvency II solvency ratio.

### Surplus risk

`Economic Surplus = Assets - PV(Modelled Liabilities)`

The stochastic engine reports the surplus distribution, 1% quantile, Surplus-at-Risk and probability of economic coverage falling below 100%.

### Liability-aware allocation

The SAA optimiser enforces:

- weights sum to 100%;
- cash minimum and maximum;
- equity, High Yield and illiquid limits;
- modified-duration-gap tolerance;
- minimum 12-month liquid-assets / projected-claims coverage.

### Cantonment

A linear programme allocates assets across synthetic liability families. Asset-class balances are fully conserved: **no euro can be assigned twice**. Pool-level duration mismatch and liquidity floors drive the allocation.

---

## Stochastic economic scenario generator

The Monte Carlo framework models five correlated factors:

- equity returns — Geometric Brownian Motion;
- interest rates — mean-reverting Vasicek-style process;
- inflation — mean-reverting AR-style process;
- credit spreads — mean-reverting process;
- foreign exchange — lognormal return process;
- annual claims severity — independent lognormal shock around projected claims.

The closed-book projection pays claims from assets year by year, scales financial sensitivities with the remaining asset base and discounts remaining claims at the scenario rate.

The model intentionally excludes future premium inflows to isolate ALM mechanics.

---

## Data architecture

```text
CSV snapshots / synthetic assumptions
        ↓
validation.py
        ↓
financial engines
        ↓
analytics assembly layer
        ↓
Streamlit decision-support pages
        ↓
executive reporting
```

The frozen CSV snapshots are validated at application startup. The interactive model recomputes from financial engines when assumptions change.

The shipped macro time series are **synthetic demonstration data**, not real historical ECB or market observations. They can be replaced by an approved public-data snapshot without changing the ALM engines.

---

## Quality controls

The repository includes **125 automated tests** covering, among other things:

- strategic weights and asset-book reconciliation;
- instrument-market-value conservation;
- positive contractual face values;
- liability payout integrity and Exposure x Frequency x Severity calibration;
- discounting and claims-inflation direction;
- DV01 and rate-shock signs;
- Monte Carlo reproducibility and factor-correlation validity;
- FX-factor presence;
- hedge effectiveness and realistic DV01 notional order of magnitude;
- liability-aware duration and liquidity constraints;
- cantonment asset conservation and liquidity floors;
- data-quality validation;
- backward-compatibility of the scenario engine after the V5 and V6 shock-dict refactors (every named scenario re-verified unchanged);
- tornado sensitivity coverage, ranking and factor isolation (real estate vs. equity, severity vs. frequency vs. inflation);
- factor-based performance-attribution reconciliation to total return and to Beginning/Ending MV, exactly;
- reinvestment cash-conservation identity and reinvestment-policy duration ordering;
- guideline compliance status and the corrected headroom sign convention;
- audit-trail change logging, no-op-on-unchanged, and validator rejection;
- reinsurance gross-to-net reconciliation, recovery capping, counterparty haircut direction, and the ultimate-cost-vs-interim-liquidity distinction under a recovery lag;
- central-analytics integration tests confirming the scenario engine and the assembly layer agree exactly (the check that caught the V6 gross/net inconsistency — see `QUALITY_REPORT.md`).

Run:

```bash
pytest -q
```

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Repository structure

```text
app.py
pages/
src/
data/
tests/
README.md
methodology.md
assumptions.md
limitations.md
model_governance.md
MISSION_COVERAGE.md
QUALITY_REPORT.md
CHANGELOG_V6.md
requirements.txt
pyproject.toml
```

---

## Model boundary

The project deliberately does **not** implement:

- regulatory Solvency II SCR;
- ORSA;
- IFRS 17 accounting;
- production reserving (no Chain-Ladder, no GLM frequency/severity fitting, no IBNR);
- a catastrophe model (the Large-Loss stress is stylised, not a cat model);
- per-occurrence reinsurance (the central treaty is a portfolio-level annual-aggregate XoL; quota-share is shown only as a simplified claims-side comparison);
- tax or capital management;
- live insurer data;
- dynamic new-business / premium modelling;
- derivative pricing, collateral, accounting or basis risk;
- management actions;
- production calibration.

These limitations are explicit because model transparency is more valuable than false precision.

---

## Recruiter summary

Insurance ALM Lab is a Python decision-support prototype built to demonstrate understanding of a non-life insurer's investment and ALM workflow. It connects a synthetic asset book and projected claim cash flows — modelled explicitly as Exposure x Frequency x Severity, net of a reinsurance layer — to economic scenarios, stress tests, sensitivity analysis, hedging analytics, constrained strategic allocation, reinvestment planning and investment-guideline monitoring, then condenses all of it into a decision-oriented Investment Committee Pack. The application deliberately focuses on **surplus, liquidity and asset-liability compatibility**, rather than standalone portfolio performance. Its calculations are modular, documented and covered by 125 automated tests, including regression tests for issues found in a structured red-team pass (see `QUALITY_REPORT.md`). All insurer-specific data and limits are synthetic and independent of Thélem assurances.

## Further reading

- `methodology.md` — every formula, its variables, units, interpretation and known limitation.
- `assumptions.md` — the full assumptions register.
- `limitations.md` — what this prototype deliberately does not model.
- `model_governance.md` — purpose, scope, inputs/outputs, validation performed.
- `MISSION_COVERAGE.md` — mission-by-mission mapping to module, code and skill demonstrated.
- `QUALITY_REPORT.md` — the full red-team log, reconciliations checked and an honest 11-point score.
- `CHANGELOG_V6.md` — exactly what changed since V5, including three real bugs found and fixed.
- `model_governance.md` — purpose, scope, inputs/outputs, validation performed, change control.
- `MISSION_COVERAGE.md` — mission-by-mission mapping to module, code and skill demonstrated.
- `QUALITY_REPORT.md` — audit findings, red-team fixes, test results and an honest 10-point score.
