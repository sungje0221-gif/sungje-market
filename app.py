import streamlit as st
from components.theme import inject_theme
from components.sidebar import render_sidebar
from pages.command_center import render as render_command_center
from pages.market_overview import render as render_market_overview
from pages.watchlist import render as render_watchlist
from pages.portfolio import render as render_portfolio
from pages.buy_planner import render as render_buy_planner
from pages.earnings import render as render_earnings
from pages.news import render as render_news
from pages.journal import render as render_journal
from pages.ai_engine import render as render_ai_engine
from pages.settings import render as render_settings

st.set_page_config(
    page_title="Sungje Market Command Center Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
page = render_sidebar()

ROUTES = {
    "Command Center": render_command_center,
    "Market Overview": render_market_overview,
    "Watchlist": render_watchlist,
    "Portfolio": render_portfolio,
    "Buy Planner": render_buy_planner,
    "Earnings": render_earnings,
    "News & Briefing": render_news,
    "Trading Journal": render_journal,
    "AI Analysis Engine": render_ai_engine,
    "Settings": render_settings,
}

ROUTES[page]()
