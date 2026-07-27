import pandas as pd
import streamlit as st
import yfinance as yf
from utils.storage import load_json

DEFAULT=["GOOGL","META","AMZN","MSFT","AAPL","AVGO","NVDA","TSLA"]

@st.cache_data(ttl=3600,show_spinner=False)
def earnings_date(ticker):
    try:
        cal=yf.Ticker(ticker).calendar
        if isinstance(cal,dict):
            v=cal.get("Earnings Date")
            return v[0] if isinstance(v,list) and v else v
    except Exception: pass
    return None

def render():
    st.title("Earnings Center")
    rows=[]; now=pd.Timestamp.now(tz="UTC")
    for t in load_json("watchlist.json",DEFAULT):
        dt=earnings_date(t); text="—"; dday="—"
        if dt is not None:
            ts=pd.Timestamp(dt)
            if ts.tzinfo is None: ts=ts.tz_localize("UTC")
            text=ts.strftime("%Y-%m-%d"); d=(ts.normalize()-now.normalize()).days; dday=f"D{d:+d}"
        rows.append({"Ticker":t,"Earnings Date":text,"D-Day":dday})
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.warning("실제 거래 전 회사 IR 일정으로 다시 확인하세요.")
