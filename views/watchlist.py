import pandas as pd
import streamlit as st
from components.charts import price_chart
from components.cards import stars
from engine.market_data import history, quote
from engine.analysis import analyze_ticker
from utils.storage import load_json, save_json
from utils.formatters import money, pct

DEFAULT=["GOOGL","META","AMZN","MSFT","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]

def render():
    st.title("Watchlist")
    tickers=load_json("watchlist.json",DEFAULT)

    a,b=st.columns([4,1])
    new=a.text_input("종목 추가",placeholder="예: GOOGL").strip().upper()
    if b.button("추가",use_container_width=True) and new:
        if new not in tickers:
            tickers.append(new); save_json("watchlist.json",tickers); st.rerun()

    rows=[]
    for ticker in tickers:
        q=quote(ticker); df=history(ticker,"6mo"); x=analyze_ticker(df)
        rows.append({"Ticker":ticker,"Price":q["price"],"Daily %":q["change_pct"],
                     "Score":x["score"],"Rating":stars(x["score"]),
                     "Action":x["action"],"Risk":x["risk"]})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,
        column_config={
            "Price":st.column_config.NumberColumn(format="$%.2f"),
            "Daily %":st.column_config.NumberColumn(format="%.2f%%"),
            "Score":st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.0f"),
        })

    selected=st.selectbox("상세 분석",tickers)
    df=history(selected,"1y"); q=quote(selected); x=analyze_ticker(df)
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Price",money(q["price"]),pct(q["change_pct"]))
    c2.metric("Score",f'{x["score"]:.0f}/100')
    c3.metric("Action",x["action"])
    c4.metric("Risk",x["risk"])
    c5.metric("RSI","—" if x["rsi"] is None else f'{x["rsi"]:.1f}')
    st.plotly_chart(price_chart(df,selected),use_container_width=True)
    c1,c2=st.columns(2)
    c1.metric("Support (60D)",money(x["support"]))
    c2.metric("Resistance (60D)",money(x["resistance"]))
    st.info(x["comment"])
    if st.button(f"{selected} 삭제"):
        save_json("watchlist.json",[x for x in tickers if x!=selected]); st.rerun()
