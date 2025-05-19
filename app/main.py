import data
import streamlit as st
import pandas as pd
from src.loading.loader import TransactionParser
from src.utils import format_ordinal
from src.visuals import charts
from src.stats import observations


def main_page():
    from components.page_config import get_page_config
    get_page_config()
    
    data.initialize_session_state()
    from components.header import get_header
    from components.topline_statistics import get_topline_statistics

    print("A", list(st.session_state.keys()))

    get_header()

    # data
    metrics = st.session_state["main_statistics"]
    day_of_year = metrics["time"]["last_updated"].dayofyear
    thirty_days_ago = metrics["time"]["last_updated"] - pd.Timedelta(days=30)
    ts_daily = st.session_state["ts_daily"]
    ts_weekly = st.session_state["ts_weekly"]
    ts_annual = st.session_state["ts_annual"]
    historical_periods = ts_daily[ts_daily["day_of_year"] == day_of_year]
    last30_days_impact_pledges = observations.precedence(
        historical_periods, metric="pledge_prior_30_periods"
    )
    last30_days_impact_citizens = observations.precedence(
        historical_periods, metric="citizens_prior_30_periods"
    )

    chart_funding = charts.plot_all_years(ts_weekly, ts_annual, metric="pledges")

    get_topline_statistics()

    middle_left, middle_right = st.columns([4, 16], border=True)

    with middle_left:
        st.header("Recent Impact")

        st.metric(
            label="Funding in last 30 days",
            value=f"${last30_days_impact_pledges.data['value'].iloc[0]:,.0f}",
            delta=f"Ranking {format_ordinal(last30_days_impact_pledges.data['rank'].iloc[0])} (out of {last30_days_impact_pledges.data['n periods'].iloc[0]} similar periods)",
            delta_color="off",
        )

        st.metric(
            label="Account openings in last 30 days",
            value=f"+{last30_days_impact_citizens.data['value'].iloc[0]:,.0f}",
            delta=f"Ranking {format_ordinal(last30_days_impact_citizens.data['rank'].iloc[0])} (out of {last30_days_impact_pledges.data['n periods'].iloc[0]} similar periods)",
            delta_color="off",
        )

        st.markdown(
            f"""Since the {thirty_days_ago.strftime('%d %b %Y')} how strong have growth indicators been?
                    To assess this, let's compare the last 30 days' figures to prior years at the same periods.
                    """
        )

    with middle_right:
        st.header("Funding History")

        st.altair_chart(
            chart_funding,
            use_container_width=True,
        )


main_page()
