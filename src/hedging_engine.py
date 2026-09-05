"""Illustrative hedge sizing for ALM risk analysis.

Hedge analytics are intentionally simple: they size overlays from first-order
sensitivities and do not model derivative pricing, collateral, basis, accounting
or transaction costs.
"""
from __future__ import annotations

HEDGE_INSTRUMENTS = {
    "EUR 5Y receive-fixed swap": {"modified_duration": 4.5},
    "EUR 10Y receive-fixed swap": {"modified_duration": 8.2},
    "EUR 15Y receive-fixed swap": {"modified_duration": 11.5},
}


def hedge_dv01_per_million(instrument: str) -> float:
    """EURm/bp for €1m notional: 1 * duration * 1bp."""
    duration = HEDGE_INSTRUMENTS[instrument]["modified_duration"]
    return duration * 1e-4


def rate_hedge(asset_dv01: float, liability_dv01: float,
               instrument: str = "EUR 10Y receive-fixed swap",
               hedge_ratio: float = 1.0,
               target_gap: float = 0.0) -> dict[str, float | str]:
    """Size a synthetic swap overlay against the asset-minus-liability DV01 gap.

    A positive gap means assets are more rate-sensitive than liabilities; the
    overlay must *reduce* asset DV01 (pay fixed / receive floating direction).
    A negative gap needs positive DV01 (receive fixed / pay floating).
    """
    before_gap = asset_dv01 - liability_dv01 - target_gap
    hedge_ratio = min(max(float(hedge_ratio), 0.0), 1.0)
    per_m = hedge_dv01_per_million(instrument)
    required_dv01_change = -before_gap * hedge_ratio
    signed_notional = required_dv01_change / per_m if per_m else 0.0
    after_gap = before_gap + signed_notional * per_m
    direction = "Receive fixed / pay floating" if signed_notional > 0 else "Pay fixed / receive floating"
    return {
        "instrument": instrument,
        "direction": direction,
        "notional_m": abs(signed_notional),
        "signed_notional_m": signed_notional,
        "hedge_ratio": hedge_ratio,
        "hedge_dv01_per_m": per_m,
        "before_gap": before_gap,
        "after_gap": after_gap,
    }


def rate_stress_pnl(dv01_gap: float, shock_bp: float) -> float:
    """First-order surplus P&L from an A-L DV01 gap under a parallel rate shock."""
    return -dv01_gap * shock_bp


def equity_hedge(equity_exposure: float, hedge_ratio: float, shock: float = -.20) -> dict[str, float]:
    hedge_ratio = min(max(float(hedge_ratio), 0.0), 1.0)
    hedge_notional = equity_exposure * hedge_ratio
    before = equity_exposure * shock
    after = (equity_exposure - hedge_notional) * shock
    return {"hedge_notional": hedge_notional, "stress_pnl_before": before, "stress_pnl_after": after, "pnl_improvement": after - before}


def fx_hedge(gross_fx_exposure: float, hedge_ratio: float, fx_shock: float = -.10) -> dict[str, float]:
    hedge_ratio = min(max(float(hedge_ratio), 0.0), 1.0)
    net_exposure = gross_fx_exposure * (1 - hedge_ratio)
    pnl_before = gross_fx_exposure * fx_shock
    pnl_after = net_exposure * fx_shock
    return {"gross_exposure": gross_fx_exposure, "net_exposure": net_exposure, "hedge_ratio": hedge_ratio,
            "stress_pnl_before": pnl_before, "stress_pnl_after": pnl_after, "pnl_improvement": pnl_after - pnl_before}
