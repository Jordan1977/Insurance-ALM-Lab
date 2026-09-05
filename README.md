# Insurance ALM Lab

**Non-Life Insurance Asset-Liability Management, Risk & Strategic Allocation Analytics**

Insurance ALM Lab is an independent Python/Streamlit decision-support prototype exploring how a non-life insurer can connect investment strategy, claim cash flows, economic scenarios and financial risk within one coherent analytical framework.

> **Disclaimer** — All portfolios, liabilities, limits and assumptions are synthetic. They do not represent Thélem assurances or any other institution. This project is educational and analytical; it is not a production ALM, reserving, IFRS 17 or Solvency II engine.

---

## What the prototype answers

The central question is:

> **Are the insurer's assets sufficiently profitable, liquid and appropriately calibrated in duration and risk to meet future claims, including under adverse scenarios?**

The analytical decision chain is:

**Macro backdrop → Economic scenario → Asset repricing → Claims / liability repricing → Economic surplus → Risk drivers → Hedging / allocation analytics → Reporting**

The key balance-sheet quantity is therefore **economic surplus**, rather than standalone portfolio return.

---

## Final release at a glance

- **€1.15bn synthetic asset book** linked to projected non-life claim cash flows.
- **Frequency × Severity liability engine** across five synthetic claim families, with settlement timing and tail classification.
- **Gross-to-net reinsurance mechanics** with annual-aggregate XoL, recovery lag, haircut and quota-share comparison.
- **Asset-liability matching** through cash flows, duration, DV01 gap and 12-month liquidity coverage.
- **Deterministic scenarios and stochastic ESG / Monte Carlo**, including rates, equity, spreads, inflation, FX and claims risk.
- **Stress testing and sensitivity analysis**, including Large-Loss and stagflation scenarios.
- **Investment decision support** through liability-aware SAA, reinvestment optimisation, hedging analytics, asset cantonment and investment-guideline monitoring.
- **Governance and reporting** through assumptions management, audit trail, automated reporting and an Investment Committee Pack.
- **149 automated tests passing**; all **23 Streamlit pages** execute end-to-end via `streamlit.testing.v1.AppTest`.

### Base-case analytical snapshot

| Metric | Result |
|---|---:|
| Economic Assets | €1,150.0m |
| Net Liability PV | €1,000.4m |
| Economic Surplus | €149.6m |
| Economic A/L Coverage | 114.9% |
| Duration Gap | +0.36y |
| DV01 Gap | +€0.0921m/bp |
| 12M Liquidity Coverage | 3.44x |

---

## Role-to-project mapping

| Typical non-life ALM responsibility | Prototype demonstration |
|---|---|
| Investment strategy & strategic asset allocation | Liability-aware SAA under duration, liquidity and risk constraints |
| Model financial assets and performance | Strategic asset book, contractual cash flows and factor-based attribution |
| Model insurer liabilities | Five synthetic non-life claim families using Exposure × Frequency × Severity |
| Analyse financial risks | Rates, spreads, equity, FX, concentration, liquidity and surplus-risk analytics |
| Explore hedging strategies | DV01-based rate hedge, equity-futures proxy and FX overlay |
| Contribute to an Economic Scenario Generator | Deterministic scenarios + correlated stochastic closed-book projection |
| Study asset cantonment by product family | Constrained allocation with full asset conservation |
| Monitor macro / financial trends | Macro regime analysis and explicit macro-to-ALM transmission |
| Improve financial reporting and risk monitoring | Executive dashboard, guidelines monitor and automated reporting |
| Monitor publications and synthesise implications | Structured research / regulatory-watch workflow |

---

## Application structure

The analytical pages are grouped into seven business-oriented sections:

1. **Executive**
2. **Non-Life Liabilities & ALM**
3. **Risk & Scenarios**
4. **Investment Strategy**
5. **Reinvestment & Hedging**
6. **Macro & Monitoring**
7. **Governance & Reporting**

The application covers the complete analytical workflow through modules including:

**Executive ALM Dashboard · Asset Book & Risk Analytics · Non-Life Liability Engine · Reinsurance · ALM Cash-Flow Matching · Economic Scenario Generator · Stress Testing · Sensitivity Analysis · Strategic Asset Allocation · Hedging Lab · Reinvestment & Maturity Management · Asset Cantonment · Performance Attribution · Macro Transmission · Investment Guidelines Monitor · Assumptions Hub · Audit Trail · Automated Reporting · Investment Committee Pack**

---

## 5-minute recruiter demo

1. **Executive Dashboard** — synthetic economic position of the insurer, net of reinsurance.
2. **Liabilities** — when and why claims are paid; frequency × severity and tail profile.
3. **Reinsurance** — gross-to-net protection and recovery timing.
4. **ALM Matching** — alignment of contractual asset cash flows with net projected claims.
5. **Sensitivity & Stress Testing** — key threats to economic surplus and Large-Loss behaviour.
6. **Reinvestment & SAA** — how investment decisions respond to liability and liquidity constraints.
7. **Investment Committee Pack** — decision-oriented synthesis of the framework.

---

## Financial & quantitative framework

### Economic balance sheet

`Economic Surplus = Economic Assets − PV(Modelled Net Liabilities)`

`Economic A/L Coverage = Economic Assets / PV(Modelled Net Liabilities)`

Economic A/L Coverage is an analytical balance-sheet metric. **It is not a Solvency II solvency ratio.**

### Contractual assets

Contractual instruments have a face value, coupon, maturity and synthetic yield. Face value is calibrated so discounted contractual cash flows reconcile to market value, avoiding the shortcut of treating market value as principal.

### Non-life liabilities

Claims are modelled through:

`Exposure × Frequency × Severity`

The liability engine combines this framework with settlement patterns, claims inflation and tail classification to project future claim cash flows.

### Reinsurance

The central balance-sheet view is net of a synthetic **portfolio-level annual-aggregate excess-of-loss layer**. Gross figures remain separately available.

The framework distinguishes ultimate claim cost from the timing of reinsurance recoveries, including recovery lag and counterparty haircut.

### Stochastic Economic Scenario Generator

The Monte Carlo framework combines correlated market factors:

- equity returns;
- interest rates;
- inflation;
- credit spreads;
- foreign exchange;

with stochastic non-life claims through:

- Poisson claim frequency by family;
- lognormal claim severity;
- pathwise reinsurance;
- lagged recoveries;
- forced-sale and liquidity effects.

### Liability-aware investment decisions

Strategic allocation and reinvestment analytics incorporate explicit constraints covering:

- portfolio-weight conservation;
- cash limits;
- equity limits;
- High Yield limits;
- illiquid-asset limits;
- duration-gap tolerance;
- minimum liquidity coverage.

The cantonment optimiser also conserves the complete asset book: **no euro can be assigned twice**.

---

## Stress & scenario analytics

The framework evaluates both financial-market and insurance-specific shocks.

Examples include:

| Scenario | Economic Surplus | Coverage |
|---|---:|---:|
| Base case | €149.6m | 114.9% |
| Rates +100bp | €140.8m | 114.5% |
| Rates −100bp | €159.2m | 115.4% |
| Credit spreads +100bp | €132.8m | 113.3% |
| Equity −20% | €99.0m | 109.9% |
| Claims inflation +1pp | €111.8m | 110.8% |
| Frequency +10% | €55.2m | 105.0% |
| Severity +10% | €55.2m | 105.0% |
| Stagflation | €13.4m | 101.3% |

A separate stylised **Large-Loss stress** pushes economic surplus negative and allows the gross-versus-net effect of reinsurance to be analysed.

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
