import importlib
import traceback

import streamlit as st

from components.sidebar import render_sidebar
from components.theme import inject_dashboard_v092, inject_heatmap_v093, inject_theme, inject_v098, inject_v301, inject_v309

APP_VERSION = "3.16"

st.set_page_config(
    page_title=f"Sungje Investment OS v{APP_VERSION}",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

# Keep global styling lightweight and stable across reruns.
inject_theme()
inject_dashboard_v092()
inject_heatmap_v093()
inject_v098()
inject_v301()
inject_v309()

# Deep links from a watchlist card should reopen the Watchlist page --
# but only once. Leaving `?watch=` in the URL after handling it meant every
# later rerun re-forced os_page back to "Watchlist" regardless of which nav
# button was actually clicked, so navigation away from Watchlist looked
# broken after visiting any ticker's card even once.
if st.query_params.get("watch"):
    st.session_state["os_page"] = "Watchlist"
    st.session_state["watch_selected"] = st.query_params.get("watch")
    st.query_params.clear()

page = render_sidebar()

# Lazy routes: only the selected page module is imported. This avoids importing
# every data-heavy page whenever the user changes pages.
ROUTES = {
    "Command Center": ("pages.command_center", "render"),
    "Heatmap": ("pages.heatmap", "render"),
    "Watchlist": ("pages.watchlist", "render"),
    "Portfolio": ("pages.portfolio", "render"),
    "Buy Planner": ("pages.buy_planner", "render"),
    "AI Center": ("pages.ai_center", "render"),
    "Earnings": ("pages.earnings", "render"),
    "News": ("pages.news", "render"),
    "Journal": ("pages.journal", "render"),
    "Schwab": ("pages.schwab_connect", "render"),
    "Settings": ("pages.settings", "render"),
}


def _load_renderer(page_name: str):
    module_name, function_name = ROUTES.get(page_name, ROUTES["Command Center"])
    module = importlib.import_module(module_name)
    # Always reload from disk. Streamlit Cloud's "git pull -> Updated app!"
    # deploys often keep the same Python process alive (no restart), so a
    # plain import_module() call returns the module cached in sys.modules
    # from whenever this process first booted -- i.e. stale code, silently,
    # with no error. Reloading guarantees the page actually reflects the
    # latest push without needing a manual "Reboot app" every time.
    module = importlib.reload(module)
    return getattr(module, function_name)


try:
    _load_renderer(page)()
except Exception as exc:
    st.error("이 페이지를 불러오는 중 오류가 발생했습니다. 새로고침 후 다시 시도하세요.")
    st.caption(f"{type(exc).__name__}: {exc}")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())
