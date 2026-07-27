import streamlit as st,yfinance as yf
from utils.storage import load_json
DEFAULT=["GOOGL","META","AMZN","MSFT","AVGO","CEG"]
@st.cache_data(ttl=900,show_spinner=False)
def news(t):
    try:return yf.Ticker(t).news or []
    except:return []
def render():
    st.title("News & AI Briefing")
    t=st.selectbox("Ticker",load_json("watchlist.json",DEFAULT))
    items=news(t)
    if not items:st.info("No news available.");return
    for item in items[:15]:
        c=item.get("content",item);title=c.get("title","Untitled");provider=c.get("provider",{})
        p=provider.get("displayName","Unknown") if isinstance(provider,dict) else str(provider)
        summary=c.get("summary") or c.get("description") or "";cu=c.get("canonicalUrl",{});url=cu.get("url") if isinstance(cu,dict) else None
        st.markdown(f"#### {title}");st.caption(p)
        if summary:st.write(summary[:600])
        if url:st.link_button("Open article",url)
        st.divider()
