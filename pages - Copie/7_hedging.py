from __future__ import annotations

import streamlit as st

from src.analytics import base_analytics
from src.asset_model import EQUITY_CLASSES, fx_exposure
from src.formatting import fmt_eur_m, fmt_dv01
from src.hedging_engine import HEDGE_INSTRUMENTS, equity_hedge, fx_hedge, rate_hedge, rate_stress_pnl
from src.ui_helpers import page_header, metric_row

page_header("Illustrative Hedging Lab",
           "How much notional is needed to close the rate, equity or FX gap, and in which direction?")
st.caption("First-order hedge sizing to demonstrate risk mechanics. No derivative pricing, basis, collateral, "
          "accounting or transaction costs.")

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)

tab_rate, tab_equity, tab_fx = st.tabs(["Interest-Rate Risk", "Equity Risk", "FX Risk"])

with tab_rate:
    controls = st.columns(2)
    instrument = controls[0].selectbox("Synthetic hedge instrument", list(HEDGE_INSTRUMENTS))
    hedge_ratio = controls[1].slider("Share of DV01 gap hedged", 0.0, 1.0, .75, .05)
    H = rate_hedge(base["kpis"]["asset_dv01"], base["kpis"]["liability_dv01"], instrument, hedge_ratio)
    metric_row([
        ("DV01 Gap Before", fmt_dv01(H["before_gap"]), None),
        ("Illustrative Notional", fmt_eur_m(H["notional_m"]), None),
        ("DV01 Gap After", fmt_dv01(H["after_gap"]), None),
    ])
    st.write(f"**Overlay direction:** {H['direction']}")
    shock_bp = st.select_slider("Parallel rate stress", options=[-200, -100, -50, 50, 100, 200], value=100)
    p1 = rate_stress_pnl(H["before_gap"], shock_bp)
    p2 = rate_stress_pnl(H["after_gap"], shock_bp)
    metric_row([
        ("Stress P&L Before Hedge", fmt_eur_m(p1), None),
        ("Stress P&L After Hedge", fmt_eur_m(p2), fmt_eur_m(p2 - p1)),
    ])

with tab_equity:
    equity_exposure = float(base["assets"].loc[base["assets"].asset_class.isin(EQUITY_CLASSES), "market_value"].sum())
    controls = st.columns(2)
    eq_ratio = controls[0].slider("Equity hedge ratio", 0.0, 1.0, .50, .05)
    eq_shock = controls[1].select_slider("Equity stress", options=[-.40, -.30, -.20, -.10], value=-.30, format_func=lambda x: f"{x:.0%}")
    E = equity_hedge(equity_exposure, eq_ratio, eq_shock)
    metric_row([
        ("Equity Exposure", fmt_eur_m(equity_exposure), None),
        ("Futures-Proxy Notional", fmt_eur_m(E["hedge_notional"]), None),
        ("Stress P&L Before", fmt_eur_m(E["stress_pnl_before"]), None),
        ("Stress P&L After", fmt_eur_m(E["stress_pnl_after"]), None),
    ])

with tab_fx:
    FX0 = fx_exposure(base["assets"], 0.0)
    controls = st.columns(2)
    fx_ratio = controls[0].slider("FX hedge ratio", 0.0, 1.0, st.session_state.get("fx_hedge_ratio", .5), .05)
    fx_shock = controls[1].select_slider("Foreign-currency move vs EUR", options=[-.15, -.10, -.05, .05, .10, .15], value=-.10, format_func=lambda x: f"{x:+.0%}")
    FX = fx_hedge(FX0["gross_fx_exposure"], fx_ratio, fx_shock)
    metric_row([
        ("Gross FX Exposure", fmt_eur_m(FX["gross_exposure"]), None),
        ("Net FX Exposure", fmt_eur_m(FX["net_exposure"]), None),
        ("Stress P&L Before", fmt_eur_m(FX["stress_pnl_before"]), None),
        ("Stress P&L After", fmt_eur_m(FX["stress_pnl_after"]), None),
    ])
