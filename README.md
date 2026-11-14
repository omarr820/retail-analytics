# Online Retail: Customer Analytics & Segmentation

Customer analytics for a UK-based online gift retailer (Dec 2010 - Dec 2011): data cleaning, EDA, RFM analysis, customer segmentation, and an interactive Streamlit dashboard.

**Live dashboard:** [omar-retail-analytics.streamlit.app](https://omar-retail-analytics.streamlit.app/)

## Key results

- **Seasonality:** net revenue in Oct-Nov 2011 was about 1.96x the Jan-Aug average; the rise starts in September and comes from more orders, not larger orders.
- **Concentration:** the top 1% of customers generate 30.5% of revenue; the `555` RFM profile (8.0% of customers) generates 45.7%.
- **Segments:** K-Means with K=5 gives five actionable segments. Champions and Active Regulars are 30.8% of customers but 77.1% of revenue.
- **Key accounts:** DBSCAN isolates 33 customers (0.8%) that generate 21.5% of revenue.

| Segment | Customers | Revenue share | Priority action |
|---|---|---|---|
| Champions | 8.3% | 53.4% | Protect: loyalty perks, account management |
| Active Regulars | 22.5% | 23.7% | Grow: cross-sell, bundles |
| Cooling Regulars | 23.1% | 15.5% | Recover: targeted win-back |
| Recent One-timers | 20.2% | 3.8% | Convert: welcome sequence |
| Lost One-timers | 25.9% | 3.5% | Limit spend: one low-cost attempt |

## Project structure

```
data/        clean_transactions.parquet, customer_rfm.parquet, customer_segments.parquet
notebooks/   01_cleaning_eda.ipynb, 02_rfm.ipynb, 03_clustering.ipynb
src/         cleaning.py, rfm.py, segments.py, data.py, ui.py
views/       dashboard pages (overview, segments, customers, rfm, key accounts, business, methodology)
reports/     final PDF summary
app.py       Streamlit dashboard
```

## How to reproduce

1. Use Python 3.10 and install dependencies:
   - Dashboard only: `pip install -r requirements.txt`
   - Notebooks: `pip install -r requirements-notebooks.txt`
2. Download the Online Retail dataset (UCI / Kaggle) and place `Online Retail.xlsx` in `data/`. It is not included in the repo.
3. Run the notebooks in order. Each saves a file in `data/` that the next one reads:
   - `01_cleaning_eda.ipynb` (sections 1-7) saves `clean_transactions.parquet`
   - `02_rfm.ipynb` (sections 8-10) saves `customer_rfm.parquet`
   - `03_clustering.ipynb` (sections 11-16) saves `customer_segments.parquet`
4. Launch the dashboard: `streamlit run app.py`

All random steps use `random_state=42`.

## Method summary

- **Cleaning:** every removal is stored in its own table with a documented reason (duplicates, stock adjustments, zero/negative prices, non-product codes, two fully reversed orders). 531,235 of 541,909 rows remain. Cancellations are kept and netted against revenue. Guest checkouts (about 25% of rows) stay in sales analysis but are excluded from customer analysis.
- **RFM:** 1-5 scores with `pd.qcut` on ranks (Recency reversed). Snapshot date is 2011-12-10.
- **Segmentation:** `log1p` + `StandardScaler`, K-Means (K chosen with Elbow, Silhouette, Davies-Bouldin, and stability), compared with Hierarchical (sample) and DBSCAN (outliers).

## Limitations

- One year of data, with December 2011 incomplete, so seasonality is not separated from growth.
- Segments cover registered customers only.
- Segment borders are soft (silhouette 0.318); K=5 was chosen for marketing usefulness.
- Findings are descriptive; recommendations are hypotheses to validate with A/B tests.
- Cancellation matching (4.5b) and fully reversed order detection (4.9) live in `01_cleaning_eda.ipynb`, not in `src/`.