from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import stock_heatmap
from engine.market_data import quote
from engine.fundamentals import ticker_info
from utils.storage import load_json

GROUPS = {
    "NASDAQ 100": ["NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","TSLA","COST","NFLX","AMD","PLTR","CSCO","TMUS","LIN","PEP","ADBE","INTU","AMGN","QCOM","TXN","BKNG","AMAT","PANW","GILD","HON","MU","SBUX","MELI","ADI"],
    "S&P 500 Leaders": ["NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","BRK-B","JPM","LLY","V","XOM","WMT","MA","COST","JNJ","NFLX","HD","PG","ORCL","ABBV","BAC","KO","CRM","CVX","PM","IBM","GE","CAT","UNH"],
    "AI & Infrastructure": ["NVDA","AVGO","AMD","MU","TSM","ASML","AMAT","LRCX","KLAC","SMCI","VRT","ETN","ANET","GLW","MSFT","GOOGL","META","AMZN","ORCL","PLTR","CEG","VST","GEV","PWR","DELL","HPE","MRVL","ARM","CRDO","ALAB"],
    "ETFs": ["VOO","SPY","QQQ","QQQM","VXF","IWM","IJH","SMH","SOXX","XLK","XLC","XLY","XLF","XLI","XLV","XLE","XLU","XLRE","XLP","XLB","ITA","NLR","SCHD","VYM","DGRO","GLD","SLV","COPX","EWY","KORU"],
}
SECTOR_GROUPS = {
    "Technology": ["AAPL","MSFT","NVDA","AVGO","ORCL","CRM","AMD","ADBE","CSCO","IBM","QCOM","TXN","AMAT","ANET","PLTR"],
    "Communication": ["GOOGL","META","NFLX","TMUS","DIS","T","VZ","CMCSA","SPOT","RDDT","PINS","SNAP"],
    "Consumer": ["AMZN","TSLA","HD","MCD","BKNG","TJX","LOW","SBUX","NKE","COST","CAVA","CMG"],
    "Financials": ["JPM","BAC","WFC","GS","MS","V","MA","AXP","BLK","SCHW","COF","C"],
    "Healthcare": ["LLY","UNH","JNJ","ABBV","MRK","AMGN","TMO","ABT","ISRG","GILD","VRTX","PFE"],
    "Industrials": ["GE","CAT","RTX","HON","UNP","ETN","PWR","GEV","BA","LMT","DE","UPS"],
    "Energy": ["XOM","CVX","COP","EOG","SLB","OXY","MPC","VLO","PSX","WMB","OKE","FANG"],
    "Utilities & Power": ["CEG","VST","NEE","SO","DUK","AEP","SRE","D","EXC","PCG","NRG","AES"],
    "Semiconductors": ["NVDA","AVGO","AMD","TSM","ASML","MU","AMAT","LRCX","KLAC","QCOM","TXN","ARM","MRVL","ALAB"],
    "Space & Defense": ["RKLB","ASTS","LUNR","PL","KTOS","LMT","RTX","NOC","GD","BA","ACHR","JOBY"],
}

@st.cache_data(ttl=300, show_spinner=False)
def build_rows(tickers, sector_name=None):
    rows=[]
    for ticker in tickers:
        q=quote(ticker); info=ticker_info(ticker)
        try: weight=max(float(info.get("marketCap") or 1),1.0)
        except (TypeError,ValueError): weight=1.0
        rows.append({"Ticker":ticker,"Price":q.get("price"),"Change %":q.get("change_pct"),"Weight":weight,"Sector":sector_name or info.get("sector") or "Market"})
    return pd.DataFrame(rows)


def _summary(df):
    valid=df.dropna(subset=["Change %"])
    if valid.empty: return 0,0,0,"—","—"
    adv=int((valid["Change %"]>0).sum()); dec=int((valid["Change %"]<0).sum())
    return adv,dec,float(valid["Change %"].mean()),valid.loc[valid["Change %"].idxmax(),"Ticker"],valid.loc[valid["Change %"].idxmin(),"Ticker"]


def render():
    st.markdown('<div class="page-kicker">MARKET BREADTH & MONEY FLOW</div>',unsafe_allow_html=True)
    st.title("Market Heatmap")
    st.caption("크기는 시가총액, 색상은 당일 등락률입니다. 클릭 없이 시장의 강약과 자금 흐름을 한눈에 확인합니다.")

    mode=st.segmented_control("View", ["Major Indexes","Sectors","My Watchlist"], default="Major Indexes")
    if mode=="Major Indexes":
        selected=st.selectbox("Index / Theme",list(GROUPS.keys()),label_visibility="collapsed"); df=build_rows(GROUPS[selected]); title=selected
    elif mode=="Sectors":
        selected=st.selectbox("Sector",list(SECTOR_GROUPS.keys()),label_visibility="collapsed"); df=build_rows(SECTOR_GROUPS[selected],selected); title=selected
    else:
        tickers=load_json("watchlist.json",[])
        if not tickers: st.info("Watchlist에 종목을 먼저 추가하세요."); return
        df=build_rows(tickers,"My Watchlist"); title="My Watchlist"

    adv,dec,avg,best,worst=_summary(df)
    for col,(label,value,note,cls) in zip(st.columns(5),[("ADVANCERS",adv,"Positive","pos"),("DECLINERS",dec,"Negative","neg"),("AVERAGE",f"{avg:+.2f}%","Breadth","pos" if avg>=0 else "neg"),("LEADER",best,"Top performer","blue"),("LAGGARD",worst,"Weakest","warn")]):
        with col: st.markdown(f'<div class="mini-stat"><span>{label}</span><b class="{cls}">{value}</b><em>{note}</em></div>',unsafe_allow_html=True)

    st.plotly_chart(stock_heatmap(df,title),use_container_width=True,config={"displaylogo":False})
    leaders,laggards=st.columns(2,gap="large")
    with leaders:
        st.markdown("#### Leaders")
        st.dataframe(df[["Ticker","Price","Change %","Sector"]].sort_values("Change %",ascending=False).head(10),use_container_width=True,hide_index=True,column_config={"Price":st.column_config.NumberColumn(format="$%.2f"),"Change %":st.column_config.NumberColumn(format="%+.2f%%")})
    with laggards:
        st.markdown("#### Laggards")
        st.dataframe(df[["Ticker","Price","Change %","Sector"]].sort_values("Change %").head(10),use_container_width=True,hide_index=True,column_config={"Price":st.column_config.NumberColumn(format="$%.2f"),"Change %":st.column_config.NumberColumn(format="%+.2f%%")})
