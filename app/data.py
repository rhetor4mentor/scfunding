import streamlit as st
import time
from datetime import datetime, timedelta
from loguru import logger
from src.loading.combined_signals import CompleteTimeSeries


@st.cache_resource
def load_complete_time_series(refresh_counter: int = 0) -> CompleteTimeSeries:
    logger.info(f"Loading complete time series with refresh_counter={refresh_counter}")
    return CompleteTimeSeries()

def populate_session_state(cts: CompleteTimeSeries) -> None:
    logger.info("Populating session state with complete time series data")
    st.session_state['cts'] = cts
    st.session_state['ts_daily'] = cts.get_time_series('D')
    st.session_state['ts_weekly'] = cts.get_time_series('W')
    st.session_state['ts_annual'] = cts.get_time_series('YE')
    st.session_state['main_statistics'] = cts.transaction_parser.main_statistics
    st.session_state['last_refresh'] = datetime.now()

def initialize_session_state():
    if 'cts' not in st.session_state:
        logger.info(f"Initializing session state (prexisting keys: {st.session_state.keys()})")
        cts = load_complete_time_series(refresh_counter=0)
        populate_session_state(cts)

def refresh_session_state():
    if 'refresh_counter' not in st.session_state:
        logger.warning("setting refresh counter to 0 as no such key was found in session_State")
        st.session_state['refresh_counter'] = 0

    st.session_state['refresh_counter'] += 1
    logger.info(f"Refreshing session state, refresh_counter={st.session_state['refresh_counter']}")
    cts = load_complete_time_series(st.session_state['refresh_counter'])
    populate_session_state(cts)

def check_and_refresh():
    if 'last_refresh' in st.session_state:
        elapsed_time = datetime.now() - st.session_state['last_refresh']
        if elapsed_time > timedelta(minutes=45):
            refresh_session_state()