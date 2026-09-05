"""Shared layout helpers (Section 52 of the V6.2 brief).

These wrap plain Streamlit calls so every page builds its header, KPI rows
and status badges the same way, instead of each page inventing its own
spacing and heading hierarchy (Section 53).
"""
from __future__ import annotations

import streamlit as st


def page_header(title: str, business_question: str, scenario: str | None = None) -> None:
    """Consistent page header (Section 16): title, one-line business
    question, and an always-visible active-scenario badge so the reader
    never has to wonder which view they are looking at (Section 15)."""
    st.title(title)
    st.caption(business_question)
    if scenario is not None:
        if scenario == "Base":
            st.caption("Active scenario: **Base** (no stress applied)")
        else:
            st.warning(f"Active scenario: **{scenario.upper()}**", icon="⚠️")


def metric_row(items: list[tuple[str, str, str | None]], help_texts: list[str | None] | None = None) -> None:
    """Render up to 4 metrics per row (Section 5): a row of more than 4 is
    split into multiple rows rather than cramming into narrow columns.
    `items` is a list of (label, value, delta) tuples."""
    help_texts = help_texts or [None] * len(items)
    for start in range(0, len(items), 4):
        chunk = items[start:start + 4]
        chunk_help = help_texts[start:start + 4]
        cols = st.columns(len(chunk))
        for col, (label, value, delta), help_text in zip(cols, chunk, chunk_help):
            col.metric(label, value, delta, help=help_text)


def status_badge(status: str) -> str:
    """Text-first status label (Section 57: never colour alone)."""
    return {"GREEN": "✅ PASS", "AMBER": "⚠️ WATCH", "RED": "🛑 BREACH"}.get(status, status)


def info_box(text: str, kind: str = "info") -> None:
    getattr(st, kind)(text)


def compact_expander(label: str = "Methodology, assumptions & limitations"):
    """A single reusable expander name/pattern so pages don't repeat long
    methodology text in the main body (Section 17)."""
    return st.expander(label)



def inject_global_css() -> None:
    """Apply restrained application-wide layout polish.

    This deliberately uses broad Streamlit data-testid selectors only for spacing,
    card wrapping and sidebar ergonomics; financial meaning never depends on CSS.
    """
    st.markdown(
        """
        <style>
        /* Main canvas: readable on common laptop widths without wasting wide screens. */
        .block-container {padding-top: 1.15rem; padding-bottom: 2.5rem; max-width: 1550px;}
        [data-testid="stSidebar"] {min-width: 285px; max-width: 330px;}
        [data-testid="stSidebar"] .block-container {padding-top: 1rem;}

        /* Consistent typography / vertical rhythm. */
        h1 {font-size: clamp(1.75rem, 2.4vw, 2.35rem) !important; line-height: 1.12 !important; margin-bottom: .2rem !important;}
        h2 {font-size: clamp(1.25rem, 1.7vw, 1.55rem) !important; margin-top: 1.2rem !important;}
        h3 {font-size: clamp(1.08rem, 1.35vw, 1.28rem) !important; margin-top: 1rem !important;}
        [data-testid="stCaptionContainer"] {line-height: 1.4;}

        /* KPI cards: prevent visual collapse and overly long wrapped labels. */
        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.18);
            border-radius: .55rem;
            padding: .72rem .82rem;
            min-height: 103px;
            background: rgba(128,128,128,.025);
        }
        [data-testid="stMetricLabel"] {min-height: 2.35em; align-items: flex-start;}
        [data-testid="stMetricLabel"] p {font-size: .88rem; line-height: 1.2;}
        [data-testid="stMetricValue"] {font-size: clamp(1.25rem, 1.8vw, 1.75rem);}

        /* Tables should remain subordinate to the analytical story. */
        [data-testid="stDataFrame"] {border-radius: .45rem; overflow: hidden;}
        [data-testid="stExpander"] {border-radius: .45rem;}

        /* Plotly/SVG containers need breathing room on shorter laptop displays. */
        [data-testid="stPlotlyChart"] {margin-top: .25rem; margin-bottom: .85rem;}

        /* Controls: keep labels compact and readable. */
        [data-testid="stWidgetLabel"] p {line-height: 1.25;}

        @media (max-width: 1400px) {
          .block-container {padding-left: 1.35rem; padding-right: 1.35rem;}
          [data-testid="stMetric"] {min-height: 98px; padding: .62rem .68rem;}
          [data-testid="stMetricLabel"] p {font-size: .82rem;}
        }
        @media (max-width: 1100px) {
          [data-testid="stSidebar"] {min-width: 260px; max-width: 290px;}
          .block-container {padding-left: 1rem; padding-right: 1rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, caption: str | None = None) -> None:
    """Consistent H2-level analytical section heading."""
    st.markdown(f"## {title}")
    if caption:
        st.caption(caption)


def compact_table(df, *, height: int | None = None, column_config=None, key: str | None = None) -> None:
    """Render an institutional-style dataframe with consistent defaults."""
    kwargs = dict(use_container_width=True, hide_index=True)
    if height is not None:
        kwargs["height"] = height
    if column_config is not None:
        kwargs["column_config"] = column_config
    if key is not None:
        kwargs["key"] = key
    st.dataframe(df, **kwargs)
