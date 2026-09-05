# Assumptions Register

All assumptions are synthetic. None represents Thélem assurances.

## Economic balance sheet

- Total synthetic assets: **€1.15bn**.
- Base claim amount before projected claims inflation: approximately **€1.0bn** across five non-life families.
- Model type: **closed book** — no future premium inflows.

## Strategic asset mix

The baseline is intentionally diversified across cash, sovereign bonds, investment-grade credit, High Yield, equities, real estate, infrastructure and private debt.

Cash expected return is calibrated close to the configurable risk-free rate to avoid a mechanically unrealistic optimiser preference for cash.

## Liability families

- Auto
- Habitation
- Responsabilité Civile
- Professionnels
- Autres

Longer-tail liability families have slower payout patterns and generally higher claims-inflation sensitivities.

## Discount curve

A transparent 1–10 year synthetic EUR spot curve is used and shifted in parallel by the global discount-rate assumption.

## Internal illustrative limits

Defaults:

- equity maximum: 20%;
- High Yield maximum: 10%;
- illiquid maximum: 20%;
- cash minimum: 5%;
- cash maximum: 20%;
- duration-gap tolerance: ±1.0 year;
- 12M liquid-assets / projected-claims target: 1.5x.

These are demonstration limits, not Thélem or regulatory limits.

## FX exposure

USD assets are treated as fully non-EUR. Mixed-currency global equity is approximated at 50% non-EUR. A configurable hedge ratio is applied in deterministic and stochastic scenarios.

## Deterministic scenarios

Scenario parameters are stylised and designed to demonstrate transmission mechanics rather than reproduce historical episodes exactly.

## Monte Carlo

Default annual assumptions include:

- equity expected return and volatility from the synthetic strategic asset assumptions;
- rate mean reversion around 3%;
- inflation mean reversion around 2%;
- non-negative credit-spread process;
- FX volatility proxy around 10%;
- annual claims-severity volatility proxy around 12% around projected claims.

Correlations are synthetic and include a negative equity-return / spread-change relationship.

## Liquidity stress

Illustrative default:

- projected 12M claims +20%;
- 5% haircut on highly liquid / liquid assets;
- only 25% of semi-liquid assets assumed monetisable, with an additional haircut.

## Hedge instruments

Synthetic fixed-rate swap durations are used only to translate A-L DV01 gaps into order-of-magnitude notionals. No derivative pricing or market quotes are used.

## Sensitivity / tornado shock sizes

The eleven single-factor shocks (±100bp rates, +1pp claims inflation, -10%/-20% equity, +50bp/+100bp credit spreads, ±10% FX, -10% real estate, +10% claims severity) are round, illustrative magnitudes chosen to be easy to sanity-check, not calibrated to any historical distribution or VaR confidence level.

## Reinvestment policy parameters (V6)

Five named policies each select one candidate from a synthetic investable universe of six instruments (EUR Sovereign 2Y/5Y/10Y, EUR IG 3Y/5Y/7Y — `REINVESTMENT_UNIVERSE` in `src/reinvestment.py`), each with an illustrative yield, duration, spread, rating and liquidity score. "Hold cash" uses an illustrative 0.2y-duration, 2.0%-yield placeholder. These are order-of-magnitude synthetic instruments for illustrating the trade-off, not fitted to any observed curve.

## Investment guidelines (illustrative internal limits)

Default limits (all editable in the sidebar / Assumptions Hub): maximum equity 20%, maximum High Yield 10%, maximum illiquid 20%, minimum cash 5%, duration-gap tolerance ±1.0y, minimum 12M liquidity coverage 1.5x, minimum Economic A/L Coverage 100%, maximum gross FX 15%, maximum single asset-class weight 45%. None of these represent Thélem assurances' actual investment guidelines.

## Non-life claims: frequency x severity (V6)

Each family's expected gross claims are Exposure Units × Frequency × Severity (`LIABILITY_FAMILIES` in `src/liability_model.py`), calibrated to reproduce the original V5 base-claims figures exactly:

| Family | Exposure (policies) | Frequency | Severity (EURm/claim) | Tail |
|---|---|---|---|---|
| Auto | 100,000 | 8.0% | 0.0400 (~€40k) | Short/Medium |
| Habitation | 80,000 | 6.0% | 0.0375 (~€37.5k) | Short |
| Responsabilité Civile | 50,000 | 3.0% | 0.1733 (~€173k) | Long |
| Professionnels | 20,000 | 4.0% | 0.1750 (~€175k) | Medium/Long |
| Autres | 30,000 | 5.0% | 0.0667 (~€67k) | Short/Medium |

These exposure/frequency/severity splits are illustrative and chosen only to reproduce a plausible aggregate claims figure per family — they are not derived from any real book of business.

## Reinsurance treaty (V6)

Default excess-of-loss structure (`DEFAULT_TREATY` in `src/reinsurance.py`), editable on the Reinsurance page: retention €280m/year, limit €400m/year, recovery rate 90%, recovery lag 1 year, counterparty haircut 5%. The retention is deliberately set **above** the base-case year-1 gross claims total (~€261m) so the treaty barely affects the base case and instead demonstrates its protective effect mainly under the Large-Loss / Cat-like stress — see methodology.md section 22 for the reasoning.
