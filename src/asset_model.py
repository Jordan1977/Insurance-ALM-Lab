"""Synthetic non-life insurer asset book and investment analytics.

All monetary values are EUR millions. No holding represents Thélem assurances.
The strategic asset-class view is deliberately simple; the instrument-level book
is internally coherent (face value -> cash flows -> market value) so ALM cash-flow
matching, DV01 and hedge sizing do not rely on fictitious principal = market value.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TOTAL_ASSETS = 1_150.0
DEFAULT_WEIGHTS = {
    "Cash / Money Market": 0.08,
    "French Government Bonds": 0.15,
    "Euro Government Bonds": 0.15,
    "IG Corporate Bonds": 0.25,
    "High Yield Bonds": 0.05,
    "Euro Equities": 0.08,
    "US Equities": 0.05,
    "Global Equities": 0.02,
    "Real Estate": 0.08,
    "Infrastructure": 0.06,
    "Private Debt": 0.03,
}
ASSET_ASSUMPTIONS = {
    "Cash / Money Market": dict(exp_ret=.025, vol=.003, duration=.20, yield_=.025, rating="AA", liquidity=1.00, geo="Euro Area", ccy="EUR", esg=70, spread_duration=0.0),
    "French Government Bonds": dict(exp_ret=.032, vol=.055, duration=7.5, yield_=.031, rating="AA", liquidity=.95, geo="France", ccy="EUR", esg=75, spread_duration=0.0),
    "Euro Government Bonds": dict(exp_ret=.033, vol=.060, duration=7.0, yield_=.032, rating="AA-", liquidity=.90, geo="Euro Area", ccy="EUR", esg=72, spread_duration=0.0),
    "IG Corporate Bonds": dict(exp_ret=.038, vol=.065, duration=5.5, yield_=.038, rating="A", liquidity=.75, geo="Euro Area", ccy="EUR", esg=65, spread_duration=4.8),
    "High Yield Bonds": dict(exp_ret=.060, vol=.110, duration=3.5, yield_=.065, rating="BB", liquidity=.55, geo="Euro Area", ccy="EUR", esg=45, spread_duration=3.0),
    "Euro Equities": dict(exp_ret=.065, vol=.170, duration=0.0, yield_=.030, rating="NR", liquidity=.95, geo="Euro Area", ccy="EUR", esg=60, spread_duration=0.0),
    "US Equities": dict(exp_ret=.075, vol=.180, duration=0.0, yield_=.015, rating="NR", liquidity=.95, geo="US", ccy="USD", esg=58, spread_duration=0.0),
    "Global Equities": dict(exp_ret=.070, vol=.165, duration=0.0, yield_=.020, rating="NR", liquidity=.90, geo="Global", ccy="Mixed", esg=62, spread_duration=0.0),
    "Real Estate": dict(exp_ret=.045, vol=.100, duration=0.0, yield_=.040, rating="NR", liquidity=.30, geo="Euro Area", ccy="EUR", esg=55, spread_duration=0.0),
    "Infrastructure": dict(exp_ret=.050, vol=.090, duration=0.0, yield_=.045, rating="NR", liquidity=.20, geo="Euro Area", ccy="EUR", esg=68, spread_duration=0.0),
    "Private Debt": dict(exp_ret=.055, vol=.080, duration=4.0, yield_=.058, rating="BBB", liquidity=.10, geo="Euro Area", ccy="EUR", esg=50, spread_duration=3.5),
}
EQUITY_CLASSES = {"Euro Equities", "US Equities", "Global Equities"}
CREDIT_CLASSES = {"IG Corporate Bonds", "High Yield Bonds", "Private Debt"}
RATE_CLASSES = {"Cash / Money Market", "French Government Bonds", "Euro Government Bonds", "IG Corporate Bonds", "High Yield Bonds", "Private Debt"}
ILLIQUID_CLASSES = {"Real Estate", "Infrastructure", "Private Debt"}


def build_asset_portfolio(weights: dict[str, float] | None = None,
                          total_assets: float = TOTAL_ASSETS,
                          seed: int = 42) -> pd.DataFrame:
    """Build the strategic asset-class balance sheet."""
    rng = np.random.default_rng(seed)
    weights = weights or DEFAULT_WEIGHTS
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}
    rows: list[dict] = []
    for asset_class, weight in weights.items():
        a = ASSET_ASSUMPTIONS[asset_class]
        market_value = total_assets * weight
        rows.append({
            "asset_class": asset_class,
            "market_value": market_value,
            "weight": weight,
            "expected_return": a["exp_ret"],
            "volatility": a["vol"],
            "duration": a["duration"],
            "yield": a["yield_"],
            "rating": a["rating"],
            "currency": a["ccy"],
            "geography": a["geo"],
            "liquidity_score": a["liquidity"],
            "esg_score": a["esg"],
            "spread_duration": a["spread_duration"],
        })
    df = pd.DataFrame(rows)
    df["modified_duration"] = np.where(df["duration"] > 0, df["duration"] / (1 + df["yield"]), 0.0)
    df["dv01"] = df["market_value"] * df["modified_duration"] * 1e-4
    df["convexity"] = np.where(
        df["modified_duration"] > 0,
        df["modified_duration"] * (df["modified_duration"] + 1) / (1 + df["yield"]) ** 2,
        0.0,
    )
    return df


def _bullet_price_factor(face_value: float, coupon_rate: float, ytm: float, maturity: int) -> float:
    years = np.arange(1, maturity + 1)
    cfs = np.full(maturity, face_value * coupon_rate, dtype=float)
    cfs[-1] += face_value
    return float((cfs / (1 + ytm) ** years).sum())


def _amortising_price_factor(face_value: float, coupon_rate: float, ytm: float, maturity: int) -> float:
    principal = face_value / maturity
    balance = face_value
    pv = 0.0
    for year in range(1, maturity + 1):
        cf = principal + balance * coupon_rate
        pv += cf / (1 + ytm) ** year
        balance -= principal
    return float(pv)


def _cashflow_risk_metrics(cash_flows: np.ndarray, ytm: float) -> tuple[float, float, float, float]:
    years = np.arange(1, len(cash_flows) + 1, dtype=float)
    pv_vec = cash_flows / (1 + ytm) ** years
    price = pv_vec.sum()
    if price <= 0:
        return 0.0, 0.0, 0.0, 0.0
    macaulay = float((years * pv_vec).sum() / price)
    modified = macaulay / (1 + ytm)
    eps = 1e-4
    p_up = float((cash_flows / (1 + ytm + eps) ** years).sum())
    p_dn = float((cash_flows / (1 + ytm - eps) ** years).sum())
    convexity = (p_up + p_dn - 2 * price) / (price * eps**2) / 1e8  # years^2-ish stable scaled finite diff
    # Use analytic-like discrete convexity for readability/stability.
    convexity = float((years * (years + 1) * pv_vec).sum() / (price * (1 + ytm) ** 2))
    return macaulay, modified, convexity, price * modified * 1e-4


def build_instrument_book(asset_df: pd.DataFrame | None = None, seed: int = 11) -> pd.DataFrame:
    """Create an internally coherent synthetic instrument book.

    For contractual assets the desired market value is first allocated by class,
    then the face value is calibrated so discounted contractual cash flows equal
    that market value at the instrument's synthetic yield.
    """
    asset_df = build_asset_portfolio() if asset_df is None else asset_df
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    idx = 1
    for _, r in asset_df.iterrows():
        asset_class = r.asset_class
        class_mv = float(r.market_value)
        n = 1 if asset_class in EQUITY_CLASSES | {"Real Estate", "Infrastructure", "Cash / Money Market"} else (6 if "Government" in asset_class else 5)
        shares = rng.dirichlet(np.ones(n)) if n > 1 else np.array([1.0])
        for share in shares:
            target_mv = class_mv * share
            ytm = float(r["yield"])
            maturity: float | None = None
            coupon = 0.0
            face_value = target_mv
            instrument_type = "Non-contractual"
            macaulay = modified = convexity = dv01 = 0.0
            if asset_class == "Cash / Money Market":
                instrument_type = "Cash"
                maturity = 0.25
                macaulay = modified = 0.20
                dv01 = target_mv * modified * 1e-4
            elif asset_class in EQUITY_CLASSES:
                instrument_type = "Equity"
            elif asset_class in {"Real Estate", "Infrastructure"}:
                instrument_type = "Real asset"
            else:
                instrument_type = "Private debt" if asset_class == "Private Debt" else "Bond"
                center = max(float(r.duration), 1.0)
                maturity = float(np.clip(rng.normal(center + 1.0, 1.7), 1, 12))
                m = int(round(maturity))
                coupon = float(np.clip(ytm + rng.normal(0, .004), .005, .10))
                unit_price = (_amortising_price_factor if instrument_type == "Private debt" else _bullet_price_factor)(1.0, coupon, ytm, m)
                face_value = target_mv / unit_price
                if instrument_type == "Private debt":
                    principal = face_value / m
                    balance = face_value
                    cfs = []
                    for _year in range(1, m + 1):
                        cfs.append(principal + balance * coupon)
                        balance -= principal
                else:
                    cfs = [face_value * coupon] * m
                    cfs[-1] += face_value
                macaulay, modified, convexity, dv01 = _cashflow_risk_metrics(np.asarray(cfs), ytm)
            rows.append({
                "instrument_id": f"I{idx:03d}",
                "asset_class": asset_class,
                "instrument_type": instrument_type,
                "market_value": target_mv,
                "face_value": face_value,
                "coupon": coupon,
                "yield": ytm,
                "maturity_years": maturity,
                "macaulay_duration": macaulay,
                "modified_duration": modified,
                "convexity": convexity,
                "dv01": dv01,
                "spread_duration": float(r.spread_duration),
                "rating": r.rating,
                "currency": r.currency,
                "liquidity_score": float(r.liquidity_score),
            })
            idx += 1
    return pd.DataFrame(rows)


def instrument_cash_flows(book: pd.DataFrame, horizon: int = 10, include_estimated_income: bool = True) -> pd.DataFrame:
    """Generate contractual cash flows plus separately-labelled estimated income.

    Also splits each cash flow into `principal_component` (money that stops
    being invested and must be reinvested or held) and `coupon_component`
    (interest / estimated income). This split is the single source used by
    both ALM cash-flow matching and the Reinvestment & Maturity Management
    module (src/reinvestment.py) -- it is not recomputed a second time there.
    """
    rows: list[dict] = []
    for _, r in book.iterrows():
        typ = r.instrument_type
        mv = float(r.market_value)
        face = float(r.get("face_value", mv))
        if typ == "Cash":
            rows.append({"instrument_id": r.instrument_id, "asset_class": r.asset_class, "year": 1, "cash_flow": mv, "cf_type": "contractual_liquidity", "principal_component": mv, "coupon_component": 0.0})
        elif typ in {"Bond", "Private debt"}:
            m = int(max(1, min(horizon, round(float(r.maturity_years)))))
            if typ == "Private debt":
                principal_payment = face / m
                balance = face
                for year in range(1, m + 1):
                    interest = balance * float(r.coupon)
                    rows.append({"instrument_id": r.instrument_id, "asset_class": r.asset_class, "year": year, "cash_flow": principal_payment + interest, "cf_type": "contractual", "principal_component": principal_payment, "coupon_component": interest})
                    balance -= principal_payment
            else:
                coupon_cf = face * float(r.coupon)
                for year in range(1, m + 1):
                    principal = face if year == m else 0.0
                    rows.append({"instrument_id": r.instrument_id, "asset_class": r.asset_class, "year": year, "cash_flow": coupon_cf + principal, "cf_type": "contractual", "principal_component": principal, "coupon_component": coupon_cf})
        elif include_estimated_income:
            annual_income = mv * float(r["yield"])
            for year in range(1, horizon + 1):
                rows.append({"instrument_id": r.instrument_id, "asset_class": r.asset_class, "year": year, "cash_flow": annual_income, "cf_type": "estimated_income", "principal_component": 0.0, "coupon_component": annual_income})
    return pd.DataFrame(rows)


def build_correlation_matrix(asset_classes: list[str]) -> pd.DataFrame:
    group = {"Cash / Money Market": 0, "French Government Bonds": 1, "Euro Government Bonds": 1, "IG Corporate Bonds": 2,
             "High Yield Bonds": 3, "Euro Equities": 4, "US Equities": 4, "Global Equities": 4,
             "Real Estate": 5, "Infrastructure": 5, "Private Debt": 3}
    gc = {(0,1):.05,(0,2):.05,(0,3):0,(0,4):-.02,(0,5):0,(1,1):.85,(1,2):.55,(1,3):.10,
          (1,4):-.20,(1,5):.05,(2,2):.75,(2,3):.45,(2,4):-.05,(2,5):.15,(3,3):.65,
          (3,4):.35,(3,5):.25,(4,4):.75,(4,5):.30,(5,5):.55}
    n = len(asset_classes)
    m = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = group[asset_classes[i]], group[asset_classes[j]]
            value = gc.get((a, b), gc.get((b, a), .1))
            m[i, j] = m[j, i] = value
    # Nearest-PSD repair (tiny only) protects optimisers if assumptions are edited.
    eigval, eigvec = np.linalg.eigh(m)
    eigval = np.clip(eigval, 1e-8, None)
    m = eigvec @ np.diag(eigval) @ eigvec.T
    d = np.sqrt(np.diag(m))
    m = m / np.outer(d, d)
    return pd.DataFrame(m, index=asset_classes, columns=asset_classes)


def portfolio_expected_return(df: pd.DataFrame) -> float:
    return float((df.weight * df.expected_return).sum())


def portfolio_volatility(df: pd.DataFrame, corr: pd.DataFrame) -> float:
    w = df.weight.to_numpy()
    sigma = df.volatility.to_numpy()
    cov = np.outer(sigma, sigma) * corr.to_numpy()
    return float(np.sqrt(w @ cov @ w))


def portfolio_modified_duration(df: pd.DataFrame) -> float:
    return float((df.market_value * df.modified_duration).sum() / df.market_value.sum())


def portfolio_asset_dv01(df: pd.DataFrame) -> float:
    return float(df.dv01.sum())


def risk_contribution(df: pd.DataFrame, corr: pd.DataFrame) -> pd.DataFrame:
    w = df.weight.to_numpy()
    sigma = df.volatility.to_numpy()
    cov = np.outer(sigma, sigma) * corr.to_numpy()
    portfolio_vol = float(np.sqrt(w @ cov @ w))
    mcr = (cov @ w) / portfolio_vol if portfolio_vol else np.zeros_like(w)
    cr = w * mcr
    out = df[["asset_class", "weight"]].copy()
    out["marginal_contribution_to_risk"] = mcr
    out["contribution_to_risk"] = cr
    out["pct_of_total_risk"] = cr / cr.sum() if cr.sum() else 0.0
    return out


def fx_exposure(df: pd.DataFrame, hedge_ratio: float = 0.0) -> dict[str, float]:
    usd = float(df.loc[df.currency.eq("USD"), "market_value"].sum())
    mixed = float(df.loc[df.currency.eq("Mixed"), "market_value"].sum()) * .5
    gross = usd + mixed
    return {"gross_fx_exposure": gross, "net_fx_exposure": gross * (1 - hedge_ratio), "hedge_ratio": hedge_ratio}
