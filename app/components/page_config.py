import streamlit as st

def get_page_config():
    st.set_page_config(
        page_title='SC Fund',
        page_icon="app/images/scfund_logo2.png",
        layout="wide",
        menu_items={
            'About': "Rhetor4mentor"
        }
    )
