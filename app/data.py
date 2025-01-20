import streamlit as st
from src.loading.loader import TransactionParser
from src.loading.combined_signals import CompleteTimeSeries

@st.cache_resource
def load_transaction_parser() -> TransactionParser:
    return TransactionParser()

@st.cache_resource
def load_complete_time_series(refresh_counter: int = 0) -> CompleteTimeSeries:
    return CompleteTimeSeries()

def populate_session_state(cts: CompleteTimeSeries) -> None:
    st.session_state['cts'] = cts
    st.session_state['ts_daily'] = cts.get_time_series('D')
    st.session_state['ts_weekly'] = cts.get_time_series('W')
    st.session_state['main_statistics'] = cts.transaction_parser.main_statistics

def initialize_session_state():
    if 'complete_time_series' not in st.session_state:
        cts = load_complete_time_series(refresh_counter=0)
        populate_session_state(cts)

def refresh_session_state():
    if 'refresh_counter' not in st.session_state:
        st.session_state['refresh_counter'] = 0

    st.session_state['refresh_counter'] += 1
    cts = load_complete_time_series(st.session_state['refresh_counter'])
    populate_session_state(cts)
