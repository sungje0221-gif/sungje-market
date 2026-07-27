import streamlit as st
import pandas as pd
from engine.portfolio import enrich_portfolio
from utils.storage import load_csv,save_csv
from utils.formatters import money
COLUMNS=['Account','Ticker','Shares','Avg Cost','Category']

def render():
    st.title('Portfolio'); df=load_csv('portfolio.csv',COLUMNS)
    with st.expander('포지션 추가',expanded=df.empty):
        with st.form('add_position'):
            c1,c2,c3,c4,c5=st.columns(5); account=c1.text_input('Account','Taxable'); ticker=c2.text_input('Ticker').upper().strip(); shares=c3.number_input('Shares',min_value=0.0,step=1.0); avg=c4.number_input('Avg Cost',min_value=0.0,step=.01); cat=c5.selectbox('Category',['ETF','Mega Cap','AI','Semiconductor','Power','Defense','Healthcare','Other'])
            if st.form_submit_button('추가') and ticker and shares>0:
                df=pd.concat([df,pd.DataFrame([[account,ticker,shares,avg,cat]],columns=COLUMNS)],ignore_index=True); save_csv('portfolio.csv',df); st.rerun()
    if df.empty: st.info('아직 등록된 포지션이 없습니다.'); return
    e=enrich_portfolio(df); total=e['Market Value'].sum(); cost=e['Cost Basis'].sum(); pl=e['P/L'].sum(); pp=(total/cost-1)*100 if cost else 0
    c1,c2,c3=st.columns(3); c1.metric('Market Value',money(total)); c2.metric('Total P/L',money(pl),f'{pp:+.2f}%'); c3.metric('Positions',str(len(e)))
    st.dataframe(e,use_container_width=True,hide_index=True,column_config={'Avg Cost':st.column_config.NumberColumn(format='$%.2f'),'Current Price':st.column_config.NumberColumn(format='$%.2f'),'Market Value':st.column_config.NumberColumn(format='$%.2f'),'Cost Basis':st.column_config.NumberColumn(format='$%.2f'),'P/L':st.column_config.NumberColumn(format='$%.2f'),'P/L %':st.column_config.NumberColumn(format='%.2f%%'),'Weight %':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.1f%%')})
    allocation=e.groupby('Category',as_index=False)['Market Value'].sum(); allocation['Weight %']=allocation['Market Value']/allocation['Market Value'].sum()*100; st.markdown('### Allocation'); st.bar_chart(allocation.set_index('Category')['Weight %'])
    target=st.selectbox('삭제할 종목',e['Ticker'].astype(str).tolist())
    if st.button('선택 종목 삭제'):
        save_csv('portfolio.csv',df[df['Ticker'].astype(str)!=target]); st.rerun()
