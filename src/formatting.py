"""Central display-formatting helpers (Section 7 of the V6.2 brief).

Internal computation always keeps full precision; these functions control
only how a number is *displayed*. Using one place for this means every page
renders "€149.6m" / "114.9%" / "+0.36y" the same way, instead of each page
inventing its own f-string precision.
"""
from __future__ import annotations


def fmt_eur_m(value: float, decimals: int = 1) -> str:
    """€149.6m -- never a bare float like 149.558192047381."""
    return f"€{value:,.{decimals}f}m"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """114.9% from a decimal ratio (1.149), never a bare 1.149492."""
    return f"{value:.{decimals}%}"


def fmt_signed_pct(value: float, decimals: int = 1) -> str:
    """+3.2% / -1.4% -- for deltas where the sign itself is informative."""
    return f"{value:+.{decimals}%}"


def fmt_bp(value: float, decimals: int = 0) -> str:
    """+50bp from a decimal shock (0.005), rounded to whole basis points by default."""
    return f"{value * 1e4:+.{decimals}f}bp"


def fmt_years(value: float, decimals: int = 2, signed: bool = False) -> str:
    """+0.36y / 3.73y -- never a bare 0.363925347."""
    sign = "+" if signed else ""
    return f"{value:{sign}.{decimals}f}y"


def fmt_ratio(value: float, decimals: int = 2, suffix: str = "x") -> str:
    """3.44x -- for coverage-style ratios."""
    return f"{value:.{decimals}f}{suffix}"


def fmt_weight(value: float, decimals: int = 1) -> str:
    """14.9% for a portfolio weight -- alias of fmt_pct with a 1-decimal default."""
    return fmt_pct(value, decimals)


def fmt_dv01(value: float, decimals: int = 3) -> str:
    """€0.429m/bp -- DV01 is expressed as EURm of P&L per basis point."""
    return f"€{value:.{decimals}f}m/bp"


def fmt_delta_eur_m(value: float, decimals: int = 0) -> str | None:
    """Signed EURm delta for st.metric's `delta` argument; None hides the delta."""
    if value is None:
        return None
    return f"€{value:+,.{decimals}f}m"
