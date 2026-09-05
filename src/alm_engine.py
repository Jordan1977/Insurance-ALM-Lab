"""Core economic ALM metrics and cash-flow matching."""
from __future__ import annotations

import numpy as np
import pandas as pd
from src.utils import maturity_bucket, BUCKET_ORDER


def economic_coverage_ratio(assets: float, liabilities: float) -> float:
    return assets / liabilities if liabilities else np.inf


def surplus(assets: float, liabilities: float) -> float:
    return assets - liabilities


def duration_gap(asset_duration: float, liability_duration: float) -> float:
    return asset_duration - liability_duration


def dv01_gap(asset_dv01: float, liability_dv01: float) -> float:
    return asset_dv01 - liability_dv01


def cash_flow_matching_table(asset_cf: pd.DataFrame, liability_cf: pd.DataFrame,
                             contractual_only: bool = True) -> pd.DataFrame:
    assets = asset_cf.copy()
    if contractual_only and "cf_type" in assets.columns:
        assets = assets[assets.cf_type.isin(["contractual", "contractual_liquidity"])]
    a = assets.groupby("year").cash_flow.sum().rename("asset_cf")
    l = liability_cf.groupby("year").cash_flow.sum().rename("liability_cf")
    table = pd.concat([a, l], axis=1).fillna(0).reset_index()
    table["coverage_ratio"] = np.where(table.liability_cf > 0, table.asset_cf / table.liability_cf, np.inf)
    table["gap"] = table.asset_cf - table.liability_cf
    table["cumulative_gap"] = table.gap.cumsum()
    table["shortfall"] = table.gap < 0
    return table


def maturity_bucket_matching(asset_cf: pd.DataFrame, liability_cf: pd.DataFrame,
                             contractual_only: bool = True) -> pd.DataFrame:
    assets = asset_cf.copy()
    if contractual_only and "cf_type" in assets.columns:
        assets = assets[assets.cf_type.isin(["contractual", "contractual_liquidity"])]
    assets["bucket"] = assets.year.apply(maturity_bucket)
    liabilities = liability_cf.copy()
    liabilities["bucket"] = liabilities.year.apply(maturity_bucket)
    a = assets.groupby("bucket").cash_flow.sum()
    l = liabilities.groupby("bucket").cash_flow.sum()
    out = pd.DataFrame(index=BUCKET_ORDER)
    out["asset_cash_flows"] = a.reindex(BUCKET_ORDER).fillna(0)
    out["liability_cash_flows"] = l.reindex(BUCKET_ORDER).fillna(0)
    out["gap"] = out.asset_cash_flows - out.liability_cash_flows
    out["coverage_ratio"] = np.where(out.liability_cash_flows > 0, out.asset_cash_flows / out.liability_cash_flows, np.inf)
    return out.reset_index(names="bucket")


def alm_kpis(total_assets: float, total_liabilities: float,
             asset_mod_dur: float, liability_mod_dur: float,
             asset_dv01: float, liability_dv01: float) -> dict[str, float]:
    return {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "surplus": surplus(total_assets, total_liabilities),
        "economic_coverage_ratio": economic_coverage_ratio(total_assets, total_liabilities),
        "asset_duration": asset_mod_dur,
        "liability_duration": liability_mod_dur,
        "duration_gap": duration_gap(asset_mod_dur, liability_mod_dur),
        "asset_dv01": asset_dv01,
        "liability_dv01": liability_dv01,
        "dv01_gap": dv01_gap(asset_dv01, liability_dv01),
    }
