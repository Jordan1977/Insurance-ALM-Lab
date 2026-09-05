"""Central data access for the ALM lab.

The financial engines do not depend on Streamlit, which keeps them testable from
pytest, notebooks and batch jobs. Streamlit caching is added only when the
package is available in the UI runtime.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

try:  # UI-only optional dependency
    import streamlit as st
    _cache = st.cache_data(show_spinner=False)
except ModuleNotFoundError:  # pytest / batch execution
    def _cache(func):
        return lru_cache(maxsize=None)(func)


def _path(name: str) -> Path:
    return DATA_DIR / name


@_cache
def load_asset_book_csv() -> pd.DataFrame:
    return pd.read_csv(_path("synthetic_assets.csv"))


@_cache
def load_instrument_book_csv() -> pd.DataFrame:
    return pd.read_csv(_path("synthetic_instrument_book.csv"))


@_cache
def load_liability_cf_csv() -> pd.DataFrame:
    return pd.read_csv(_path("synthetic_liabilities.csv"))


@_cache
def load_yield_curve_csv() -> pd.DataFrame:
    return pd.read_csv(_path("synthetic_yield_curve.csv"))


@_cache
def load_macro_data() -> pd.DataFrame:
    """Load the documented offline *synthetic* macro dataset.

    It intentionally remains separate from the synthetic insurer balance sheet.
    The file is a reproducible stand-in for a public-data feed and is never
    described as observed ECB or market history.
    """
    df = pd.read_csv(_path("macro_data.csv"), parse_dates=["date"])
    return df.sort_values("date").reset_index(drop=True)


def sync_snapshot_csvs(asset_df: pd.DataFrame, instrument_df: pd.DataFrame,
                        liability_cf_df: pd.DataFrame, curve_df: pd.DataFrame) -> None:
    """Regenerate frozen synthetic snapshots explicitly (never on UI reruns)."""
    asset_df.to_csv(_path("synthetic_assets.csv"), index=False)
    instrument_df.to_csv(_path("synthetic_instrument_book.csv"), index=False)
    liability_cf_df.to_csv(_path("synthetic_liabilities.csv"), index=False)
    curve_df.to_csv(_path("synthetic_yield_curve.csv"), index=False)


@_cache
def load_public_macro_snapshot() -> pd.DataFrame:
    """Load a small, dated PUBLIC macro snapshot used for recruiter-facing context.

    Unlike ``macro_data.csv`` (synthetic history), every row in this file carries
    an explicit source, observation date and download/as-of date. The app never
    blends these observations into the insurer calibration automatically; the
    user must deliberately translate them into assumptions/scenarios.
    """
    df = pd.read_csv(_path("public_macro_snapshot.csv"), parse_dates=["observation_date", "as_of_date"])
    return df.sort_values(["category", "series"]).reset_index(drop=True)
