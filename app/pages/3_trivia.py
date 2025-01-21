import pandas as pd
import streamlit as st
from src.visuals import charts
from src.stats import observations
from src import utils

def quality_pattern(percentile: float) -> str:
    if (percentile >= 33) and (percentile <= 67):
        commonality = 'fairly common'
    elif percentile > 67:
        commonality = 'particularly high'
    else: 
        commonality = 'particularly low'
    return commonality

def trivia():
    import streamlit as st
    from components.page_config import get_page_config
    from components.header import get_header
    from data import initialize_session_state

    get_page_config()
    get_header()

    initialize_session_state()
    
    middle_left, middle_right = st.columns([10, 10], border=True)
    
    with middle_left:
        st.header("A Day in Star Citizen's Crowdfunding")
        date_input = st.date_input(
            label='Pick a day', 
            value="today", 
            min_value=None, 
            max_value=utils.yesterday(), 
            key=None, 
            help="We'll tell you some details about crowdfunding back then.", 
            on_change=None, 
            args=None, 
            kwargs=None, 
            format="YYYY/MM/DD", 
            disabled=False,
            label_visibility="visible")
        insight = st.empty()

    data_citizens = observations.precedence(df=st.session_state['ts_daily'], timestamp=pd.Timestamp(date_input), metric='delta_citizens')
    data_pledges = observations.precedence(df=st.session_state['ts_daily'], timestamp=pd.Timestamp(date_input), metric='delta_pledge')

    pledge_percentile = data_pledges.data['percentile'].iloc[0]
    pledge_commonality: str = quality_pattern(pledge_percentile)
    
    citizens_percentile = data_citizens.data['percentile'].iloc[0]
    citizens_commonality: str = quality_pattern(citizens_percentile)

    version = data_pledges.data['version'].iloc[0]
    if version in ['Pre-Release']:
        verb = 'waiting while SC was in'
    elif version in ['Alpha 3.18.0']:
        verb = 'were perhaps able to log into'
    elif version in ['Alpha 4.0']:
        verb = 'jumping to Pyro in'
    else:
        verb = 'testing'

    on_sale = data_pledges.data['on_sale'].iloc[0]

    if on_sale > 0:
        add_on = '- There was a sale that day.'
    else:
        add_on = ''

    insight.write(f"""
    - Citizens were {verb} {version}
    - {data_citizens.data['period'].iloc[0]} added a whole **${data_pledges.data['value'].iloc[0]:,.0f}** in new pledges (a pattern that was {pledge_commonality} ({utils.format_ordinal(pledge_percentile)} percentile)
    - This brought the crowdfunding total to ${data_citizens.data['total_pledge'].iloc[0]/1e6:.1f}M.
    - During that day **{data_citizens.data['value'].iloc[0]:,.0f}** new accounts were opened, totalling {data_citizens.data['total_citizens'].iloc[0]:,.0f}. Such a pattern was {citizens_commonality} ({utils.format_ordinal(citizens_percentile)} percentile).
    {add_on}
    """)

    with middle_right:
        st.header('Patch History')

        selected_year = st.selectbox(
            label='Go back in time',
            index=0,
            options=st.session_state['cts'].funding_years[::-1],
            help="Note that the first row indicates what patch was live on 1st of January, which typically means that it was released the year prior. The row index thus gives you the number of patches that were released that year. In this version we do not distinguish between major and minor patches."
        )

        if selected_year:
            year_view = st.session_state['cts'].game_version_parser.year_view(selected_year)
            
            pct_live_col = f"pct live in {selected_year}"
            days_live_col = f"days live in {selected_year}"
            year_view.rename(columns={
                'version': 'build',
                'pct_live': pct_live_col,
                'days_live': days_live_col,
                }, inplace=True,
            )

            year_in_patch = year_view.drop(columns=['major', 'minor', 'patch']).style.format(
            {   'date': '{:%a %d %b %Y}',
                pct_live_col: '{:.0%}', 
                days_live_col: '{:,.0f} days'
             })

            middle_left, middle_right = st.columns(2)

            with middle_left:
                st.metric(label='Big patch releases', 
                          help='How many large patches went live during the year.',
                          value=len(year_view[['major', 'minor']].drop_duplicates()) - 1,
                )

            with middle_right:
                st.metric(label='Total releases', 
                          help='How many patches went live, including .X ones.',
                          value=len(year_view) - 1,
                )

            st.dataframe(year_in_patch, use_container_width=True)

trivia()