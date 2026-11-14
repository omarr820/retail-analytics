"""Business Overview: time, product, and geography views (all transactions)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data, ui

# Country name (as in the dataset) -> ISO-3 code for the map.
# "Unspecified", "European Community" and "Channel Islands" have no single
# country polygon, so they are left out of the map (and reported in a note).
_ISO3 = {
    "United Kingdom": "GBR", "Germany": "DEU", "France": "FRA", "EIRE": "IRL",
    "Ireland": "IRL", "Spain": "ESP", "Netherlands": "NLD", "Belgium": "BEL",
    "Switzerland": "CHE", "Portugal": "PRT", "Australia": "AUS", "Norway": "NOR",
    "Italy": "ITA", "Finland": "FIN", "Cyprus": "CYP", "Sweden": "SWE",
    "Austria": "AUT", "Denmark": "DNK", "Japan": "JPN", "Poland": "POL",
    "Israel": "ISR", "USA": "USA", "United States": "USA", "Hong Kong": "HKG",
    "Singapore": "SGP", "Iceland": "ISL", "Canada": "CAN", "Greece": "GRC",
    "Malta": "MLT", "United Arab Emirates": "ARE", "RSA": "ZAF",
    "South Africa": "ZAF", "Lebanon": "LBN", "Lithuania": "LTU", "Brazil": "BRA",
    "Czech Republic": "CZE", "Czechia": "CZE", "Bahrain": "BHR",
    "Saudi Arabia": "SAU", "Korea": "KOR", "Thailand": "THA",
}

_MAP_SCALE = [[0.0, "#F3E6D3"], [0.35, "#E8A91E"], [0.7, "#C4533A"], [1.0, "#34193A"]]


def _revenue_axis(fig) -> None:
    fig.update_yaxes(title="Net revenue (GBP)", tickprefix="£", tickformat=",.0f")


def _country_map(ctry: pd.DataFrame) -> None:
    """World choropleth of net revenue or orders by country."""
    d = ctry.copy()
    d["iso3"] = d["Country"].map(_ISO3)
    mapped = d.dropna(subset=["iso3"]).copy()
    skipped = d[d["iso3"].isna() & (d["net_revenue"] != 0)]

    c1, c2, _ = st.columns([1.2, 1.6, 2])
    metric = c1.radio("Metric", ["Net revenue", "Orders"], horizontal=True, key="bo_map_metric")
    scale = c2.radio("Color scale", ["Log (shows small markets)", "Linear"],
                     horizontal=True, key="bo_map_scale",
                     help="The UK is so large that a linear scale leaves every other country pale.")
    field = "net_revenue" if metric == "Net revenue" else "orders"
    prefix = "£" if field == "net_revenue" else ""
    use_log = scale.startswith("Log")

    vals = mapped[field].clip(lower=1)
    colorbar = dict(title=metric, thickness=12, len=0.7, outlinewidth=0)
    if use_log:
        z = np.log10(vals)
        lo, hi = int(np.floor(z.min())), int(np.ceil(z.max()))
        ticks = list(range(lo, hi + 1))
        colorbar.update(tickvals=ticks, ticktext=[f"{prefix}{10 ** t:,.0f}" for t in ticks])
    else:
        z = vals
        colorbar.update(tickprefix=prefix, tickformat=",.0f")

    fig = go.Figure(go.Choropleth(
        locations=mapped["iso3"], locationmode="ISO-3", z=z, text=mapped["Country"],
        customdata=np.stack([mapped["net_revenue"], mapped["orders"]], axis=-1),
        hovertemplate=("<b>%{text}</b><br>Net revenue: £%{customdata[0]:,.0f}"
                       "<br>Orders: %{customdata[1]:,.0f}<extra></extra>"),
        colorscale=_MAP_SCALE, marker_line_color="#F7F0E3", marker_line_width=0.6,
        colorbar=colorbar))
    ui.style_fig(fig, f"{metric} by country", height=480, legend=False)
    fig.update_geos(
        projection_type="natural earth", showframe=False, showcoastlines=False,
        showland=True, landcolor="#EADFCB", showcountries=True,
        countrycolor="rgba(52,25,58,0.15)", bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-58, 85])
    fig.update_layout(margin=dict(l=0, r=0, t=56, b=0))
    ui.show(fig, key="bo_map")

    n_markets = int((mapped["orders"] > 0).sum())
    nonuk = mapped[mapped["Country"] != "United Kingdom"].sort_values(field, ascending=False)
    note = ""
    if not nonuk.empty:
        top = nonuk.iloc[0]
        note = (f" Largest market outside the UK: {top['Country']} "
                f"({prefix}{top[field]:,.0f}).")
    if len(skipped):
        note += (" Not drawn (no single country): "
                 + ", ".join(skipped["Country"].astype(str)) + ".")
    ui.takeaway(f"{n_markets} countries placed orders.{note}")


def render() -> None:
    ui.page_header("Business Overview", "Revenue over time, products, and countries (all transactions).",
                   eyebrow="Business")
    try:
        agg = data.business_aggregates()
    except data.DataError as exc:
        st.error(str(exc), icon=":material/error:")
        return

    monthly_all = agg["monthly"]
    uk_df = agg["uk_split"]
    uk_share = (uk_df.loc[uk_df["region"] == "United Kingdom", "net_revenue"].sum()
                / uk_df["net_revenue"].sum())
    ui.kpi_row([
        ("Net revenue", ui.gbp_short(monthly_all["net_revenue"].sum()), "all transactions, cancellations netted"),
        ("Sales invoices", ui.num(monthly_all["invoices"].sum()), "unique invoices, sales lines only"),
        ("Countries", ui.num((agg["countries"]["orders"] > 0).sum()), "with at least one order"),
        ("UK share", ui.pct(uk_share), "of net revenue"),
    ], colors=[ui.TERRA, ui.TEAL, ui.SAFFRON, ui.SAGE])
    st.caption("Uses every transaction line, including guest checkouts. Sidebar filters do not apply. "
               "Net revenue includes cancellations; product rankings use sales lines only.")

    tab_t, tab_p, tab_g = st.tabs(["Time", "Products", "Geography"])

    with tab_t:
        monthly = monthly_all.copy()
        last = agg["last_date"]
        incomplete = (last.strftime("%Y-%m")
                      if last.normalize() < (last + pd.offsets.MonthEnd(0)).normalize() else None)
        label_inc = f"Incomplete (data ends {last:%b %d, %Y})"
        monthly["status"] = np.where(monthly["YearMonth"] == incomplete, label_inc, "Complete month")
        with ui.card():
            fig = px.bar(monthly, x="YearMonth", y="net_revenue", color="status",
                         color_discrete_map={"Complete month": ui.TERRA, label_inc: ui.NEUTRAL},
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
        fig = px.bar(wk, x="DayOfWeek", y="net_revenue", color_discrete_sequence=[ui.TEAL])
        for d in agg["missing_days"]:
            fig.add_annotation(x=d, y=0, text="no data", showarrow=False, yshift=14)
        ui.style_fig(fig, "Net revenue by weekday", legend=False)
        fig.update_xaxes(title="")
        _revenue_axis(fig)
        with c1, ui.card():
            ui.show(fig, key="bo_wk")
            lead = wk.sort_values("net_revenue", ascending=False).iloc[0]
            note = (f" No transactions exist for {', '.join(agg['missing_days'])}." if agg["missing_days"] else "")
            ui.takeaway(f"{lead['DayOfWeek']} has the highest net revenue ({ui.gbp(lead['net_revenue'])}).{note}")

        hr = agg["hourly"]
        fig = px.bar(hr, x="Hour", y="net_revenue", color_discrete_sequence=[ui.SAFFRON])
        ui.style_fig(fig, "Net revenue by hour of day", legend=False)
        fig.update_xaxes(title="Hour of day", dtick=1)
        _revenue_axis(fig)
        with c2, ui.card():
            ui.show(fig, key="bo_hr")
            peak = hr.sort_values("net_revenue", ascending=False).iloc[0]
            ui.takeaway(f"Peak hour is {int(peak['Hour']):02d}:00 ({ui.gbp(peak['net_revenue'])}).")

    with tab_p:
        c1, c2 = st.columns(2)
        for col, key, title, xlabel, fmt, color in (
            (c1, "top_revenue", "Top 10 products by revenue", "Revenue (GBP)", "£%{x:,.0f}", ui.ACCENT),
            (c2, "top_units", "Top 10 products by units", "Units sold", "%{x:,.0f} units", ui.TERRA),
        ):
            field = "revenue" if key == "top_revenue" else "units"
            d = agg[key].sort_values(field)
            fig = px.bar(d, x=field, y="name", orientation="h", color_discrete_sequence=[color])
            fig.update_traces(hovertemplate="%{y}<br>" + fmt + "<extra></extra>")
            ui.style_fig(fig, title, height=420, legend=False)
            fig.update_xaxes(title=xlabel)
            fig.update_yaxes(title="")
            with col, ui.card():
                ui.show(fig, key=f"bo_{key}")
                lead = agg[key].iloc[0]
                ui.takeaway(f"{lead['name']} leads with {ui.gbp(lead['revenue'])} revenue and {lead['units']:,.0f} units.")
        st.caption("Sales lines only (cancellations excluded). Product name = most frequent Description per StockCode.")

    with tab_g:
        ctry = agg["countries"]
        with ui.card():
            _country_map(ctry)

        c1, c2 = st.columns([3, 2])
        nonuk = ctry[ctry["Country"] != "United Kingdom"].head(10).sort_values("net_revenue")
        fig = px.bar(nonuk, x="net_revenue", y="Country", orientation="h",
                     color_discrete_sequence=[ui.TEAL], hover_data={"orders": ":,.0f"})
        ui.style_fig(fig, "Top 10 countries outside the UK", height=420, legend=False)
        fig.update_xaxes(title="Net revenue (GBP)", tickprefix="£", tickformat=",.0f")
        fig.update_yaxes(title="")
        with c1, ui.card():
            ui.show(fig, key="bo_ctry")
            top = nonuk.iloc[-1]
            ui.takeaway(f"{top['Country']} is the largest non-UK market ({ui.gbp(top['net_revenue'])}).")

        uk = agg["uk_split"]
        fig = px.pie(uk, names="region", values="net_revenue", hole=0.58,
                     color="region", color_discrete_map={"United Kingdom": ui.PLUM, "Rest of world": ui.SAFFRON})
        fig.update_traces(textinfo="percent",
                          hovertemplate="%{label}<br>£%{value:,.0f} (%{percent})<extra></extra>")
        ui.style_fig(fig, "UK vs rest of world", height=420)
        with c2, ui.card():
            ui.show(fig, key="bo_uk")
            share = uk.loc[uk["region"] == "United Kingdom", "net_revenue"].sum() / uk["net_revenue"].sum()
            ui.takeaway(f"The UK accounts for {ui.pct(share)} of net revenue.")