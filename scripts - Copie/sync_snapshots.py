"""Regenerate frozen synthetic CSV snapshots after engine assumption changes."""
from src.asset_model import build_asset_portfolio, build_instrument_book
from src.liability_model import build_liability_cash_flows, discount_curve
from src.data_loader import sync_snapshot_csvs

if __name__ == "__main__":
    assets = build_asset_portfolio()
    instruments = build_instrument_book(assets)
    liabilities = build_liability_cash_flows()
    curve = discount_curve()
    sync_snapshot_csvs(assets, instruments, liabilities, curve)
    print("Synthetic snapshots updated.")
