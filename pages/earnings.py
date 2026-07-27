import streamlit as st
import pandas as pd
import yfinance as yf
from utils.storage import load_json
DEFAULT=['GOOGL','META','AMZN','MSFT','AAPL','AVGO','NVDA','TSLA']

@st.cache_data(ttl=3600,show_spinner=False)
def earnings_date(ticker):
    try:
        cal=yf.Ticker(ticker).calendar
        if isinstance(cal,dict):
            v=cal.get('Earnings Date'); return v[0] if isinstance(v,list) and v else v
        if hasattr(cal,'loc') and 'Earnings Date' in cal.index:
            v=cal.loc['Earnings Date']; return v.iloc[0] if hasattr(v,'iloc') else v
    except Exception: pass
    return None

def render():
    st.title('Earnings Center'); rows=[]; now=pd.Timestamp.now(tz='UTC')
    for t in load_json('watchlist.json',DEFAULT):
        dt=earnings_date(t); days=None; text='—'
        if dt is not None:
            ts=pd.Timestamp(dt); ts=ts.tz_localize('UTC') if ts.tzinfo is None else ts; text=ts.strftime('%Y-%m-%d'); days=(ts.normalize()-now.normalize()).days
        rows.append({'Ticker':t,'Earnings Date':text,'D-Day':None if days is None else f'D{days:+d}'})
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.warning('Yahoo Finance의 실적 일정은 변경되거나 누락될 수 있으므로 실제 거래 전 회사 IR 일정을 다시 확인하세요.')
