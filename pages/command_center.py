import streamlit as st
from components.cards import score_badge,stars
from engine.market_data import quote,quote_table,history
from engine.indicators import trend_score
from utils.formatters import money,pct

ASSETS={'S&P 500':'^GSPC','Nasdaq':'^IXIC','Russell 2000':'^RUT','VIX':'^VIX','US 10Y':'^TNX','Dollar':'DX-Y.NYB','WTI':'CL=F','Gold':'GC=F','Silver':'SI=F','USD/KRW':'KRW=X','KOSPI':'^KS11'}
SECTORS={'AI / Nasdaq':'QQQ','Semiconductor':'SMH','Nuclear':'NLR','Defense':'ITA','Healthcare':'XLV','Financial':'XLF','Energy':'XLE','Small Cap':'IWM'}

def render():
    st.title('Sungje Market Command Center')
    st.caption('오늘 시장을 10초 안에 읽는 화면')
    score=round((trend_score(history('SPY'))+trend_score(history('QQQ')))/2,1)
    vals=[('Market Score',f'{score:.0f}/100',score_badge(score)),('VIX','^VIX',None),('US 10Y','^TNX',None),('Dollar','DX-Y.NYB',None),('WTI','CL=F',None)]
    cols=st.columns(5)
    for i,(label,ticker,delta) in enumerate(vals):
        if i==0: cols[i].metric(label,ticker,delta)
        else:
            q=quote(ticker); cols[i].metric(label,money(q['price']),pct(q['change_pct']))
    view='시장 추세는 강한 편입니다. 강한 종목의 눌림목 중심으로 접근하세요.' if score>=72 else '시장 추세는 중립 이상입니다. 추격매수보다 분할매수가 중요합니다.' if score>=55 else '시장 위험이 높아진 상태입니다. 현금 비중과 손절 기준을 먼저 관리하세요.'
    st.info(f'{stars(score)}  {view}')
    st.markdown('### Cross Asset')
    st.dataframe(quote_table(ASSETS),use_container_width=True,hide_index=True,column_config={'Price':st.column_config.NumberColumn(format='%.2f'),'Change %':st.column_config.NumberColumn(format='%.2f%%')})
    st.markdown('### Sector Rotation')
    rows=[]
    for label,ticker in SECTORS.items():
        s=trend_score(history(ticker)); q=quote(ticker); rows.append({'Sector':label,'ETF':ticker,'Score':round(s,1),'Rating':stars(s),'Daily %':q['change_pct']})
    st.dataframe(rows,use_container_width=True,hide_index=True,column_config={'Score':st.column_config.ProgressColumn(min_value=0,max_value=100,format='%.0f'),'Daily %':st.column_config.NumberColumn(format='%.2f%%')})
