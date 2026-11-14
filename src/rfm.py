"""Customer-level features and RFM scoring (see 02_rfm.ipynb)."""
import pandas as pd


def build_customer_features(df: pd.DataFrame) -> pd.DataFrame:
    """One row per registered customer. Recency/Frequency use sales invoices only;
    monetary is net revenue (sales minus cancellations), rounded to 2 decimals."""
    cust = df[df["CustomerID"].notna()]
    sales = cust[~cust["IsCancellation"]]
    canc = cust[cust["IsCancellation"]]

    snapshot = df["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)

    per_inv = sales.groupby(["CustomerID", "InvoiceNo"]).agg(
        revenue=("TotalLineRevenue", "sum"),
        units=("Quantity", "sum"),
        lines=("StockCode", "size"),
        date=("InvoiceDate", "min"),
    ).reset_index()

    feat = per_inv.groupby("CustomerID").agg(
        frequency=("InvoiceNo", "nunique"),
        gross_revenue=("revenue", "sum"),
        avg_order_value=("revenue", "mean"),
        avg_units_per_order=("units", "mean"),
        avg_lines_per_order=("lines", "mean"),
        first_purchase=("date", "min"),
        last_purchase=("date", "max"),
    )
    feat["recency"] = (snapshot - feat["last_purchase"].dt.normalize()).dt.days
    feat["tenure_days"] = (snapshot - feat["first_purchase"].dt.normalize()).dt.days
    feat["cancelled_value"] = (-canc.groupby("CustomerID")["TotalLineRevenue"].sum()).reindex(feat.index).fillna(0)
    feat["monetary"] = (feat["gross_revenue"] - feat["cancelled_value"]).round(2)
    country = cust.groupby("CustomerID")["Country"].agg(lambda s: s.mode().iloc[0])
    feat["is_uk"] = (country.reindex(feat.index) == "United Kingdom").astype(int)
    return feat.reset_index()


def isolate_nonpositive_monetary(feat: pd.DataFrame):
    """Customers with net monetary <= 0 cannot be log-transformed or scored."""
    mask = feat["monetary"] <= 0
    return feat[~mask].reset_index(drop=True), feat[mask].copy()


def score_rfm(feat: pd.DataFrame) -> pd.DataFrame:
    """1-5 scores with qcut on ranks. Recency is reversed (5 = most recent)."""
    out = feat.copy()
    out["R"] = pd.qcut(out["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    out["F"] = pd.qcut(out["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["M"] = pd.qcut(out["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["RFM_Score"] = out["R"].astype(str) + out["F"].astype(str) + out["M"].astype(str)
    out["RFM_Sum"] = out["R"] + out["F"] + out["M"]
    return out