from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

NAV_GROUPS = {
    "HOME": ["Command Center"],
    "MARKETS": ["Markets", "Heatmap", "Watchlist"],
    "PORTFOLIO": ["Portfolio", "Buy Planner"],
    "INTELLIGENCE": ["AI Center", "Earnings", "News"],
    "SYSTEM": ["Journal", "Schwab", "Settings"],
}
NAV_ICONS = {"Command Center":"⌂","Markets":"◫","Heatmap":"▦","Watchlist":"☆","Portfolio":"◉","Buy Planner":"＋","AI Center":"✦","Earnings":"◷","News":"≡","Journal":"✎","Schwab":"⛓","Settings":"⚙"}

def _refresh_all():
    st.cache_data.clear()
    try:
        from engine.schwab import clear_cache
        clear_cache()
    except Exception:
        pass
    st.session_state["last_manual_refresh"] = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%I:%M:%S %p")
    st.rerun()

def _set_page(name):
    st.session_state["os_page"] = name

def render_sidebar():
    st.markdown("""<style>
    [data-testid="stSidebar"]{min-width:185px!important;max-width:185px!important;width:185px!important}
    [data-testid="stSidebar"]>div:first-child{width:185px!important}
    [data-testid="stSidebar"] .stButton button{padding:.42rem .55rem!important;font-size:12px!important;text-align:left!important}
    [data-testid="stSidebar"] .os-brand{padding-bottom:4px!important}
    [data-testid="stSidebar"] .os-brand-subtitle{font-size:7px!important}
    [data-testid="stSidebar"] .nav-group-label{margin-top:13px!important;margin-bottom:3px!important;font-size:7px!important}
    [data-testid="stSidebar"] .sidebar-status-card{display:none!important}
    </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("""<div class="os-brand"><div class="os-brand-mark">S</div><div><div class="os-brand-title">SUNGJE</div><div class="os-brand-subtitle">INVESTMENT OS v3.00</div></div></div>""", unsafe_allow_html=True)
        if st.button("↻ Refresh", use_container_width=True, type="primary"):
            _refresh_all()
        last = st.session_state.get("last_manual_refresh", "—")
        st.markdown(f'<div class="refresh-time">Updated · {last}</div>', unsafe_allow_html=True)
        choices=[x for g in NAV_GROUPS.values() for x in g]
        current=st.session_state.get("os_page","Command Center")
        if current not in choices: current="Command Center"
        for group, items in NAV_GROUPS.items():
            st.markdown(f'<div class="nav-group-label">{group}</div>', unsafe_allow_html=True)
            for item in items:
                st.button(f"{NAV_ICONS[item]}  {item}", key=f"nav_{item}", use_container_width=True, type="primary" if item==current else "secondary", on_click=_set_page, args=(item,))
    return current
