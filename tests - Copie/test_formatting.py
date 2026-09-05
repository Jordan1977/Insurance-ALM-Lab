from src.formatting import (
    fmt_eur_m, fmt_pct, fmt_signed_pct, fmt_bp, fmt_years, fmt_ratio,
    fmt_weight, fmt_dv01, fmt_delta_eur_m,
)


def test_fmt_eur_m_rounds_to_one_decimal_by_default():
    assert fmt_eur_m(149.558192047381) == "€149.6m"


def test_fmt_pct_converts_decimal_ratio():
    assert fmt_pct(1.149492) == "114.9%"


def test_fmt_signed_pct_shows_sign():
    assert fmt_signed_pct(0.032) == "+3.2%"
    assert fmt_signed_pct(-0.014) == "-1.4%"


def test_fmt_bp_converts_decimal_shock_to_whole_bp():
    assert fmt_bp(0.005) == "+50bp"
    assert fmt_bp(-0.01) == "-100bp"


def test_fmt_years_default_and_signed():
    assert fmt_years(3.73) == "3.73y"
    assert fmt_years(0.363925347, signed=True) == "+0.36y"


def test_fmt_ratio_default_suffix():
    assert fmt_ratio(3.440063277988934) == "3.44x"


def test_fmt_weight_is_one_decimal_percent():
    assert fmt_weight(0.149) == "14.9%"


def test_fmt_dv01_three_decimals():
    assert fmt_dv01(0.4286) == "€0.429m/bp"


def test_fmt_delta_eur_m_none_passthrough():
    assert fmt_delta_eur_m(None) is None
    assert fmt_delta_eur_m(12.3) == "€+12m"
