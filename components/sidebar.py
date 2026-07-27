import streamlit as st

def render_sidebar():
    with st.sidebar:
        st.markdown("## 📈 SUNGJE")
        st.caption("MARKET COMMAND CENTER v4.1")
        st.divider()
        page = st.radio(
            "Navigation",
            [
                "Command Center",
                "Market Overview",
                "Watchlist",
                "Portfolio",
                "Buy Planner",
                "Earnings",
                "News & Briefing",
                "Trading Journal",
                "AI Analysis Engine",
                "Schwab Connection",
                "Settings",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("**Market Status**")
        st.success("● DATA ONLINE")
        st.caption("Yahoo Finance")
        st.caption("Quotes may be delayed")
    return page
