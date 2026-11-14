"""RFM: score distributions, R x F heatmap, RFM strings."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src import data, ui

_CATS = {"segment": ui.SEGMENTS}
_HEAT_SCALE = [[0.0, "#F7F0E3"], [0.45, "#E8A91E"], [0.75, "#C4533A"], [1.0, "#34193A"]]


@st.fragment
def _distributions(view: pd.DataFrame) -> None:
    """Distribution picker (reruns only this fragment)."""
    choice = st.radio("Distribution", ["Recency", "Frequency", "Monetary"],
                      horizontal=True, key="rfm_dist")
    plot = view.assign(
        log10_frequency=np.log10(view["frequency"]),
        log10_monetary=np.log10(view["monetary"]),
    )
    spec = {
        "Recency": ("recency", "Recency (days since last order)"),
        "Frequency": ("log10_frequency", "log10(orders)  [0 = 1 order, 1 = 10 orders]"),
        "Monetary": ("log10_monetary", "log10(net revenue)  [2 = £100, 3 = £1,000]"),
    }
    col, xlabel = spec[choice]
    fig = px.histogram(plot, x=col, color="segment", nbins=40, barmode="stack",
                       color_discrete_map=ui.SEGMENT_COLORS, category_orders=_CATS)
    ui.style_fig(fig, f"{choice} distribution by segment")
    fig.update_xaxes(title=xlabel)
    fig.update_yaxes(title="Customers")
    ui.show(fig, key=f"rfm_hist_{choice}")
    if choice == "Recency":
        ui.takeaway(f"Median recency is {view['recency'].median():,.0f} days; "
                    f"{ui.pct((view['recency'] <= 30).mean())} of customers ordered in the last 30 days.")
    elif choice == "Frequency":
        ui.takeaway(f"Median customer placed {view['frequency'].median():,.0f} orders; "
                    f"{ui.pct((view['frequency'] == 1).mean())} placed exactly one.")
    else:
        ui.takeaway(f"Median net revenue per customer is {ui.gbp(view['monetary'].median())}, "
                    f"against a mean of {ui.gbp(view['monetary'].mean())} (right-skewed).")


def render() -> None:
    _, view = data.get_view()
    ui.page_header("RFM", "Recency, frequency, and monetary scores across customers.",
                   eyebrow="Customers")
    if view.empty:
        ui.empty_state()
        return

    ui.kpi_row([
        ("Median recency", f"{view['recency'].median():,.0f} d", "days since last order"),
        ("Median orders", f"{view['frequency'].median():,.0f}", "invoices per customer"),
        ("Median net revenue", ui.gbp(view["monetary"].median()), f"mean {ui.gbp(view['monetary'].mean())}"),
        ("One-order customers", ui.pct((view["frequency"] == 1).mean()), "placed exactly one order"),
    ], colors=[ui.TERRA, ui.TEAL, ui.SAFFRON, ui.SAGE])

    with st.expander("How to read the scores"):
        st.markdown(
            "- **R (recency):** 5 = most recent buyers, 1 = longest since last order.\n"
            "- **F (frequency):** 5 = most orders, 1 = fewest.\n"
            "- **M (monetary):** 5 = highest net revenue, 1 = lowest.\n"
            "- The RFM string joins the three scores, e.g. `555` is the best profile; "
            "RFM sum adds them (3 to 15).")

    ui.section("Distributions", "How customers spread across each dimension")
    with ui.card():
        _distributions(view)

    ui.section("R x F heatmap", "Where the money sits")
    sc = view.assign(R=view["R"].astype(int), F=view["F"].astype(int))
    pivot = (sc.pivot_table(index="R", columns="F", values="monetary", aggfunc="mean")
             .reindex(index=[5, 4, 3, 2, 1], columns=[1, 2, 3, 4, 5]))
    with ui.card():
        fig = px.imshow(pivot, text_auto=",.0f", aspect="auto", color_continuous_scale=_HEAT_SCALE,
                        labels=dict(x="F score (frequency)", y="R score (recency)",
                                    color="Avg net revenue (GBP)"))
        fig.update_xaxes(type="category")
        fig.update_yaxes(type="category")
        ui.style_fig(fig, "Average net revenue by R and F score", height=400, legend=False)
        ui.show(fig, key="rfm_heat")
        stacked = pivot.stack()
        if not stacked.empty:
            (r_best, f_best), v_best = stacked.idxmax(), stacked.max()
            ui.takeaway(f"The highest average net revenue ({ui.gbp(v_best)}) is in the R={r_best}, "
                        f"F={f_best} cell; empty cells have no customers.")

    ui.section("Revenue by RFM sum")
    by_sum = view.groupby("RFM_Sum")["monetary"].sum().reset_index()
    by_sum["share_pct"] = by_sum["monetary"] / by_sum["monetary"].sum() * 100
    with ui.card():
        fig = px.bar(by_sum, x="RFM_Sum", y="share_pct", color_discrete_sequence=[ui.TEAL])
        fig.update_traces(hovertemplate="RFM sum %{x}<br>%{y:.1f}% of net revenue<extra></extra>")
        ui.style_fig(fig, "Share of net revenue by RFM sum", legend=False)
        fig.update_xaxes(title="RFM sum (3 = lowest, 15 = highest)", dtick=1)
        fig.update_yaxes(title="Share of net revenue (%)", ticksuffix="%")
        ui.show(fig, key="rfm_sum")
        top = by_sum.sort_values("share_pct", ascending=False).iloc[0]
        ui.takeaway(f"RFM sum {int(top['RFM_Sum'])} carries the largest revenue share ({top['share_pct']:.1f}%).")

    ui.section("Top RFM strings", "The 15 profiles with the most revenue")
    strings = view.groupby("RFM_Score").agg(
        customers=("CustomerID", "size"), revenue=("monetary", "sum"),
        median_recency=("recency", "median")).reset_index()
    strings["revenue_share"] = strings["revenue"] / strings["revenue"].sum() * 100
    strings = strings.sort_values("revenue_share", ascending=False).head(15)
    strings["RFM_Score"] = strings["RFM_Score"].astype(str)
    cc = st.column_config
    ui.show_df(
        strings[["RFM_Score", "customers", "revenue_share", "median_recency"]],
        hide_index=True,
        column_config={
            "RFM_Score": cc.TextColumn("RFM string"),
            "customers": cc.NumberColumn("Customers", format="%d"),
            "revenue_share": cc.ProgressColumn("Share of net revenue", format="%.1f%%",
                                               min_value=0.0, max_value=float(strings["revenue_share"].max())),
            "median_recency": cc.NumberColumn("Median recency (days)", format="%d"),
        })
    ui.takeaway(f"The top 15 RFM strings hold {strings['revenue_share'].sum():.1f}% of net revenue in view.")