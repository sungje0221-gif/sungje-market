import pandas as pd
import streamlit as st
import yfinance as yf

@st.cache_data(ttl=300, show_spinner=False)
def history(ticker, period="6mo", interval="1d"):
    try:
        data = yf.download(ticker, period=period, interval=interval,
                           auto_adjust=False, progress=False, threads=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data.dropna(how="all")
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=180, show_spinner=False)
def quote(ticker):
    df = history(ticker, "5d", "1d")
    if df.empty or "Close" not in df:
        return {"ticker":ticker,"price":None,"change_pct":None,"volume":None}
    close = df["Close"].dropna()
    if close.empty:
        return {"ticker":ticker,"price":None,"change_pct":None,"volume":None}
    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else price
    volume = float(df["Volume"].dropna().iloc[-1]) if "Volume" in df and not df["Volume"].dropna().empty else None
    return {
        "ticker":ticker,
        "price":price,
        "change_pct":((price/prev)-1)*100 if prev else 0,
        "volume":volume,
    }
