import streamlit as st
import os

TITLE = "SC Fund"
HEADER = "SC Funding Analyser"

def get_header(page_title: str = TITLE, header: str = HEADER):
    st.title(header)
    logo_path = os.path.join(os.path.dirname(__file__), "../images/scfund_logo2.png")
    logo_path = os.path.abspath(logo_path)
    
    if os.path.exists(logo_path):
        st.logo(logo_path, size="large")
    else:
        st.warning("Logo image not found. Please ensure the image is available at the specified path.")
