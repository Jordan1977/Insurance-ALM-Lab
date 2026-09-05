# Methodology

All monetary amounts are expressed in **EUR millions** unless stated otherwise. The model is a simplified economic ALM framework for a synthetic non-life insurer.

## 1. Economic balance sheet

### Economic surplus

`Surplus = Economic Assets - PV(Modelled Liabilities)`

Interpretation: the economic buffer available after the present value of projected claim cash flows.

### Economic A/L Coverage

`Coverage = Economic Assets / PV(Modelled Liabilities)`

This is not a Solvency II solvency ratio.

## 2. Liability cash flows

Each non-life family has:

- base claim amount;
- payout weights by projection year;
- claims-inflation sensitivity;
- claim-volatility proxy.

Projected cash flow:

`CF(family,t) = BaseCF(family,t) × cumulative claims-inflation factor`

In the deterministic model, family claims inflation is the configured base claims inflation scaled by family sensitivity.

Present value:

`PV = Σ CF_t / (1 + r_t)^t`

where `r_t` is the synthetic EUR spot rate for year `t`.

## 3. Duration, convexity and DV01

Macaulay duration is the PV-weighted timing of cash flows.

Modified duration:

`D_mod ≈ - (1/PV) × dPV/dr`

DV01:

`DV01 = PV × D_mod × 0.0001`

The liability engine estimates modified duration numerically with ±1bp parallel shifts to the full curve.

## 4. Contractual asset book

For synthetic bonds and private debt:

1. target market value is allocated from the strategic asset book;
2. coupon, maturity and synthetic yield are assigned;
3. face value is calibrated so discounted contractual cash flows equal target market value;
4. cash-flow metrics are calculated from the resulting schedule.

This prevents the common prototype error `market value = principal`.

Non-contractual assets do not receive fictitious principal maturity. Estimated income from equity / real assets is labelled separately and excluded from contractual cash-flow matching.

## 5. Cash-flow matching

Annual contractual coverage:

`Coverage_t = Contractual Asset CF_t / Projected Claims_t`

Gap:

`Gap_t = Asset CF_t - Liability CF_t`

The model also aggregates flows into 0–1y, 1–3y, 3–5y, 5–7y, 7–10y and 10y+ buckets.

## 6. Market-risk approximation

Portfolio volatility:

`σ_p = sqrt(w' Σ w)`

Marginal contribution to risk:

`MCR_i = (Σw)_i / σ_p`

Contribution to risk:

`CR_i = w_i × MCR_i`

Rate shock on fixed-rate assets uses modified duration plus convexity:

`ΔP/P ≈ -D_mod Δy + 0.5 × Convexity × (Δy)^2`

Credit-spread impact:

`ΔP/P ≈ -SpreadDuration × ΔSpread`

## 7. Deterministic scenario attribution

Each scenario decomposes asset P&L into:

- rate effect;
- credit-spread effect;
- equity / real-asset effect;
- FX effect.

Liability impact is separately recomputed from the shocked discount-rate level and claims-inflation assumption.

Surplus attribution therefore closes to:

`Stressed Surplus = Base Surplus + Asset effects - Liability revaluation`

## 8. Stochastic economic scenario generator

Five correlated factors are simulated:

1. Equity — GBM log return
   `ln(S_t/S_{t-1}) = (μ - 0.5σ²)Δt + σ√Δt Z`
2. Rates — Vasicek-style mean reversion
   `r_t = r_{t-1} + a(b-r_{t-1}) + σZ`
3. Inflation — mean-reverting AR process
4. Credit spreads — non-negative mean-reverting process
5. FX — lognormal return process
6. Claims severity — positive lognormal multiplier around projected annual claims

The input correlation matrix is repaired to a positive-semidefinite correlation matrix before Cholesky decomposition.

## 9. Dynamic closed-book projection

At each annual step:

- asset carry is accrued;
- rate, spread, equity, real-asset and FX factor effects are applied;
- sensitivities scale with the remaining asset base;
- projected claims are paid from assets;
- remaining claims are valued at the scenario rate.

No future premiums are modelled.

## 10. Surplus-at-Risk

For confidence `c`:

`q = percentile(Surplus, 1-c)`

`Surplus-at-Risk = max(Base Surplus - q, 0)`

Tail expected shortfall is calculated from simulated surplus values below the selected quantile.

## 11. Liquidity

Base 12M claims coverage:

`Liquid Assets / Next-12M Projected Claims`

This is an illustrative internal ALM metric, **not regulatory LCR**.

The liquidity stress applies claim uplift and liquidity haircuts to monetisable assets.

## 12. Hedge sizing

A synthetic swap DV01 per €1m notional is:

`DV01_hedge = Modified Duration × 0.0001 EURm/bp`

Required signed notional:

`Notional = Required DV01 Change / Hedge DV01 per €1m`

Positive DV01 is represented by receive-fixed; negative DV01 by pay-fixed.

Equity and FX overlays reduce the exposed notional by the selected hedge ratio.

## 13. Liability-aware strategic allocation

The optimiser minimises a transparent return/risk/duration objective under explicit constraints:

- total weights = 100%;
- cash minimum / maximum;
- equity maximum;
- High Yield maximum;
- illiquid maximum;
- absolute modified-duration gap ≤ tolerance;
- liquid assets / next-12M claims ≥ target.

The objective is educational and is not a production investment policy optimiser.

## 14. Asset cantonment

Decision variable:

`x(i,j) = EURm of asset class i assigned to liability family j`

Constraints:

- each asset class is fully conserved across pools;
- each pool receives its target share of total assets;
- each pool satisfies a minimum 12M liquidity floor.

Duration mismatch is minimised using positive/negative linear slack variables. The exercise is analytical, not legal or accounting ring-fencing.

## 15. Sensitivity analysis / tornado

Every row in the tornado chart calls `evaluate_deterministic_scenario` (the same function used by the Economic Scenarios and Stress Testing pages) with a single isolated factor shock — no sensitivity formula is duplicated. Two liability-side isolations were added specifically for this module:

- `extra_claim_inflation`: adds to the base claims-inflation assumption independently of a named scenario's own inflation shock.
- `severity_shock`: a uniform multiplier on projected claim cash flows (`severity_multiplier` in `src/liability_model.py`), representing a claims-severity shock that is economically distinct from a claims-inflation shock even though both change the same cash-flow numbers.

An optional `real_estate_shock` key in the shock dict isolates real assets from the equity shock; if omitted, real assets keep the original behaviour of moving at 0.5× the equity shock (unchanged for every named scenario — this is backward-compatible by construction, see `tests/test_scenario_refactor.py`).

## 16. Performance attribution (V6 rebuild)

**V6 correction — see CHANGELOG_V6.md:** the V5 version derived a "realised" return as `expected_return + random noise` and called it `historical_return_1y`, which was misleading since nothing in that number came from an actual observation. V6 removes the field entirely and replaces it with an **Illustrative Factor-Based Return Attribution**: one explicitly-labelled `SYNTHETIC_TRAILING_12M_SHOCK` (`src/performance_attribution.py`) is run through the same `deterministic_asset_attribution` function used by every scenario and tornado calculation elsewhere in the app — no second P&L formula exists.

`Beginning MV_i + Carry_i + Rate P&L_i + Spread P&L_i + Equity/Real P&L_i + FX P&L_i = Ending MV_i`, exactly, for every asset class (`tests/test_performance_attribution.py`). **This is explicitly not a Brinson attribution** — the dataset has no separate benchmark or policy-weight return series to support a genuine allocation/selection decomposition, and the model does not fabricate one.

## 17. Reinvestment & maturity management (V6 rebuild)

**V6 change from V1 — see CHANGELOG_V6.md:** the V5 version sized a reinvestment as a single first-order duration blend from the *sum* of positive net cash-flow years. V6 runs an explicit year-by-year cash account (`src/reinvestment.py`):

`Opening Cash + Coupon Income + Bond Maturities + Reinsurance Recoveries − Gross Claims Paid = Cash Available Before Reinvestment`

If a year's own inflows fall short of that year's gross claims outflow, the gap is funded from the insurer's other liquid assets (`shortfall_funded_externally`), not carried forward as a growing negative cash balance. `Ending Cash = Cash Available After Funding − Amount Reinvested`, which is always ≥ 0 and reconciles exactly (`tests/test_reinvestment.py::test_cash_conservation_holds_exactly_every_year`).

Five named policies (Hold cash, **Reinvest short** — new in V6, Reinvest at same maturity, Extend duration, Liability-matching reinvestment) each select a candidate from a synthetic investable universe (`REINVESTMENT_UNIVERSE`: EUR Sovereign 2Y/5Y/10Y, EUR IG 3Y/5Y/7Y — Section 27) and blend the *actual* amount invested (from the cash account above, not a heuristic) into the current book's duration and yield.

## 18. Investment guidelines monitor

Guidelines compare a computed metric against a synthetic internal limit and return GREEN/AMBER/RED plus a `headroom` figure. **Sign convention: headroom is always positive when compliant and negative when in breach**, regardless of whether the guideline is a ceiling (e.g. maximum equity) or a floor (e.g. minimum cash) — an earlier version returned `current − limit` unconditionally, which read backwards for floor-type guidelines; this was caught in the red-team pass and fixed (`tests/test_guidelines.py::test_headroom_sign_convention_...`). Both a proposed SAA allocation and a reinvestment policy are tested through the exact same `check_compliance` function used for the current book.

## 19. Audit trail

`update_assumption()` (`src/audit_trail.py`) is the single function that should be used to change a tracked assumption: it validates the new value, no-ops if unchanged, and appends one entry with the previous value, new value, reason and affected modules. This is explicitly a **prototype analytical audit trail**, not a regulatory one.

## 20. Investment Committee Pack

Condenses thirteen sections (executive position net of reinsurance, non-life claims outlook, gross vs net / reinsurance, current allocation, performance attribution, ALM matching & liquidity, top risk drivers, active scenario, investment guidelines, reinvestment, hedging, liability-aware allocation, items for review — V6 added the claims-outlook and reinsurance sections) by calling the same functions used on their dedicated pages — no figure is recomputed independently. "Items for Committee Review" use "Key Watchpoint" / "Analytical Observation" / "item for review" language and are generated from threshold checks on computed values only; the wording never says "recommendation", "buy" or "sell".

## 21. Frequency x Severity claims engine (V6)

Each non-life family's expected gross claims are **derived**, not free-standing:

`Expected Claim Count = Exposure Units × Frequency`
`Expected Severity = base severity per claim (EURm)`
`Expected Gross Claims = Expected Claim Count × Expected Severity`

Calibration reproduces the original V5 base-claims figures exactly (`tests/test_frequency_severity.py::test_expected_gross_claims_matches_original_calibration`), so the balance-sheet scale is unchanged. `frequency_shock` and `severity_shock` isolate the two components for the Sensitivity/Tornado module; at this aggregate ALM level they have an **identical arithmetic effect** on projected claims (Claims = Frequency × Severity with no distributional convolution modelled), which is a documented simplification, not a hidden one — see limitations.md. Each family also carries a `tail` classification (Short / Short-Medium / Medium-Long / Long) and a qualitative `liquidity_requirement`, used to compute the Long-Tail / Short-Tail liability PV split (`total_liability_metrics()["long_tail_share"]`).

## 22. Reinsurance (V6 — the main new module)

Modelled as a single portfolio-level **annual aggregate** excess-of-loss layer (`src/reinsurance.py`), not a per-claim-occurrence layer — a deliberate tractability simplification, documented here and in limitations.md.

For each year's gross claims `G_t`:

`Recoverable Layer_t = clip(G_t − Retention, 0, Limit)`
`Gross Recovery_t = Recoverable Layer_t × Recovery Rate`
`Effective Recovery_t = Gross Recovery_t × (1 − Counterparty Haircut)`
`Net Claims_t = G_t − Effective Recovery_t` (ultimate net cost, dated to the year the claim is paid)

The cash from that recovery is received at `t + Recovery Lag`, which can differ from `t` — Section 13's key distinction: **Ultimate Net Claim Cost** (used for the economic balance sheet / duration) is kept separate from the **Interim Liquidity Requirement** (`src.reinsurance.liquidity_impact`: gross claims paid this year, less recovery cash *actually received* this year — used for the 12M Liquidity Coverage metric). A treaty can lower the ultimate loss while still leaving a temporary cash gap.

The default treaty (retention €280m, limit €400m, recovery rate 90%, lag 1y, haircut 5%) is calibrated **above** ordinary base-case annual claims (~€261m in year 1) so it barely bites in the base case — preserving the original ~115% Economic A/L Coverage calibration used for stress testing — while triggering materially larger recoveries under the Large-Loss / Cat-like stress (`tests/test_reinsurance.py::test_default_treaty_barely_touches_base_case_but_bites_under_large_loss_stress`). This mirrors how a real excess-of-loss layer is meant to protect against a tail year, not everyday claims volatility.

Family-level net cash flows (`net_liability_cash_flows`) allocate each year's total effective recovery back to families pro-rata to their share of that year's gross claims, so Σ(net by family) reconciles exactly to net by year without pretending the treaty attaches separately to each family.

**Net liabilities are the headline balance-sheet figure everywhere in the app** (`src/analytics.py`, `evaluate_deterministic_scenario`) — gross figures remain available under `liabilities_gross` / `reinsurance` and are never silently mixed with net figures (Section 4/16/64; enforced in `tests/test_analytics.py`).

