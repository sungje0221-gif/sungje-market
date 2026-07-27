import pandas as pd,streamlit as st,yfinance as yf

@st.cache_data(ttl=300,show_spinner=False)
def history(ticker,period="6mo",interval="1d"):
    try:
        d=yf.download(ticker,period=period,interval=interval,auto_adjust=False,progress=False,threads=False)
        if isinstance(d.columns,pd.MultiIndex):d.columns=d.columns.get_level_values(0)
        return d.dropna(how="all")
    except:return pd.DataFrame()

@st.cache_data(ttl=180,show_spinner=False)
def quote(ticker):
    d=history(ticker,"5d","1d")
    if d.empty or "Close" not in d:return {"price":None,"change_pct":None,"volume":None}
    c=d["Close"].dropna()
    if c.empty:return {"price":None,"change_pct":None,"volume":None}
    price=float(c.iloc[-1]);prev=float(c.iloc[-2]) if len(c)>1 else price
    volume=float(d["Volume"].dropna().iloc[-1]) if "Volume" in d and not d["Volume"].dropna().empty else None
    return {"price":price,"change_pct":((price/prev)-1)*100 if prev else 0,"volume":volume}

@st.cache_data(ttl=900,show_spinner=False)
def info(ticker):
    try:return yf.Ticker(ticker).fast_info
    except:return {}
