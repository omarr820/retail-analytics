"""Cleaning steps for the Online Retail dataset (rules documented in 01_cleaning_eda.ipynb)."""
import pandas as pd

NON_PRODUCT_CODES = [
    "POST", "DOT", "C2", "M", "m", "D", "S",
    "BANK CHARGES", "AMAZONFEE", "CRUK", "B",
]


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Year"] = df["InvoiceDate"].dt.year
    df["Month"] = df["InvoiceDate"].dt.month
    df["DayOfWeek"] = df["InvoiceDate"].dt.day_name()
    df["Hour"] = df["InvoiceDate"].dt.hour
    return df


def cast_identifiers(df: pd.DataFrame) -> pd.DataFrame:
    """CustomerID is read as float because of missing values; cast to string via Int64."""
    df = df.copy()
    df["CustomerID"] = df["CustomerID"].astype("Int64").astype("string")
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    return df


def drop_duplicates(df: pd.DataFrame):
    """Return (clean_df, removed_df)."""
    mask = df.duplicated(keep="first")
    return df[~mask].copy(), df[mask].copy()


def flag_cancellations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["IsCancellation"] = df["InvoiceNo"].astype(str).str.startswith("C")
    return df


def isolate_inventory_adjustments(df: pd.DataFrame):
    """Negative quantity without a C prefix."""
    mask = (df["Quantity"] < 0) & (~df["IsCancellation"])
    return df[~mask].copy(), df[mask].copy()


def isolate_nonpositive_price(df: pd.DataFrame):
    mask = df["UnitPrice"] <= 0
    return df[~mask].copy(), df[mask].copy()


def isolate_non_product_codes(df: pd.DataFrame):
    mask = df["StockCode"].isin(NON_PRODUCT_CODES)
    return df[~mask].copy(), df[mask].copy()


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["TotalLineRevenue"] = df["Quantity"] * df["UnitPrice"]
    df["Is_UK"] = (df["Country"] == "United Kingdom").astype(int)
    df["YearMonth"] = df["InvoiceDate"].dt.to_period("M").astype(str)
    return df