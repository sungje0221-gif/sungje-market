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
    "Technology": "XLK", "Communication": "XLC", "Consumer": "XLY", "Financials": "XLF",
    "Industrials": "XLI", "Healthcare": "XLV", "Energy": "XLE", "Utilities": "XLU",
    "Real Estate": "XLRE", "Defensive": "XLP", "Materials": "XLB", "Semiconductor": "SMH",
    "Nuclear": "NLR", "Defense": "ITA",
}
WATCH = ["GOOGL", "META", "MSFT", "AAPL", "NVDA", "AMZN", "TSLA", "CEG", "SKHY", "VXF"]


def _safe_score(ticker: str) -> float:
    try:
        return float(trend_score(history(ticker, "6mo")))
    except Exception:
        return 50.0


def _playbook(score: float, vix: dict, ten: dict, oil: dict):
    buy = "코어와 상대강도 상위 종목만 1차 분할매수" if score >= 50 else "신규 매수는 계획 금액의 25% 이하"
    hold = "10년물 금리 하락 수혜 성장주와 반도체 유지" if (ten.get("change_pct") or 0) < 0 else "코어 ETF와 현금 비중 유지"
    avoid = "장 초반 급등 추격과 레버리지 확대" if (vix.get("price") or 0) < 25 else "레버리지·집중매수·물타기"
    watch = "에너지 약세와 소비·운송 비용 개선" if (oil.get("change_pct") or 0) <= -3 else "금리·달러·반도체 상대강도"
    return [("BUY", buy, "buy"), ("HOLD", hold, "hold"), ("AVOID", avoid, "avoid"), ("WATCH", watch, "watch")]


def _hero_ticker(label: str, data: dict) -> str:
    change = data.get("change_pct")
    cls = "up" if (change or 0) >= 0 else "down"
    return f'<div class="hero-quote"><span>{label}</span><b>{money(data.get("price"))}</b><em class="{cls}">{pct(change)}</em></div>'


def render() -> None:
    now = datetime.now()
    spy, nasdaq, vix, ten, dxy, oil = quote("^GSPC"), quote("^IXIC"), quote("^VIX"), quote("^TNX"), quote("DX-Y.NYB"), quote("CL=F")
    st.markdown(
        f"""
        <div class="hero compact-hero">
          <div class="hero-row">
            <div><div class="hero-kicker">PERSONAL INVESTMENT OPERATING SYSTEM</div>
            <div class="hero-title">Good {"Morning" if now.hour < 12 else "Afternoon" if now.hour < 18 else "Evening"}, Sungje</div>
            <div class="hero-sub">{now.strftime('%A, %B %d · %I:%M %p')} Pacific Time</div></div>
            <div class="hero-market-strip">{_hero_ticker('S&P 500', spy)}{_hero_ticker('NASDAQ', nasdaq)}{_hero_ticker('VIX', vix)}</div>
          </div>
        </div>
        """, unsafe_allow_html=True,
    )

    score = round((_safe_score("SPY") + _safe_score("QQQ")) / 2, 1)
    ai_score = round((_safe_score("QQQ") + _safe_score("SMH")) / 2)
    fear = max(0, min(100, round(100 - (vix.get("price") or 20) * 2.2 + 25)))
    items = [
        ("Market Score", f"{score:.0f}/100", badge(score), "pos" if score >= 55 else "neg"),
        ("AI / Tech", f"{ai_score:.0f}/100", stars(ai_score), "purple"),
        ("Risk", "LOW" if score >= 65 else "MEDIUM" if score >= 45 else "HIGH", "Trend + volatility", "pos" if score >= 65 else "warn" if score >= 45 else "neg"),
        ("Fear & Greed", str(fear), "Greed" if fear >= 60 else "Neutral" if fear >= 40 else "Fear", "pos" if fear >= 60 else "warn" if fear >= 40 else "neg"),
        ("US 10Y", f"{ten.get('price') or 0:.2f}%", pct(ten.get("change_pct")), "blue"),
        ("WTI", money(oil.get("price")), pct(oil.get("change_pct")), "pos" if (oil.get("change_pct") or 0) >= 0 else "neg"),
    ]
    for col, item in zip(st.columns(6), items):
        with col: card(*item)

    st.markdown('<div class="section-eyebrow">TODAY\'S ACTION PLAN</div>', unsafe_allow_html=True)
    st.markdown("### Playbook")
    for col, (label, message, tone) in zip(st.columns(4), _playbook(score, vix, ten, oil)):
        with col:
            st.markdown(f'<div class="action-card {tone}"><div class="action-label">{label}</div><div class="action-copy">{message}</div></div>', unsafe_allow_html=True)

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.markdown('<div class="section-eyebrow">GLOBAL PULSE</div>', unsafe_allow_html=True)
        st.markdown("### Market Overview")
        rows=[]
        for label,ticker in {"S&P 500":"^GSPC","NASDAQ":"^IXIC","Dow Jones":"^DJI","Russell 2000":"^RUT","VIX":"^VIX","US 10Y":"^TNX","Dollar":"DX-Y.NYB","WTI":"CL=F"}.items():
            data=quote(ticker); rows.append({"Asset":label,"Price":data.get("price"),"Change %":data.get("change_pct")})
        colored_change_table(pd.DataFrame(rows), price_col="Price", change_col="Change %")
    with right:
        st.markdown('<div class="section-eyebrow">RELATIVE STRENGTH</div>', unsafe_allow_html=True)
        st.markdown("### Opportunities")
        rows=[]
        for ticker in WATCH:
            data=quote(ticker); rows.append({"Ticker":ticker,"Score":round(_safe_score(ticker)),"Daily %":data.get("change_pct")})
        colored_change_table(pd.DataFrame(rows).sort_values(["Score","Daily %"],ascending=False).head(7), price_col="__none__", change_col="Daily %", score_col="Score")

    st.markdown('<div class="section-eyebrow">MONEY FLOW</div>', unsafe_allow_html=True)
    st.markdown("### Sector Rotation")
    rows=[]
    for label,ticker in SECTORS.items():
        data=quote(ticker); rows.append({"Sector":label,"Ticker":ticker,"Daily %":data.get("change_pct")})
    st.plotly_chart(sector_treemap(pd.DataFrame(rows)), use_container_width=True)

    left,right=st.columns([1.35,1],gap="large")
    with left:
        st.markdown('<div class="section-eyebrow">AI BRIEF</div>', unsafe_allow_html=True)
        st.markdown("### Market View")
        brief=market_brief(score,vix.get("price"),ten.get("price"),dxy.get("price"))
        st.markdown(f'<div class="panel"><div class="brief-score">{stars(score)} {score:.0f}/100</div><div class="brief-copy">{brief}</div><span class="chip">Bias: {badge(score)}</span><span class="chip">1–3 Days</span></div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section-eyebrow">RISK CONTROL</div>', unsafe_allow_html=True)
        st.markdown("### Risk Gauges")
        a,b=st.columns(2)
        with a: st.plotly_chart(gauge(fear,"Fear & Greed"),use_container_width=True)
        with b: st.plotly_chart(gauge(score,"Market Score"),use_container_width=True)
