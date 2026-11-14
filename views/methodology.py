"""Methodology: decisions, definitions, and limitations."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src import data, ui


def render() -> None:
    df_all = data.load_customers()
    ui.page_header("Methodology", "How the data was cleaned, scored, and segmented, and where it falls short.")

    tab_c, tab_r, tab_s, tab_l = st.tabs(["Cleaning", "RFM", "Segmentation", "Limitations"])

    with tab_c:
        st.markdown(
            "The raw file has **541,909** invoice lines. After cleaning, **531,235** remain; "
            "**10,674** were removed or isolated. Every removal is stored in its own table "
            "with a documented reason. Nothing is dropped silently.")
        steps = pd.DataFrame([
            ("Fully duplicated rows", 5268, "Likely double entries that would count revenue twice."),
            ("Inventory adjustments", 1336, "Negative quantity without a cancellation prefix, zero price, no customer."),
            ("Zero or negative price", 1176, "Stock corrections, gifts, and accounting entries; not sales."),
            ("Non-product codes", 2890, "Shipping, fees, commissions, discounts, manual entries."),
            ("Fully reversed orders", 4, "Two huge orders cancelled within minutes (net effect zero)."),
        ], columns=["Step", "Rows", "Reason"])
        ui.show_df(steps, hide_index=True)
        st.markdown(
            "- Cancellations (invoices starting with `C`) are **kept** and netted against revenue.\n"
            "- Guest checkouts (no CustomerID) stay in sales analysis but are excluded from customer analysis.\n"
            "- All revenue figures are product revenue (shipping and fees excluded).")

    with tab_r:
        st.markdown(
            "- **Recency:** days from last purchase to the snapshot date, 2011-12-10 (last transaction date + 1 day).\n"
            "- **Frequency:** unique sales invoices. **Monetary:** net revenue in GBP.\n"
            "- Each metric gets a 1-5 score with `pd.qcut` (frequency is ranked first because of ties). "
            "Recency is reversed, so 5 = most recent.\n"
            "- The three scores form the RFM string (for example `555`).")

    with tab_s:
        st.markdown(
            "- **Preprocessing:** `log1p` on recency, frequency, and monetary, then `StandardScaler`. "
            "CustomerID and the R/F/M scores are not used as features.\n"
            "- **K-Means with K=5** (silhouette 0.318, `random_state=42`). K was chosen from the elbow, "
            "silhouette, Davies-Bouldin, stability across random starts, and the marketing meaning of "
            "each segment. Statistics alone favored a coarser split.\n"
            "- **Hierarchical (Ward)** on a sample of customers and **DBSCAN** (`eps=0.6`, `min_samples=6`) "
            f"as comparisons. DBSCAN flags **{int(df_all['is_outlier'].sum())}** key accounts.\n"
            "- **Segment names** come from the cluster medians (recency, frequency, monetary), "
            "not from a ready-made template.")
        mapping = df_all.groupby("segment", observed=True).agg(
            kmeans_cluster=("kmeans", lambda s: ", ".join(map(str, sorted(s.unique())))),
            customers=("CustomerID", "size"),
            median_recency=("recency", "median"),
            median_frequency=("frequency", "median"),
            median_monetary=("monetary", "median"),
        ).reset_index()
        mapping["segment"] = mapping["segment"].astype(str)
        ui.show_df(mapping, hide_index=True)
        st.caption("Computed from the data: which K-Means cluster each segment name maps to.")

    with tab_l:
        st.markdown(
            "- One year of data, with December 2011 incomplete, so seasonality cannot be separated from growth.\n"
            "- Segments cover registered customers only; guest checkouts are excluded.\n"
            "- Segment borders are soft (silhouette 0.318); the data looks like a continuum.\n"
            "- No Saturday transactions exist in the data.\n"
            "- Findings are descriptive; no causal claims are made.\n"
            "- Suggested actions are hypotheses to validate with A/B tests.")