import pandas as pd
import streamlit as st
from engine.market_data import quote
from engine.planner import build_plan
from utils.formatters import money

def render():
    st.title("Buy Planner")
    c1,c2,c3=st.columns(3)
    ticker=c1.text_input("Ticker","GOOGL").upper().strip()
    budget=c2.number_input("총 예산",min_value=100.0,value=5000.0,step=100.0)
    spacing=c3.slider("단계 간격",1.0,15.0,4.0,0.5,format="%.1f%%")
    current=quote(ticker)["price"]
    base=st.number_input("기준 가격",min_value=0.01,value=float(current) if current else 100.0,step=0.01)
    plan=pd.DataFrame(build_plan(base,budget,3,spacing))
    st.dataframe(plan,use_container_width=True,hide_index=True,
        column_config={
            "Buy Price":st.column_config.NumberColumn(format="$%.2f"),
            "Allocation":st.column_config.NumberColumn(format="$%.2f"),
            "Estimated Cost":st.column_config.NumberColumn(format="$%.2f"),
        })
    shares=int(plan["Shares"].sum()); cost=float(plan["Estimated Cost"].sum())
    avg=cost/shares if shares else 0
    c1,c2,c3=st.columns(3)
    c1.metric("총 주식 수",shares); c2.metric("예상 사용액",money(cost)); c3.metric("예상 평균단가",money(avg))
