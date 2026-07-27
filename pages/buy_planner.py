import streamlit as st
import pandas as pd
from engine.market_data import quote
from engine.planner import build_plan
from utils.formatters import money

def render():
    st.title('Buy Planner'); st.caption('예산과 간격을 기준으로 3단계 분할매수 계획을 계산합니다.')
    c1,c2,c3=st.columns(3); ticker=c1.text_input('Ticker','GOOGL').upper().strip(); budget=c2.number_input('총 예산',min_value=100.0,value=5000.0,step=100.0); spacing=c3.slider('각 단계 간격',1.0,15.0,4.0,.5,format='%.1f%%')
    current=quote(ticker)['price']; manual=st.number_input('기준 가격',min_value=.01,value=float(current) if current else 100.0,step=.01)
    plan=pd.DataFrame(build_plan(manual,budget,spacing)); st.dataframe(plan,use_container_width=True,hide_index=True,column_config={'Buy Price':st.column_config.NumberColumn(format='$%.2f'),'Allocation':st.column_config.NumberColumn(format='$%.2f'),'Estimated Cost':st.column_config.NumberColumn(format='$%.2f')})
    shares=int(plan['Shares'].sum()); cost=float(plan['Estimated Cost'].sum()); avg=cost/shares if shares else 0
    a,b,c=st.columns(3); a.metric('총 주식 수',str(shares)); b.metric('예상 사용액',money(cost)); c.metric('예상 평균단가',money(avg))
    if current:
        st.success('현재 가격은 1차 매수 구간 안에 있습니다.') if current<=plan.iloc[0]['Buy Price'] else st.info('현재 가격이 1차 매수가보다 높습니다. 추격보다 대기 구간입니다.')
