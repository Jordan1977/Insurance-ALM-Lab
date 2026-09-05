"""Reinvestment & Maturity Management V2.

Answers a concrete ALM question: as bonds mature, coupons are received,
reinsurance recoveries arrive and claims are paid, how much cash is left to
reinvest each year -- and what happens to asset duration, the duration gap
and expected return under a few named reinvestment policies?

V6 change from V1: the old version sized a reinvestment as a single
first-order duration blend from the *sum* of positive net cash flow years.
This version runs an explicit YEAR-BY-YEAR cash account:

    Opening Cash
    + Coupon Income
    + Bond Maturities (principal)
    + Reinsurance Recoveries (cash actually received that year)
    - Gross Claims Paid (the insurer pays the claim in full; the recovery
      arrives separately, on its own lag -- see src/reinsurance.py)
    = Cash Available Before Reinvestment
    - Amount Reinvested (the full available balance, if positive)
    = Ending Cash

so `Opening Cash + Inflows - Outflows - Investments = Ending Cash` holds
exactly, by construction, every year (tests/test_reinvestment.py enforces
this as a genuine conservation check, not a tautology to be trusted blindly).

This reuses `instrument_cash_flows` (src/asset_model.py) for the
principal/coupon split and `src.reinsurance.reinsurance_summary` for the
claims/recovery cash timing -- no cash-flow formula is recomputed here.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.asset_model import instrument_cash_flows, portfolio_modified_duration, portfolio_asset_dv01
from src.reinsurance import ExcessOfLossTreaty, DEFAULT_TREATY, reinsurance_summary
from scipy.optimize import minimize

REINVESTMENT_POLICIES = [
    "Hold cash",
    "Reinvest short",
    "Reinvest at same maturity",
    "Extend duration",
    "Liability-matching reinvestment",
]


@dataclass(frozen=True)
class ReinvestmentCandidate:
    """One instrument in the synthetic investable universe (Section 27)."""
    name: str
    yield_: float
    duration: float
    spread: float
    rating: str
    liquidity: float
    maturity: float


REINVESTMENT_UNIVERSE: list[ReinvestmentCandidate] = [
    ReinvestmentCandidate("EUR Sovereign 2Y", .028, 1.9, .000, "AA", .95, 2),
    ReinvestmentCandidate("EUR Sovereign 5Y", .031, 4.6, .000, "AA", .90, 5),
    ReinvestmentCandidate("EUR Sovereign 10Y", .033, 8.5, .000, "AA-", .85, 10),
    ReinvestmentCandidate("EUR IG 3Y", .035, 2.8, .007, "A", .75, 3),
    ReinvestmentCandidate("EUR IG 5Y", .037, 4.5, .008, "A", .70, 5),
    ReinvestmentCandidate("EUR IG 7Y", .039, 6.1, .009, "BBB", .65, 7),
]

CASH_DURATION, CASH_YIELD = 0.2, .020  # illustrative near-cash placement


def _closest_candidate(target_duration: float) -> ReinvestmentCandidate:
    return min(REINVESTMENT_UNIVERSE, key=lambda c: abs(c.duration - target_duration))


def optimize_liability_matching_basket(target_duration: float, min_liquidity: float = 0.70) -> dict:
    """Optimise a small reinvestment basket around a target duration.

    The objective is intentionally transparent: minimise duration mismatch,
    mildly penalise lower-liquidity assets and reward yield only as a tertiary
    criterion. It is not a production optimiser and does not model transaction
    costs or capital charges.
    """
    durations = np.array([c.duration for c in REINVESTMENT_UNIVERSE], dtype=float)
    yields = np.array([c.yield_ for c in REINVESTMENT_UNIVERSE], dtype=float)
    liquidity = np.array([c.liquidity for c in REINVESTMENT_UNIVERSE], dtype=float)
    n = len(REINVESTMENT_UNIVERSE)
    target = float(np.clip(target_duration, durations.min(), durations.max()))

    def objective(w: np.ndarray) -> float:
        duration_penalty = (float(w @ durations) - target) ** 2
        liquidity_penalty = max(min_liquidity - float(w @ liquidity), 0.0) ** 2
        yield_reward = float(w @ yields)
        concentration_penalty = float(np.sum(w**2))
        return duration_penalty + 2.0 * liquidity_penalty + 0.02 * concentration_penalty - 0.02 * yield_reward

    constraints = [
        {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},
        {"type": "ineq", "fun": lambda w: float(w @ liquidity - min_liquidity)},
    ]
    result = minimize(objective, np.full(n, 1.0 / n), method="SLSQP", bounds=[(0.0, 1.0)] * n,
                      constraints=constraints, options={"maxiter": 1000, "ftol": 1e-12})
    if not result.success:
        raise RuntimeError(f"Liability-matching reinvestment optimisation failed: {result.message}")
    w = np.maximum(result.x, 0.0)
    w /= w.sum()
    return {
        "weights": {c.name: float(x) for c, x in zip(REINVESTMENT_UNIVERSE, w) if x > 1e-6},
        "duration": float(w @ durations),
        "yield": float(w @ yields),
        "liquidity": float(w @ liquidity),
        "target_duration": target,
        "success": bool(result.success),
    }


def select_candidate(policy: str, current_asset_duration: float, liability_duration: float) -> ReinvestmentCandidate | None:
    """None represents holding cash (no universe instrument selected)."""
    if policy == "Hold cash":
        return None
    if policy == "Reinvest short":
        return REINVESTMENT_UNIVERSE[0]  # EUR Sovereign 2Y
    if policy == "Extend duration":
        return REINVESTMENT_UNIVERSE[2]  # EUR Sovereign 10Y
    if policy == "Reinvest at same maturity":
        return _closest_candidate(current_asset_duration)
    if policy == "Liability-matching reinvestment":
        return _closest_candidate(liability_duration)
    raise ValueError(f"Unknown reinvestment policy: {policy}")


def annual_cash_projection(instrument_book: pd.DataFrame, gross_liability_cf: pd.DataFrame,
                           policy: str, current_asset_duration: float, liability_duration: float,
                           treaty: ExcessOfLossTreaty = DEFAULT_TREATY, horizon: int = 5,
                           opening_cash: float = 0.0) -> tuple[pd.DataFrame, ReinvestmentCandidate | None]:
    """Run the explicit year-by-year cash account described in the module
    docstring and return (ladder, chosen candidate).

    If a year's own coupon/maturity/recovery inflows fall short of that
    year's gross claims outflow, the gap is funded from the insurer's other
    liquid assets (tracked separately as `shortfall_funded_externally`), NOT
    carried forward as a growing negative cash balance -- an insurer draws on
    its liquid buffer each year, it does not run an ever-larger overdraft on
    this specific instrument's cash-flow stream. This is exactly the
    liquidity trade-off the Executive Dashboard's 12M Liquidity Coverage
    metric is meant to monitor.
    """
    asset_cf = instrument_cash_flows(instrument_book, horizon=horizon)
    liq = reinsurance_summary(gross_liability_cf, treaty)["liquidity_detail"]
    candidate = select_candidate(policy, current_asset_duration, liability_duration)

    rows = []
    cash = max(opening_cash, 0.0)
    for year in range(1, horizon + 1):
        year_assets = asset_cf[asset_cf.year == year]
        maturing = float(year_assets.principal_component.sum())
        coupon = float(year_assets.coupon_component.sum())
        liq_row = liq.loc[liq.year == year]
        recovery_in = float(liq_row.cash_inflow_this_year.iloc[0]) if len(liq_row) else 0.0
        gross_claims_out = float(liq_row.cash_outflow_this_year.iloc[0]) if len(liq_row) else 0.0

        opening = cash
        cash_available = opening + coupon + maturing + recovery_in - gross_claims_out
        shortfall_funded = max(-cash_available, 0.0)
        cash_available_after_funding = cash_available + shortfall_funded  # floored at 0
        invested = max(cash_available_after_funding, 0.0)
        ending = cash_available_after_funding - invested  # == 0 whenever invested == cash_available_after_funding

        rows.append({
            "year": year, "opening_cash": opening, "coupon_income": coupon,
            "bond_maturities": maturing, "reinsurance_recoveries": recovery_in,
            "gross_claims_paid": gross_claims_out,
            "cash_available_before_reinvestment": cash_available,
            "shortfall_funded_externally": shortfall_funded,
            "amount_reinvested": invested, "ending_cash": ending,
        })
        cash = ending
    return pd.DataFrame(rows), candidate


def policy_outcome(asset_df: pd.DataFrame, instrument_book: pd.DataFrame, gross_liability_cf: pd.DataFrame,
                   policy: str, liability_duration: float, treaty: ExcessOfLossTreaty = DEFAULT_TREATY,
                   horizon: int = 5) -> dict:
    """Blend the actually-invested amount (from `annual_cash_projection`, not
    a heuristic sum) into the current book to get the resulting duration,
    DV01 and expected-yield pickup under one named policy."""
    total_assets = float(asset_df.market_value.sum())
    current_duration = portfolio_modified_duration(asset_df)
    current_dv01 = portfolio_asset_dv01(asset_df)
    current_yield = float((asset_df.market_value * asset_df["yield"]).sum() / total_assets)

    ladder, candidate = annual_cash_projection(instrument_book, gross_liability_cf, policy,
                                               current_duration, liability_duration, treaty, horizon)
    invested_total = float(ladder.amount_reinvested.sum())
    remaining_assets = max(total_assets - invested_total, 0.0)
    remaining_weight = remaining_assets / total_assets if total_assets else 0.0
    reinvested_weight = 1.0 - remaining_weight

    basket = None
    if policy == "Liability-matching reinvestment" and invested_total > 1e-9:
        # Target the duration required on the *new money* so the resulting whole
        # book moves toward the net-liability duration rather than merely buying
        # the single bond closest to the liability duration.
        required_new_money_duration = (liability_duration * total_assets - remaining_assets * current_duration) / invested_total
        basket = optimize_liability_matching_basket(required_new_money_duration)
        new_duration = basket["duration"]
        new_yield = basket["yield"]
    else:
        new_duration = CASH_DURATION if candidate is None else candidate.duration
        new_yield = CASH_YIELD if candidate is None else candidate.yield_

    asset_duration_after = remaining_weight * current_duration + reinvested_weight * new_duration
    dv01_after = current_dv01 * (asset_duration_after / current_duration if current_duration else 1.0)
    expected_yield_after = remaining_weight * current_yield + reinvested_weight * new_yield

    return {
        "policy": policy,
        "candidate": "Optimized bond basket" if basket is not None else (candidate.name if candidate else "Cash / money market"),
        "basket_weights": basket["weights"] if basket is not None else None,
        "basket_liquidity": basket["liquidity"] if basket is not None else None,
        "ladder": ladder,
        "invested_total": invested_total,
        "reinvested_share_of_book": reinvested_weight,
        "asset_duration_before": current_duration,
        "asset_duration_after": asset_duration_after,
        "duration_gap_after": asset_duration_after - liability_duration,
        "asset_dv01_after": dv01_after,
        "expected_yield_before": current_yield,
        "expected_yield_after": expected_yield_after,
        "yield_pickup": expected_yield_after - current_yield,
        "final_cash_balance": float(ladder.ending_cash.iloc[-1]),
    }


def compare_reinvestment_policies(asset_df: pd.DataFrame, instrument_book: pd.DataFrame,
                                  gross_liability_cf: pd.DataFrame, liability_duration: float,
                                  treaty: ExcessOfLossTreaty = DEFAULT_TREATY, horizon: int = 5) -> pd.DataFrame:
    rows = [policy_outcome(asset_df, instrument_book, gross_liability_cf, p, liability_duration, treaty, horizon)
            for p in REINVESTMENT_POLICIES]
    return pd.DataFrame([{k: v for k, v in r.items() if k != "ladder"} for r in rows])
