from datetime import datetime

import pandas as pd,streamlit as st
from components.cards import card,badge,stars
from components.charts import sector_treemap,gauge
from engine.market_data import quote,history
from engine.indicators import trend_score
from engine.analysis import market_brief
from utils.formatters import money,pct
from components.tables import colored_change_table

SECTORS={"Technology":"XLK","Communication":"XLC","Consumer Cyclical":"XLY","Financials":"XLF",
"Industrials":"XLI","Healthcare":"XLV","Energy":"XLE","Utilities":"XLU","Real Estate":"XLRE",
"Consumer Defensive":"XLP","Materials":"XLB","Semiconductor":"SMH","Nuclear":"NLR","Defense":"ITA"}
WATCH=["GOOGL","META","MSFT","AAPL","NVDA","AMZN","TSLA","CEG"]

def render():
    now_text = datetime.now().strftime("%A, %B %d · %I:%M:%S %p")
    st.markdown(f"""<div class="hero"><div class="hero-kicker">Personal Investment Operating System</div>
    <div class="hero-title">Good Morning, Sungje ☀️</div>
    <div class="hero-sub">Your market command center for intelligent investing · Updated {now_text}</div></div>""",unsafe_allow_html=True)

    spy=history("SPY","6mo");qqq=history("QQQ","6mo")
    score=round((trend_score(spy)+trend_score(qqq))/2,1)
    vix=quote("^VIX");ten=quote("^TNX");dxy=quote("DX-Y.NYB");oil=quote("CL=F")
    fear=max(0,min(100,round(100-(vix["price"] or 20)*2.2+25)))
    ai_score=round((trend_score(history("QQQ","6mo"))+trend_score(history("SMH","6mo")))/2)

    cols=st.columns(6)
    items=[
      ("Market Score",f"{score:.0f}/100",badge(score),"pos" if score>=55 else "neg"),
      ("AI Score",f"{ai_score:.0f}/100",stars(ai_score),"purple"),
      ("Risk Level","LOW" if score>=65 else "MEDIUM" if score>=45 else "HIGH","Trend + Volatility","pos" if score>=65 else "warn" if score>=45 else "neg"),
      ("Fear & Greed",str(fear),"Greed" if fear>=60 else "Neutral" if fear>=40 else "Fear","pos" if fear>=60 else "warn" if fear>=40 else "neg"),
      ("VIX",money(vix["price"]),pct(vix["change_pct"]),"blue"),
      ("WTI",money(oil["price"]),pct(oil["change_pct"]),"pos" if (oil["change_pct"] or 0)>=0 else "neg"),
    ]
    for c,it in zip(cols,items):
        with c:card(*it)

    st.markdown("### Today's Playbook")
    playbook = []
    if score < 45:
        playbook.append("시장 점수가 낮습니다. 신규 매수는 평소 계획의 25~50%만 실행하세요.")
    elif score < 60:
        playbook.append("중립 구간입니다. 강한 종목만 1차 분할하고 추격매수는 피하세요.")
    else:
        playbook.append("시장 추세가 우호적입니다. 코어·리더 종목의 계획된 분할매수가 가능합니다.")
    if (vix["price"] or 0) >= 25:
        playbook.append("VIX가 높습니다. 레버리지와 단일 종목 집중도를 줄이세요.")
    if (ten["change_pct"] or 0) < 0:
        playbook.append("10년물 금리가 하락 중이라 성장주에는 상대적으로 우호적입니다.")
    if (oil["change_pct"] or 0) <= -3:
        playbook.append("유가가 크게 하락 중입니다. 에너지 약세와 소비·운송 비용 개선을 함께 확인하세요.")

    cols_play = st.columns(min(4, len(playbook)))
    for i, message in enumerate(playbook[:4]):
        with cols_play[i]:
            st.markdown(f'<div class="panel" style="min-height:118px"><b>{i+1}</b><br>{message}</div>', unsafe_allow_html=True)

    st.write("")
    left,right=st.columns([1.5,1])
    with left:
        st.markdown("### Market Overview")
        rows=[]
        for label,t in {"S&P 500":"^GSPC","NASDAQ":"^IXIC","Dow Jones":"^DJI","Russell 2000":"^RUT","VIX":"^VIX","US 10Y":"^TNX","DXY":"DX-Y.NYB","WTI":"CL=F"}.items():
            q=quote(t);rows.append({"Asset":label,"Price":q["price"],"Change %":q["change_pct"]})
        colored_change_table(pd.DataFrame(rows), price_col="Price", change_col="Change %")
    with right:
        st.markdown("### Today's Opportunities")
        opp=[]
        for t in WATCH:
            s=trend_score(history(t,"6mo"));q=quote(t)
            opp.append({"Ticker":t,"Score":round(s),"Daily %":q["change_pct"]})
        odf=pd.DataFrame(opp).sort_values("Score",ascending=False).head(6)
        colored_change_table(odf, price_col="__none__", change_col="Daily %", score_col="Score")

    st.markdown("### Sector Rotation")
    srows=[]
    for label,t in SECTORS.items():
        q=quote(t);srows.append({"Sector":label,"Ticker":t,"Daily %":q["change_pct"]})
    st.plotly_chart(sector_treemap(pd.DataFrame(srows)),use_container_width=True)

    l,r=st.columns([1.35,1])
    with l:
        st.markdown("### AI Market Briefing")
        brief=market_brief(score,vix["price"],ten["price"],dxy["price"])
        st.markdown(f"""<div class="panel"><div style="font-size:21px;font-weight:800">{stars(score)} {score:.0f}/100</div>
        <div style="line-height:1.8;margin-top:10px">{brief}</div>
        <span class="chip">Market Bias: {badge(score)}</span><span class="chip">Timeframe: 1–3 Days</span></div>""",unsafe_allow_html=True)
    with r:
        st.markdown("### Risk Gauges")
        g1,g2=st.columns(2)
        with g1:st.plotly_chart(gauge(fear,"Fear & Greed"),use_container_width=True)
        with g2:st.plotly_chart(gauge(score,"Market Score"),use_container_width=True)
