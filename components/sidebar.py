from datetime import datetime

import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown("## 📈 SUNGJE")
        st.caption("SUNGJE INVESTMENT OS v7")

        if st.button("🔄 Refresh All Data", use_container_width=True, type="primary"):
            st.cache_data.clear()
            try:
                from engine.schwab import clear_cache
                clear_cache()
            except Exception:
                pass
            st.session_state["last_manual_refresh"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            st.rerun()

        last_refresh = st.session_state.get("last_manual_refresh")
        if last_refresh:
            st.caption(f"Last refreshed: {last_refresh}")

        st.divider()
        page = st.radio(
            "Navigation",
            [
                "Command Center",
                "Market Overview",
                "Market Heat Maps",
                "Watchlist",
                "Portfolio",
                "Portfolio AI Advisor",
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
