from datetime import datetime

import streamlit as st

NAV_GROUPS = {
    "HOME": ["Command Center"],
    "MARKETS": ["Markets", "Heatmap", "Watchlist"],
    "PORTFOLIO": ["Portfolio", "AI Advisor", "Buy Planner"],
    "INTELLIGENCE": ["Earnings", "News", "AI Lab"],
    "SYSTEM": ["Journal", "Schwab", "Settings"],
}

NAV_ICONS = {
    "Command Center": "⌂", "Markets": "◫", "Heatmap": "▦", "Watchlist": "☆",
    "Portfolio": "◉", "AI Advisor": "✦", "Buy Planner": "＋", "Earnings": "◷",
    "News": "≡", "AI Lab": "◇", "Journal": "✎", "Schwab": "⛓", "Settings": "⚙",
}


def _refresh_all() -> None:
    st.cache_data.clear()
    try:
        from engine.schwab import clear_cache
        clear_cache()
    except Exception:
        pass
    st.session_state["last_manual_refresh"] = datetime.now().strftime("%I:%M:%S %p")
    st.rerun()


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="os-brand">
                <div class="os-brand-mark">S</div>
                <div><div class="os-brand-title">SUNGJE</div>
                <div class="os-brand-subtitle">INVESTMENT OS v1.00</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("↻  Refresh Market Data", use_container_width=True, type="primary"):
            _refresh_all()
        last_refresh = st.session_state.get("last_manual_refresh", "Not refreshed yet")
        st.markdown(f'<div class="refresh-time">Last refresh · {last_refresh}</div>', unsafe_allow_html=True)

        choices = [item for group in NAV_GROUPS.values() for item in group]
        current = st.session_state.get("os_page", "Command Center")
        if current not in choices:
            current = "Command Center"

        selected = current
        for group_name, group_items in NAV_GROUPS.items():
            st.markdown(f'<div class="nav-group-label">{group_name}</div>', unsafe_allow_html=True)
            for item in group_items:
                if st.button(
                    f"{NAV_ICONS[item]}   {item}", key=f"nav_{item}", use_container_width=True,
                    type="primary" if item == selected else "secondary",
                ):
                    st.session_state["os_page"] = item
                    st.rerun()

        st.markdown(
            """
            <div class="sidebar-status-card">
              <div class="status-row"><span class="status-dot"></span><b>Market data online</b></div>
              <div class="status-copy">Yahoo Finance · quotes may be delayed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return selected
