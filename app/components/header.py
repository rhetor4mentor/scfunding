import streamlit as st

TITLE = "SC Fund"
HEADER = "SC Funding Analyser"

def get_header(page_title: str = TITLE, header: str = HEADER):

    st.title(header)
    st.logo("app/images/scfund_logo2.png", size="large",)
