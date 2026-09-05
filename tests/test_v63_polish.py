"""Static regression guards for the V6.3 recruiter-facing UX pass."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "pages"


def test_no_five_plus_column_rows_remain_in_pages():
    for path in PAGES.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for n in range(5, 10):
            assert f"st.columns({n})" not in text, f"Dense {n}-column row remains in {path.name}"


def test_all_analytical_pages_use_shared_header_except_overview():
    for path in PAGES.glob("*.py"):
        if path.name == "0_overview.py":
            continue
        text = path.read_text(encoding="utf-8")
        assert "page_header(" in text, f"Shared page header missing in {path.name}"


def test_sidebar_points_to_current_changelog():
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Model version: V6.3" in text
    assert "CHANGELOG_V6.3.md" in text


def test_global_css_is_applied():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    helpers = (ROOT / "src" / "ui_helpers.py").read_text(encoding="utf-8")
    assert "inject_global_css()" in app
    assert "def inject_global_css" in helpers
