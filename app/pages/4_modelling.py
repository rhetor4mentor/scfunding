import streamlit as st
from src.visuals import charts
from src.modelling.train import load_possible_features

def about():
    import streamlit as st
    from components.header import get_header
    from components.page_config import get_page_config
    from data import initialize_session_state
    get_page_config()
    
    get_header(header='Time Series Modelling')
    st.warning("I'm planning to provide some time series modelling that shed lights on what tends to influence both pledge and account growth. Bear with me, this will come in a future version of the app.")

    initialize_session_state()

    df = st.session_state['ts_daily']
    wf = st.session_state['ts_weekly']

    features: dict = load_possible_features()
    feature_list = [item for sublist in features.values() for item in sublist]

    top_left, top_top, top_right = st.columns([4, 4, 4], border=True)
    middle_left, middle_right = st.columns([10, 10], border=True)


    with top_left:
        st.header('Approach')

    with top_top:
        st.header('Features', help='What variables are to be evaluated in the model?')
        with st.expander(label='Feature details'):
            st.write(features)
        
    with top_right:
        st.header('Takeaways')

    with middle_left:
        st.header('Data')

        st.dataframe(df[feature_list])

    with middle_right:
        st.header('Overview', help='The data used in modelling is at daily level. Here we aggregate it to weekly level for convenience.')

        line_chart = charts.plot_line_chart(
            wf, 
            first_line_settings={ 'x': 'delta_pledge','type': 'Q','format': '$,.0f','title': 'Pledges ($)' }, 
            second_line_settings={ 'x': 'delta_citizens','type': 'Q','format': ',.0f','title': 'Accounts' }, 
            title='Pledges and account creations over time',   
        )

        st.altair_chart(line_chart, use_container_width=True)

about()