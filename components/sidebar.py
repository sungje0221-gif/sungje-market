from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

NAV_GROUPS = {
    "HOME": ["Command Center"],
    "MARKETS": ["Markets", "Heatmap", "Watchlist"],
    "PORTFOLIO": ["Portfolio", "Buy Planner"],
    "INTELLIGENCE": ["AI Center", "Earnings", "News"],
    "SYSTEM": ["Journal", "Settings"],
}

NAV_ICONS = {
    "Command Center": "⌂", "Markets": "◫", "Heatmap": "▦", "Watchlist": "☆",
    "Portfolio": "◉", "Buy Planner": "＋", "AI Center": "✦", "Earnings": "◷",
    "News": "≡", "Journal": "✎", "Settings": "⚙",
}


def _refresh_all() -> None:
    st.cache_data.clear()
    try:
        from engine.schwab import clear_cache
        clear_cache()
    except Exception:
        pass
    st.session_state["last_manual_refresh"] = datetime.now(
        ZoneInfo("America/Los_Angeles")
    ).strftime("%I:%M:%S %p")


def _set_page(page_name: str) -> None:
    st.session_state["os_page"] = page_name


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div class="os-brand">
                <div class="os-brand-mark">S</div>
                <div><div class="os-brand-title">SUNGJE</div>
                <div class="os-brand-subtitle">INVESTMENT OS v3.02</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("↻ Refresh", use_container_width=True, type="primary"):
            _refresh_all()

        choices = [item for group in NAV_GROUPS.values() for item in group]
        current = st.session_state.get("os_page", "Command Center")
        if current not in choices:
            current = "Command Center"

        for group_name, group_items in NAV_GROUPS.items():
            st.markdown(f'<div class="nav-group-label">{group_name}</div>', unsafe_allow_html=True)
            for item in group_items:
                st.button(
                    f"{NAV_ICONS[item]}  {item}",
                    key=f"nav_{item}",
                    use_container_width=True,
                    type="primary" if item == current else "secondary",
                    on_click=_set_page,
                    args=(item,),
                )

        last_refresh = st.session_state.get("last_manual_refresh")
        if last_refresh:
            st.caption(f"Updated {last_refresh}")
    return st.session_state.get("os_page", current)
