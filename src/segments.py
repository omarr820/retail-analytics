"""Segment names and loader used by the Streamlit app."""
import pandas as pd

SEGMENT_NAMES = {
    1: "Champions",
    4: "Active Regulars",
    2: "Recent One-timers",
    0: "Cooling Regulars",
    3: "Lost One-timers",
}

SEGMENT_ORDER = ["Champions", "Active Regulars", "Recent One-timers",
                 "Cooling Regulars", "Lost One-timers"]


def load_segments(path: str = "data/customer_segments.parquet") -> pd.DataFrame:
    return pd.read_parquet(path)