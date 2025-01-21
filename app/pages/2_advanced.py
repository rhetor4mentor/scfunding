import streamlit as st
from src.visuals import charts


def advanced():
    import streamlit as st
    from components.header import get_header
    from components.page_config import get_page_config
    from components.topline_statistics import get_topline_statistics
    from data import initialize_session_state
    
    get_page_config()
    get_header()
    initialize_session_state()
    get_topline_statistics()
    
    metrics = st.session_state['main_statistics']
    year = metrics['time']['last_updated'].year
    ts_daily = st.session_state['ts_daily']
    ts_weekly = st.session_state['ts_weekly']
    middle_left, middle_right = st.columns([10, 10], border=True)
    
    with middle_left:
        chart_line = charts.plot_line_chart(
            dataframe=ts_weekly,
            first_line_settings={'x': 'cumulative_avg_pledge_total', 'type': 'Q', 'format': '$,.0f', 'title': 'Avg. pledge/account'},
            second_line_settings={'x': 'total_pledge', 'type': 'Q', 'format': '$,.0f', 'title': 'Total Pledges ($)'},
            )
        st.header('Cumulative Average Pledges')
        st.altair_chart(chart_line, use_container_width=True)

    with middle_right:
        st.header(f'{year} Progress')
        chart_race_to_dayofyear = charts.plot_transactions_years_to_date(ts_daily, metric='pledges')
        st.altair_chart(chart_race_to_dayofyear, use_container_width=True)

advanced()