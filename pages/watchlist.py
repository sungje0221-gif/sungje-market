import streamlit as st
import pandas as pd
from components.charts import price_chart
from components.cards import stars
from engine.market_data import history,quote
from engine.analysis import analyze_ticker
from utils.formatters import money,pct
from utils.storage import load_json,save_json
DEFAULT=['GOOGL','META','AMZN','MSFT','AVGO','SMH','CEG','VRT','ETN','ANET','SKHY','SPCX']

def render():
    st.title('Watchlist')
    tickers=load_json('watchlist.json',DEFAULT)
    c1,c2=st.columns([3,1]); new=c1.text_input('종목 추가',placeholder='예: GOOGL').strip().upper()
    c2.write(''); c2.write('')
    if c2.button('추가',use_container_width=True) and new:
        if new not in tickers: tickers.append(new); save_json('watchlist.json',tickers); st.rerun()
    rows=[]
    for t in tickers:
        q=quote(t); a=analyze_ticker(history(t)); rows.append({'Ticker':t,'Price':q['price'],'Daily %':q['change_pct'],'Score':a['score'],'Rating':stars(a['score']),'Action':a['action'],'Risk':a['risk'],'Volume':q['volume']})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,column_config={'Price':st.column_config.NumberColumn(format='$%.2f'),'Daily %':st.column_config.NumberColumn(format='%.2f%%'),'Score':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.0f'),'Volume':st.column_config.NumberColumn(format='compact')})
    selected=st.selectbox('상세 분석',tickers); df=history(selected,'1y'); q=quote(selected); a=analyze_ticker(df)
    cols=st.columns(5); cols[0].metric('Price',money(q['price']),pct(q['change_pct'])); cols[1].metric('Score',f"{a['score']:.0f}/100"); cols[2].metric('Action',a['action']); cols[3].metric('Risk',a['risk']); cols[4].metric('RSI','—' if a['rsi'] is None else f"{a['rsi']:.1f}")
    st.plotly_chart(price_chart(df,selected),use_container_width=True)
    s1,s2=st.columns(2); s1.metric('Support (60D)',money(a['support'])); s2.metric('Resistance (60D)',money(a['resistance'])); st.info(a['comment'])
    if st.button(f'{selected} 삭제'):
        save_json('watchlist.json',[x for x in tickers if x!=selected]); st.rerun()
