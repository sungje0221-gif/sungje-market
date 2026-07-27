import traceback

import streamlit as st

from components.sidebar import render_sidebar
from components.theme import inject_dashboard_v092, inject_heatmap_v093, inject_theme, inject_v098
from pages.ai_engine import render as render_ai_engine
from pages.buy_planner import render as render_buy_planner
from pages.command_center import render as render_command_center
from pages.earnings import render as render_earnings
from pages.heatmap import render as render_heatmap
from pages.journal import render as render_journal
from pages.market_overview import render as render_market_overview
from pages.news import render as render_news
from pages.portfolio import render as render_portfolio
from pages.portfolio_advisor import render as render_portfolio_advisor
from pages.schwab_connect import render as render_schwab_connect
from pages.settings import render as render_settings
from pages.watchlist import render as render_watchlist

APP_VERSION = "1.00"

st.set_page_config(
    page_title=f"Sungje Investment OS v{APP_VERSION}",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)

inject_theme()
inject_dashboard_v092()
inject_heatmap_v093()
inject_v098()
page = render_sidebar()

ROUTES = {
    "Command Center": render_command_center,
    "Markets": render_market_overview,
    "Heatmap": render_heatmap,
    "Watchlist": render_watchlist,
    "Portfolio": render_portfolio,
    "AI Advisor": render_portfolio_advisor,
    "Buy Planner": render_buy_planner,
    "Earnings": render_earnings,
    "News": render_news,
    "Journal": render_journal,
    "AI Lab": render_ai_engine,
    "Schwab": render_schwab_connect,
    "Settings": render_settings,
}

try:
    ROUTES.get(page, render_command_center)()
except Exception as exc:
    st.error("이 페이지를 불러오는 중 오류가 발생했습니다. 새로고침 후 다시 시도하세요.")
    st.caption(f"{type(exc).__name__}: {exc}")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())
