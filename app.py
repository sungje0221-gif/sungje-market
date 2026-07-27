import streamlit as st

from components.sidebar import render_sidebar
from components.theme import inject_theme
from views.command_center import render as render_command_center
from views.watchlist import render as render_watchlist
from views.portfolio import render as render_portfolio
from views.buy_planner import render as render_buy_planner
from views.earnings import render as render_earnings
from views.news import render as render_news
from views.journal import render as render_journal
from views.settings import render as render_settings

st.set_page_config(
    page_title="Sungje Market Command Center Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()
page = render_sidebar()

routes = {
    "Command Center": render_command_center,
    "Watchlist": render_watchlist,
    "Portfolio": render_portfolio,
    "Buy Planner": render_buy_planner,
    "Earnings": render_earnings,
    "News": render_news,
    "Trading Journal": render_journal,
    "Settings": render_settings,
}

routes[page]()
