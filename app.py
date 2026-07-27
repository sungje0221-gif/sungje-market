import streamlit as st
from components.sidebar import render_sidebar
from pages import command_center, watchlist, portfolio, buy_planner, earnings, news, journal, settings

st.set_page_config(page_title='Sungje Market Command Center Pro', page_icon='📈', layout='wide', initial_sidebar_state='expanded')
page = render_sidebar()
ROUTES = {
    'Command Center': command_center.render,
    'Watchlist': watchlist.render,
    'Portfolio': portfolio.render,
    'Buy Planner': buy_planner.render,
    'Earnings': earnings.render,
    'News': news.render,
    'Trading Journal': journal.render,
    'Settings': settings.render,
}
ROUTES[page]()
