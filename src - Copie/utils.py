"""
utils.py
--------
Small, dependency-free helper functions reused across the ALM engine.
Kept deliberately simple: every function has one job and a docstring
explaining the ALM question it supports.
"""

from __future__ import annotations
import numpy as np
import pandas as pd


def discount_factor(rate: float, t: float) -> float:
    """Standard annual-compounding discount factor: 1 / (1+r)^t."""
    return 1.0 / (1.0 + rate) ** t


def present_value(cash_flows: np.ndarray, rate: float, years: np.ndarray) -> float:
    """PV of a stream of cash flows at a flat discount rate."""
    return float(np.sum(cash_flows / (1.0 + rate) ** years))


def macaulay_duration(cash_flows: np.ndarray, rate: float, years: np.ndarray) -> float:
    """
    Macaulay duration = time-weighted average of PV of cash flows / total PV.
    Answers: "On average, when do these cash flows occur, in PV terms?"
    """
    pv = cash_flows / (1.0 + rate) ** years
    total_pv = pv.sum()
    if total_pv == 0:
        return 0.0
    return float(np.sum(years * pv) / total_pv)


def modified_duration(macaulay_dur: float, rate: float) -> float:
    """Modified duration = Macaulay duration / (1 + r). Sensitivity of PV to a rate shift."""
    return macaulay_dur / (1.0 + rate)


def convexity(cash_flows: np.ndarray, rate: float, years: np.ndarray) -> float:
    """
    Simplified convexity estimate: second-order sensitivity of PV to rate changes.
    Convexity = Σ CF_t * t * (t+1) / (1+r)^(t+2)  /  PV
    """
    pv = cash_flows / (1.0 + rate) ** years
    total_pv = pv.sum()
    if total_pv == 0:
        return 0.0
    conv = np.sum(cash_flows * years * (years + 1) / (1.0 + rate) ** (years + 2))
    return float(conv / total_pv)


def dv01(pv: float, modified_dur: float) -> float:
    """
    DV01 (a.k.a. PV01): change in present value for a 1bp parallel rate move.
    DV01 = PV * ModDuration * 0.0001
    """
    return pv * modified_dur * 0.0001


def status_flag(value: float, green_bound: float, amber_bound: float, higher_is_better: bool = True) -> str:
    """
    Simple traffic-light classification used throughout the dashboards.
    higher_is_better=True  -> value >= green_bound => GREEN, >= amber_bound => AMBER, else RED
    higher_is_better=False -> reversed logic (e.g. duration gap, VaR)
    """
    if higher_is_better:
        if value >= green_bound:
            return "GREEN"
        elif value >= amber_bound:
            return "AMBER"
        return "RED"
    else:
        if value <= green_bound:
            return "GREEN"
        elif value <= amber_bound:
            return "AMBER"
        return "RED"


STATUS_COLORS = {"GREEN": "#1e7f4f", "AMBER": "#c98a1f", "RED": "#b23b3b"}


def fmt_eur(x: float, unit: str = "m") -> str:
    """Format a euro amount in millions ('m') or billions ('bn') with a sign."""
    if unit == "bn":
        return f"€{x/1000:,.2f}bn"
    return f"€{x:,.1f}m"


def fmt_pct(x: float, decimals: int = 1) -> str:
    return f"{x*100:.{decimals}f}%"


def maturity_bucket(years: float) -> str:
    """Bucket a maturity/duration figure into standard ALM buckets."""
    if years <= 1:
        return "0-1y"
    elif years <= 3:
        return "1-3y"
    elif years <= 5:
        return "3-5y"
    elif years <= 7:
        return "5-7y"
    elif years <= 10:
        return "7-10y"
    return "10y+"


BUCKET_ORDER = ["0-1y", "1-3y", "3-5y", "5-7y", "7-10y", "10y+"]
