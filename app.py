"""Customer analytics dashboard: navigation, global filters, layout."""
import streamlit as st

st.set_page_config(
    page_title="Customer Analytics",
    page_icon=":material/insights:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src import data, ui  # noqa: E402
from views import (  # noqa: E402
    business, customers, key_accounts, methodology, overview, rfm, segments_page,
)


def _reset(defaults: dict) -> None:
    """Callback: put every filter back to its default."""
    for key, value in defaults.items():
        st.session_state[key] = value


def _sane(key: str, default) -> None:
    """Make sure a range filter in session_state is a (low, high) pair."""
    cur = st.session_state.get(key)
    if not (isinstance(cur, (tuple, list)) and len(cur) == 2):
        st.session_state[key] = default


def render_sidebar(df) -> None:
    """Global filters, shared with every page through st.session_state."""
    defaults = data.filter_defaults(df)
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    for key in (data.K_REC, data.K_FREQ, data.K_MON):
        _sane(key, defaults[key])
    mon_options = data.monetary_options(df)

    with st.sidebar:
        counter = st.container()
        st.markdown("**Filters**")
        st.multiselect(
            "Segments", ui.SEGMENTS, key=data.K_SEG,
            help="Show only customers in the selected segments.",
        )
        st.radio(
            "Country", ["All", "UK", "Non-UK"], key=data.K_COUNTRY, horizontal=True,
            help="UK = customers whose country is United Kingdom.",
        )
        st.slider(
            "Recency (days since last order)",
            int(df["recency"].min()), int(df["recency"].max()), key=data.K_REC,
            help="Lower = bought more recently (snapshot date 2011-12-10).",
        )
        st.slider(
            "Frequency (number of invoices)",
            int(df["frequency"].min()), int(df["frequency"].max()), key=data.K_FREQ,
            help="Unique sales invoices per customer.",
        )
        st.select_slider(
            "Monetary (net revenue, GBP)", options=mon_options,
            value=st.session_state[data.K_MON], key=data.K_MON,
            format_func=ui.gbp,
            help="Steps follow customer percentiles because revenue is very skewed.",
        )
        st.toggle(
            "Include key accounts", key=data.K_OUT,
            help="Key accounts are the DBSCAN outliers. The Key Accounts page ignores this toggle.",
        )
        st.button("Reset filters", on_click=_reset, args=(defaults,),
                  icon=":material/restart_alt:")

        view = data.apply_filters(df, st.session_state)
        counter.markdown(
            ui.kpi_card("Customers in view", f"{len(view):,}",
                        f"of {len(df):,} registered customers"),
            unsafe_allow_html=True,
        )
        if not data.transactions_available():
            st.caption(
                "Business Overview is hidden: data/clean_transactions.parquet "
                "was not found."
            )


ui.inject_css()

try:
    customers_df = data.load_customers()
except data.DataError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

render_sidebar(customers_df)

pages = [
    st.Page(overview.render, title="Overview", icon=":material/dashboard:",
            url_path="overview", default=True),
    st.Page(segments_page.render, title="Segments", icon=":material/groups:",
            url_path="segments"),
    st.Page(customers.render, title="Customers", icon=":material/person_search:",
            url_path="customers"),
    st.Page(rfm.render, title="RFM", icon=":material/grid_view:", url_path="rfm"),
    st.Page(key_accounts.render, title="Key Accounts", icon=":material/key:",
            url_path="key-accounts"),
]
if data.transactions_available():
    pages.append(st.Page(business.render, title="Business Overview",
                         icon=":material/storefront:", url_path="business"))
pages.append(st.Page(methodology.render, title="Methodology",
                     icon=":material/menu_book:", url_path="methodology"))

st.navigation(pages).run()
ui.footer()