import pandas as pd,streamlit as st
from components.charts import candlestick
from components.cards import stars
from engine.market_data import quote,history
from engine.analysis import analyze
from utils.storage import load_json,save_json
from utils.formatters import money,pct,compact

DEFAULT=["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]
def render():
    st.title("Watchlist")
    tickers=load_json("watchlist.json",DEFAULT)
    c1,c2=st.columns([5,1])
    new=c1.text_input("Add ticker",placeholder="GOOGL").strip().upper()
    if c2.button("Add",use_container_width=True) and new:
        if new not in tickers:tickers.append(new);save_json("watchlist.json",tickers);st.rerun()

    rows=[]
    for t in tickers:
        q=quote(t);a=analyze(history(t,"1y"))
        rows.append({"Ticker":t,"Price":q["price"],"Daily %":q["change_pct"],"Score":a["score"],"Rating":stars(a["score"]),
                     "Action":a["action"],"Risk":a["risk"],"RSI":a["rsi"],"Volume":q["volume"]})
    df=pd.DataFrame(rows).sort_values("Score",ascending=False)
    st.dataframe(df,use_container_width=True,hide_index=True,
      column_config={"Price":st.column_config.NumberColumn(format="$%.2f"),"Daily %":st.column_config.NumberColumn(format="%.2f%%"),
                     "Score":st.column_config.ProgressColumn(min_value=0,max_value=100),"RSI":st.column_config.NumberColumn(format="%.1f"),
                     "Volume":st.column_config.NumberColumn(format="compact")})

    selected=st.selectbox("Ticker analysis",tickers)
    h=history(selected,"1y");q=quote(selected);a=analyze(h)
    m=st.columns(7)
    vals=[("Price",money(q["price"]),pct(q["change_pct"])),("Score",f'{a["score"]:.0f}/100',""),
          ("Action",a["action"],""),("Risk",a["risk"],""),("RSI","—" if a["rsi"] is None else f'{a["rsi"]:.1f}',""),
          ("Support",money(a["support"]),""),("Resistance",money(a["resistance"]),"")]
    for c,(lab,val,delta) in zip(m,vals):c.metric(lab,val,delta)
    st.plotly_chart(candlestick(h,selected),use_container_width=True)
    st.info(f'{selected}: {a["action"]} · Trend score {a["score"]:.0f} · Risk {a["risk"]}')
    if st.button(f"Remove {selected}"):
        save_json("watchlist.json",[x for x in tickers if x!=selected]);st.rerun()
