from datetime import datetime

import pandas as pd
import streamlit as st

from components.cards import badge, card, stars
from components.charts import gauge, sector_treemap
from components.tables import colored_change_table
from engine.analysis import market_brief
from engine.indicators import trend_score
from engine.market_data import history, quote
from utils.formatters import money, pct

SECTORS = {
    "Technology": "XLK", "Communication": "XLC", "Consumer Cyclical": "XLY",
    "Financials": "XLF", "Industrials": "XLI", "Healthcare": "XLV",
    "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE",
    "Consumer Defensive": "XLP", "Materials": "XLB", "Semiconductor": "SMH",
    "Nuclear": "NLR", "Defense": "ITA",
}
WATCH = ["GOOGL", "META", "MSFT", "AAPL", "NVDA", "AMZN", "TSLA", "CEG", "SKHY", "VXF"]


def _safe_score(ticker: str) -> float:
    try:
        return float(trend_score(history(ticker, "6mo")))
    except Exception:
        return 50.0


def _playbook(score: float, vix: dict, ten: dict, oil: dict) -> list[str]:
    messages: list[str] = []
    if score < 45:
        messages.append("시장 점수가 약합니다. 신규 매수는 평소 계획의 25~50%만 실행하세요.")
    elif score < 60:
        messages.append("중립 구간입니다. 강한 종목만 1차 분할하고 추격매수는 피하세요.")
    else:
        messages.append("시장 추세가 우호적입니다. 코어·리더 종목의 계획된 분할매수가 가능합니다.")
    if (vix.get("price") or 0) >= 25:
        messages.append("VIX가 높습니다. 레버리지와 단일 종목 집중도를 낮추세요.")
    else:
        messages.append("변동성은 통제 가능한 구간입니다. 다만 장 초반 추격매수는 피하세요.")
    if (ten.get("change_pct") or 0) < 0:
        messages.append("10년물 금리가 하락 중이라 성장주와 반도체에는 상대적으로 우호적입니다.")
    else:
        messages.append("10년물 금리 방향을 확인하세요. 급등 시 고밸류 성장주 비중 확대는 보류하세요.")
    if (oil.get("change_pct") or 0) <= -3:
        messages.append("유가가 크게 하락 중입니다. 에너지 약세와 소비·운송 비용 개선을 함께 확인하세요.")
    else:
        messages.append("오늘은 지수보다 종목 선택이 중요합니다. 상대강도 상위 종목만 선별하세요.")
    return messages[:4]


def render() -> None:
    now = datetime.now()
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-row">
            <div>
              <div class="hero-kicker">Personal Investment Operating System</div>
              <div class="hero-title">Market Command Center</div>
              <div class="hero-sub">한 화면에서 시장 방향, 위험도, 오늘의 매수 판단을 확인합니다.</div>
            </div>
            <div class="hero-clock"><b>{now.strftime('%A, %B %d')}</b>{now.strftime('%I:%M %p')} · Pacific Time</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    spy_score = _safe_score("SPY")
    qqq_score = _safe_score("QQQ")
    score = round((spy_score + qqq_score) / 2, 1)
    vix, ten, dxy, oil = quote("^VIX"), quote("^TNX"), quote("DX-Y.NYB"), quote("CL=F")
    fear = max(0, min(100, round(100 - (vix.get("price") or 20) * 2.2 + 25)))
    ai_score = round((_safe_score("QQQ") + _safe_score("SMH")) / 2)

    cols = st.columns(6)
    items = [
        ("Market Score", f"{score:.0f}/100", badge(score), "pos" if score >= 55 else "neg"),
        ("AI / Tech Score", f"{ai_score:.0f}/100", stars(ai_score), "purple"),
        ("Risk Level", "LOW" if score >= 65 else "MEDIUM" if score >= 45 else "HIGH",
         "Trend + volatility", "pos" if score >= 65 else "warn" if score >= 45 else "neg"),
        ("Fear & Greed", str(fear), "Greed" if fear >= 60 else "Neutral" if fear >= 40 else "Fear",
         "pos" if fear >= 60 else "warn" if fear >= 40 else "neg"),
        ("VIX", money(vix.get("price")), pct(vix.get("change_pct")), "blue"),
        ("WTI Crude", money(oil.get("price")), pct(oil.get("change_pct")),
         "pos" if (oil.get("change_pct") or 0) >= 0 else "neg"),
    ]
    for col, item in zip(cols, items):
        with col:
            card(*item)

    st.markdown('<div class="section-eyebrow">ACTION PLAN</div>', unsafe_allow_html=True)
    st.markdown("### Today's Playbook")
    playbook = _playbook(score, vix, ten, oil)
    for col, message, number in zip(st.columns(4), playbook, range(1, 5)):
        with col:
            st.markdown(
                f'<div class="playbook-card"><div class="playbook-number">{number}</div>'
                f'<div class="playbook-copy">{message}</div></div>',
                unsafe_allow_html=True,
            )

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="section-eyebrow">GLOBAL PULSE</div>', unsafe_allow_html=True)
        st.markdown("### Market Overview")
        rows = []
        instruments = {
            "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "Dow Jones": "^DJI",
            "Russell 2000": "^RUT", "VIX": "^VIX", "US 10Y": "^TNX",
            "Dollar Index": "DX-Y.NYB", "WTI": "CL=F",
        }
        for label, ticker in instruments.items():
            data = quote(ticker)
            rows.append({"Asset": label, "Price": data.get("price"), "Change %": data.get("change_pct")})
        colored_change_table(pd.DataFrame(rows), price_col="Price", change_col="Change %")

    with right:
        st.markdown('<div class="section-eyebrow">RELATIVE STRENGTH</div>', unsafe_allow_html=True)
        st.markdown("### Today's Opportunities")
        opportunities = []
        for ticker in WATCH:
            data = quote(ticker)
            opportunities.append({"Ticker": ticker, "Score": round(_safe_score(ticker)), "Daily %": data.get("change_pct")})
        opportunity_df = pd.DataFrame(opportunities).sort_values(["Score", "Daily %"], ascending=False).head(7)
        colored_change_table(opportunity_df, price_col="__none__", change_col="Daily %", score_col="Score")

    st.markdown('<div class="section-eyebrow">MONEY FLOW</div>', unsafe_allow_html=True)
    st.markdown("### Sector Rotation")
    sector_rows = []
    for label, ticker in SECTORS.items():
        data = quote(ticker)
        sector_rows.append({"Sector": label, "Ticker": ticker, "Daily %": data.get("change_pct")})
    st.plotly_chart(sector_treemap(pd.DataFrame(sector_rows)), use_container_width=True)

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.markdown('<div class="section-eyebrow">DECISION SUPPORT</div>', unsafe_allow_html=True)
        st.markdown("### AI Market Briefing")
        brief = market_brief(score, vix.get("price"), ten.get("price"), dxy.get("price"))
        st.markdown(
            f"""<div class="panel"><div style="font-size:22px;font-weight:900">{stars(score)} {score:.0f}/100</div>
            <div style="line-height:1.8;margin-top:10px;color:#b8c6d6">{brief}</div>
            <span class="chip">Market Bias: {badge(score)}</span><span class="chip">Timeframe: 1–3 Days</span></div>""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown('<div class="section-eyebrow">RISK CONTROL</div>', unsafe_allow_html=True)
        st.markdown("### Risk Gauges")
        gauge_left, gauge_right = st.columns(2)
        with gauge_left:
            st.plotly_chart(gauge(fear, "Fear & Greed"), use_container_width=True)
        with gauge_right:
            st.plotly_chart(gauge(score, "Market Score"), use_container_width=True)
