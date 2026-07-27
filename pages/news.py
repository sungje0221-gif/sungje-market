import streamlit as st
import yfinance as yf
from utils.storage import load_json
DEFAULT=['GOOGL','META','AMZN','MSFT','AVGO','CEG']

@st.cache_data(ttl=900,show_spinner=False)
def get_news(ticker):
    try: return yf.Ticker(ticker).news or []
    except Exception: return []

def render():
    st.title('News'); ticker=st.selectbox('Ticker',load_json('watchlist.json',DEFAULT)); items=get_news(ticker)
    if not items: st.info('뉴스를 불러오지 못했습니다.'); return
    for item in items[:12]:
        content=item.get('content',item); title=content.get('title','Untitled'); provider=content.get('provider',{}); provider_name=provider.get('displayName','Unknown') if isinstance(provider,dict) else str(provider); summary=content.get('summary') or content.get('description') or ''; canonical=content.get('canonicalUrl',{}); url=canonical.get('url') if isinstance(canonical,dict) else None
        st.markdown(f'#### {title}'); st.caption(provider_name)
        if summary: st.write(summary[:500])
        if url: st.link_button('기사 열기',url)
        st.divider()
