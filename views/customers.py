"""Customers: searchable table, single-customer detail, downloads."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import data, ui


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _detail(df_all: pd.DataFrame, cid: str) -> None:
    row = df_all[df_all["CustomerID"] == cid]
    if row.empty:
        st.warning(f"Customer {cid} was not found.")
        return
    r = row.iloc[0]
    seg = str(r["segment"])
    st.subheader(f"Customer {cid}")
    ui.kpi_row([
        ("Segment", seg, "Key account" if r["is_outlier"] else "Regular customer"),
        ("RFM string", str(r["RFM_Score"]), f"RFM sum {int(r['RFM_Sum'])}"),
        ("Recency", f"{r['recency']:,.0f} days", f"last order {r['last_purchase']:%Y-%m-%d}"),
    ], per_row=3)
    ui.kpi_row([
        ("Orders", ui.num(r["frequency"]), f"avg order {ui.gbp(r['avg_order_value'])}"),
        ("Net revenue", ui.gbp(r["monetary"]), f"cancelled value {ui.gbp(abs(r['cancelled_value']))}"),
        ("Tenure", f"{r['tenure_days']:,.0f} days", f"first order {r['first_purchase']:%Y-%m-%d}"),
    ], per_row=3)

    labels = ["Recency (more recent = higher)", "Frequency", "Monetary"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=[r["pct_recency"], r["pct_frequency"], r["pct_monetary"]],
        orientation="h", name="All customers", marker_color=ui.NEUTRAL))
    fig.add_trace(go.Bar(
        y=labels, x=[r["seg_pct_recency"], r["seg_pct_frequency"], r["seg_pct_monetary"]],
        orientation="h", name=f"Within {seg}", marker_color=ui.SEGMENT_COLORS[seg]))
    fig.add_vline(x=50, line_dash="dash", line_color=ui.NEUTRAL)
    ui.style_fig(fig, "Percentile rank versus all customers and within the segment", height=320)
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="Percentile (0-100)", range=[0, 100])
    ui.show(fig, key="cust_pct")
    ui.takeaway(
        f"Net revenue is higher than {r['pct_monetary']:.0f}% of all customers and "
        f"{r['seg_pct_monetary']:.0f}% of {seg} customers.")


def render() -> None:
    df_all, view = data.get_view()
    ui.page_header("Customers", "Search the customer table and open a single-customer view.")
    if view.empty:
        ui.empty_state()
        return

    q = st.text_input("Search by CustomerID", placeholder="e.g. 14646",
                      help="Matches any part of the ID.")
    shown = view
    if q.strip():
        shown = view[view["CustomerID"].str.contains(q.strip(), case=False, regex=False)]
    if shown.empty:
        st.info("No customer matches that ID within the current filters.")
        return
    shown = shown.sort_values("monetary", ascending=False)
    table = ui.table_frame(shown)

    st.caption(f"{len(table):,} customers. Click a header to sort; click a row to open its detail.")
    event = ui.show_df(
        table, column_config=ui.table_config(df_all["revenue_share_pct"].max()),
        hide_index=True, on_select="rerun", selection_mode="single-row",
        key="cust_table", height=420)
    rows = getattr(getattr(event, "selection", None), "rows", [])

    pick = st.selectbox("Or pick a customer", table["CustomerID"].tolist(), index=None,
                        placeholder="Type a CustomerID", key="cust_pick",
                        help="A selected table row takes priority over this box.")
    cid = table.iloc[rows[0]]["CustomerID"] if rows else pick

    c1, c2 = st.columns(2)
    c1.download_button("Download filtered table (CSV)",
                       _csv(shown[data.CUSTOMER_COLUMNS]), "customers_filtered.csv",
                       "text/csv", icon=":material/download:")
    summary = data.segment_summary(view)
    c2.download_button("Download segment summary (CSV)", _csv(summary),
                       "segment_summary.csv", "text/csv", icon=":material/download:")

    if cid:
        st.divider()
        _detail(df_all, str(cid))