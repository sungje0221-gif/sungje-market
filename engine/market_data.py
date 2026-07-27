import pandas as pd
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=300,show_spinner=False)
def history(ticker,period='6mo',interval='1d'):
    try:
        d=yf.download(ticker,period=period,interval=interval,auto_adjust=False,progress=False,threads=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
        return d.dropna(how='all')
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=180,show_spinner=False)
def quote(ticker):
    d=history(ticker,'5d','1d')
    if d.empty or 'Close' not in d: return {'ticker':ticker,'price':None,'change_pct':None,'volume':None}
    c=d['Close'].dropna()
    if c.empty: return {'ticker':ticker,'price':None,'change_pct':None,'volume':None}
    p=float(c.iloc[-1]); prev=float(c.iloc[-2]) if len(c)>1 else p
    vol=float(d['Volume'].dropna().iloc[-1]) if 'Volume' in d and not d['Volume'].dropna().empty else None
    return {'ticker':ticker,'price':p,'change_pct':((p/prev)-1)*100 if prev else 0,'volume':vol}

def quote_table(items):
    rows=[]
    for label,ticker in items.items():
        q=quote(ticker); rows.append({'Asset':label,'Ticker':ticker,'Price':q['price'],'Change %':q['change_pct']})
    return pd.DataFrame(rows)
