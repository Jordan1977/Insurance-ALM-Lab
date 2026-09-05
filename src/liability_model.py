"""Synthetic non-life claims cash-flow engine.

This is a closed-book economic projection proxy, not a reserving, IFRS 17,
Solvency II or regulatory capital model. The purpose is to demonstrate how an
ALM analyst links claim timing and claims inflation to investment constraints.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

YEARS = np.arange(1, 11)

# Frequency x Severity x Exposure decomposition (Section 6 of the V6 brief).
# `base_claims` (used throughout the rest of the engine) is DERIVED as
# exposure_units x frequency x severity -- not a free-standing number --
# so the two views can never silently diverge. Values are illustrative:
# exposure_units are policy counts, frequency is claims per policy per year,
# severity is average cost per claim in EURm.
LIABILITY_FAMILIES = {
    "Auto": dict(
        exposure_units=100_000, frequency=.080, severity=.0400,
        payout=[.28, .24, .16, .11, .08, .05, .03, .02, .02, .01],
        inflation_sensitivity=1.0, frequency_volatility=.03, severity_volatility=.15,
        claim_vol=.10, tail="Short/Medium", liquidity_requirement="High",
    ),
    "Habitation": dict(
        exposure_units=80_000, frequency=.060, severity=.03750,
        payout=[.45, .25, .13, .08, .04, .02, .01, .01, .005, .005],
        inflation_sensitivity=.8, frequency_volatility=.04, severity_volatility=.20,
        claim_vol=.12, tail="Short", liquidity_requirement="Very High",
    ),
    "Responsabilité Civile": dict(
        exposure_units=50_000, frequency=.030, severity=.17333,
        payout=[.10, .14, .14, .12, .11, .10, .09, .08, .07, .05],
        inflation_sensitivity=1.3, frequency_volatility=.06, severity_volatility=.35,
        claim_vol=.15, tail="Long", liquidity_requirement="Low",
    ),
    "Professionnels": dict(
        exposure_units=20_000, frequency=.040, severity=.17500,
        payout=[.20, .18, .15, .12, .10, .09, .07, .05, .03, .01],
        inflation_sensitivity=1.1, frequency_volatility=.05, severity_volatility=.30,
        claim_vol=.13, tail="Medium/Long", liquidity_requirement="Medium",
    ),
    "Autres": dict(
        exposure_units=30_000, frequency=.050, severity=.06667,
        payout=[.30, .22, .15, .10, .08, .06, .04, .02, .02, .01],
        inflation_sensitivity=.9, frequency_volatility=.04, severity_volatility=.18,
        claim_vol=.11, tail="Short/Medium", liquidity_requirement="Medium",
    ),
}


def expected_claim_count(assumptions: dict, frequency_shock: float = 0.0) -> float:
    """Expected number of claims = Exposure x Frequency x (1 + frequency shock)."""
    return assumptions["exposure_units"] * assumptions["frequency"] * (1 + frequency_shock)


def expected_severity(assumptions: dict, severity_shock: float = 0.0) -> float:
    """Expected cost per claim (EURm) under an isolated severity shock."""
    return assumptions["severity"] * (1 + severity_shock)


def expected_gross_claims(assumptions: dict, frequency_shock: float = 0.0, severity_shock: float = 0.0) -> float:
    """Expected Gross Claims = Expected Claim Count x Expected Severity (Section 6).

    A pure frequency shock and a pure severity shock have an identical
    arithmetic effect on this aggregate figure, since Claims = Frequency x
    Severity with no distributional convolution modelled here -- this is a
    deliberate ALM-level simplification (see limitations.md); a full
    actuarial frequency/severity model would differentiate their
    contribution to the *tail* of the claims distribution, which this
    deterministic engine does not attempt to capture.
    """
    return expected_claim_count(assumptions, frequency_shock) * expected_severity(assumptions, severity_shock)


def _normalise(values: list[float]) -> np.ndarray:
    p = np.asarray(values, dtype=float)
    if p.sum() <= 0:
        raise ValueError("Payout profile must have a positive sum.")
    return p / p.sum()


def discount_curve(flat_rate: float = .03) -> pd.DataFrame:
    """Transparent synthetic EUR spot curve, shifted by the user's level assumption."""
    base = np.array([.023,.0235,.0245,.026,.0275,.0285,.0295,.0305,.0310,.0315])
    shift = flat_rate - .03
    return pd.DataFrame({"year": YEARS, "spot_rate": np.maximum(base + shift, -.005)})


def build_liability_cash_flows(claim_inflation: float = .025,
                               families: dict | None = None,
                               inflation_path: np.ndarray | None = None,
                               severity_multiplier: float = 1.0,
                               frequency_shock: float = 0.0,
                               severity_shock: float = 0.0) -> pd.DataFrame:
    """`severity_multiplier` scales every projected claim cash flow uniformly and
    independently of claims inflation -- used to isolate a "claims severity"
    shock (e.g. for the Monte Carlo engine) from an inflation shock, which move
    liabilities through different economic channels even though both
    ultimately change the same cash-flow numbers.

    `frequency_shock` and `severity_shock` isolate the two components of
    `expected_gross_claims` (Exposure x Frequency x Severity) for the
    Sensitivity / Tornado module -- see the docstring on
    `expected_gross_claims` for why they are arithmetically equivalent at
    this aggregate level but conceptually distinct risk drivers.
    """
    families = families or LIABILITY_FAMILIES
    rows: list[dict] = []
    for name, assumptions in families.items():
        payout = _normalise(assumptions["payout"])
        base_claims = expected_gross_claims(assumptions, frequency_shock, severity_shock)
        base_cash_flows = base_claims * payout
        sensitivity = assumptions["inflation_sensitivity"]
        if inflation_path is None:
            factors = (1 + claim_inflation * sensitivity) ** YEARS
        else:
            path = np.asarray(inflation_path, dtype=float)[: len(YEARS)]
            if len(path) < len(YEARS):
                path = np.pad(path, (0, len(YEARS)-len(path)), mode="edge")
            factors = np.cumprod(1 + path * sensitivity)
        for year, weight, base_cf, cf in zip(YEARS, payout, base_cash_flows, base_cash_flows * factors * severity_multiplier):
            rows.append({
                "family": name,
                "year": int(year),
                "payout_weight": float(weight),
                "base_cash_flow": float(base_cf),
                "cash_flow": float(cf),
                "inflation_sensitivity": float(sensitivity),
            })
    return pd.DataFrame(rows)


def pv_duration_metrics(cash_flows: np.ndarray, years: np.ndarray, rates: np.ndarray) -> tuple[float, float, float, float, float]:
    """PV, Macaulay duration, modified duration, convexity and DV01 for an
    arbitrary (year, cash_flow, rate) triple -- the single formula reused by
    both the gross liability engine and the net-of-reinsurance engine
    (src/reinsurance.py) so PV/duration is never computed twice."""
    discount = (1 + rates) ** years
    pv_vector = cash_flows / discount
    pv = float(pv_vector.sum())
    if pv <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    macaulay = float((years * pv_vector).sum() / pv)
    eps = 1e-4
    pv_up = float(np.sum(cash_flows / (1 + rates + eps) ** years))
    pv_down = float(np.sum(cash_flows / (1 + rates - eps) ** years))
    modified = (pv_down - pv_up) / (2 * pv * eps)
    convexity = (pv_up + pv_down - 2 * pv) / (pv * eps**2)
    dv01 = pv * modified * 1e-4
    return pv, macaulay, modified, convexity, dv01


def build_liability_summary(discount_rate: float = .03,
                            claim_inflation: float = .025,
                            families: dict | None = None,
                            inflation_path: np.ndarray | None = None,
                            severity_multiplier: float = 1.0,
                            frequency_shock: float = 0.0,
                            severity_shock: float = 0.0) -> pd.DataFrame:
    families = families or LIABILITY_FAMILIES
    cf = build_liability_cash_flows(claim_inflation, families, inflation_path, severity_multiplier, frequency_shock, severity_shock)
    curve = discount_curve(discount_rate).set_index("year")
    rows: list[dict] = []
    for name, assumptions in families.items():
        sub = cf[cf.family == name].sort_values("year")
        years = sub.year.to_numpy(float)
        cfs = sub.cash_flow.to_numpy(float)
        rates = curve.loc[sub.year, "spot_rate"].to_numpy(float)
        pv, macaulay, modified, convexity, dv01 = pv_duration_metrics(cfs, years, rates)
        claims_12m = float(sub.loc[sub.year == 1, "cash_flow"].sum())
        claims_3y = float(sub.loc[sub.year <= 3, "cash_flow"].sum())
        claims_beyond_5y = float(sub.loc[sub.year > 5, "cash_flow"].sum())
        liquidity_need = claims_12m / float(sub.cash_flow.sum()) if float(sub.cash_flow.sum()) else 0.0
        liquidity_need = claims_12m / float(sub.cash_flow.sum())
        rows.append({
            "family": name,
            "base_claims_amount": expected_gross_claims(assumptions, frequency_shock, severity_shock),
            "present_value": pv,
            "macaulay_duration": macaulay,
            "modified_duration": modified,
            "convexity": convexity,
            "dv01": dv01,
            "weighted_avg_maturity": macaulay,
            "claims_12m": claims_12m,
            "claims_3y": claims_3y,
            "claims_beyond_5y": claims_beyond_5y,
            "liquidity_need": liquidity_need,
            "inflation_sensitivity": assumptions["inflation_sensitivity"],
            "claim_volatility": assumptions["claim_vol"],
            "tail_classification": assumptions.get("tail", "n/a"),
            "liquidity_requirement": assumptions.get("liquidity_requirement", "n/a"),
        })
    return pd.DataFrame(rows)


def liability_cash_flow_pivot(claim_inflation: float = .025, families: dict | None = None) -> pd.DataFrame:
    df = build_liability_cash_flows(claim_inflation, families)
    pivot = df.pivot(index="year", columns="family", values="cash_flow")
    pivot["Total"] = pivot.sum(axis=1)
    return pivot


def total_liability_metrics(discount_rate: float = .03, claim_inflation: float = .025,
                            severity_multiplier: float = 1.0,
                            frequency_shock: float = 0.0,
                            severity_shock: float = 0.0) -> dict[str, float]:
    summary = build_liability_summary(discount_rate, claim_inflation, severity_multiplier=severity_multiplier,
                                      frequency_shock=frequency_shock, severity_shock=severity_shock)
    total_pv = float(summary.present_value.sum())
    mod_duration = float((summary.present_value * summary.modified_duration).sum() / total_pv)
    macaulay = float((summary.present_value * summary.macaulay_duration).sum() / total_pv)
    convexity = float((summary.present_value * summary.convexity).sum() / total_pv)
    dv01 = float(summary.dv01.sum())
    long_tail_mask = summary["tail_classification"].isin(["Long", "Medium/Long"])
    long_tail_pv = float(summary.loc[long_tail_mask, "present_value"].sum())
    return {
        "present_value": total_pv,
        "macaulay_duration": macaulay,
        "modified_duration": mod_duration,
        "convexity": convexity,
        "dv01": dv01,
        "claims_12m": float(summary.claims_12m.sum()),
        "claims_3y": float(summary.claims_3y.sum()),
        "claims_beyond_5y": float(summary.claims_beyond_5y.sum()),
        "long_tail_share": long_tail_pv / total_pv if total_pv else 0.0,
        "short_tail_share": 1.0 - (long_tail_pv / total_pv if total_pv else 0.0),
    }


def projected_claims_12m(claim_inflation: float = .025) -> float:
    cf = build_liability_cash_flows(claim_inflation)
    return float(cf.loc[cf.year == 1, "cash_flow"].sum())
