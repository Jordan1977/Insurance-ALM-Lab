"""Strategic asset-allocation optimisation with explicit ALM constraints."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.asset_model import EQUITY_CLASSES, ILLIQUID_CLASSES


def optimize_allocation(asset_df: pd.DataFrame, corr: pd.DataFrame,
                        liability_duration: float,
                        mode: str = "Liability-Aware",
                        cash_min: float = .05,
                        equity_max: float = .20,
                        illiquid_max: float = .20,
                        hy_max: float = .10,
                        duration_gap_tolerance: float = 1.0,
                        liquidity_target: float = 1.5,
                        claims_12m: float | None = None,
                        total_assets: float | None = None,
                        cash_max: float = .20,
                        risk_free_rate: float = .025) -> tuple[pd.DataFrame, dict]:
    """Optimise strategic weights while respecting liabilities and liquidity.

    Liability-Aware minimises a transparent return/risk/duration objective and,
    unlike the earlier prototype, enforces duration-gap and 12M-liquidity
    constraints directly.
    """
    n = len(asset_df)
    mu = asset_df.expected_return.to_numpy(float)
    sig = asset_df.volatility.to_numpy(float)
    cov = np.outer(sig, sig) * corr.to_numpy(float)
    dur = asset_df.modified_duration.to_numpy(float)
    liquidity = asset_df.liquidity_score.to_numpy(float)
    classes = asset_df.asset_class.tolist()
    eq = np.array([c in EQUITY_CLASSES for c in classes], dtype=float)
    ill = np.array([c in ILLIQUID_CLASSES for c in classes], dtype=float)
    cash = np.array([c == "Cash / Money Market" for c in classes], dtype=float)
    hy = np.array([c == "High Yield Bonds" for c in classes], dtype=float)
    liquid = np.array([q >= .75 for q in liquidity], dtype=float)
    total_assets = float(total_assets or asset_df.market_value.sum())
    required_liquid_weight = 0.0 if not claims_12m else min(float(claims_12m) * liquidity_target / total_assets, .95)

    def port_vol(w: np.ndarray) -> float:
        return float(np.sqrt(max(w @ cov @ w, 0.0)))

    def port_return(w: np.ndarray) -> float:
        return float(w @ mu)

    def objective(w: np.ndarray) -> float:
        v = port_vol(w)
        r = port_return(w)
        if mode == "Min Vol":
            return v
        if mode == "Max Sharpe":
            return -(r - risk_free_rate) / max(v, 1e-9)
        # Scale components so no single unit dominates silently.
        duration_mismatch = abs(float(w @ dur) - liability_duration)
        return -(r - risk_free_rate) + 0.30 * v + 0.015 * duration_mismatch

    constraints = [
        {"type": "eq", "fun": lambda w: w.sum() - 1.0},
        {"type": "ineq", "fun": lambda w: w @ cash - cash_min},
        {"type": "ineq", "fun": lambda w: cash_max - w @ cash},
        {"type": "ineq", "fun": lambda w: equity_max - w @ eq},
        {"type": "ineq", "fun": lambda w: illiquid_max - w @ ill},
        {"type": "ineq", "fun": lambda w: hy_max - w @ hy},
        {"type": "ineq", "fun": lambda w: duration_gap_tolerance - (w @ dur - liability_duration)},
        {"type": "ineq", "fun": lambda w: duration_gap_tolerance + (w @ dur - liability_duration)},
        {"type": "ineq", "fun": lambda w: w @ liquid - required_liquid_weight},
    ]
    bounds = [(0.0, .45)] * n
    start = asset_df.weight.to_numpy(float)
    result = minimize(objective, start, bounds=bounds, constraints=constraints, method="SLSQP", options={"maxiter": 2000, "ftol": 1e-10})
    weights = result.x if result.success else start
    asset_duration = float(weights @ dur)
    liquid_weight = float(weights @ liquid)
    liquidity_coverage = (liquid_weight * total_assets / claims_12m) if claims_12m else np.inf
    output = pd.DataFrame({"asset_class": classes, "current_weight": start, "optimized_weight": weights})
    metrics = {
        "expected_return": port_return(weights),
        "volatility": port_vol(weights),
        "sharpe": (port_return(weights) - risk_free_rate) / max(port_vol(weights), 1e-9),
        "asset_duration": asset_duration,
        "duration_gap": asset_duration - liability_duration,
        "liquid_weight": liquid_weight,
        "liquidity_coverage": liquidity_coverage,
        "success": bool(result.success),
        "message": str(result.message),
    }
    return output, metrics
