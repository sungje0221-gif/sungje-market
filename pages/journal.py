from datetime import date
import streamlit as st
import pandas as pd
from utils.storage import load_csv,save_csv
COLUMNS=['Date','Ticker','Action','Price','Shares','Reason','Result','Lesson']

def render():
    st.title('Trading Journal'); df=load_csv('journal.csv',COLUMNS)
    with st.form('journal_form'):
        c1,c2,c3,c4,c5=st.columns(5); d=c1.date_input('Date',date.today()); ticker=c2.text_input('Ticker').upper().strip(); action=c3.selectbox('Action',['BUY','SELL','HOLD','WATCH']); price=c4.number_input('Price',min_value=0.0,step=.01); shares=c5.number_input('Shares',min_value=0.0,step=1.0); reason=st.text_area('Reason'); result=st.selectbox('Result',['OPEN','WIN','LOSS','BREAKEVEN']); lesson=st.text_area('Lesson')
        if st.form_submit_button('저장') and ticker:
            row=pd.DataFrame([[str(d),ticker,action,price,shares,reason,result,lesson]],columns=COLUMNS); save_csv('journal.csv',pd.concat([df,row],ignore_index=True)); st.rerun()
    if df.empty: st.info('아직 기록이 없습니다.'); return
    wins=int((df['Result']=='WIN').sum()); losses=int((df['Result']=='LOSS').sum()); closed=wins+losses; rate=wins/closed*100 if closed else 0
    a,b,c=st.columns(3); a.metric('Entries',len(df)); b.metric('Closed Trades',closed); c.metric('Win Rate',f'{rate:.1f}%'); st.dataframe(df.sort_values('Date',ascending=False),use_container_width=True,hide_index=True)
