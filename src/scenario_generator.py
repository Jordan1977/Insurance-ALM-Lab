"""Deterministic and stochastic ALM scenario engine."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.asset_model import EQUITY_CLASSES, CREDIT_CLASSES, RATE_CLASSES, fx_exposure
from src.liability_model import LIABILITY_FAMILIES

DETERMINISTIC_SCENARIOS = {
    "Base": dict(d_rate=0., equity_shock=0., credit_spread_shock=0., inflation_shock=0., fx_shock=0.),
    "Rates +100bp": dict(d_rate=.01, equity_shock=0., credit_spread_shock=0., inflation_shock=0., fx_shock=0.),
    "Rates +200bp": dict(d_rate=.02, equity_shock=0., credit_spread_shock=0., inflation_shock=0., fx_shock=0.),
    "Rates -100bp": dict(d_rate=-.01, equity_shock=0., credit_spread_shock=0., inflation_shock=0., fx_shock=0.),
    "Equity -20%": dict(d_rate=0., equity_shock=-.20, credit_spread_shock=0., inflation_shock=0., fx_shock=0.),
    "Equity -30%": dict(d_rate=0., equity_shock=-.30, credit_spread_shock=.005, inflation_shock=0., fx_shock=-.05),
    "Credit Spreads +100bp": dict(d_rate=0., equity_shock=-.05, credit_spread_shock=.01, inflation_shock=0., fx_shock=0.),
    "Inflation +2%": dict(d_rate=.005, equity_shock=0., credit_spread_shock=0., inflation_shock=.02, fx_shock=0.),
    "Stagflation": dict(d_rate=.012, equity_shock=-.15, credit_spread_shock=.008, inflation_shock=.02, fx_shock=-.05),
    "Recession": dict(d_rate=-.015, equity_shock=-.25, credit_spread_shock=.012, inflation_shock=-.005, fx_shock=.05),
    "Risk-on": dict(d_rate=.003, equity_shock=.12, credit_spread_shock=-.003, inflation_shock=.003, fx_shock=.03),
    "Liquidity / Claims Stress": dict(d_rate=.005, equity_shock=-.10, credit_spread_shock=.006, inflation_shock=.015, fx_shock=-.03),
}


def deterministic_asset_attribution(df: pd.DataFrame, name_or_shock: str | dict, fx_hedge_ratio: float = 0.0) -> pd.DataFrame:
    """Break deterministic asset P&L into rate, spread, equity/real-asset and FX channels.

    `name_or_shock` is either a key into DETERMINISTIC_SCENARIOS, or a raw shock
    dict (used by the Sensitivity / Tornado module to isolate a single factor
    without duplicating this formula -- see src/sensitivity.py). An optional
    `real_estate_shock` key isolates real assets from the equity shock; if
    absent, real assets keep the original behaviour of moving at 0.5x the
    equity shock (unchanged for every named scenario).
    """
    raw = DETERMINISTIC_SCENARIOS[name_or_shock] if isinstance(name_or_shock, str) else name_or_shock
    s = {"d_rate": 0.0, "equity_shock": 0.0, "credit_spread_shock": 0.0, "inflation_shock": 0.0, "fx_shock": 0.0, **raw}
    rows = []
    for _, r in df.iterrows():
        mv = float(r.market_value)
        rate = (-float(r.modified_duration) * s["d_rate"] + .5 * float(r.convexity) * s["d_rate"]**2) * mv if r.asset_class in RATE_CLASSES else 0.0
        spread = -float(r.spread_duration) * s["credit_spread_shock"] * mv if r.asset_class in CREDIT_CLASSES else 0.0
        if r.asset_class in EQUITY_CLASSES:
            equity = mv * s["equity_shock"]
        elif r.asset_class in {"Real Estate", "Infrastructure"}:
            real_estate_shock = s.get("real_estate_shock", .5 * s["equity_shock"])
            equity = mv * real_estate_shock
        else:
            equity = 0.0
        fx = 0.0
        if r.currency == "USD":
            fx = mv * s["fx_shock"] * (1 - fx_hedge_ratio)
        elif r.currency == "Mixed":
            fx = mv * .5 * s["fx_shock"] * (1 - fx_hedge_ratio)
        rows.append({"asset_class": r.asset_class, "rate_pnl": rate, "spread_pnl": spread, "equity_real_pnl": equity, "fx_pnl": fx})
    return pd.DataFrame(rows)


def apply_deterministic_scenario(df: pd.DataFrame, name_or_shock: str | dict, fx_hedge_ratio: float = 0.0) -> pd.DataFrame:
    attribution = deterministic_asset_attribution(df, name_or_shock, fx_hedge_ratio)
    out = df.copy().reset_index(drop=True)
    out = pd.concat([out, attribution.drop(columns="asset_class")], axis=1)
    out["pnl"] = out[["rate_pnl", "spread_pnl", "equity_real_pnl", "fx_pnl"]].sum(axis=1)
    out["market_value_stressed"] = np.maximum(out.market_value + out.pnl, 0.0)
    return out


def scenario_discount_rate(base: float, name: str) -> float:
    return base + DETERMINISTIC_SCENARIOS[name]["d_rate"]


def scenario_claim_inflation(base: float, name: str) -> float:
    return max(base + DETERMINISTIC_SCENARIOS[name]["inflation_shock"], -.02)


# Factors: equity return, short-rate innovation, inflation, credit-spread change, FX return.
DEFAULT_FACTOR_CORR = np.array([
    [1.00, -.20, .10, -.35, .15],
    [-.20, 1.00, .40, -.10, -.10],
    [.10, .40, 1.00, .05, -.05],
    [-.35, -.10, .05, 1.00, -.10],
    [.15, -.10, -.05, -.10, 1.00],
])


def _nearest_psd_correlation(corr: np.ndarray) -> np.ndarray:
    corr = np.asarray(corr, dtype=float)
    eigval, eigvec = np.linalg.eigh((corr + corr.T) / 2)
    eigval = np.clip(eigval, 1e-8, None)
    m = eigvec @ np.diag(eigval) @ eigvec.T
    d = np.sqrt(np.diag(m))
    return m / np.outer(d, d)


def _correlated_normals(n: int, h: int, corr: np.ndarray, seed: int) -> np.ndarray:
    corr = _nearest_psd_correlation(corr)
    rng = np.random.default_rng(seed)
    L = np.linalg.cholesky(corr)
    return rng.standard_normal((n, h, len(corr))) @ L.T


def run_monte_carlo(n_sims: int = 1000, horizon: int = 10,
                    equity_mu: float = .07, equity_sigma: float = .17,
                    r0: float = .03, rate_mean_rev_speed: float = .15,
                    rate_long_term: float = .03, rate_sigma: float = .01,
                    infl0: float = .025, infl_long_term: float = .02,
                    infl_ar1: float = .6, infl_sigma: float = .008,
                    spread0: float = .01, spread_long_term: float = .01,
                    spread_mean_rev_speed: float = .25, spread_sigma: float = .006,
                    fx_mu: float = 0.0, fx_sigma: float = .10,
                    claim_severity_sigma: float = .12,
                    corr: np.ndarray | None = None, seed: int = 123) -> dict[str, np.ndarray]:
    """Generate transparent stochastic market and non-life claims factors.

    Claim frequency is now simulated explicitly by family from a Poisson model
    around each branch's expected claim count. Severity remains an aggregate
    lognormal multiplier. Frequency is deliberately independent of market
    factors in this educational prototype; catastrophe dependence is handled
    through deterministic large-loss stresses rather than hidden correlation.
    """
    corr = DEFAULT_FACTOR_CORR if corr is None else corr
    z = _correlated_normals(n_sims, horizon, corr, seed)
    eqz, rz, iz, sz, fxz = [z[..., i] for i in range(5)]
    logret = (equity_mu - .5 * equity_sigma**2) + equity_sigma * eqz
    equity_growth = np.exp(logret)
    equity_returns = equity_growth - 1
    fx_logret = (fx_mu - .5 * fx_sigma**2) + fx_sigma * fxz
    fx_returns = np.exp(fx_logret) - 1

    # Real assets: moderate return/volatility, explicitly correlated to equities
    # without expanding the documented 5x5 market-factor correlation matrix.
    real_rng = np.random.default_rng(seed + 8_003)
    real_idio = real_rng.standard_normal((n_sims, horizon))
    real_z = .60 * eqz + np.sqrt(1 - .60**2) * real_idio
    real_sigma, real_mu = .08, .045
    real_returns = np.exp((real_mu - .5 * real_sigma**2) + real_sigma * real_z) - 1

    severity_rng = np.random.default_rng(seed + 10_007)
    severity_z = severity_rng.standard_normal((n_sims, horizon))
    claim_severity_multiplier = np.exp(-.5 * claim_severity_sigma**2 + claim_severity_sigma * severity_z)

    from src.liability_model import expected_claim_count
    fams = list(LIABILITY_FAMILIES)
    expected_counts = np.array([expected_claim_count(LIABILITY_FAMILIES[f]) for f in fams], dtype=float)
    freq_rng = np.random.default_rng(seed + 20_011)
    sampled_counts = freq_rng.poisson(expected_counts[None, None, :], size=(n_sims, horizon, len(fams)))
    claim_frequency_multiplier = sampled_counts / expected_counts[None, None, :]

    rates = np.zeros((n_sims, horizon))
    inflation = np.zeros_like(rates)
    spreads = np.zeros_like(rates)
    rp = np.full(n_sims, r0)
    ip = np.full(n_sims, infl0)
    sp = np.full(n_sims, spread0)
    for t in range(horizon):
        rp = rp + rate_mean_rev_speed * (rate_long_term - rp) + rate_sigma * rz[:, t]
        rates[:, t] = np.maximum(rp, -.01)
        ip = infl_long_term + infl_ar1 * (ip - infl_long_term) + infl_sigma * iz[:, t]
        inflation[:, t] = np.maximum(ip, -.03)
        sp = sp + spread_mean_rev_speed * (spread_long_term - sp) + spread_sigma * sz[:, t]
        spreads[:, t] = np.maximum(sp, 0.)
    return {
        "equity_returns": equity_returns,
        "real_asset_returns": real_returns,
        "cumulative_equity_return": np.cumprod(equity_growth, axis=1) - 1,
        "rates": rates,
        "inflation": inflation,
        "credit_spreads": spreads,
        "fx_returns": fx_returns,
        "claim_severity_multiplier": claim_severity_multiplier,
        "claim_frequency_multiplier": claim_frequency_multiplier,
    }


def _apply_claim_cash_flow_to_assets(values: np.ndarray, amount: np.ndarray, cash_mask: np.ndarray) -> np.ndarray:
    """Apply annual claim/recovery cash flow to simulated asset rows.

    Positive ``amount`` is an outflow: use Cash / Money Market first, then sell
    remaining assets pro-rata. Negative ``amount`` is an inflow: add it to cash.
    This keeps the stochastic projection self-financing without pretending to
    model transaction costs or a detailed forced-sale policy.
    """
    out = values.copy()
    cash_idx = np.where(cash_mask)[0]
    if len(cash_idx) != 1:
        raise ValueError("Expected exactly one Cash / Money Market row in the strategic asset book.")
    c = cash_idx[0]
    inflow = np.maximum(-amount, 0.0)
    out[:, c] += inflow
    remaining = np.maximum(amount, 0.0)
    from_cash = np.minimum(out[:, c], remaining)
    out[:, c] -= from_cash
    remaining -= from_cash
    noncash = ~cash_mask
    total_non_cash = out[:, noncash].sum(axis=1)
    scale = np.where(total_non_cash > 0, np.maximum(1.0 - remaining / total_non_cash, 0.0), 0.0)
    out[:, noncash] *= scale[:, None]
    return np.maximum(out, 0.0)


def surplus_distribution_from_mc(mc: dict[str, np.ndarray], asset_df: pd.DataFrame,
                                  base_discount_rate: float = .03,
                                  base_claim_inflation: float = .025,
                                  horizon_year: int = 5,
                                  fx_hedge_ratio: float = .5,
                                  treaty=None) -> pd.DataFrame:
    """Dynamic closed-book ALM projection with instrument-class exposure updates.

    Improvements over V6:
    * market values evolve row by row rather than scaling every exposure with a
      single total-asset ratio;
    * claim frequency is simulated explicitly by non-life family;
    * claims are paid gross while reinsurance recoveries arrive with the treaty
      lag, preserving the liquidity distinction between ultimate net cost and
      interim cash need;
    * remaining liabilities use net-of-reinsurance claim amounts, consistent
      with the central economic balance sheet.

    No future premiums, taxes, capital model, collateral or management-action
    optimisation are modelled.
    """
    from src.liability_model import expected_gross_claims
    from src.reinsurance import DEFAULT_TREATY
    treaty = DEFAULT_TREATY if treaty is None else treaty

    n = mc["rates"].shape[0]
    h = min(horizon_year, mc["rates"].shape[1])
    fams = list(LIABILITY_FAMILIES)
    sensitivities = np.array([LIABILITY_FAMILIES[f]["inflation_sensitivity"] for f in fams])
    payouts = np.array([expected_gross_claims(LIABILITY_FAMILIES[f]) * np.asarray(LIABILITY_FAMILIES[f]["payout"], dtype=float) for f in fams])
    payouts = payouts / np.array([np.asarray(LIABILITY_FAMILIES[f]["payout"], dtype=float).sum() for f in fams])[:, None]

    gross_path_claims = np.zeros((n, 10))
    cumulative = np.ones((n, len(fams)))
    for t in range(10):
        inflation_t = mc["inflation"][:, min(t, h - 1)] if h else np.full(n, .025)
        family_claim_inflation = base_claim_inflation + (inflation_t[:, None] - .025) * sensitivities[None, :]
        family_claim_inflation = np.maximum(family_claim_inflation, -.05)
        cumulative *= 1 + family_claim_inflation
        fam_cf = cumulative * payouts[:, t][None, :]
        if t < h:
            if "claim_frequency_multiplier" in mc:
                fam_cf *= mc["claim_frequency_multiplier"][:, t, :]
            if "claim_severity_multiplier" in mc:
                fam_cf *= mc["claim_severity_multiplier"][:, t, None]
        gross_path_claims[:, t] = fam_cf.sum(axis=1)

    recoverable_layer = np.clip(gross_path_claims - treaty.retention, 0.0, treaty.limit)
    effective_recoveries = recoverable_layer * treaty.recovery_rate * (1 - treaty.counterparty_haircut)
    net_path_claims = gross_path_claims - effective_recoveries

    # Recovery cash is shifted by the treaty lag for liquidity/asset evolution.
    recovery_received = np.zeros_like(effective_recoveries)
    lag = int(treaty.recovery_lag)
    if lag == 0:
        recovery_received[:] = effective_recoveries
    elif lag < recovery_received.shape[1]:
        recovery_received[:, lag:] = effective_recoveries[:, :-lag]

    values = np.tile(asset_df.market_value.to_numpy(dtype=float), (n, 1))
    classes = asset_df.asset_class.astype(str).to_numpy()
    rate_mask = np.isin(classes, list(RATE_CLASSES))
    credit_mask = np.isin(classes, list(CREDIT_CLASSES))
    equity_mask = np.isin(classes, list(EQUITY_CLASSES))
    real_mask = np.isin(classes, ["Real Estate", "Infrastructure"])
    cash_mask = classes == "Cash / Money Market"
    currencies = asset_df.currency.astype(str).to_numpy()
    usd_share = np.where(currencies == "USD", 1.0, np.where(currencies == "Mixed", .5, 0.0))
    durations = asset_df.modified_duration.to_numpy(dtype=float)
    convexities = asset_df.convexity.to_numpy(dtype=float)
    spread_durations = asset_df.spread_duration.to_numpy(dtype=float)
    yields = asset_df["yield"].to_numpy(dtype=float)

    claims_paid = np.zeros(n)
    recoveries_received_total = np.zeros(n)
    prev_rate = np.full(n, base_discount_rate)
    prev_spread = np.full(n, .01)
    minimum_liquidity_buffer = np.full(n, np.inf)
    forced_sale_amount = np.zeros(n)
    liquidity_shortfall_flag = np.zeros(n, dtype=bool)

    for t in range(h):
        d_rate = mc["rates"][:, t] - prev_rate
        d_spread = mc["credit_spreads"][:, t] - prev_spread
        ret = np.broadcast_to(yields, values.shape).copy()
        ret[:, rate_mask] += (-durations[rate_mask][None, :] * d_rate[:, None]
                              + .5 * convexities[rate_mask][None, :] * d_rate[:, None]**2)
        ret[:, credit_mask] += -spread_durations[credit_mask][None, :] * d_spread[:, None]
        ret[:, equity_mask] += mc["equity_returns"][:, t, None]
        ret[:, real_mask] += mc.get("real_asset_returns", .5 * mc["equity_returns"])[:, t, None]
        ret += usd_share[None, :] * (1 - fx_hedge_ratio) * mc["fx_returns"][:, t, None]
        values = np.maximum(values * (1 + ret), 0.0)

        net_cash_outflow = gross_path_claims[:, t] - recovery_received[:, t]
        cash_before_claims = values[:, cash_mask].sum(axis=1)
        forced_this_year = np.maximum(net_cash_outflow - cash_before_claims, 0.0)
        forced_sale_amount += forced_this_year
        liquidity_shortfall_flag |= forced_this_year > 1e-9
        values = _apply_claim_cash_flow_to_assets(values, net_cash_outflow, cash_mask)
        claims_paid += gross_path_claims[:, t]
        recoveries_received_total += recovery_received[:, t]
        minimum_liquidity_buffer = np.minimum(minimum_liquidity_buffer, values[:, cash_mask].sum(axis=1))
        prev_rate = mc["rates"][:, t]
        prev_spread = mc["credit_spreads"][:, t]

    assets = values.sum(axis=1)
    remaining_years = np.arange(1, 10 - h + 1)
    if len(remaining_years):
        liabilities = (net_path_claims[:, h:] / (1 + mc["rates"][:, h - 1, None]) ** remaining_years[None, :]).sum(axis=1)
    else:
        liabilities = np.zeros(n)
    economic_surplus = assets - liabilities
    coverage = np.where(liabilities > 0, assets / liabilities, np.inf)
    return pd.DataFrame({
        "simulated_assets": assets,
        "simulated_liabilities": liabilities,
        "surplus": economic_surplus,
        "economic_coverage_ratio": coverage,
        "gross_claims_paid": claims_paid,
        "reinsurance_recoveries_received": recoveries_received_total,
        "claims_paid": claims_paid - recoveries_received_total,
        "minimum_cash_buffer": minimum_liquidity_buffer,
        "forced_sale_amount": forced_sale_amount,
        "liquidity_shortfall_flag": liquidity_shortfall_flag,
    })

def evaluate_deterministic_scenario(asset_df: pd.DataFrame, name_or_shock: str | dict,
                                    base_discount_rate: float = .03,
                                    base_claim_inflation: float = .025,
                                    fx_hedge_ratio: float = .5,
                                    extra_claim_inflation: float = 0.0,
                                    severity_shock: float = 0.0,
                                    frequency_shock: float = 0.0,
                                    label: str | None = None,
                                    treaty=None) -> dict:
    """Evaluate a scenario on both sides of the synthetic economic balance sheet.

    `name_or_shock` is either a DETERMINISTIC_SCENARIOS key (unchanged path, used
    by the Economic Scenarios / Stress Testing / Macro Transmission pages) or a
    raw shock dict (used by the Sensitivity / Tornado module -- src/sensitivity.py
    -- to isolate one factor at a time without a second, duplicated formula).
    `extra_claim_inflation`, `severity_shock` and `frequency_shock` add
    liability-side isolation on top of whatever `inflation_shock` the shock
    dict itself carries, which lets a tornado test claims inflation, claims
    severity and claim frequency as three independent single-factor shocks,
    even though frequency and severity move the same aggregate cash-flow
    number here (see `expected_gross_claims` docstring in liability_model.py).

    Liabilities are NET of reinsurance by default (`treaty` defaults to
    `src.reinsurance.DEFAULT_TREATY`) -- Section 4/64 of the V6 brief: there
    is exactly one liability basis used everywhere in the app, so a scenario
    evaluated here and the same scenario evaluated via `src.analytics` must
    agree exactly (see tests/test_analytics.py).
    """
    from src.reinsurance import total_net_liability_metrics, DEFAULT_TREATY
    treaty = DEFAULT_TREATY if treaty is None else treaty

    if isinstance(name_or_shock, str):
        shock = DETERMINISTIC_SCENARIOS[name_or_shock]
        scenario_name = name_or_shock
    else:
        shock = name_or_shock
        scenario_name = label or "Custom shock"

    base_liabilities = total_net_liability_metrics(base_discount_rate, base_claim_inflation, treaty)
    stressed_assets = apply_deterministic_scenario(asset_df, shock, fx_hedge_ratio)
    stressed_discount_rate = base_discount_rate + shock.get("d_rate", 0.0)
    stressed_claim_inflation = max(base_claim_inflation + shock.get("inflation_shock", 0.0) + extra_claim_inflation, -.02)
    stressed_liabilities = total_net_liability_metrics(
        stressed_discount_rate,
        stressed_claim_inflation,
        treaty,
        frequency_shock=frequency_shock,
        severity_shock=severity_shock,
    )
    base_assets = float(asset_df.market_value.sum())
    base_liab = float(base_liabilities["present_value"])
    stressed_asset_value = float(stressed_assets.market_value_stressed.sum())
    stressed_liab_value = float(stressed_liabilities["present_value"])
    base_surplus = base_assets - base_liab
    stressed_surplus = stressed_asset_value - stressed_liab_value
    attribution = {
        "Rate effect": float(stressed_assets.rate_pnl.sum()),
        "Credit spread effect": float(stressed_assets.spread_pnl.sum()),
        "Equity / real-asset effect": float(stressed_assets.equity_real_pnl.sum()),
        "FX effect": float(stressed_assets.fx_pnl.sum()),
        "Liability revaluation / claims inflation": -(stressed_liab_value - base_liab),
    }
    return {
        "scenario": scenario_name,
        "base_assets": base_assets,
        "base_liabilities": base_liab,
        "base_surplus": base_surplus,
        "base_coverage": base_assets / base_liab,
        "stressed_assets": stressed_asset_value,
        "stressed_liabilities": stressed_liab_value,
        "surplus": stressed_surplus,
        "coverage": stressed_asset_value / stressed_liab_value,
        "delta_surplus": stressed_surplus - base_surplus,
        "attribution": attribution,
        "asset_detail": stressed_assets,
        "liability_metrics": stressed_liabilities,
    }
