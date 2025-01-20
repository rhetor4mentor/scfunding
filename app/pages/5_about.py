import streamlit as st
from src.visuals import charts

def about():
    import streamlit as st
    from components.header import get_header
    from components.page_config import get_page_config
    from data import initialize_session_state
    get_page_config()
    get_header()

    initialize_session_state()

    middle_left, middle_middle, middle_right = st.columns([4, 4, 4], border=True)

    with middle_left:
        st.header("Disclaimer")
        st.markdown('''This is an unofficial [Star Citizen](https://robertsspaceindustries.com/) application, not affiliated with the Cloud Imperium Games.''')
        st.image('https://robertsspaceindustries.com/i/2be4826ef804191d2ede49fed62b390ec15fdbd2/resize(840,672,cover,crop(840,672,0,0,2FFvzA2zeqoVY7xdzjgPLMPd3QhaUVt5raNdzxHRxAwxC5goA3hy9838QyR2qBqV45AwW7vEmCw1ki6uHEzF2fxUkw55iGKsVEikoLuDVBJDYuC5mMqWa6KtyHbyG))/75/sc-gamecard-5-4-840x672-.webp')
    with middle_middle:
        st.header('Credits')
        st.markdown('''The entire CCU Games team, and in particular [R1scHwA](https://robertsspaceindustries.com/citizens/R1scHwA) for maintaining the Crowdfunding spreadsheet this site relies upon (as well as an awesome [application](https://ccugame.app/)!)''')
        st.markdown('''[Syncend](https://www.paypal.com/donate/?hosted_button_id=2EUW7MY8EDCWU) for hosting a [dashboard](https://ccugame.app/statistics/funding-dashboard) on CCU Games that served as a clear inspiration for this one!''')
        st.image('images/made_by_the_community_large.png', use_container_width=False)

    with middle_right:
        st.header('Author')
        st.markdown('My name is [Rhethor4mentor](https://robertsspaceindustries.com/citizens/Rhethor4mentor). You may find me in-game, come and say hi!')
        st.image('images/scfund_logo2_large.png', use_container_width=False)


about()