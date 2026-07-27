import streamlit as st

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("## 📈 Sungje Market")
        st.caption("Command Center Pro v3.1")
        st.divider()

        page = st.radio(
            "Navigation",
            [
                "Command Center",
                "Watchlist",
                "Portfolio",
                "Buy Planner",
                "Earnings",
                "News",
                "Trading Journal",
                "Settings",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.markdown("**Quick View**")
        st.caption("US market · AI · Semi · Power")
        st.caption("Yahoo Finance data")
        st.caption("Quotes may be delayed.")
    return page
