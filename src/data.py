"""Cached loaders, shared filter logic, and aggregations."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from src.segments import SEGMENT_ORDER, load_segments

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS_PATH = ROOT / "data" / "customer_segments.parquet"
TRANSACTIONS_PATH = ROOT / "data" / "clean_transactions.parquet"

CUSTOMER_COLUMNS = [
    "CustomerID", "frequency", "gross_revenue", "avg_order_value",
    "avg_units_per_order", "avg_lines_per_order", "first_purchase",
    "last_purchase", "recency", "tenure_days", "cancelled_value", "monetary",
    "is_uk", "R", "F", "M", "RFM_Score", "RFM_Sum", "kmeans", "dbscan",
    "is_outlier", "segment",
]
TX_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
    "Country", "DayOfWeek", "Hour", "IsCancellation", "TotalLineRevenue",
    "Is_UK", "YearMonth",
]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]

# Session-state keys for the global filters.
K_SEG, K_COUNTRY = "f_segments", "f_country"
K_REC, K_FREQ, K_MON, K_OUT = "f_recency", "f_frequency", "f_monetary", "f_outliers"


class DataError(Exception):
    """Raised with a user-friendly message when data cannot be loaded."""


# ------------------------------------------------------------------ customers
@st.cache_data(show_spinner="Loading customers...")
def load_customers() -> pd.DataFrame:
    """Load customer_segments.parquet and add derived columns."""
    if not SEGMENTS_PATH.exists():
        raise DataError(
            f"Missing file: {SEGMENTS_PATH.relative_to(ROOT)}. Commit it to "
            "the repo (see README / deployment steps)."
        )
    df = load_segments(SEGMENTS_PATH)
    missing = [c for c in CUSTOMER_COLUMNS if c not in df.columns]
    if missing:
        raise DataError(f"customer_segments.parquet is missing columns: {missing}")

    df = df.copy()
    unknown = set(df["segment"].astype(str)) - set(map(str, SEGMENT_ORDER))
    if unknown:
        raise DataError(f"Unknown segment names in data: {sorted(unknown)}")

    df["CustomerID"] = df["CustomerID"].astype(str)
    for col in ("first_purchase", "last_purchase"):
        df[col] = pd.to_datetime(df[col])
    df["is_uk"] = df["is_uk"].astype(bool)
    df["is_outlier"] = df["is_outlier"].astype(bool)
    df["segment"] = pd.Categorical(
        df["segment"].astype(str),
        categories=[str(s) for s in SEGMENT_ORDER],
        ordered=True,
    )

    total = df["monetary"].sum()
    df["revenue_share_pct"] = df["monetary"] / total * 100

    # Percentile ranks (0-100) versus all customers and within the segment.
    df["pct_recency"] = df["recency"].rank(pct=True, ascending=False) * 100
    df["pct_frequency"] = df["frequency"].rank(pct=True) * 100
    df["pct_monetary"] = df["monetary"].rank(pct=True) * 100
    grp = df.groupby("segment", observed=True)
    df["seg_pct_recency"] = grp["recency"].rank(pct=True, ascending=False) * 100
    df["seg_pct_frequency"] = grp["frequency"].rank(pct=True) * 100
    df["seg_pct_monetary"] = grp["monetary"].rank(pct=True) * 100
    return df


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-segment metrics for the rows in `df` (only segments present)."""
    if df.empty:
        return pd.DataFrame()
    n, total = len(df), df["monetary"].sum()
    out = df.groupby("segment", observed=True).agg(
        customers=("CustomerID", "size"),
        revenue=("monetary", "sum"),
        median_recency=("recency", "median"),
        median_frequency=("frequency", "median"),
        median_monetary=("monetary", "median"),
        repeat_rate=("frequency", lambda s: (s >= 2).mean()),
        mean_aov=("avg_order_value", "mean"),
    )
    out["customer_share"] = out["customers"] / n
    out["revenue_share"] = out["revenue"] / total
    return out.reset_index()


# -------------------------------------------------------------------- filters
def monetary_options(df: pd.DataFrame) -> list[float]:
    """Slider steps that follow customer percentiles (monetary is very skewed)."""
    lo = float(np.floor(df["monetary"].min()))
    hi = float(np.ceil(df["monetary"].max()))
    q = np.quantile(df["monetary"], np.linspace(0, 1, 101))
    opts = sorted(set(np.round(q).astype(float)) | {lo, hi})
    return [o for o in opts if lo <= o <= hi]


def filter_defaults(df: pd.DataFrame) -> dict:
    """Default (= no filtering) value for every global filter."""
    mon = monetary_options(df)
    return {
        K_SEG: [str(s) for s in SEGMENT_ORDER],
        K_COUNTRY: "All",
        K_REC: (int(df["recency"].min()), int(df["recency"].max())),
        K_FREQ: (int(df["frequency"].min()), int(df["frequency"].max())),
        K_MON: (mon[0], mon[-1]),
        K_OUT: True,
    }


def apply_filters(df: pd.DataFrame, state, force_outliers: bool = False) -> pd.DataFrame:
    """Apply the global filters stored in `state` (st.session_state)."""
    mask = df["segment"].astype(str).isin(state.get(K_SEG, list(map(str, SEGMENT_ORDER))))
    country = state.get(K_COUNTRY, "All")
    if country == "UK":
        mask &= df["is_uk"]
    elif country == "Non-UK":
        mask &= ~df["is_uk"]
    for key, col in ((K_REC, "recency"), (K_FREQ, "frequency"), (K_MON, "monetary")):
        rng = state.get(key)
        if rng:
            mask &= df[col].between(rng[0], rng[1])
    include_outliers = True if force_outliers else state.get(K_OUT, True)
    if not include_outliers:
        mask &= ~df["is_outlier"]
    return df[mask]


def get_view(force_outliers: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (all customers, customers after the sidebar filters)."""
    df = load_customers()
    return df, apply_filters(df, st.session_state, force_outliers)


# --------------------------------------------------------------- transactions
def transactions_available() -> bool:
    """True if the optional transactions file is deployed."""
    return TRANSACTIONS_PATH.exists()


@st.cache_data(show_spinner="Aggregating transactions...")
def business_aggregates() -> dict:
    """Pre-aggregate clean_transactions.parquet for the Business Overview."""
    if not TRANSACTIONS_PATH.exists():
        raise DataError(
            f"Missing file: {TRANSACTIONS_PATH.relative_to(ROOT)} "
            "(optional; the Business Overview page needs it)."
        )
    try:
        tx = pd.read_parquet(TRANSACTIONS_PATH, columns=TX_COLUMNS)
    except Exception as exc:
        raise DataError(
            "Could not read clean_transactions.parquet with the expected "
            f"columns {TX_COLUMNS}: {exc}"
        ) from exc

    tx["IsCancellation"] = tx["IsCancellation"].astype(bool)
    tx["InvoiceDate"] = pd.to_datetime(tx["InvoiceDate"])
    tx["InvoiceNo"] = tx["InvoiceNo"].astype(str)
    sales = tx[~tx["IsCancellation"]]

    # Net revenue views (cancellations included).
    monthly = tx.groupby("YearMonth", as_index=False).agg(net_revenue=("TotalLineRevenue", "sum"))
    monthly["invoices"] = monthly["YearMonth"].map(sales.groupby("YearMonth")["InvoiceNo"].nunique())

    weekday = (
        tx.groupby("DayOfWeek")["TotalLineRevenue"].sum()
        .reindex(WEEKDAYS).fillna(0).rename("net_revenue").reset_index()
    )
    missing_days = [d for d in WEEKDAYS if d not in set(tx["DayOfWeek"])]

    hourly = tx.groupby("Hour", as_index=False).agg(net_revenue=("TotalLineRevenue", "sum"))

    # Products: sales lines only; name = most frequent Description per code.
    names = (
        sales.groupby(["StockCode", "Description"]).size().reset_index(name="n")
        .sort_values("n", ascending=False).drop_duplicates("StockCode")
        .set_index("StockCode")["Description"].astype(str).str.strip()
    )
    prod = sales.groupby("StockCode").agg(
        units=("Quantity", "sum"), revenue=("TotalLineRevenue", "sum")
    )
    prod["name"] = names.reindex(prod.index).fillna(prod.index.to_series())
    prod = prod.reset_index()

    countries = tx.groupby("Country").agg(net_revenue=("TotalLineRevenue", "sum"))
    countries["orders"] = sales.groupby("Country")["InvoiceNo"].nunique()
    countries = countries.fillna(0).reset_index().sort_values("net_revenue", ascending=False)

    uk = tx.groupby("Is_UK").agg(net_revenue=("TotalLineRevenue", "sum")).reset_index()
    uk["region"] = np.where(uk["Is_UK"].astype(bool), "United Kingdom", "Rest of world")

    return {
        "monthly": monthly,
        "weekday": weekday,
        "missing_days": missing_days,
        "hourly": hourly,
        "top_revenue": prod.nlargest(10, "revenue"),
        "top_units": prod.nlargest(10, "units"),
        "countries": countries,
        "uk_split": uk,
        "first_date": tx["InvoiceDate"].min(),
        "last_date": tx["InvoiceDate"].max(),
    }