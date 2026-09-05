from __future__ import annotations

import streamlit as st

from src.analytics import base_analytics, scenario_analytics
from src.asset_model import build_instrument_book
from src.formatting import fmt_eur_m, fmt_pct, fmt_years, fmt_ratio, fmt_signed_pct
from src.guidelines import check_compliance, overall_compliance, portfolio_guideline_metrics
from src.hedging_engine import rate_hedge
from src.liability_model import build_liability_cash_flows
from src.optimization import optimize_allocation
from src.reinvestment import annual_cash_projection
from src.reporting import build_html_report
from src.sensitivity import tornado_analysis, top_risk_drivers
from src.ui_helpers import page_header, metric_row

active_scenario = st.session_state.get("active_scenario", "Base")
page_header("Investment Committee Pack",
           "What does the committee need to see to decide what to review next?",
           scenario=active_scenario)
st.caption("Every figure below is read from the same engines used elsewhere in the app — nothing here is recomputed.")

base = base_analytics(
    st.session_state.get("asset_weights"),
    st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025),
    st.session_state.get("fx_hedge_ratio", .5),
)
stress = scenario_analytics(base, active_scenario, st.session_state.get("discount_rate", .03),
                            st.session_state.get("claim_inflation", .025), st.session_state.get("fx_hedge_ratio", .5))
limits = dict(
    equity_max=st.session_state.get("equity_max", .20), hy_max=st.session_state.get("hy_max", .10),
    illiquid_max=st.session_state.get("illiquid_max", .20), cash_min=st.session_state.get("cash_min", .05),
    duration_gap_tolerance=st.session_state.get("duration_gap_tolerance", 1.0),
    liquidity_target=st.session_state.get("liquidity_target", 1.5),
)
metrics = portfolio_guideline_metrics(base["assets"])
check = check_compliance(metrics, base["kpis"], base["liquidity_coverage"], limits)
status, breaches = overall_compliance(check)
reins = base["reinsurance"]
tornado = st.session_state.get("tornado_result") or tornado_analysis(
    base["assets"], st.session_state.get("discount_rate", .03),
    st.session_state.get("claim_inflation", .025), st.session_state.get("fx_hedge_ratio", .5))

# ---------------------------------------------------------------- A. Position
st.header("A. Position")
metric_row([
    ("Assets", fmt_eur_m(base["kpis"]["total_assets"]), None),
    ("Net Liabilities", fmt_eur_m(base["kpis"]["total_liabilities"]), None),
    ("Surplus", fmt_eur_m(base["kpis"]["surplus"]), None),
    ("Coverage", fmt_pct(base["kpis"]["economic_coverage_ratio"]), None),
])
metric_row([
    ("12M Liquidity", fmt_ratio(base["liquidity_coverage"]), None),
    ("Duration Gap", fmt_years(base["kpis"]["duration_gap"], signed=True), None),
])

# ---------------------------------------------------------------- B. Claims & Reinsurance
st.header("B. Claims & Reinsurance")
metric_row([
    ("Gross Claims 12M", fmt_eur_m(base["claims_12m_gross"]), None),
    ("Recoveries 12M", fmt_eur_m(reins["recoveries_12m"]), None),
    ("Net Claims 12M", fmt_eur_m(reins["claims_12m_net"]), None),
    ("Long-Tail Share", fmt_pct(base["liabilities_gross"]["long_tail_share"], 0), None),
])

# ---------------------------------------------------------------- C. Top risks
st.header("C. Top risks")
for line in top_risk_drivers(tornado, 3):
    st.write(f"• {line}")

# ---------------------------------------------------------------- D. Active scenario
st.header("D. Active scenario")
if active_scenario != "Base":
    metric_row([
        ("Δ Surplus", f"{stress['delta_surplus']:+,.0f}m EUR", None),
        ("Coverage After Stress", fmt_pct(stress["coverage"]), fmt_signed_pct(stress["coverage"] - base["kpis"]["economic_coverage_ratio"])),
    ])
else:
    st.write("Base case — no stress applied. Select a scenario on the Economic Scenarios page.")

# ---------------------------------------------------------------- E. Guidelines
st.header("E. Guidelines")
n_red, n_amber = int((check.status == "RED").sum()), int((check.status == "AMBER").sum())
(st.error if status == "NON-COMPLIANT" else st.success)(f"**{status}** — {n_red} breach(es), {n_amber} warning(s)" + (f": {', '.join(breaches)}" if breaches else "."))
worst = check.sort_values("headroom").iloc[0]
st.caption(f"Tightest headroom: **{worst.guideline}** ({worst.headroom:+.2f} vs. limit {worst.limit:.2f}).")

# ---------------------------------------------------------------- F. Strategy
st.header("F. Strategy")
weights, saa_metrics = optimize_allocation(
    base["assets"], base["corr"], base["liabilities"]["modified_duration"], mode="Liability-Aware",
    cash_min=st.session_state.get("cash_min", .05), cash_max=st.session_state.get("cash_max", .20),
    equity_max=limits["equity_max"], illiquid_max=limits["illiquid_max"], hy_max=limits["hy_max"],
    duration_gap_tolerance=limits["duration_gap_tolerance"], liquidity_target=limits["liquidity_target"],
    claims_12m=base["claims_12m"], total_assets=base["kpis"]["total_assets"],
    risk_free_rate=st.session_state.get("risk_free_rate", .025),
)
book = build_instrument_book(base["assets"])
gross_cf = build_liability_cash_flows(st.session_state.get("claim_inflation", .025))
ladder, _ = annual_cash_projection(book, gross_cf, "Liability-matching reinvestment",
                                   base["kpis"]["asset_duration"], base["liabilities"]["modified_duration"],
                                   base["treaty"], horizon=3)
H = rate_hedge(base["kpis"]["asset_dv01"], base["kpis"]["liability_dv01"])
if not saa_metrics["success"]:
    st.warning(f"Feasible SAA solution not found under current constraints ({saa_metrics['message']}) — "
              "the duration-gap figure below reflects the current book, not an optimised proposal.")
metric_row([
    ("SAA Duration Gap", fmt_years(saa_metrics["duration_gap"], signed=True), fmt_years(saa_metrics["duration_gap"] - base["kpis"]["duration_gap"], signed=True)),
    ("3Y Reinvested", fmt_eur_m(ladder.amount_reinvested.sum()), None),
    ("Hedge: DV01 Gap After", f"€{H['after_gap']:+.3f}m/bp", None),
])
st.caption(f"Liability-Aware SAA expected return {fmt_pct(saa_metrics['expected_return'], 2)}. "
           f"Full detail: Strategic Allocation, Reinvestment & Maturity Management, Hedging Lab pages.")

# ---------------------------------------------------------------- G. Watchpoints
st.header("G. Committee watchpoints")
st.caption("Key Watchpoint / Analytical Observation — never an investment recommendation.")


def _watchpoint(observation: str, why: str, analysis: str) -> str:
    return f"**{observation}** — {why} *Analysis to consider:* {analysis}"


candidates = []
if abs(base["kpis"]["duration_gap"]) > limits["duration_gap_tolerance"] * .5:
    candidates.append((abs(base["kpis"]["duration_gap"]), _watchpoint(
        f"Duration gap is {base['kpis']['duration_gap']:+.2f}y.",
        f"This is more than half of the ±{limits['duration_gap_tolerance']:.1f}y internal tolerance, so a parallel rate move has an asymmetric effect on assets vs. net liabilities.",
        "review a partial interest-rate hedge, or a liability-matching reinvestment tilt.")))
if metrics["equity_weight"] > limits["equity_max"] * .8:
    candidates.append((metrics["equity_weight"], _watchpoint(
        f"Equity allocation is {metrics['equity_weight']:.0%}.",
        f"This is approaching the {limits['equity_max']:.0%} internal limit, leaving limited headroom before a guideline breach.",
        "review the equity risk budget alongside the Liability-Aware SAA proposal.")))
top_driver = tornado.iloc[0]
candidates.append((abs(top_driver.surplus_impact) / max(base["kpis"]["surplus"], 1.0), _watchpoint(
    f"{top_driver.factor} is the largest isolated surplus sensitivity.",
    f"It moves economic surplus by {top_driver.surplus_impact:+,.0f}m EUR on its own, more than any other single factor tested.",
    "review the adequacy of reinsurance protection and short-term liquidity buffers for this specific risk.")))
if base["liquidity_coverage"] < limits["liquidity_target"] * 1.2:
    candidates.append((1.0 / max(base["liquidity_coverage"], .01), _watchpoint(
        f"12M liquidity coverage is {base['liquidity_coverage']:.2f}x.",
        f"This has limited headroom over the {limits['liquidity_target']:.2f}x internal target.",
        "review the liquidity buffer under a claims or forced-sale stress.")))
if status == "NON-COMPLIANT":
    candidates.append((10.0, _watchpoint("Current book is NON-COMPLIANT with Investment Guidelines.",
                                         f"Breached: {', '.join(breaches)}.",
                                         "review the breached constraint(s) before any further allocation change.")))
candidates.sort(key=lambda x: -x[0])
shown = [text for _, text in candidates[:5]] or [
    "No configured guideline is close to breach in the current base view; continue monitoring concentration and scenario risk."]
for item in shown:
    st.write(f"• {item}")

st.divider()
sections = [
    ("A. Position", [f"Assets {fmt_eur_m(base['kpis']['total_assets'])}, Net Liabilities {fmt_eur_m(base['kpis']['total_liabilities'])}, Surplus {fmt_eur_m(base['kpis']['surplus'])}, Coverage {fmt_pct(base['kpis']['economic_coverage_ratio'])}."]),
    ("B. Claims & Reinsurance", [f"Gross {fmt_eur_m(base['claims_12m_gross'])}, Recoveries {fmt_eur_m(reins['recoveries_12m'])}, Net {fmt_eur_m(reins['claims_12m_net'])} (12M)."]),
    ("C. Top Risks", top_risk_drivers(tornado, 3)),
    ("D. Active Scenario", [f"{active_scenario}: Δ Surplus {stress['delta_surplus']:+,.0f}m EUR." if active_scenario != "Base" else "Base case."]),
    ("E. Guidelines", [f"{status}" + (f" — {', '.join(breaches)}" if breaches else "")]),
    ("F. Strategy", [f"SAA duration gap {fmt_years(saa_metrics['duration_gap'], signed=True)} vs current {fmt_years(base['kpis']['duration_gap'], signed=True)}."]),
    ("G. Committee Watchpoints", shown),
]
html = build_html_report(f"Investment Committee Pack — Scenario: {active_scenario}", sections)
st.download_button("Download Committee Pack (.html)", html, file_name="investment_committee_pack.html", mime="text/html")
st.caption("Synthetic data disclaimer: all figures above are generated from an independent educational prototype "
           "and do not represent Thélem assurances or any other institution.")
