from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

import pandas as pd
import streamlit as st

from components.cards import badge, stars
from components.charts import sector_treemap
from components.tables import colored_change_table
from engine.analysis import market_brief
from engine.indicators import trend_score
from engine.market_data import history, quote
from utils.formatters import money, pct

SECTORS = {
    "Technology": "XLK",
    "Communication": "XLC",
    "Consumer": "XLY",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Defensive": "XLP",
    "Materials": "XLB",
    "Semiconductor": "SMH",
    "Nuclear": "NLR",
    "Defense": "ITA",
}

WATCH = ["VOO", "VXF", "GOOGL", "CEG", "SKHY", "KORU", "QQQM", "SMH"]

MARKET_ASSETS = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
    "US 10Y": "^TNX",
    "Dollar": "DX-Y.NYB",
    "WTI": "CL=F",
}


def _safe_score(ticker: str) -> float:
    try:
        value = trend_score(history(ticker, "6mo"))
        return float(value) if value is not None else 50.0
    except Exception:
        return 50.0


def _sparkline_svg(ticker: str, width: int = 146, height: int = 36) -> str:
    """Return a tiny dependency-free SVG sparkline for a dashboard card."""
    try:
        frame = history(ticker, "1mo", "1d")
        values = frame["Close"].dropna().astype(float).tail(22).tolist()
    except Exception:
        values = []

    if len(values) < 2:
        return '<div class="spark-empty">No chart</div>'

    low, high = min(values), max(values)
    spread = high - low or 1.0
    points = []
    for index, value in enumerate(values):
        x = index * width / max(1, len(values) - 1)
        y = height - 3 - ((value - low) / spread) * (height - 8)
        points.append(f"{x:.1f},{y:.1f}")

    positive = values[-1] >= values[0]
    stroke = "#35d6a5" if positive else "#ff6474"
    fill = "rgba(53,214,165,.10)" if positive else "rgba(255,100,116,.10)"
    polygon = f"0,{height} " + " ".join(points) + f" {width},{height}"
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
        f'<polygon points="{polygon}" fill="{fill}" />'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="{stroke}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" />'
        "</svg>"
    )


def _market_state(score: float, vix_value: float | None) -> tuple[str, str]:
    vix = vix_value or 20
    if score >= 65 and vix < 22:
        return "RISK ON", "positive"
    if score < 42 or vix >= 28:
        return "DEFENSIVE", "negative"
    return "SELECTIVE", "neutral"


def _hero_ticker(label: str, ticker: str, data: dict) -> str:
    change = data.get("change_pct")
    css = "up" if (change or 0) >= 0 else "down"
    price = data.get("price")
    if ticker == "^TNX" and price is not None:
        shown_price = f"{price:.2f}%"
    else:
        shown_price = money(price)
    return (
        '<div class="hero-quote">'
        f'<span>{escape(label)}</span><b>{shown_price}</b>'
        f'<em class="{css}">{pct(change)}</em></div>'
    )


def _signal_card(label: str, value: str, note: str, tone: str, ticker: str) -> str:
    return f"""
    <div class="signal-card {tone}">
      <div class="signal-top"><span>{escape(label)}</span><span class="signal-dot"></span></div>
      <div class="signal-value">{value}</div>
      <div class="signal-note">{note}</div>
      {_sparkline_svg(ticker)}
    </div>
    """


def _playbook(score: float, vix: dict, ten: dict, oil: dict):
    buy = "코어 ETF와 상대강도 상위 종목만 1차 분할매수" if score >= 55 else "신규 매수는 계획 금액의 25% 이하로 제한"
    hold = "기존 강한 종목은 추세 훼손 전까지 유지" if score >= 50 else "코어 ETF와 현금 비중을 우선 유지"
    avoid = "장 초반 급등 추격과 레버리지 확대" if (vix.get("price") or 0) < 25 else "레버리지·집중매수·감정적 물타기"
    watch = "에너지 약세에 따른 소비·운송 수혜" if (oil.get("change_pct") or 0) <= -3 else "금리·달러·반도체 상대강도 변화"
    if (ten.get("change_pct") or 0) > 1.5:
        watch = "10년물 금리 상승과 성장주 압력"
    return [
        ("BUY", buy, "buy", "01"),
        ("HOLD", hold, "hold", "02"),
        ("AVOID", avoid, "avoid", "03"),
        ("WATCH", watch, "watch", "04"),
    ]


def _watch_card(ticker: str, score: float, data: dict) -> str:
    change = data.get("change_pct")
    change_class = "up" if (change or 0) >= 0 else "down"
    score_class = "strong" if score >= 65 else "weak" if score < 45 else "mid"
    return f"""
    <div class="watch-card">
      <div class="watch-head"><b>{ticker}</b><span class="score-pill {score_class}">{score:.0f}</span></div>
      <div class="watch-price">{money(data.get('price'))}</div>
      <div class="watch-change {change_class}">{pct(change)}</div>
      {_sparkline_svg(ticker, width=170, height=42)}
    </div>
    """


def render() -> None:
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    quotes = {label: quote(ticker) for label, ticker in MARKET_ASSETS.items()}
    spy = quotes["S&P 500"]
    nasdaq = quotes["NASDAQ"]
    vix = quotes["VIX"]
    ten = quotes["US 10Y"]
    dxy = quotes["Dollar"]
    oil = quotes["WTI"]

    score = round((_safe_score("SPY") + _safe_score("QQQ")) / 2, 1)
    ai_score = round((_safe_score("QQQ") + _safe_score("SMH")) / 2)
    fear = max(0, min(100, round(100 - (vix.get("price") or 20) * 2.2 + 25)))
    state, state_tone = _market_state(score, vix.get("price"))

    greeting = "Morning" if now.hour < 12 else "Afternoon" if now.hour < 18 else "Evening"
    st.markdown(
        f"""
        <div class="hero terminal-hero">
          <div class="hero-row">
            <div class="hero-copy">
              <div class="hero-kicker">SUNGJE INVESTMENT OS · COMMAND CENTER</div>
              <div class="hero-title">Good {greeting}, Sungje</div>
              <div class="hero-sub">{now.strftime('%A, %B %d · %I:%M %p')} Pacific Time</div>
              <div class="market-regime {state_tone}"><span></span>{state}</div>
            </div>
            <div class="hero-market-strip">
              {_hero_ticker('S&P 500', '^GSPC', spy)}
              {_hero_ticker('NASDAQ', '^IXIC', nasdaq)}
              {_hero_ticker('VIX', '^VIX', vix)}
              {_hero_ticker('US 10Y', '^TNX', ten)}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    signal_cards = [
        ("Market Score", f"{score:.0f}<small>/100</small>", badge(score), "blue-card", "SPY"),
        ("AI / Tech", f"{ai_score:.0f}<small>/100</small>", stars(ai_score), "purple-card", "QQQ"),
        ("Fear & Greed", str(fear), "Greed" if fear >= 60 else "Neutral" if fear >= 40 else "Fear", "green-card" if fear >= 60 else "yellow-card", "^VIX"),
        ("Volatility", f"{vix.get('price') or 0:.2f}", pct(vix.get("change_pct")), "red-card" if (vix.get("price") or 0) >= 25 else "blue-card", "^VIX"),
        ("US 10Y", f"{ten.get('price') or 0:.2f}%", pct(ten.get("change_pct")), "yellow-card", "^TNX"),
        ("Dollar", money(dxy.get("price")), pct(dxy.get("change_pct")), "blue-card", "DX-Y.NYB"),
    ]
    for col, item in zip(st.columns(6), signal_cards):
        with col:
            st.markdown(_signal_card(*item), unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><div><span>TODAY\'S ACTION PLAN</span><h3>Playbook</h3></div><em>Rules before emotions</em></div>', unsafe_allow_html=True)
    for col, (label, message, tone, number) in zip(st.columns(4), _playbook(score, vix, ten, oil)):
        with col:
            st.markdown(
                f'<div class="action-card {tone}"><div class="action-top"><div class="action-label">{label}</div><span>{number}</span></div><div class="action-copy">{message}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-heading"><div><span>PERSONAL RADAR</span><h3>My Watchlist</h3></div><em>Trend score · daily move · 1 month path</em></div>', unsafe_allow_html=True)
    watch_items = []
    for ticker in WATCH:
        watch_items.append((ticker, _safe_score(ticker), quote(ticker)))
    for row_start in range(0, len(watch_items), 4):
        cols = st.columns(4)
        for col, (ticker, ticker_score, data) in zip(cols, watch_items[row_start : row_start + 4]):
            with col:
                st.markdown(_watch_card(ticker, ticker_score, data), unsafe_allow_html=True)

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="section-heading compact"><div><span>GLOBAL PULSE</span><h3>Market Overview</h3></div></div>', unsafe_allow_html=True)
        rows = []
        for label, ticker in MARKET_ASSETS.items():
            data = quotes[label]
            rows.append({"Asset": label, "Price": data.get("price"), "Change %": data.get("change_pct")})
        colored_change_table(pd.DataFrame(rows), price_col="Price", change_col="Change %")

    with right:
        st.markdown('<div class="section-heading compact"><div><span>AI BRIEF</span><h3>Decision Context</h3></div></div>', unsafe_allow_html=True)
        brief = market_brief(score, vix.get("price"), ten.get("price"), dxy.get("price"))
        st.markdown(
            f"""
            <div class="ai-brief-panel">
              <div class="ai-brief-head"><span>OS SIGNAL</span><b>{score:.0f}/100</b></div>
              <div class="ai-brief-copy">{escape(str(brief))}</div>
              <div class="brief-tags"><span>Bias · {badge(score)}</span><span>Horizon · 1–3 Days</span><span>Regime · {state}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-heading"><div><span>MONEY FLOW</span><h3>Sector Rotation</h3></div><em>Daily relative performance</em></div>', unsafe_allow_html=True)
    sector_rows = []
    for label, ticker in SECTORS.items():
        data = quote(ticker)
        sector_rows.append({"Sector": label, "Ticker": ticker, "Daily %": data.get("change_pct")})
    st.plotly_chart(sector_treemap(pd.DataFrame(sector_rows)), use_container_width=True, config={"displayModeBar": False})
