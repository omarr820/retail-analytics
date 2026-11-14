"""Segments: profile cards, comparison charts, compare-two-segments."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data, ui


def _profile_cards(seg: pd.DataFrame) -> None:
    for start in range(0, len(seg), 3):
        chunk = seg.iloc[start:start + 3]
        for col, (_, r) in zip(st.columns(3), chunk.iterrows()):
            name = str(r["segment"])
            stats = [
                ("Customers", ui.num(r["customers"])),
                ("Customer share", ui.pct(r["customer_share"])),
                ("Revenue share", ui.pct(r["revenue_share"])),
                ("Median recency", f"{r['median_recency']:,.0f} d"),
                ("Median orders", f"{r['median_frequency']:,.0f}"),
                ("Median revenue", ui.gbp(r["median_monetary"])),
            ]
            col.markdown(
                ui.segment_card(name, ui.SEGMENT_COLORS[name], stats,
                                ui.SEGMENT_ACTIONS.get(name)),
                unsafe_allow_html=True)


def _share_chart(seg: pd.DataFrame) -> None:
    long = seg.melt(id_vars="segment", value_vars=["customer_share", "revenue_share"],
                    var_name="metric", value_name="share")
    long["metric"] = long["metric"].map(
        {"customer_share": "Share of customers", "revenue_share": "Share of net revenue"})
    long["share_pct"] = long["share"] * 100
    fig = px.bar(long, x="segment", y="share_pct", color="segment",
                 pattern_shape="metric", barmode="group",
                 color_discrete_map=ui.SEGMENT_COLORS,
                 pattern_shape_map={"Share of customers": "/", "Share of net revenue": ""},
                 category_orders={"segment": ui.SEGMENTS},
                 text=long["share_pct"].map(lambda v: f"{v:.1f}%"),
                 hover_data={"metric": True, "share_pct": ":.1f", "segment": False})
    fig.update_traces(textposition="outside")
    ui.style_fig(fig, "Revenue share vs customer share by segment", legend=False)
    fig.update_xaxes(title="")
    fig.update_yaxes(title="Share (%)", ticksuffix="%")
    ui.show(fig, key="seg_share")
    top = seg.sort_values("revenue_share", ascending=False).iloc[0]
    ui.takeaway(
        "Solid bars = share of net revenue, hatched bars = share of customers. "
        f"{top['segment']} hold {ui.pct(top['revenue_share'])} of revenue from "
        f"{ui.pct(top['customer_share'])} of customers.")


def _scatter3d(view: pd.DataFrame) -> None:
    plot = view.assign(
        lr=np.log1p(view["recency"]),
        lf=np.log1p(view["frequency"]),
        lm=np.log1p(view["monetary"]),
    )
    cols = ["CustomerID", "recency", "frequency", "monetary"]
    hover = ("<b>%{customdata[0]}</b><br>Recency: %{customdata[1]:,.0f} days<br>"
             "Orders: %{customdata[2]:,.0f}<br>Net revenue: £%{customdata[3]:,.0f}"
             "<extra>%s</extra>")
    fig = go.Figure()
    for s in ui.SEGMENTS:
        d = plot[(plot["segment"].astype(str) == s) & ~plot["is_outlier"]]
        if d.empty:
            continue
        fig.add_trace(go.Scatter3d(
            x=d["lr"], y=d["lf"], z=d["lm"], mode="markers", name=s,
            customdata=d[cols].to_numpy(), hovertemplate=hover % s,
            marker=dict(size=3, color=ui.SEGMENT_COLORS[s], opacity=0.75)))
    ko = plot[plot["is_outlier"]]
    if not ko.empty:
        fig.add_trace(go.Scatter3d(
            x=ko["lr"], y=ko["lf"], z=ko["lm"], mode="markers", name="Key accounts",
            customdata=ko[cols].to_numpy(), hovertemplate=hover % "Key account",
            marker=dict(size=6, symbol="diamond", color="#FFFFFF",
                        line=dict(color="#111827", width=2))))
    ui.style_fig(fig, "Customers in log space (log1p of recency, orders, revenue)", height=560)
    fig.update_layout(scene=dict(
        xaxis_title="log(1 + recency days)",
        yaxis_title="log(1 + orders)",
        zaxis_title="log(1 + net revenue GBP)"))
    ui.show(fig, key="seg_3d")
    ui.takeaway(
        "Each point is a customer; diamonds are key accounts. Segments overlap at the "
        "edges, which is why the borders between segments are soft.")


def _radar(seg: pd.DataFrame) -> None:
    if len(seg) < 2:
        st.info("Select at least two segments in the sidebar to see the comparison.")
        return
    metrics = {
        "median_recency": "Recency (more recent = outer)",
        "median_frequency": "Orders",
        "median_monetary": "Net revenue",
        "mean_aov": "Avg order value",
        "repeat_rate": "Repeat rate",
    }
    base = seg.set_index("segment")[list(metrics)].astype(float)
    rng = (base.max() - base.min()).replace(0, 1)
    scaled = (base - base.min()) / rng
    scaled["median_recency"] = 1 - scaled["median_recency"]
    labels = list(metrics.values())

    fig = go.Figure()
    for name in scaled.index:
        name = str(name)
        vals = scaled.loc[name].tolist()
        fig.add_trace(go.Scatterpolar(
            r=vals + vals[:1], theta=labels + labels[:1], fill="toself", name=name,
            line=dict(color=ui.SEGMENT_COLORS[name]), opacity=0.55))
    ui.style_fig(fig, "Segment comparison (medians, min-max normalized)", height=460)
    fig.update_layout(polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 1], showticklabels=False, gridcolor="rgba(128,128,128,0.3)")))
    ui.show(fig, key="seg_radar")
    best = seg.sort_values("median_monetary", ascending=False).iloc[0]
    fresh = seg.sort_values("median_recency").iloc[0]
    ui.takeaway(
        "0 = lowest segment, 1 = highest segment in view. "
        f"{best['segment']} has the highest median revenue ({ui.gbp(best['median_monetary'])}); "
        f"{fresh['segment']} bought most recently (median {fresh['median_recency']:,.0f} days ago).")


@st.fragment
def _compare(view: pd.DataFrame) -> None:
    """Compare two segments side by side (reruns only this fragment)."""
    c1, c2 = st.columns(2)
    a = c1.selectbox("Segment A", ui.SEGMENTS, index=0, key="cmp_a")
    b = c2.selectbox("Segment B", ui.SEGMENTS, index=len(ui.SEGMENTS) - 1, key="cmp_b")
    if a == b:
        st.info("Pick two different segments.")
        return
    seg = data.segment_summary(view).set_index(
        data.segment_summary(view)["segment"].astype(str))
    metrics = [
        ("Customers", "customers", ui.num),
        ("Share of customers", "customer_share", ui.pct),
        ("Share of net revenue", "revenue_share", ui.pct),
        ("Median recency (days)", "median_recency", lambda v: f"{v:,.0f}"),
        ("Median orders", "median_frequency", lambda v: f"{v:,.0f}"),
        ("Median net revenue", "median_monetary", ui.gbp),
        ("Repeat-buyer rate", "repeat_rate", ui.pct),
        ("Avg order value", "mean_aov", ui.gbp),
    ]
    missing = [s for s in (a, b) if s not in seg.index]
    if missing:
        st.info(f"No customers in view for: {', '.join(missing)}.")
        return
    rows = []
    for label, key, fmt in metrics:
        va, vb = float(seg.loc[a, key]), float(seg.loc[b, key])
        ratio = f"x{vb / va:,.2f}" if va else "n/a"
        rows.append({"Metric": label, a: fmt(va), b: fmt(vb), "B vs A": ratio})
    ui.show_df(pd.DataFrame(rows), hide_index=True)
    ui.takeaway("B vs A is the ratio of B's value to A's value; both use the filtered customers.")


def render() -> None:
    _, view = data.get_view()
    ui.page_header("Segments", "Profiles, comparisons, and suggested actions for each segment.")
    if view.empty:
        ui.empty_state()
        return
    seg = data.segment_summary(view)
    present = seg["segment"].astype(str).tolist()

    # Selected segment is synced with the URL (?segment=...).
    qp = st.query_params.get("segment")
    if "focus_segment" not in st.session_state:
        st.session_state["focus_segment"] = qp if qp in ui.SEGMENTS else ui.SEGMENTS[0]
    focus = st.selectbox("Focus segment", ui.SEGMENTS, key="focus_segment",
                         help="Synced with the page URL, so you can share a link.")
    if st.query_params.get("segment") != focus:
        st.query_params["segment"] = focus

    tab_prof, tab_chart, tab_cmp = st.tabs(["Profiles", "Charts", "Compare"])

    with tab_prof:
        _profile_cards(seg)
        with st.expander(f"What to do: {focus}", expanded=True):
            st.markdown(f"**Suggested action to test:** {ui.SEGMENT_ACTIONS.get(focus, '')}")
            if focus in present:
                r = seg[seg["segment"].astype(str) == focus].iloc[0]
                st.markdown(
                    f"- {ui.num(r['customers'])} customers in view, "
                    f"{ui.pct(r['revenue_share'])} of net revenue\n"
                    f"- Median recency {r['median_recency']:,.0f} days, "
                    f"{r['median_frequency']:,.0f} orders, {ui.gbp(r['median_monetary'])} net revenue")
            else:
                st.caption("This segment has no customers under the current filters.")
            st.caption("Suggested actions are hypotheses to test (for example with an A/B test), not proven effects.")

    with tab_chart:
        _share_chart(seg)
        _scatter3d(view)
        _radar(seg)

    with tab_cmp:
        _compare(view)