import pandas as pd
import streamlit as st

from components.cards import html_card, stars, score_badge
from components.charts import sector_heatmap
from engine.market_data import quote, history
from engine.indicators import trend_score
from utils.formatters import money, pct

ASSETS = {
    "S&P 500":"^GSPC","Nasdaq":"^IXIC","Russell 2000":"^RUT",
    "VIX":"^VIX","US 10Y":"^TNX","Dollar":"DX-Y.NYB",
    "WTI":"CL=F","Gold":"GC=F","Silver":"SI=F",
    "USD/KRW":"KRW=X","KOSPI":"^KS11",
}
SECTORS = {
    "AI / Nasdaq":"QQQ","Semiconductor":"SMH","Nuclear":"NLR",
    "Defense":"ITA","Healthcare":"XLV","Financial":"XLF",
    "Energy":"XLE","Small Cap":"IWM",
}

def state_from_change(v):
    if v is None: return "neutral"
    return "positive" if v >= 0 else "negative"

def render():
    st.markdown("""
    <div class="smcc-hero">
      <div class="smcc-kicker">Personal Investment Operating System</div>
      <div class="smcc-title">Sungje Market Command Center</div>
      <div class="smcc-sub">오늘 시장을 10초 안에 읽고, 무엇을 해야 할지 결정하는 화면</div>
    </div>
    """, unsafe_allow_html=True)

    spy = history("SPY","6mo")
    qqq = history("QQQ","6mo")
    score = round((trend_score(spy)+trend_score(qqq))/2,1)

    metrics = [
        ("Market Score", f"{score:.0f}/100", score_badge(score), "positive" if score >= 55 else "negative"),
        ("VIX", money(quote("^VIX")["price"]), pct(quote("^VIX")["change_pct"]), state_from_change(quote("^VIX")["change_pct"])),
        ("US 10Y", money(quote("^TNX")["price"]), pct(quote("^TNX")["change_pct"]), state_from_change(quote("^TNX")["change_pct"])),
        ("Dollar", money(quote("DX-Y.NYB")["price"]), pct(quote("DX-Y.NYB")["change_pct"]), state_from_change(quote("DX-Y.NYB")["change_pct"])),
        ("WTI", money(quote("CL=F")["price"]), pct(quote("CL=F")["change_pct"]), state_from_change(quote("CL=F")["change_pct"])),
    ]
    cols = st.columns(5)
    for c, item in zip(cols, metrics):
        with c: html_card(*item)

    st.write("")
    left, right = st.columns([1.7,1])
    with left:
        st.markdown("### Sector Rotation")
        sector_rows = []
        for label,ticker in SECTORS.items():
            df = history(ticker,"6mo")
            q = quote(ticker)
            sector_rows.append({"Sector":label,"Ticker":ticker,"Score":trend_score(df),"Daily %":q["change_pct"]})
        sector_df = pd.DataFrame(sector_rows)
        st.plotly_chart(sector_heatmap(sector_df), use_container_width=True)
    with right:
        st.markdown("### AI Market View")
        if score >= 72:
            msg = "시장 추세가 강합니다. 강한 종목의 눌림목 매수가 유리합니다."
            picks = "GOOGL · META · CEG"
        elif score >= 55:
            msg = "중립 이상입니다. 추격매수보다 분할매수와 종목 선별이 중요합니다."
            picks = "GOOGL · SMH · VXF"
        else:
            msg = "시장 위험이 높습니다. 현금 비중과 손절 기준을 먼저 관리하세요."
            picks = "VOO · XLV · Cash"
        st.markdown(
            f"""
            <div class="smcc-panel">
              <div class="smcc-label">TODAY'S DECISION</div>
              <div style="font-size:22px;font-weight:800;margin:10px 0">{stars(score)} {score:.0f}/100</div>
              <div style="line-height:1.7">{msg}</div>
              <div style="margin-top:16px">
                <span class="smcc-chip">Top Focus</span>
                <span class="smcc-chip">{picks}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Cross Asset")
    rows = []
    for label,ticker in ASSETS.items():
        q = quote(ticker)
        rows.append({"Asset":label,"Ticker":ticker,"Price":q["price"],"Change %":q["change_pct"]})
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price":st.column_config.NumberColumn(format="%.2f"),
            "Change %":st.column_config.NumberColumn(format="%.2f%%"),
        },
    )
