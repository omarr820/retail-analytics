"""Key Accounts: DBSCAN outliers."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src import data, ui


def render() -> None:
    df_all, view = data.get_view(force_outliers=True)
    ui.page_header("Key Accounts", "Customers DBSCAN flagged as outliers: very large or unusual buyers.")
    ka = view[view["is_outlier"]]
    st.caption("The sidebar toggle for key accounts is ignored here; all other filters apply.")
    if ka.empty:
        st.info("No key accounts match the current filters.", icon=":material/filter_alt_off:")
        return

    others = view[~view["is_outlier"]]
    ui.kpi_row([
        ("Key accounts", ui.num(len(ka)), f"{ui.pct(len(ka) / len(df_all))} of all customers"),
        ("Revenue share", ui.pct(ka["monetary"].sum() / df_all["monetary"].sum()),
         "of all customers' net revenue"),
        ("Median orders", f"{ka['frequency'].median():,.0f}",
         f"others in view: {others['frequency'].median():,.0f}" if len(others) else ""),
        ("Median net revenue", ui.gbp(ka["monetary"].median()),
         f"others in view: {ui.gbp(others['monetary'].median())}" if len(others) else ""),
    ])

    tab_t, tab_s, tab_d = st.tabs(["Table", "Frequency vs revenue", "Segment distribution"])

    with tab_t:
        table = ui.table_frame(ka.sort_values("monetary", ascending=False))
        ui.show_df(table, column_config=ui.table_config(df_all["revenue_share_pct"].max()),
                   hide_index=True)
        st.download_button("Download key accounts (CSV)",
                           ka[data.CUSTOMER_COLUMNS].to_csv(index=False).encode("utf-8"),
                           "key_accounts.csv", "text/csv", icon=":material/download:")

    with tab_s:
        plot = ka.assign(region=ka["is_uk"].map({True: "UK", False: "Non-UK"}))
        fig = px.scatter(plot, x="frequency", y="monetary", color="segment",
                         log_x=True, log_y=True, hover_name="CustomerID",
                         color_discrete_map=ui.SEGMENT_COLORS, category_orders={"segment": ui.SEGMENTS},
                         hover_data={"recency": ":,.0f", "frequency": ":,.0f",
                                     "monetary": ":,.0f", "region": True, "segment": False},
                         labels={"frequency": "Orders (log)", "monetary": "Net revenue, GBP (log)"})
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color="rgba(0,0,0,0.5)")))
        ui.style_fig(fig, "Key accounts: orders vs net revenue")
        ui.show(fig, key="ka_scatter")
        top = ka.sort_values("monetary", ascending=False).iloc[0]
        ui.takeaway(f"The largest account is {top['CustomerID']} with {ui.gbp(top['monetary'])} "
                    f"net revenue from {top['frequency']:,.0f} orders.")

    with tab_d:
        counts = (ka["segment"].astype(str).value_counts()
                  .reindex(ui.SEGMENTS).dropna().rename("customers").reset_index())
        counts.columns = ["segment", "customers"]
        fig = px.bar(counts, x="segment", y="customers", color="segment",
                     color_discrete_map=ui.SEGMENT_COLORS, category_orders={"segment": ui.SEGMENTS},
                     text="customers")
        ui.style_fig(fig, "K-Means segment of key accounts", legend=False)
        fig.update_xaxes(title="")
        fig.update_yaxes(title="Key accounts")
        ui.show(fig, key="ka_dist")
        lead = counts.sort_values("customers", ascending=False).iloc[0]
        ui.takeaway(f"{int(lead['customers'])} of {len(ka)} key accounts sit in the {lead['segment']} segment.")