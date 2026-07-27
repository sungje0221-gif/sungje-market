import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.markdown('## 📈 Sungje Market')
        st.caption('Command Center Pro')
        st.divider()
        page = st.radio('Navigation', ['Command Center','Watchlist','Portfolio','Buy Planner','Earnings','News','Trading Journal','Settings'], label_visibility='collapsed')
        st.divider()
        st.caption('Data source: Yahoo Finance')
        st.caption('Quotes may be delayed.')
    return page
