import pandas as pd,streamlit as st,yfinance as yf
from utils.storage import load_json
DEFAULT=["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","TSLA"]
@st.cache_data(ttl=3600,show_spinner=False)
def date_for(t):
    try:
        c=yf.Ticker(t).calendar
        if isinstance(c,dict):
            v=c.get("Earnings Date");return v[0] if isinstance(v,list) and v else v
    except:return None
def render():
    st.title("Earnings Calendar")
    now=pd.Timestamp.now(tz="UTC");rows=[]
    for t in load_json("watchlist.json",DEFAULT):
        dt=date_for(t);text="—";dd="—"
        if dt is not None:
            ts=pd.Timestamp(dt);ts=ts.tz_localize("UTC") if ts.tzinfo is None else ts
            text=ts.strftime("%Y-%m-%d");d=(ts.normalize()-now.normalize()).days;dd=f"D{d:+d}"
        rows.append({"Ticker":t,"Earnings Date":text,"D-Day":dd})
    st.dataframe(rows,use_container_width=True,hide_index=True)
    st.warning("Verify dates with company investor relations before trading.")
