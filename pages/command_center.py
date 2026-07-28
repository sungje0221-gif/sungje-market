from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from components.cards import badge
from engine.analysis import market_brief
from engine.indicators import trend_score
from engine.market_data import batch_history, batch_quotes, direct_daily_quote
from utils.formatters import money, pct
from utils.storage import load_json

WATCH_FALLBACK = ["VOO", "QQQM", "GOOGL", "SKHY", "KORU", "SMH", "JPM", "AVGO", "NVDA", "AMZN", "META", "HOOD"]

TOP_MARKET = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Russell": "^RUT",
    "VIX": "^VIX",
    "US 10Y": "^TNX",
    "DXY": "DX-Y.NYB",
}

FUTURES = {
    "S&P": "ES=F",
    "Nasdaq": "NQ=F",
    "Dow": "YM=F",
    "Russell": "RTY=F",
    "VIX": "^VIX",
}

MACRO = {
    "DXY": "DX-Y.NYB",
    "US 10Y": "^TNX",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Oil": "CL=F",
}

KOREA = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "삼성전자 (005930)": "005930.KS",
    "SK하이닉스 (000660)": "000660.KS",
    "USD/KRW": "KRW=X",
}


def _fmt_price(label: str, price: float | None) -> str:
    if price is None:
        return "—"
    if label == "US 10Y":
        return f"{price:.2f}%"
    if label == "USD/KRW":
        return f"₩{price:,.2f}"
    if label in {"삼성전자 (005930)", "SK하이닉스 (000660)"}:
        return f"₩{price:,.0f}"
    if label in {"S&P 500", "NASDAQ", "Russell", "VIX", "S&P", "Nasdaq", "Dow", "KOSPI", "KOSDAQ"}:
        return f"{price:,.2f}"
    return f"${price:,.2f}"


def _watchlist_tickers(limit: int = 12) -> list[str]:
    raw = load_json("watchlist.json", [])
    tickers: list[str] = []
    for item in raw:
        ticker = item.get("ticker") if isinstance(item, dict) else item
        ticker = str(ticker or "").strip().upper()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return (tickers or WATCH_FALLBACK)[:limit]


def _score_from_frame(frame) -> float:
    try:
        score = trend_score(frame)
        return float(score) if score is not None else 50.0
    except Exception:
        return 50.0


def _priority_tag(score: float, change: float | None) -> tuple[str, str]:
    change = float(change or 0)
    if score >= 70 and change >= 0:
        return "BUY", "buy"
    if score >= 58:
        return "HOLD", "hold"
    if score <= 35:
        return "RISK", "risk"
    if abs(change) >= 4:
        return "MOVE", "move"
    return "WATCH", "watch"


def _top_quote(label: str, ticker: str, data: dict, frame=None) -> str:
    change = data.get("change_pct")
    css = "up" if (change or 0) >= 0 else "down"
    spark = _sparkline_svg(frame, (change or 0) >= 0).replace("priority-spark", "top-spark")
    return (
        '<div class="top-quote">'
        f'<span>{escape(label)}</span><b>{_fmt_price(label, data.get("price"))}</b>'
        f'<em class="{css}">{pct(change)}</em>{spark}</div>'
    )


def _sparkline_svg(frame, positive: bool) -> str:
    try:
        closes = frame["Close"].dropna().tail(28).astype(float).tolist()
    except Exception:
        closes = []
    if len(closes) < 2:
        return '<svg class="priority-spark" viewBox="0 0 120 34" aria-hidden="true"><path d="M2 18 L118 18"/></svg>'
    low, high = min(closes), max(closes)
    span = (high - low) or 1.0
    points = []
    for idx, value in enumerate(closes):
        x = 2 + idx * 116 / (len(closes) - 1)
        y = 31 - ((value - low) / span) * 27
        points.append(f"{x:.1f},{y:.1f}")
    css = "spark-up" if positive else "spark-down"
    return f'<svg class="priority-spark {css}" viewBox="0 0 120 34" aria-hidden="true"><polyline points="{" ".join(points)}"/></svg>'


def _priority_card(ticker: str, score: float, data: dict, frame=None) -> str:
    change = data.get("change_pct")
    positive = (change or 0) >= 0
    css = "up" if positive else "down"
    tag, tag_css = _priority_tag(score, change)
    sparkline = _sparkline_svg(frame, positive)
    return f"""
    <div class="priority-card">
      <div class="priority-left">
        <div class="priority-top"><b>{escape(ticker)}</b><span class="priority-score">{score:.0f}</span></div>
        <div class="priority-price">{money(data.get('price'))}</div>
        <div class="priority-change {css}">{pct(change)}</div>
      </div>
      <div class="priority-right">
        {sparkline}
        <div class="priority-tag {tag_css}">{tag}</div>
      </div>
    </div>
    """


def _group_panel(title: str, subtitle: str, items: dict[str, str], quotes: dict[str, dict]) -> str:
    rows = []
    for label, ticker in items.items():
        data = quotes.get(ticker, {})
        change = data.get("change_pct")
        css = "up" if (change or 0) >= 0 else "down"
        rows.append(
            '<div class="market-row">'
            f'<span>{escape(label)}</span>'
            f'<b>{_fmt_price(label, data.get("price"))}</b>'
            f'<em class="{css}">{pct(change)}</em>'
            '</div>'
        )
    return f"""
    <div class="market-group-panel">
      <div class="market-group-head"><span>{escape(subtitle)}</span><h3>{escape(title)}</h3></div>
      {''.join(rows)}
    </div>
    """


def render() -> None:
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    watch_tickers = _watchlist_tickers(12)

    all_tickers = tuple(dict.fromkeys(
        list(TOP_MARKET.values()) + list(FUTURES.values()) + list(MACRO.values()) + list(KOREA.values()) + watch_tickers
    ))
    quote_map = batch_quotes(all_tickers)

    # Korean indexes and equities are fetched independently. Yahoo's multi-symbol
    # daily response can refresh those symbols unevenly, which previously produced
    # mismatched prices and daily percentages in this panel.
    for korea_ticker in KOREA.values():
        korea_quote = direct_daily_quote(korea_ticker)
        if korea_quote.get("price") is not None:
            quote_map[korea_ticker] = korea_quote

    histories = batch_history(tuple(watch_tickers + ["SPY", "QQQ"] + list(TOP_MARKET.values())), period="6mo", interval="1d")
    market_score = round((_score_from_frame(histories.get("SPY")) + _score_from_frame(histories.get("QQQ"))) / 2, 1)

    vix = quote_map.get("^VIX", {})
    ten = quote_map.get("^TNX", {})
    dxy = quote_map.get("DX-Y.NYB", {})
    fear = max(0, min(100, round(100 - (vix.get("price") or 20) * 2.2 + 25)))
    state = "RISK ON" if market_score >= 65 and (vix.get("price") or 20) < 22 else "DEFENSIVE" if market_score < 42 or (vix.get("price") or 20) >= 28 else "SELECTIVE"
    state_tone = "positive" if state == "RISK ON" else "negative" if state == "DEFENSIVE" else "neutral"

    greeting = "Morning" if now.hour < 12 else "Afternoon" if now.hour < 18 else "Evening"
    top_quotes = "".join(_top_quote(label, ticker, quote_map.get(ticker, {}), histories.get(ticker)) for label, ticker in TOP_MARKET.items())
    fear_html = (
        '<div class="top-quote">'
        '<span>Fear & Greed</span>'
        f'<b>{fear}</b><em class="{"up" if fear >= 50 else "down"}">{"Greed" if fear >= 60 else "Neutral" if fear >= 40 else "Fear"}</em>'
        '</div>'
    )

    st.markdown(
        f"""
        <style>
        .command-hero{{padding:17px 18px!important;margin-bottom:14px!important}}
        .command-hero .hero-row{{align-items:center!important}}
        .command-hero .hero-copy{{min-width:245px}}
        .command-hero .hero-title{{font-size:26px!important;margin-top:1px!important}}
        .command-hero .hero-sub{{font-size:11px!important;margin-top:3px!important}}
        .command-top-strip{{display:grid;grid-template-columns:repeat(7,minmax(105px,1fr));gap:8px;flex:1}}
        .top-quote{{padding:10px 11px 8px;border-radius:11px;background:rgba(5,15,27,.68);border:1px solid rgba(111,143,178,.20);min-width:0;min-height:82px}}
        .top-quote span{{display:block;font-size:9px;color:#7890a8;text-transform:uppercase;letter-spacing:.08em;white-space:nowrap}}
        .top-quote b{{display:block;font-size:16px;margin-top:3px;white-space:nowrap}}
        .top-quote em{{display:block;font-style:normal;font-size:10px;margin-top:1px;font-weight:850}}
        .top-spark{{width:100%;height:18px;margin-top:4px;overflow:visible}}.top-spark polyline,.top-spark path{{fill:none;stroke:#7c8ea2;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.9}}.top-spark.spark-up polyline{{stroke:#35d6a5}}.top-spark.spark-down polyline{{stroke:#ff6474}}
        .priority-grid-note{{font-size:9px;color:#70869c;margin-top:-5px;margin-bottom:8px}}
        .priority-card{{min-height:88px;padding:12px 13px;border-radius:13px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid rgba(148,163,184,.14);display:grid;grid-template-columns:minmax(0,1fr) 126px;gap:12px;align-items:center}}
        .priority-left{{min-width:0}}.priority-right{{display:flex;flex-direction:column;align-items:flex-end;justify-content:space-between;min-height:62px}}
        .priority-top{{display:flex;align-items:center;justify-content:space-between;gap:8px}}.priority-top b{{font-size:14px;letter-spacing:.01em}}.priority-score{{font-size:9px;padding:3px 7px;border-radius:999px;color:#9cb2c8;border:1px solid rgba(148,163,184,.18)}}
        .priority-price{{font-size:20px;font-weight:850;line-height:1.15;margin-top:5px;white-space:nowrap}}.priority-change{{font-size:11px;font-weight:850;margin-top:3px}}
        .priority-spark{{width:120px;height:34px;overflow:visible}}.priority-spark polyline,.priority-spark path{{fill:none;stroke:#7c8ea2;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.92}}.priority-spark.spark-up polyline{{stroke:#35d6a5}}.priority-spark.spark-down polyline{{stroke:#ff6474}}
        .priority-tag{{display:inline-block;font-size:9px;font-weight:900;letter-spacing:.09em;padding:3px 9px;border-radius:999px;background:rgba(100,166,255,.09);color:#64a6ff}}
        .priority-tag.buy{{color:#35d6a5;background:rgba(53,214,165,.09)}}.priority-tag.risk{{color:#ff6474;background:rgba(255,100,116,.09)}}.priority-tag.move{{color:#f3c969;background:rgba(243,201,105,.09)}}
        .market-group-panel{{border-radius:15px;padding:18px 18px;background:linear-gradient(180deg,rgba(13,29,48,.98),rgba(8,20,34,.98));border:1px solid rgba(148,163,184,.14)}}
        .market-group-head span{{font-size:10px;letter-spacing:.14em;color:#6f89a5;font-weight:900}}.market-group-head h3{{font-size:20px!important;margin:3px 0 10px!important}}
        .market-row{{display:grid;grid-template-columns:1.15fr .9fr .65fr;gap:7px;align-items:center;padding:9px 0;border-top:1px solid rgba(148,163,184,.08);font-size:13px}}
        .market-row span{{color:#b8c8d8;font-size:13px}}.market-row b{{text-align:right;font-size:14px;white-space:nowrap}}.market-row em{{text-align:right;font-style:normal;font-size:12px;font-weight:850}}
        .compact-brief{{margin-top:12px;padding:12px 14px!important;min-height:auto!important}}.compact-brief .ai-brief-copy{{font-size:11px!important;line-height:1.55!important}}
        @media(max-width:1200px){{.command-top-strip{{grid-template-columns:repeat(4,minmax(90px,1fr))}}}}
        @media(max-width:900px){{.command-top-strip{{grid-template-columns:repeat(2,minmax(0,1fr));margin-top:12px}}.command-hero .hero-row{{display:block!important}}}}
        </style>
        <div class="hero terminal-hero command-hero">
          <div class="hero-row">
            <div class="hero-copy">
              <div class="hero-title">Good {greeting}, Sungje</div>
              <div class="hero-sub">{now.strftime('%A, %B %d · %I:%M %p')} Pacific Time</div>
              <div class="market-regime {state_tone}"><span></span>{state}</div>
            </div>
            <div class="command-top-strip">{top_quotes}{fear_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    watch_items = []
    for ticker in watch_tickers:
        score = _score_from_frame(histories.get(ticker))
        data = quote_map.get(ticker, {})
        watch_items.append((ticker, score, data))
    watch_items.sort(key=lambda item: (item[1], abs(float(item[2].get("change_pct") or 0))), reverse=True)

    st.markdown('<div class="section-heading"><div><span>PERSONAL RADAR</span><h3>Today’s Priority</h3></div><em>Top 12 from My Watchlist</em></div>', unsafe_allow_html=True)
    st.markdown('<div class="priority-grid-note">Compact view · score, price, daily move and current signal</div>', unsafe_allow_html=True)
    for row_start in range(0, len(watch_items), 4):
        cols = st.columns(4)
        for col, (ticker, score, data) in zip(cols, watch_items[row_start:row_start + 4]):
            with col:
                st.markdown(_priority_card(ticker, score, data, histories.get(ticker)), unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><div><span>GLOBAL PULSE</span><h3>Futures · Macro · Korea</h3></div><em>One-screen market context</em></div>', unsafe_allow_html=True)
    groups = [("US Futures", "OVERNIGHT DIRECTION", FUTURES), ("Macro & Commodities", "RATES · FX · COMMODITIES", MACRO), ("Korea Market", "KOSPI · KOSDAQ · LEADERS", KOREA)]
    for col, (title, subtitle, items) in zip(st.columns(3), groups):
        with col:
            st.markdown(_group_panel(title, subtitle, items, quote_map), unsafe_allow_html=True)

    brief = market_brief(market_score, vix.get("price"), ten.get("price"), dxy.get("price"))
    st.markdown(
        f"""
        <div class="ai-brief-panel compact-brief">
          <div class="ai-brief-head"><span>AI DECISION CONTEXT</span><b>{market_score:.0f}/100</b></div>
          <div class="ai-brief-copy">{escape(str(brief))}</div>
          <div class="brief-tags"><span>Bias · {badge(market_score)}</span><span>Horizon · 1–3 Days</span><span>Regime · {state}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
