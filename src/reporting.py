"""Deterministic executive ALM narrative and portable HTML report."""
from __future__ import annotations
from html import escape


def executive_summary(kpis: dict, liquidity_coverage: float, equity_risk: float,
                      scenario: str | None = None, stressed: dict | None = None) -> list[str]:
    lines = [
        f"Economic A/L coverage is {kpis['economic_coverage_ratio']:.1%}, with an economic surplus of €{kpis['surplus']:.1f}m.",
        f"The modified-duration gap is {kpis['duration_gap']:+.2f} years and the A-L DV01 gap is €{kpis['dv01_gap']:+.4f}m per bp.",
        f"12-month liquid-assets / projected-claims coverage is {liquidity_coverage:.2f}x (illustrative internal ALM metric, not a regulatory LCR).",
        f"Equities contribute {equity_risk:.1%} of total modelled asset volatility risk.",
    ]
    if scenario and scenario != "Base":
        if stressed:
            lines.append(f"Under the active '{scenario}' scenario, coverage changes to {stressed['coverage']:.1%} and surplus to €{stressed['surplus']:.1f}m.")
        else:
            lines.append(f"Active scenario: {scenario}. Review stressed coverage and surplus before interpreting mitigation analytics.")
    return lines


def build_html_report(title: str, sections: list[tuple[str, list[str]]]) -> str:
    body = []
    for heading, lines in sections:
        body.append(f"<h2>{escape(heading)}</h2>")
        body.append("<ul>" + "".join(f"<li>{escape(line)}</li>" for line in lines) + "</ul>")
    body_html = "".join(body)
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:980px;margin:36px auto;color:#1f2937;line-height:1.45}}h1{{border-bottom:2px solid #d1d5db;padding-bottom:12px}}h2{{margin-top:28px}}.note{{font-size:12px;color:#6b7280;background:#f3f4f6;padding:12px}}</style></head><body><h1>{escape(title)}</h1>{body_html}<div class='note'>Independent educational ALM prototype. Synthetic insurer balance sheet; not regulatory, actuarial or investment advice.</div></body></html>"""
