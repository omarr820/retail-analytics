"""Theme, CSS, formatting, KPI cards, and Plotly styling helpers."""
from __future__ import annotations

import html
from typing import Sequence

import pandas as pd
import streamlit as st

from src.segments import SEGMENT_ORDER

SEGMENTS: list[str] = [str(s) for s in SEGMENT_ORDER]

ACCENT = "#0D9488"
NEUTRAL = "#8B93A1"
FONT_STACK = (
    '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, '
    '"Helvetica Neue", Arial, sans-serif'
)

_NAMED_COLORS = {
    "Champions": "#E0A100",
    "Active Regulars": "#0D9488",
    "Recent One-timers": "#3B82F6",
    "Cooling Regulars": "#E5484D",
    "Lost One-timers": "#8B93A1",
}
_FALLBACK = ["#E0A100", "#0D9488", "#3B82F6", "#E5484D", "#8B93A1", "#6B7280"]

# One consistent color per segment, used in ALL charts.
SEGMENT_COLORS: dict[str, str] = {
    s: _NAMED_COLORS.get(s, _FALLBACK[i % len(_FALLBACK)])
    for i, s in enumerate(SEGMENTS)
}

SEGMENT_ACTIONS: dict[str, str] = {
    "Champions": (
        "Protect with loyalty perks, early access, a referral program, "
        "and account management for key accounts."
    ),
    "Active Regulars": "Grow with cross-sell, bundles, and volume incentives.",
    "Recent One-timers": (
        "Convert with a welcome sequence aimed at a second purchase."
    ),
    "Cooling Regulars": (
        "Recover with a targeted win-back offer, highest past spend first."
    ),
    "Lost One-timers": "Limit spend; one low-cost reactivation attempt.",
}

_GRID = "rgba(128,128,128,0.22)"

# Font is applied to text elements only (never to icon spans), so the
# Material icon font in the sidebar keeps working.
_CSS = """
<style>
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}
.stApp, .stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp li, .stApp td, .stApp th, .stApp input, .stApp textarea, .stApp button {font-family: %(font)s;}
h1 {font-weight: 650; letter-spacing: -0.02em; margin-bottom: 0.1rem;}
h2, h3 {font-weight: 600; letter-spacing: -0.01em;}
.page-sub {opacity: 0.7; margin: 0 0 1.4rem 0; font-size: 1.02rem;}
.kpi {border: 1px solid rgba(128,128,128,0.28); border-radius: 12px;
      padding: 14px 16px; background: rgba(128,128,128,0.07);
      margin-bottom: 0.6rem; height: 100%%;}
.kpi-label {font-size: 0.74rem; text-transform: uppercase;
            letter-spacing: 0.06em; opacity: 0.68;}
.kpi-value {font-size: 1.6rem; font-weight: 650; line-height: 1.25;
            font-variant-numeric: tabular-nums;}
.kpi-ctx {font-size: 0.8rem; opacity: 0.65;}
.seg-card {border: 1px solid rgba(128,128,128,0.28); border-left: 5px solid #888;
           border-radius: 12px; padding: 14px 16px; margin-bottom: 0.8rem;
           background: rgba(128,128,128,0.07);}
.seg-name {font-size: 1.05rem; font-weight: 650; margin-bottom: 0.5rem;}
.seg-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(105px, 1fr));
           gap: 0.55rem;}
.seg-val {font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums;}
.seg-action {margin-top: 0.7rem; font-size: 0.88rem; opacity: 0.85;}
.seg-action b {opacity: 0.7; font-weight: 600;}
[data-testid="stDataFrame"] {font-variant-numeric: tabular-nums;}
</style>
""" % {"font": FONT_STACK}


# ---------------------------------------------------------------- formatting
def gbp(x: float, decimals: int = 0) -> str:
    """Format as GBP with thousands separators."""
    return "n/a" if pd.isna(x) else f"£{x:,.{decimals}f}"


def gbp_short(x: float) -> str:
    """Compact GBP for KPI cards (K / M)."""
    if pd.isna(x):
        return "n/a"
    if abs(x) >= 1e6:
        return f"£{x / 1e6:,.2f}M"
    if abs(x) >= 1e4:
        return f"£{x / 1e3:,.1f}K"
    return gbp(x)


def pct(x: float) -> str:
    """Format a fraction (0-1) as a percentage with one decimal."""
    return "n/a" if pd.isna(x) else f"{x * 100:.1f}%"


def num(x: float) -> str:
    """Integer with thousands separators."""
    return "n/a" if pd.isna(x) else f"{x:,.0f}"


# ------------------------------------------------------- Streamlit wrappers
def inject_css() -> None:
    """Inject the global CSS block (cards, spacing, typography)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    """Page title with a one-line subtitle."""
    st.title(title)
    st.markdown(
        f'<p class="page-sub">{html.escape(subtitle)}</p>',
        unsafe_allow_html=True,
    )


def show(fig, key: str | None = None) -> None:
    """Render a Plotly figure full-width (width="stretch" with fallback)."""
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except Exception:  # older Streamlit without width="stretch"
        st.plotly_chart(fig, use_container_width=True, key=key)


def show_df(df: pd.DataFrame, **kwargs):
    """Render a dataframe full-width (width="stretch" with fallback)."""
    try:
        return st.dataframe(df, width="stretch", **kwargs)
    except Exception:
        return st.dataframe(df, use_container_width=True, **kwargs)


def takeaway(text: str) -> None:
    """One-sentence takeaway caption under a chart."""
    st.caption(text)


def empty_state() -> None:
    """Friendly message when filters return zero rows."""
    st.info(
        "No customers match the current filters. Widen the ranges, "
        "re-select segments, or press Reset filters in the sidebar.",
        icon=":material/filter_alt_off:",
    )


def footer() -> None:
    """About line at the bottom of every page."""
    st.divider()
    st.caption(
        "Customer analytics dashboard · Online Retail dataset "
        "(Dec 2010 - Dec 2011) · Findings are descriptive; suggested "
        "actions are hypotheses to test, not proven effects."
    )


# --------------------------------------------------------------------- cards
def kpi_card(label: str, value: str, context: str = "") -> str:
    """HTML for one KPI card."""
    ctx = (
        f'<div class="kpi-ctx">{html.escape(context)}</div>' if context else ""
    )
    return (
        f'<div class="kpi"><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>{ctx}</div>'
    )


def kpi_row(items: Sequence[tuple[str, str, str]], per_row: int | None = None) -> None:
    """Render KPI cards in rows. items = (label, value, context)."""
    per_row = per_row or len(items)
    for start in range(0, len(items), per_row):
        chunk = items[start:start + per_row]
        for col, (label, value, ctx) in zip(st.columns(len(chunk)), chunk):
            col.markdown(kpi_card(label, value, ctx), unsafe_allow_html=True)


def segment_card(
    name: str,
    color: str,
    stats: Sequence[tuple[str, str]],
    action: str | None = None,
) -> str:
    """HTML for a segment profile card."""
    cells = "".join(
        f'<div><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="seg-val">{html.escape(value)}</div></div>'
        for label, value in stats
    )
    act = (
        '<div class="seg-action"><b>Suggested action to test:</b> '
        f"{html.escape(action)}</div>"
        if action
        else ""
    )
    return (
        f'<div class="seg-card" style="border-left-color:{color}">'
        f'<div class="seg-name">{html.escape(name)}</div>'
        f'<div class="seg-grid">{cells}</div>{act}</div>'
    )


# ------------------------------------------------------------------- plotly
def style_fig(fig, title: str, height: int = 380, legend: bool = True):
    """Apply the shared Plotly look (transparent bg, grid, fonts)."""
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15)),
        height=height,
        margin=dict(l=8, r=8, t=56, b=60 if legend else 20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK),
        showlegend=legend,
        legend=dict(title_text="", orientation="h", yanchor="top", y=-0.16, x=0),
    )
    fig.update_xaxes(gridcolor=_GRID, zerolinecolor=_GRID, automargin=True)
    fig.update_yaxes(gridcolor=_GRID, zerolinecolor=_GRID, automargin=True)
    return fig


# --------------------------------------------------- shared customer table
TABLE_COLUMNS = [
    "CustomerID", "segment", "RFM_Score", "recency", "frequency", "monetary",
    "avg_order_value", "revenue_share_pct", "cancelled_value", "is_outlier",
]


def table_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Display-ready customer table (plain dtypes, reset index)."""
    out = df[TABLE_COLUMNS].copy()
    out["segment"] = out["segment"].astype(str)
    out["RFM_Score"] = out["RFM_Score"].astype(str)
    out["cancelled_value"] = out["cancelled_value"].abs()
    return out.reset_index(drop=True)


def table_config(max_share_pct: float) -> dict:
    """column_config shared by the Customers and Key Accounts tables."""
    cc = st.column_config
    return {
        "CustomerID": cc.TextColumn("Customer ID"),
        "segment": cc.TextColumn("Segment"),
        "RFM_Score": cc.TextColumn("RFM"),
        "recency": cc.NumberColumn("Recency (days)", format="%d"),
        "frequency": cc.NumberColumn("Orders", format="%d"),
        "monetary": cc.NumberColumn("Net revenue", format="£%.0f"),
        "avg_order_value": cc.NumberColumn("Avg order", format="£%.0f"),
        "revenue_share_pct": cc.ProgressColumn(
            "Share of total revenue", format="%.2f%%",
            min_value=0.0, max_value=float(max_share_pct),
        ),
        "cancelled_value": cc.NumberColumn("Cancelled value", format="£%.0f"),
        "is_outlier": cc.CheckboxColumn("Key account"),
    }