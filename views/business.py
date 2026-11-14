"""Business Overview: time, product, and geography views (all transactions)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src import data, ui


def _revenue_axis(fig) -> None:
    fig.update_yaxes(title="Net revenue (GBP)", tickprefix="£", tickformat=",.0f")


def render() -> None:
    ui.page_header("Business Overview", "Revenue over time, products, and countries (all transactions).")
    try:
        agg = data.business_aggregates()
    except data.DataError as exc:
        st.error(str(exc), icon=":material/error:")
        return
    st.caption("Uses every transaction line, including guest checkouts. Sidebar filters do not apply. "
               "Net revenue includes cancellations; product rankings use sales lines only.")

    tab_t, tab_p, tab_g = st.tabs(["Time", "Products", "Geography"])

    with tab_t:
        monthly = agg["monthly"].copy()
        last = agg["last_date"]
        incomplete = (last.strftime("%Y-%m")
                      if last.normalize() < (last + pd.offsets.MonthEnd(0)).normalize() else None)
        label_inc = f"Incomplete (data ends {last:%b %d, %Y})"
        monthly["status"] = np.where(monthly["YearMonth"] == incomplete, label_inc, "Complete month")
        fig = px.bar(monthly, x="YearMonth", y="net_revenue", color="status",
                     color_discrete_map={"Complete month": ui.ACCENT, label_inc: ui.NEUTRAL},
                     hover_data={"invoices": ":,.0f"})
        ui.style_fig(fig, "Monthly net revenue")
        fig.update_xaxes(title="Month")
        _revenue_axis(fig)
        ui.show(fig, key="bo_month")
        full = monthly[monthly["status"] == "Complete month"]
        best = full.loc[full["net_revenue"].idxmax()]
        ui.takeaway(f"{best['YearMonth']} is the strongest complete month ({ui.gbp(best['net_revenue'])})."
                    + (f" {incomplete} is incomplete, so it is not comparable to a full month." if incomplete else ""))

        c1, c2 = st.columns(2)
        wk = agg["weekday"]
        fig = px.bar(wk, x="DayOfWeek", y="net_revenue", color_discrete_sequence=[ui.ACCENT])
        for d in agg["missing_days"]:
            fig.add_annotation(x=d, y=0, text="no data", showarrow=False, yshift=14)
        ui.style_fig(fig, "Net revenue by weekday", legend=False)
        fig.update_xaxes(title="")
        _revenue_axis(fig)
        with c1:
            ui.show(fig, key="bo_wk")
            lead = wk.sort_values("net_revenue", ascending=False).iloc[0]
            note = (f" No transactions exist for {', '.join(agg['missing_days'])}." if agg["missing_days"] else "")
            ui.takeaway(f"{lead['DayOfWeek']} has the highest net revenue ({ui.gbp(lead['net_revenue'])}).{note}")

        hr = agg["hourly"]
        fig = px.bar(hr, x="Hour", y="net_revenue", color_discrete_sequence=[ui.ACCENT])
        ui.style_fig(fig, "Net revenue by hour of day", legend=False)
        fig.update_xaxes(title="Hour of day", dtick=1)
        _revenue_axis(fig)
        with c2:
            ui.show(fig, key="bo_hr")
            peak = hr.sort_values("net_revenue", ascending=False).iloc[0]
            ui.takeaway(f"Peak hour is {int(peak['Hour']):02d}:00 ({ui.gbp(peak['net_revenue'])}).")

    with tab_p:
        c1, c2 = st.columns(2)
        for col, key, title, xlabel, fmt in (
            (c1, "top_revenue", "Top 10 products by revenue", "Revenue (GBP)", "£%{x:,.0f}"),
            (c2, "top_units", "Top 10 products by units", "Units sold", "%{x:,.0f} units"),
        ):
            field = "revenue" if key == "top_revenue" else "units"
            d = agg[key].sort_values(field)
            fig = px.bar(d, x=field, y="name", orientation="h", color_discrete_sequence=[ui.ACCENT])
            fig.update_traces(hovertemplate="%{y}<br>" + fmt + "<extra></extra>")
            ui.style_fig(fig, title, height=420, legend=False)
            fig.update_xaxes(title=xlabel)
            fig.update_yaxes(title="")
            with col:
                ui.show(fig, key=f"bo_{key}")
                lead = agg[key].iloc[0]
                ui.takeaway(f"{lead['name']} leads with {ui.gbp(lead['revenue'])} revenue and {lead['units']:,.0f} units.")
        st.caption("Sales lines only (cancellations excluded). Product name = most frequent Description per StockCode.")

    with tab_g:
        ctry = agg["countries"]
        c1, c2 = st.columns([3, 2])
        nonuk = ctry[ctry["Country"] != "United Kingdom"].head(10).sort_values("net_revenue")
        fig = px.bar(nonuk, x="net_revenue", y="Country", orientation="h",
                     color_discrete_sequence=[ui.ACCENT], hover_data={"orders": ":,.0f"})
        ui.style_fig(fig, "Top 10 countries outside the UK", height=420, legend=False)
        fig.update_xaxes(title="Net revenue (GBP)", tickprefix="£", tickformat=",.0f")
        fig.update_yaxes(title="")
        with c1:
            ui.show(fig, key="bo_ctry")
            top = nonuk.iloc[-1]
            ui.takeaway(f"{top['Country']} is the largest non-UK market ({ui.gbp(top['net_revenue'])}).")

        uk = agg["uk_split"]
        fig = px.pie(uk, names="region", values="net_revenue", hole=0.55,
                     color="region", color_discrete_map={"United Kingdom": ui.ACCENT, "Rest of world": ui.NEUTRAL})
        fig.update_traces(textinfo="percent",
                          hovertemplate="%{label}<br>£%{value:,.0f} (%{percent})<extra></extra>")
        ui.style_fig(fig, "UK vs rest of world", height=420)
        with c2:
            ui.show(fig, key="bo_uk")
            share = uk.loc[uk["region"] == "United Kingdom", "net_revenue"].sum() / uk["net_revenue"].sum()
            ui.takeaway(f"The UK accounts for {ui.pct(share)} of net revenue.")
