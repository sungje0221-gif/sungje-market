import pandas as pd,streamlit as st
from engine.market_data import quote,history
from engine.indicators import trend_score
from components.charts import sector_treemap
from components.colored_tables import style_signed_columns
from components.tables import colored_change_table

GROUPS={
"US Indices":{"S&P 500":"^GSPC","NASDAQ":"^IXIC","Dow Jones":"^DJI","Russell 2000":"^RUT"},
"Rates & FX":{"US 10Y":"^TNX","Dollar":"DX-Y.NYB","USD/KRW":"KRW=X","USD/JPY":"JPY=X"},
"Commodities":{"WTI":"CL=F","Gold":"GC=F","Silver":"SI=F","Copper":"HG=F"},
"Global":{"KOSPI":"^KS11","Nikkei":"^N225","Hang Seng":"^HSI","Euro Stoxx":"^STOXX50E"},
}
def render():
    st.title("Market Overview")
    for title,items in GROUPS.items():
        st.markdown(f"### {title}")
        rows=[]
        for label,t in items.items():
            q=quote(t);rows.append({"Asset":label,"Ticker":t,"Price":q["price"],"Change %":q["change_pct"],"Trend Score":trend_score(history(t,"6mo"))})
        colored_change_table(pd.DataFrame(rows), price_col="Price", change_col="Change %", score_col="Trend Score")
