"""Theme, CSS, formatting, KPI cards, and Plotly styling helpers."""
from __future__ import annotations

import html
from typing import Sequence

import pandas as pd
import streamlit as st

from src.segments import SEGMENT_ORDER

SEGMENTS: list[str] = [str(s) for s in SEGMENT_ORDER]

# ------------------------------------------------------------------ palette
PLUM = "#34193A"
TERRA = "#C4533A"
SAFFRON = "#E8A91E"
TEAL = "#2B6E73"
SAGE = "#8AAE86"
MAUVE = "#8E7A93"
CREAM = "#F7F0E3"
SAND = "#EFE5D2"
INK = "#2A2230"

ACCENT = "#5E3A66"      # generic single-series bars
NEUTRAL = "#B3A5B6"     # muted / incomplete data
PALETTE = [TERRA, TEAL, SAFFRON, SAGE, "#6B4E71", MAUVE]

HEAD_FONT = '"DM Serif Display", "Playfair Display", Georgia, serif'
FONT_STACK = (
    '"Inter", system-ui, -apple-system, "Segoe UI", Roboto, '
    '"Helvetica Neue", Arial, sans-serif'
)

_NAMED_COLORS = {
    "Champions": SAFFRON,
    "Active Regulars": TEAL,
    "Recent One-timers": SAGE,
    "Cooling Regulars": TERRA,
    "Lost One-timers": MAUVE,
}
_FALLBACK = [SAFFRON, TEAL, SAGE, TERRA, MAUVE, "#6B4E71"]

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

_GRID = "rgba(52,25,58,0.10)"

# NOTE: tokens like __PLUM__ are replaced with plain str.replace (no "%"
# formatting), so CSS percentages can never clash with Python formatting.
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@400;500;600;700&display=swap');

.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px;}
.stApp, .stApp p, .stApp label, .stApp li, .stApp td, .stApp th,
.stApp input, .stApp textarea, .stApp button {font-family: __FONT__;}
.stApp h1, .stApp h2, .stApp h3 {font-family: __HEAD__; font-weight: 400;
    letter-spacing: -0.005em; color: __PLUM__;}

/* ---------- hero header ---------- */
.hero {position: relative; padding: 22px 26px 20px; margin-bottom: 1.4rem;
       border-radius: 20px; overflow: hidden; color: __CREAM__;
       background: linear-gradient(120deg, __PLUM__ 0%, #4B2650 55%, #5E3A66 100%);}
.hero::before {content: ""; position: absolute; right: -50px; top: -70px;
       width: 230px; height: 230px; border-radius: 50%; background: __TERRA__; opacity: .95;}
.hero::after {content: ""; position: absolute; right: 70px; top: -20px;
       width: 120px; height: 120px; border-radius: 50%; background: __SAFFRON__;}
.hero-eyebrow {position: relative; z-index: 1; font-size: .72rem; font-weight: 600;
       letter-spacing: .14em; text-transform: uppercase; color: __SAFFRON__;}
.hero-title {position: relative; z-index: 1; font-family: __HEAD__; font-size: 2.15rem;
       line-height: 1.15; margin: 4px 0 4px 0; color: __CREAM__;}
.hero-sub {position: relative; z-index: 1; margin: 0; max-width: 62%; opacity: .82; font-size: .98rem;}

/* ---------- section heading ---------- */
.sec {display: flex; align-items: baseline; gap: 10px; margin: 1.6rem 0 .6rem 0;}
.sec-dot {width: 11px; height: 11px; border-radius: 50%; background: __TERRA__;
          box-shadow: 9px 5px 0 -2px __SAFFRON__; flex: none; transform: translateY(1px);}
.sec-title {font-family: __HEAD__; font-size: 1.45rem; color: __PLUM__; line-height: 1.1;}
.sec-sub {font-size: .88rem; color: rgba(42,34,48,.62);}

/* ---------- KPI cards ---------- */
.kpi {position: relative; overflow: hidden; border: 1px solid rgba(52,25,58,.12);
      border-radius: 14px; padding: 16px 16px 12px; background: #FFFDF8;
      margin-bottom: .6rem; height: 100%;
      box-shadow: 0 6px 18px -12px rgba(52,25,58,.35);}
.kpi::before {content: ""; position: absolute; left: 0; top: 0; right: 0; height: 5px;
      background: var(--kc, __TERRA__);}
.kpi-label {font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
            color: rgba(42,34,48,.62); font-weight: 600;}
.kpi-value {font-family: __HEAD__; font-size: 1.85rem; line-height: 1.2; color: __PLUM__;
            font-variant-numeric: tabular-nums;}
.kpi-ctx {font-size: .8rem; color: rgba(42,34,48,.6);}

/* ---------- segment cards ---------- */
.seg-card {border: 1px solid rgba(52,25,58,.12); border-left: 6px solid #888;
           border-radius: 14px; padding: 14px 16px; margin-bottom: .8rem;
           background: #FFFDF8; box-shadow: 0 6px 18px -12px rgba(52,25,58,.35);}
.seg-name {font-family: __HEAD__; font-size: 1.2rem; color: __PLUM__; margin-bottom: .35rem;}
.seg-bar {height: 7px; border-radius: 99px; background: rgba(52,25,58,.09);
          margin: 2px 0 .7rem 0; overflow: hidden;}
.seg-bar > span {display: block; height: 100%; border-radius: 99px;}
.seg-bar-label {font-size: .7rem; color: rgba(42,34,48,.6); text-transform: uppercase;
                letter-spacing: .07em;}
.seg-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(105px, 1fr)); gap: .55rem;}
.seg-val {font-size: 1.05rem; font-weight: 600; font-variant-numeric: tabular-nums;}
.seg-action {margin-top: .7rem; padding: 8px 10px; border-radius: 10px; font-size: .86rem;
             background: rgba(232,169,30,.14);}
.seg-action b {font-weight: 600;}

/* ---------- takeaway ---------- */
.takeaway {border-left: 4px solid __TEAL__; background: rgba(43,110,115,.09);
           padding: 8px 12px; border-radius: 0 10px 10px 0; font-size: .87rem;
           margin: .35rem 0 .2rem 0; color: __INK__;}

/* ---------- tabs as pills ---------- */
.stTabs [data-baseweb="tab-list"] {gap: 8px; border-bottom: none;}
.stTabs [data-baseweb="tab"] {border-radius: 999px; padding: 6px 18px; height: auto;
      background: rgba(52,25,58,.07);}
.stTabs [data-baseweb="tab"] p {font-weight: 600; font-size: .9rem;}
.stTabs [aria-selected="true"] {background: __PLUM__;}
.stTabs [aria-selected="true"] p {color: __CREAM__;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display: none;}

/* ---------- containers, sidebar ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;
      border-color: rgba(52,25,58,.14); background: rgba(255,253,248,.7);}
section[data-testid="stSidebar"] {border-right: 1px solid rgba(52,25,58,.12);}
.brand {display: flex; align-items: center; gap: 12px; padding: 4px 0 14px 0;}
.brand-mark {width: 38px; height: 38px; border-radius: 50%; flex: none;
      background: radial-gradient(circle at 68% 68%, __SAFFRON__ 0 28%, transparent 29%),
                  radial-gradient(circle at 40% 40%, __TERRA__ 0 62%, __PLUM__ 63%);}
.brand-name {font-family: __HEAD__; font-size: 1.2rem; line-height: 1.1; color: __PLUM__;}
.brand-sub {font-size: .7rem; color: rgba(42,34,48,.6); letter-spacing: .04em;}
.side-label {font-size: .72rem; text-transform: uppercase; letter-spacing: .12em;
             font-weight: 700; color: __TERRA__; margin: .4rem 0 .2rem 0;}
[data-testid="stDataFrame"] {font-variant-numeric: tabular-nums;}
</style>
"""
for _k, _v in {
    "__FONT__": FONT_STACK, "__HEAD__": HEAD_FONT, "__PLUM__": PLUM, "__TERRA__": TERRA,
    "__SAFFRON__": SAFFRON, "__TEAL__": TEAL, "__CREAM__": CREAM, "__INK__": INK,
}.items():
    _CSS = _CSS.replace(_k, _v)


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


def sidebar_brand() -> None:
    """Logo mark + app name at the top of the sidebar."""
    st.markdown(
        '<div class="brand"><div class="brand-mark"></div><div>'
        '<div class="brand-name">Retail Analytics</div>'
        '<div class="brand-sub">Customers · Segments · Geography</div>'
        "</div></div>",
        unsafe_allow_html=True,
    )


def side_label(text: str) -> None:
    """Small uppercase label for sidebar groups."""
    st.markdown(f'<div class="side-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str, eyebrow: str = "Customer analytics") -> None:
    """Hero banner with title and one-line subtitle."""
    st.markdown(
        f'<div class="hero"><div class="hero-eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="hero-title">{html.escape(title)}</div>'
        f'<p class="hero-sub">{html.escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def section(title: str, sub: str = "") -> None:
    """Section heading with a two-dot accent and optional hint."""
    hint = f'<span class="sec-sub">{html.escape(sub)}</span>' if sub else ""
    st.markdown(
        f'<div class="sec"><span class="sec-dot"></span>'
        f'<span class="sec-title">{html.escape(title)}</span>{hint}</div>',
        unsafe_allow_html=True,
    )


def card():
    """Bordered container for a chart + its takeaway (use with `with`)."""
    return st.container(border=True)


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
    """One-sentence takeaway under a chart."""
    st.markdown(f'<div class="takeaway">{html.escape(text)}</div>', unsafe_allow_html=True)


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
def kpi_card(label: str, value: str, context: str = "", color: str | None = None) -> str:
    """HTML for one KPI card (top bar uses `color`)."""
    ctx = f'<div class="kpi-ctx">{html.escape(context)}</div>' if context else ""
    style = f' style="--kc:{color}"' if color else ""
    return (
        f'<div class="kpi"{style}><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>{ctx}</div>'
    )


def kpi_row(items: Sequence[tuple[str, str, str]], per_row: int | None = None,
            colors: Sequence[str] | None = None) -> None:
    """Render KPI cards in rows. items = (label, value, context)."""
    per_row = per_row or len(items)
    colors = list(colors) if colors else PALETTE
    idx = 0
    for start in range(0, len(items), per_row):
        chunk = items[start:start + per_row]
        for col, (label, value, ctx) in zip(st.columns(len(chunk)), chunk):
            col.markdown(kpi_card(label, value, ctx, colors[idx % len(colors)]),
                         unsafe_allow_html=True)
            idx += 1


def segment_card(
    name: str,
    color: str,
    stats: Sequence[tuple[str, str]],
    action: str | None = None,
    share: float | None = None,
) -> str:
    """HTML for a segment profile card (`share` = revenue share, 0-1, draws a bar)."""
    cells = "".join(
        f'<div><div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="seg-val">{html.escape(value)}</div></div>'
        for label, value in stats
    )
    bar = ""
    if share is not None and not pd.isna(share):
        w = max(0.0, min(float(share), 1.0)) * 100
        bar = (f'<div class="seg-bar-label">Share of net revenue</div>'
               f'<div class="seg-bar"><span style="width:{w:.1f}%;background:{color}"></span></div>')
    act = (
        '<div class="seg-action"><b>Suggested action to test:</b> '
        f"{html.escape(action)}</div>"
        if action
        else ""
    )
    return (
        f'<div class="seg-card" style="border-left-color:{color}">'
        f'<div class="seg-name">{html.escape(name)}</div>{bar}'
        f'<div class="seg-grid">{cells}</div>{act}</div>'
    )


# ------------------------------------------------------------------- plotly
def style_fig(fig, title: str, height: int = 380, legend: bool = True):
    """Apply the shared Plotly look (transparent bg, soft grid, serif title)."""
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left",
                   font=dict(size=18, family=HEAD_FONT, color=PLUM)),
        height=height,
        margin=dict(l=8, r=8, t=56, b=60 if legend else 20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_STACK, color=INK),
        colorway=PALETTE,
        bargap=0.28,
        showlegend=legend,
        legend=dict(title_text="", orientation="h", yanchor="top", y=-0.16, x=0),
        hoverlabel=dict(bgcolor="#FFFDF8", bordercolor=PLUM, font=dict(color=INK)),
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