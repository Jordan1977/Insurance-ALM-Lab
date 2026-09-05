"""Synthetic asset-cantonment optimisation by non-life liability family.

This is an analytical segregation exercise, not legal/accounting ring-fencing.
Every euro of synthetic assets is assigned exactly once. A linear programme
minimises duration mismatch while enforcing a family-level liquidity floor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from src.liability_model import build_liability_summary


def cantonment_analysis(asset_df: pd.DataFrame, discount_rate: float = .03,
                        claim_inflation: float = .025,
                        liquidity_target: float = 1.20) -> tuple[pd.DataFrame, pd.DataFrame]:
    liabilities = build_liability_summary(discount_rate, claim_inflation).reset_index(drop=True)
    assets = asset_df.reset_index(drop=True)
    n_a, n_l = len(assets), len(liabilities)
    total_assets = float(assets.market_value.sum())
    pool_targets = total_assets * (liabilities.present_value / liabilities.present_value.sum()).to_numpy()

    # Variables = x[i,j] allocations + positive/negative duration mismatch slacks per pool.
    n_x = n_a * n_l
    n_var = n_x + 2 * n_l
    c = np.zeros(n_var)
    # Small liquidity/quality compatibility cost avoids arbitrary equivalent optima.
    for i, a in assets.iterrows():
        for j, l in liabilities.iterrows():
            c[i*n_l+j] = .02 * (1-float(a.liquidity_score)) * (1 + 4*float(l.liquidity_need))
    c[n_x:] = 1.0  # primary objective: minimise absolute duration mismatch numerator

    A_eq, b_eq = [], []
    # Asset conservation.
    for i, a in assets.iterrows():
        row = np.zeros(n_var)
        row[i*n_l:(i+1)*n_l] = 1.0
        A_eq.append(row); b_eq.append(float(a.market_value))
    # Pool target and duration absolute-deviation equations.
    for j, l in liabilities.iterrows():
        row = np.zeros(n_var)
        for i in range(n_a): row[i*n_l+j] = 1.0
        A_eq.append(row); b_eq.append(float(pool_targets[j]))

        dur_row = np.zeros(n_var)
        for i, a in assets.iterrows(): dur_row[i*n_l+j] = float(a.modified_duration)
        dur_row[n_x + j] = -1.0                 # positive slack
        dur_row[n_x + n_l + j] = 1.0            # negative slack
        A_eq.append(dur_row); b_eq.append(float(pool_targets[j] * l.modified_duration))

    # Liquidity floor per pool: liquid allocated >= claims_12m * target.
    A_ub, b_ub = [], []
    liquid_mask = (assets.liquidity_score.to_numpy() >= .75).astype(float)
    for j, l in liabilities.iterrows():
        row = np.zeros(n_var)
        for i in range(n_a): row[i*n_l+j] = -liquid_mask[i]
        required = min(float(l.claims_12m) * liquidity_target, float(pool_targets[j]) * .95)
        A_ub.append(row); b_ub.append(-required)

    bounds = [(0, None)] * n_var
    result = linprog(c, A_ub=np.asarray(A_ub), b_ub=np.asarray(b_ub), A_eq=np.asarray(A_eq), b_eq=np.asarray(b_eq), bounds=bounds, method="highs")
    if not result.success:
        raise RuntimeError(f"Cantonment optimisation failed: {result.message}")
    x = result.x[:n_x].reshape(n_a, n_l)

    allocation_rows, summary_rows = [], []
    for j, l in liabilities.iterrows():
        amounts = x[:, j]
        assigned = float(amounts.sum())
        for i, a in assets.iterrows():
            if amounts[i] > 1e-8:
                allocation_rows.append({"family": l.family, "asset_class": a.asset_class, "amount": float(amounts[i]), "share_of_pool": float(amounts[i]/assigned)})
        asset_duration = float(np.average(assets.modified_duration, weights=amounts))
        liquid_assets = float(amounts[liquid_mask.astype(bool)].sum())
        summary_rows.append({
            "family": l.family,
            "assets_assigned": assigned,
            "liabilities_pv": float(l.present_value),
            "economic_coverage": assigned/float(l.present_value),
            "asset_duration": asset_duration,
            "liability_duration": float(l.modified_duration),
            "duration_gap": asset_duration-float(l.modified_duration),
            "liquidity_coverage_12m": liquid_assets/float(l.claims_12m),
        })
    return pd.DataFrame(summary_rows), pd.DataFrame(allocation_rows)
