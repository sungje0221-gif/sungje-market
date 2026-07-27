import streamlit as st
import yfinance as yf
from utils.storage import load_json

DEFAULT=["GOOGL","META","AMZN","MSFT","AVGO","CEG"]

@st.cache_data(ttl=900,show_spinner=False)
def get_news(ticker):
    try: return yf.Ticker(ticker).news or []
    except Exception: return []

def render():
    st.title("News")
    ticker=st.selectbox("Ticker",load_json("watchlist.json",DEFAULT))
    items=get_news(ticker)
    if not items:
        st.info("뉴스를 불러오지 못했습니다."); return
    for item in items[:12]:
        c=item.get("content",item)
        title=c.get("title","Untitled"); provider=c.get("provider",{})
        p=provider.get("displayName","Unknown") if isinstance(provider,dict) else str(provider)
        summary=c.get("summary") or c.get("description") or ""
        cu=c.get("canonicalUrl",{}); url=cu.get("url") if isinstance(cu,dict) else None
        st.markdown(f"#### {title}"); st.caption(p)
        if summary: st.write(summary[:500])
        if url: st.link_button("기사 열기",url)
        st.divider()
