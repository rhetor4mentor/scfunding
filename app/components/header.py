import streamlit as st
import os

from src.utils import format_timedelta
from data import refresh_session_state


TITLE = "SC Fund"
HEADER = "SC Funding Analyzer"

metrics = st.session_state["main_statistics"]
delta_time = format_timedelta(td=metrics["time"]["time_since_measure"])


def get_header(page_title: str = TITLE, header: str = HEADER):

    header_left, header_right = st.columns([6, 6])
    header_left.title(header)

    logo_path = os.path.join(os.path.dirname(__file__), "../images/scfund_logo2.png")
    logo_path = os.path.abspath(logo_path)

    if os.path.exists(logo_path):
        st.logo(logo_path, size="large")
    else:
        st.warning(
            "Logo image not found. Please ensure the image is available at the specified path."
        )

    with header_right:
        refresh_cont = st.container(border=True)
        left, right = refresh_cont.columns([2, 10])

        with left:
            if st.button("Refresh"):
                refresh_session_state()

        with right:
            st.markdown(f"**Last refresh.**\n{delta_time} ago.", help="Based on the last hourly transaction record captured at last refresh.")            
    