from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from components.cards import badge
from engine.analysis import market_brief
from engine.indicators import trend_score
from engine.market_data import batch_history, batch_quotes
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
    "USD/KRW": "KRW=X",
    "EWY": "EWY",
    "KORU": "KORU",
    "SKHY": "SKHY",
}


def _fmt_price(label: str, price: float | None) -> str:
    if price is None:
        return "—"
    if label == "US 10Y":
        return f"{price:.2f}%"
    if label == "USD/KRW":
        return f"₩{price:,.2f}"
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


def _top_quote(label: str, ticker: str, data: dict) -> str:
    change = data.get("change_pct")
    css = "up" if (change or 0) >= 0 else "down"
    return (
        '<div class="top-quote">'
        f'<span>{escape(label)}</span><b>{_fmt_price(label, data.get("price"))}</b>'
        f'<em class="{css}">{pct(change)}</em></div>'
    )


def _priority_card(ticker: str, score: float, data: dict) -> str:
    change = data.get("change_pct")
    css = "up" if (change or 0) >= 0 else "down"
    tag, tag_css = _priority_tag(score, change)
    return f"""
    <div class="priority-card">
      <div class="priority-top"><b>{escape(ticker)}</b><span class="priority-score">{score:.0f}</span></div>
      <div class="priority-middle"><strong>{money(data.get('price'))}</strong><em class="{css}">{pct(change)}</em></div>
      <div class="priority-tag {tag_css}">{tag}</div>
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

    histories = batch_history(tuple(watch_tickers + ["SPY", "QQQ"]), period="6mo", interval="1d")
    market_score = round((_score_from_frame(histories.get("SPY")) + _score_from_frame(histories.get("QQQ"))) / 2, 1)

    vix = quote_map.get("^VIX", {})
    ten = quote_map.get("^TNX", {})
    dxy = quote_map.get("DX-Y.NYB", {})
    fear = max(0, min(100, round(100 - (vix.get("price") or 20) * 2.2 + 25)))
    state = "RISK ON" if market_score >= 65 and (vix.get("price") or 20) < 22 else "DEFENSIVE" if market_score < 42 or (vix.get("price") or 20) >= 28 else "SELECTIVE"
    state_tone = "positive" if state == "RISK ON" else "negative" if state == "DEFENSIVE" else "neutral"

    greeting = "Morning" if now.hour < 12 else "Afternoon" if now.hour < 18 else "Evening"
    top_quotes = "".join(_top_quote(label, ticker, quote_map.get(ticker, {})) for label, ticker in TOP_MARKET.items())
    fear_html = (
        '<div class="top-quote">'
        '<span>Fear & Greed</span>'
        f'<b>{fear}</b><em class="{"up" if fear >= 50 else "down"}">{"Greed" if fear >= 60 else "Neutral" if fear >= 40 else "Fear"}</em>'
        '</div>'
    )

    st.markdown(
        f"""
        <style>
        .command-hero{{padding:15px 18px!important;margin-bottom:14px!important}}
        .command-hero .hero-row{{align-items:center!important}}
        .command-hero .hero-copy{{min-width:265px}}
        .command-hero .hero-title{{font-size:26px!important;margin-top:1px!important}}
        .command-hero .hero-sub{{font-size:11px!important;margin-top:3px!important}}
        .command-top-strip{{display:grid;grid-template-columns:repeat(7,minmax(82px,1fr));gap:6px;flex:1}}
        .top-quote{{padding:8px 9px;border-radius:10px;background:rgba(5,15,27,.58);border:1px solid rgba(111,143,178,.17);min-width:0}}
        .top-quote span{{display:block;font-size:8px;color:#7890a8;text-transform:uppercase;letter-spacing:.08em;white-space:nowrap}}
        .top-quote b{{display:block;font-size:13px;margin-top:2px;white-space:nowrap}}
        .top-quote em{{display:block;font-style:normal;font-size:9px;margin-top:1px}}
        .priority-grid-note{{font-size:9px;color:#70869c;margin-top:-5px;margin-bottom:8px}}
        .priority-card{{min-height:76px;padding:10px 11px;border-radius:13px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid rgba(148,163,184,.14)}}
        .priority-top,.priority-middle{{display:flex;align-items:center;justify-content:space-between;gap:8px}}
        .priority-top b{{font-size:12px}}.priority-score{{font-size:8px;padding:3px 6px;border-radius:999px;color:#9cb2c8;border:1px solid rgba(148,163,184,.15)}}
        .priority-middle{{margin-top:7px}}.priority-middle strong{{font-size:15px}}.priority-middle em{{font-size:10px;font-style:normal;font-weight:800}}
        .priority-tag{{display:inline-block;margin-top:7px;font-size:8px;font-weight:900;letter-spacing:.09em;padding:2px 6px;border-radius:999px;background:rgba(100,166,255,.09);color:#64a6ff}}
        .priority-tag.buy{{color:#35d6a5;background:rgba(53,214,165,.09)}}.priority-tag.risk{{color:#ff6474;background:rgba(255,100,116,.09)}}.priority-tag.move{{color:#f3c969;background:rgba(243,201,105,.09)}}
        .market-group-panel{{border-radius:15px;padding:13px 14px;background:linear-gradient(180deg,rgba(13,29,48,.98),rgba(8,20,34,.98));border:1px solid rgba(148,163,184,.14)}}
        .market-group-head span{{font-size:8px;letter-spacing:.14em;color:#6f89a5;font-weight:900}}.market-group-head h3{{font-size:17px!important;margin:1px 0 7px!important}}
        .market-row{{display:grid;grid-template-columns:1.15fr .9fr .65fr;gap:7px;align-items:center;padding:6px 0;border-top:1px solid rgba(148,163,184,.08);font-size:10px}}
        .market-row span{{color:#a9bacb}}.market-row b{{text-align:right;font-size:11px;white-space:nowrap}}.market-row em{{text-align:right;font-style:normal;font-size:9px;font-weight:850}}
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
                st.markdown(_priority_card(ticker, score, data), unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><div><span>GLOBAL PULSE</span><h3>Futures · Macro · Korea</h3></div><em>One-screen market context</em></div>', unsafe_allow_html=True)
    groups = [("US Futures", "OVERNIGHT DIRECTION", FUTURES), ("Macro", "RATES · FX · COMMODITIES", MACRO), ("Korea", "KOSPI · FX · US PROXIES", KOREA)]
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
