import streamlit as st
from datetime import datetime, timedelta
from loguru import logger
from src.loading.combined_signals import CompleteTimeSeries


class TimeChecker:
    last_refresh_time = datetime.min  # Initialize with a very old date
    delay = 45

    @classmethod
    def check_and_set(cls):
        now = datetime.now()
        if now - cls.last_refresh_time > timedelta(minutes=cls.delay):
            cls.last_refresh_time = now
            return True
        return False

    @classmethod
    def set(cls, time):
        cls.last_refresh_time = time


@st.cache_resource
def load_complete_time_series(refresh_time: datetime) -> CompleteTimeSeries:
    logger.info(f"Loading complete time series with refresh_time={refresh_time}")
    return CompleteTimeSeries()


def populate_session_state(cts: CompleteTimeSeries) -> None:
    logger.info("Populating session state with complete time series data")
    st.session_state["cts"] = cts
    st.session_state["main_statistics"] = cts.transaction_parser.main_statistics
    st.session_state["ts_daily"] = cts.get_time_series("D")
    st.session_state["ts_weekly"] = cts.get_time_series("W")
    st.session_state["ts_annual"] = cts.get_time_series("YE")
    st.session_state["last_refresh"] = datetime.now()


def initialize_session_state():
    if "cts" not in st.session_state:
        if TimeChecker.check_and_set():
            logger.info("Refreshing data due to time check")
        last_refresh_time = TimeChecker.last_refresh_time
        logger.info(
            f"Initializing session state (last refresh time: {last_refresh_time})"
        )
        cts = load_complete_time_series(last_refresh_time)
        populate_session_state(cts)


def refresh_session_state():
    logger.info("Refreshing session state")
    TimeChecker.set(time=datetime.now())
    cts = load_complete_time_series(TimeChecker.last_refresh_time)
    populate_session_state(cts)
