"""Reinsurance / Gross-to-Net claims engine.

Modelled as a single portfolio-level ANNUAL AGGREGATE excess-of-loss layer for
tractability -- this is a deliberate simplification, documented here and in
limitations.md: a real non-life excess-of-loss treaty attaches per claim
occurrence, not to the sum of a year's claims. The purpose is to demonstrate
the gross -> reinsurance -> net mechanic and its liquidity-timing effect on
an ALM model, not to build a placement-grade reinsurance pricing tool.

Ultimate Net Claim Cost vs Interim Liquidity Requirement (Section 13 of the
V6 brief) are kept genuinely distinct here:
  - `net_claims` is the ultimate economic claim cost after (haircut-adjusted)
    recoveries, dated to the year the claim itself is paid;
  - `recovery_received` is when the *cash* from the reinsurer actually
    arrives, shifted by `recovery_lag` years -- a treaty can reduce the
    ultimate loss while still leaving a temporary liquidity gap.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ExcessOfLossTreaty:
    """Simplified annual-aggregate excess-of-loss reinsurance structure.

    retention: EURm of annual claims retained by the insurer before recoveries start.
    limit: EURm of maximum annual recoverable above the retention (layer width).
    recovery_rate: share of the recoverable layer actually ceded/recovered (0-1);
        <1.0 represents e.g. a co-participation or placement below 100%.
    recovery_lag: years between the claim being paid and the cash recovery being received.
    counterparty_haircut: expected shortfall on recoveries from reinsurer credit risk (0-1).

    Default calibration is set ABOVE the base-case year-1 gross claims total
    (~€261m) so the base case is barely touched by the treaty -- an
    excess-of-loss layer should protect mainly against a large-loss / tail
    year, not ordinary-course claims. This preserves the ~115% base-case
    Economic A/L Coverage calibrated for stress testing (see assumptions.md)
    while still producing a materially different, and larger, GROSS-vs-NET
    story precisely when a Large-Loss / Cat-like stress is applied (Section 15).
    """
    retention: float = 280.0
    limit: float = 400.0
    recovery_rate: float = 0.90
    recovery_lag: int = 1
    counterparty_haircut: float = 0.05

    def __post_init__(self):
        if self.retention < 0 or self.limit < 0:
            raise ValueError("Retention and limit must be non-negative.")
        if not 0 <= self.recovery_rate <= 1:
            raise ValueError("recovery_rate must be in [0, 1].")
        if not 0 <= self.counterparty_haircut <= 1:
            raise ValueError("counterparty_haircut must be in [0, 1].")
        if self.recovery_lag < 0:
            raise ValueError("recovery_lag must be >= 0.")


DEFAULT_TREATY = ExcessOfLossTreaty()


def apply_reinsurance_to_annual_claims(gross_by_year: pd.Series, treaty: ExcessOfLossTreaty = DEFAULT_TREATY) -> pd.DataFrame:
    """Apply the treaty to a Series indexed by year (EURm gross claims per year).

    Returns one row per year with gross claims, gross recoverable, ceded
    recovery, counterparty haircut, effective recovery, ultimate net claims,
    and the year the recovery cash is actually received.
    """
    years = gross_by_year.index.to_numpy()
    gross = gross_by_year.to_numpy(dtype=float)
    recoverable_layer = np.clip(gross - treaty.retention, 0.0, treaty.limit)
    gross_recovery = recoverable_layer * treaty.recovery_rate
    haircut_amount = gross_recovery * treaty.counterparty_haircut
    effective_recovery = gross_recovery - haircut_amount
    net_claims = gross - effective_recovery
    return pd.DataFrame({
        "year": years,
        "gross_claims": gross,
        "gross_recovery": gross_recovery,
        "counterparty_haircut": haircut_amount,
        "effective_recovery": effective_recovery,
        "net_claims": net_claims,
        "recovery_received_year": years + treaty.recovery_lag,
    })


def net_liability_cash_flows(liability_cf: pd.DataFrame, treaty: ExcessOfLossTreaty = DEFAULT_TREATY) -> pd.DataFrame:
    """Take the family-level gross claims cash-flow table (as produced by
    `src/liability_model.build_liability_cash_flows`) and return a family-level
    NET cash-flow table, allocating each year's total effective recovery back
    to families **pro-rata to their share of that year's gross claims**. This
    keeps Σ(net by family) == net by year exactly (see
    tests/test_reinsurance.py) without pretending the treaty attaches
    separately to each family (it is portfolio-level, per the class docstring).
    """
    gross_by_year = liability_cf.groupby("year")["cash_flow"].sum()
    treaty_result = apply_reinsurance_to_annual_claims(gross_by_year, treaty).set_index("year")

    out = liability_cf.copy()
    year_gross = out["year"].map(gross_by_year)
    family_share = np.where(year_gross > 0, out["cash_flow"] / year_gross, 0.0)
    year_net = out["year"].map(treaty_result["net_claims"])
    year_effective_recovery = out["year"].map(treaty_result["effective_recovery"])
    out["gross_cash_flow"] = out["cash_flow"]
    out["effective_recovery_allocated"] = family_share * year_effective_recovery
    out["cash_flow"] = family_share * year_net  # net becomes the working cash_flow for downstream PV/duration
    return out


def liquidity_impact(treaty_result: pd.DataFrame) -> pd.DataFrame:
    """Interim liquidity view: for each year, the claim is paid in full (gross)
    while the matching recovery cash may only arrive `recovery_lag` years
    later. This is what should feed a liquidity coverage calculation, as
    distinct from the ultimate net claim cost used in the economic balance
    sheet (Section 13 of the V6 brief)."""
    out = treaty_result.copy()
    out["cash_outflow_this_year"] = out["gross_claims"]
    out["cash_inflow_this_year"] = 0.0
    for _, row in treaty_result.iterrows():
        recv_year = row["recovery_received_year"]
        mask = out["year"] == recv_year
        out.loc[mask, "cash_inflow_this_year"] += row["effective_recovery"]
    out["net_liquidity_impact_this_year"] = out["cash_outflow_this_year"] - out["cash_inflow_this_year"]
    return out


def net_liability_summary(discount_rate: float = .03, claim_inflation: float = .025,
                          treaty: ExcessOfLossTreaty = DEFAULT_TREATY,
                          frequency_shock: float = 0.0, severity_shock: float = 0.0,
                          families: dict | None = None) -> pd.DataFrame:
    """Family-level summary (PV, duration, DV01, claims_12m/3y) computed on
    NET-of-reinsurance cash flows, using the exact same `pv_duration_metrics`
    formula as the gross engine (`src/liability_model.py`) -- no second PV
    formula is created for the net view."""
    from src.liability_model import (
        LIABILITY_FAMILIES, build_liability_cash_flows, discount_curve, pv_duration_metrics,
    )
    families = families or LIABILITY_FAMILIES
    gross_cf = build_liability_cash_flows(claim_inflation, families, frequency_shock=frequency_shock, severity_shock=severity_shock)
    net_cf = net_liability_cash_flows(gross_cf, treaty)
    curve = discount_curve(discount_rate).set_index("year")

    rows = []
    for name, assumptions in families.items():
        sub = net_cf[net_cf.family == name].sort_values("year")
        years = sub.year.to_numpy(float)
        cfs = sub.cash_flow.to_numpy(float)  # already netted by net_liability_cash_flows
        rates = curve.loc[sub.year, "spot_rate"].to_numpy(float)
        pv, macaulay, modified, convexity, dv01 = pv_duration_metrics(cfs, years, rates)
        claims_12m = float(sub.loc[sub.year == 1, "cash_flow"].sum())
        claims_3y = float(sub.loc[sub.year <= 3, "cash_flow"].sum())
        claims_beyond_5y = float(sub.loc[sub.year > 5, "cash_flow"].sum())
        gross_claims_12m = float(sub.loc[sub.year == 1, "gross_cash_flow"].sum())
        rows.append({
            "family": name, "present_value": pv, "macaulay_duration": macaulay,
            "modified_duration": modified, "convexity": convexity, "dv01": dv01,
            "claims_12m": claims_12m, "claims_3y": claims_3y, "claims_beyond_5y": claims_beyond_5y,
            "gross_claims_12m": gross_claims_12m,
            "tail_classification": assumptions.get("tail", "n/a"),
        })
    return pd.DataFrame(rows)


def total_net_liability_metrics(discount_rate: float = .03, claim_inflation: float = .025,
                                treaty: ExcessOfLossTreaty = DEFAULT_TREATY,
                                frequency_shock: float = 0.0, severity_shock: float = 0.0) -> dict:
    """Aggregate net-of-reinsurance liability metrics -- the NET counterpart of
    `src.liability_model.total_liability_metrics`, aggregated the same way
    (present-value-weighted duration/convexity)."""
    summary = net_liability_summary(discount_rate, claim_inflation, treaty, frequency_shock, severity_shock)
    total_pv = float(summary.present_value.sum())
    if total_pv <= 0:
        return {"present_value": 0.0, "modified_duration": 0.0, "macaulay_duration": 0.0,
                "convexity": 0.0, "dv01": 0.0, "claims_12m": 0.0, "claims_3y": 0.0,
                "claims_beyond_5y": 0.0, "gross_claims_12m": 0.0}
    mod_duration = float((summary.present_value * summary.modified_duration).sum() / total_pv)
    macaulay = float((summary.present_value * summary.macaulay_duration).sum() / total_pv)
    convexity = float((summary.present_value * summary.convexity).sum() / total_pv)
    return {
        "present_value": total_pv,
        "macaulay_duration": macaulay,
        "modified_duration": mod_duration,
        "convexity": convexity,
        "dv01": float(summary.dv01.sum()),
        "claims_12m": float(summary.claims_12m.sum()),
        "claims_3y": float(summary.claims_3y.sum()),
        "claims_beyond_5y": float(summary.claims_beyond_5y.sum()),
        "gross_claims_12m": float(summary.gross_claims_12m.sum()),
    }


def reinsurance_summary(liability_cf: pd.DataFrame, treaty: ExcessOfLossTreaty = DEFAULT_TREATY) -> dict:
    gross_by_year = liability_cf.groupby("year")["cash_flow"].sum()
    result = apply_reinsurance_to_annual_claims(gross_by_year, treaty)
    liq = liquidity_impact(result)
    return {
        "treaty": treaty,
        "annual_detail": result,
        "liquidity_detail": liq,
        "total_gross_claims": float(result.gross_claims.sum()),
        "total_effective_recovery": float(result.effective_recovery.sum()),
        "total_net_claims": float(result.net_claims.sum()),
        "claims_12m_gross": float(result.loc[result.year == result.year.min(), "gross_claims"].sum()),
        "claims_12m_net": float(result.loc[result.year == result.year.min(), "net_claims"].sum()),
        "recoveries_12m": float(result.loc[result.year == result.year.min(), "effective_recovery"].sum()),
    }


@dataclass(frozen=True)
class QuotaShareTreaty:
    """Simplified proportional treaty used only for analytical comparison.

    ``ceded_share`` is the fraction of gross claims ceded to the reinsurer.
    Premiums, commissions, reinstatements and treaty-specific accounting are
    intentionally out of scope; this is a claims-side ALM illustration only.
    """
    ceded_share: float = 0.30
    recovery_lag: int = 0
    counterparty_haircut: float = 0.02

    def __post_init__(self):
        if not 0 <= self.ceded_share <= 1:
            raise ValueError("ceded_share must be in [0, 1].")
        if not 0 <= self.counterparty_haircut <= 1:
            raise ValueError("counterparty_haircut must be in [0, 1].")
        if self.recovery_lag < 0:
            raise ValueError("recovery_lag must be >= 0.")


def apply_quota_share_to_annual_claims(
    gross_by_year: pd.Series, treaty: QuotaShareTreaty = QuotaShareTreaty()
) -> pd.DataFrame:
    """Apply a simple quota-share claims cession to annual gross claims."""
    years = gross_by_year.index.to_numpy()
    gross = gross_by_year.to_numpy(dtype=float)
    gross_recovery = gross * treaty.ceded_share
    haircut_amount = gross_recovery * treaty.counterparty_haircut
    effective_recovery = gross_recovery - haircut_amount
    return pd.DataFrame({
        "year": years,
        "gross_claims": gross,
        "gross_recovery": gross_recovery,
        "counterparty_haircut": haircut_amount,
        "effective_recovery": effective_recovery,
        "net_claims": gross - effective_recovery,
        "recovery_received_year": years + treaty.recovery_lag,
    })


def compare_reinsurance_structures(
    gross_by_year: pd.Series,
    xol: ExcessOfLossTreaty = DEFAULT_TREATY,
    quota_share: QuotaShareTreaty = QuotaShareTreaty(),
) -> pd.DataFrame:
    """Compare No RI, quota share and XoL on the same gross-claims vector.

    This is deliberately a *claims-side* comparison. It does not compare ceded
    premium economics, commissions or capital treatment, so the output is framed
    as analytical protection comparison rather than treaty recommendation.
    """
    gross = float(gross_by_year.sum())
    no_ri = gross
    qs = apply_quota_share_to_annual_claims(gross_by_year, quota_share)
    xl = apply_reinsurance_to_annual_claims(gross_by_year, xol)
    rows = [
        {"structure": "No reinsurance", "gross_claims": gross, "effective_recovery": 0.0, "net_claims": no_ri},
        {"structure": f"Quota share ({quota_share.ceded_share:.0%})", "gross_claims": gross,
         "effective_recovery": float(qs.effective_recovery.sum()), "net_claims": float(qs.net_claims.sum())},
        {"structure": "Annual aggregate XoL", "gross_claims": gross,
         "effective_recovery": float(xl.effective_recovery.sum()), "net_claims": float(xl.net_claims.sum())},
    ]
    out = pd.DataFrame(rows)
    out["recovery_share_of_gross"] = out.effective_recovery / out.gross_claims.replace(0, np.nan)
    return out
