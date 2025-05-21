import streamlit as st
from millify import millify
from src.visuals import charts

CAP_LAST_DAYS: int = None


def get_topline_statistics():
    ts_daily = st.session_state["ts_daily"]
    metrics = st.session_state["main_statistics"]

    chart_pledge_recent = charts.plot_current_vs_last_year(
        ts_daily, metric="pledges", show_title=False, cap_last_x_days=CAP_LAST_DAYS
    ).properties(height=250)
    chart_citizens_recent = charts.plot_current_vs_last_year(
        ts_daily, metric="citizens", show_title=False, cap_last_x_days=CAP_LAST_DAYS
    ).properties(height=250)

    top_left, top_middle = st.columns([8, 8], border=True)


    funding_total = f"${millify(metrics['pledges']['total_historically'], precision=2)}"
    funding_this_year = f"+${millify(metrics['pledges']['total_this_year'], precision=2)}"
    accounts_total = millify(metrics['citizens']['total_historically'], precision=2)
    accounts_this_year = f"+{millify(metrics['citizens']['total_this_year'], precision=2)}"
    year = metrics["time"]["last_updated"].year


    with top_left:

        top_left_left, top_left_right = st.columns([0.3, 0.7], border=False)

        with top_left_left:
            st.metric(
                label="Funding since 2012",
                value=funding_total,
                delta=funding_this_year,
                delta_color="off",
                help="This figures excludes subscriptions (not used for development) and private investments. It is solely based on pledges paid by backers.",
                label_visibility="visible",
                border=False,
            )

            st.metric(
                label=f"Funding in {year}",
                value=funding_this_year,
                delta=f"{metrics['pledges']['pct_change_year_on_year']:+,.0%} vs {year-1}",
                delta_color="normal",
                help=f"Pledges reported since the beginning of the year. It is compared to funding in {year-1} at the same period of the year (to the exact hour).",
                label_visibility="visible",
                border=False,
            )

        with top_left_right:
            st.altair_chart(
                chart_pledge_recent,
                use_container_width=True,
                theme="streamlit",
            )

    with top_middle:

        middle_left, middle_right = st.columns([0.3, 0.7], border=False)

        with middle_left:
            st.metric(
                label="Accounts registered",
                value=accounts_total,
                delta=accounts_this_year,
                delta_color="off",
                help="Please keep in mind that not all accounts are paying accounts, and backers may own multiple accounts.",
                label_visibility="visible",
                border=False,
            )

            st.metric(
                label=f"Accounts registered in {year}",
                value=accounts_this_year,
                delta=f"{metrics['citizens']['pct_change_year_on_year']:+,.0%} vs {year-1}",
                delta_color="normal",
                help=f"Account creations since the beginning of the year. It is compared to account creations in {year-1} at the same period of the year (to the exact hour).",
                label_visibility="visible",
                border=False,
            )

        with middle_right:
            st.altair_chart(
                chart_citizens_recent, use_container_width=True, theme="streamlit"
            )

