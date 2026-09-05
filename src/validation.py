"""Data-quality checks for frozen synthetic snapshots."""
from __future__ import annotations

import numpy as np
import pandas as pd

KNOWN_RATINGS = {"AAA", "AA", "AA-", "A", "BBB", "BB", "NR"}
KNOWN_CURRENCIES = {"EUR", "USD", "Mixed"}


def _check(label: str, ok: bool, detail: str) -> dict:
    return {"check": label, "status": "PASS" if ok else "FAIL", "detail": detail}


def validate_asset_book(df: pd.DataFrame) -> list[dict]:
    checks = []
    weight_sum = float(df["weight"].sum())
    checks.append(_check("Weights sum to 100%", abs(weight_sum - 1.0) < 1e-6, f"Σweights = {weight_sum:.6f}"))
    checks.append(_check("No missing values", int(df.isna().sum().sum()) == 0, f"{int(df.isna().sum().sum())} missing cell(s)"))
    checks.append(_check("No duplicate asset classes", not df["asset_class"].duplicated().any(), "Unique strategic classes"))
    checks.append(_check("No negative market values", bool((df.market_value >= 0).all()), "All MV >= 0"))
    checks.append(_check("No negative duration", bool((df.duration >= 0).all()), "All duration >= 0"))
    bad_rating = sorted(set(df.rating) - KNOWN_RATINGS)
    checks.append(_check("Ratings within known scale", not bad_rating, f"Unknown ratings: {bad_rating}" if bad_rating else "All ratings recognised"))
    bad_ccy = sorted(set(df.currency) - KNOWN_CURRENCIES)
    checks.append(_check("Currencies within known set", not bad_ccy, f"Unknown currencies: {bad_ccy}" if bad_ccy else "All currencies recognised"))
    return checks


def validate_instrument_book(df: pd.DataFrame, asset_df: pd.DataFrame | None = None) -> list[dict]:
    checks = []
    checks.append(_check("No negative instrument market values", bool((df.market_value >= 0).all()), "All instrument MV >= 0"))
    checks.append(_check("Instrument IDs unique", bool(df.instrument_id.is_unique), "All instrument IDs unique"))
    maturity = df.maturity_years.dropna()
    checks.append(_check("Maturities within plausible range", bool(((maturity > 0) & (maturity <= 40)).all()), "0 < maturity <= 40y"))
    bond_mask = df.instrument_type.isin(["Bond", "Private debt"])
    checks.append(_check("Contractual assets have positive face value", bool((df.loc[bond_mask, "face_value"] > 0).all()), "All bond/private-debt notionals positive"))
    checks.append(_check("Contractual assets have maturities", bool(df.loc[bond_mask, "maturity_years"].notna().all()), "No missing contractual maturity"))
    if asset_df is not None:
        by_class_i = df.groupby("asset_class").market_value.sum().sort_index()
        by_class_a = asset_df.set_index("asset_class").market_value.sort_index()
        aligned = by_class_i.reindex(by_class_a.index).fillna(0)
        max_diff = float((aligned - by_class_a).abs().max())
        checks.append(_check("Instrument book reconciles to strategic book", max_diff < 1e-5, f"Max class MV difference = €{max_diff:.6f}m"))
    return checks


def validate_liability_cash_flows(df: pd.DataFrame) -> list[dict]:
    checks = []
    checks.append(_check("Liability cash flows non-negative", bool((df.cash_flow >= 0).all()), "All projected claims >= 0"))
    checks.append(_check("No missing liability values", int(df.isna().sum().sum()) == 0, f"{int(df.isna().sum().sum())} missing cell(s)"))
    if "payout_weight" in df.columns:
        sums = df.groupby("family").payout_weight.sum()
        max_error = float((sums - 1.0).abs().max())
        checks.append(_check("Payout weights sum to 100% by family", max_error < 1e-6, f"Max payout error = {max_error:.2e}"))
    base_totals = df.groupby("family").base_cash_flow.sum()
    checks.append(_check("Every family has positive base claims", bool((base_totals > 0).all()), "All family base claims > 0"))
    return checks


def validate_yield_curve(df: pd.DataFrame) -> list[dict]:
    checks = []
    checks.append(_check("Spot rates above -2% floor", bool((df.spot_rate >= -.02).all()), "All rates >= -2%"))
    years = df.year.to_numpy()
    strictly_increasing = bool(np.all(np.diff(years) > 0))
    checks.append(_check("Tenors strictly increasing and unique", strictly_increasing, "Strict tenor ordering" if strictly_increasing else "Duplicate or non-increasing tenor"))
    return checks


def full_data_quality_report(asset_df: pd.DataFrame, instrument_df: pd.DataFrame,
                             liability_cf_df: pd.DataFrame, curve_df: pd.DataFrame) -> pd.DataFrame:
    rows = validate_asset_book(asset_df) + validate_instrument_book(instrument_df, asset_df) + validate_liability_cash_flows(liability_cf_df) + validate_yield_curve(curve_df)
    return pd.DataFrame(rows)


def overall_status(report: pd.DataFrame) -> str:
    return "PASS" if (report.status == "PASS").all() else "FAIL"
