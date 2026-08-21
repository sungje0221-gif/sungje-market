from __future__ import annotations

import math
from typing import Any

import pandas as pd
import streamlit as st

from components.tables import colored_change_table
from engine.indicators import trend_score
from engine.market_data import history, quote

FUTURES = {
    "S&P 500": "ES=F",
    "Nasdaq 100": "NQ=F",
    "Dow": "YM=F",
    "Russell 2000": "RTY=F",
    "VIX": "^VIX",
}

MACRO = {
    "US Dollar": "DX-Y.NYB",
    "US 10Y": "^TNX",
    "Gold": "GC=F",
    "Silver": "SI=F",
    "WTI Oil": "CL=F",
}

KOREA = {
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "USD/KRW": "KRW=X",
    "EWY": "EWY",
    "KORU": "KORU",
    "SKHY": "SKHY",
}

OTHER_GROUPS = {
    "US Cash Indices": {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Dow Jones": "^DJI",
        "Russell 2000": "^RUT",
    },
    "Global Markets": {
        "Nikkei": "^N225",
        "Hang Seng": "^HSI",
        "Euro Stoxx 50": "^STOXX50E",
    },
}


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
        return None if math.isnan(number) else number
    except (TypeError, ValueError):
        return None


def _fetch_group(items: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, ticker in items.items():
        q = quote(ticker)
        rows.append(
            {
                "label": label,
                "ticker": ticker,
                "price": _safe_float(q.get("price")),
                "change": _safe_float(q.get("change_pct")),
                "source": q.get("source", "Unavailable"),
            }
        )
    return rows


def _fmt_price(label: str, price: float | None) -> str:
    if price is None:
        return "—"
    if label == "US 10Y":
        return f"{price:.3f}%"
    if label == "USD/KRW":
        return f"₩{price:,.2f}"
    if label in {"S&P 500", "Nasdaq 100", "Dow", "Russell 2000", "VIX", "KOSPI", "KOSDAQ"}:
        return f"{price:,.2f}"
    return f"${price:,.2f}"


def _change_class(change: float | None) -> str:
    if change is None or abs(change) < 0.005:
        return "flat"
    return "up" if change > 0 else "down"


def _card_html(row: dict[str, Any], note: str = "") -> str:
    change = row["change"]
    css = _change_class(change)
    arrow = "▲" if change is not None and change > 0 else "▼" if change is not None and change < 0 else "•"
    delta = "—" if change is None else f"{arrow} {change:+.2f}%"
    return f"""
    <div class="future-card {css}">
      <div class="future-label">{row['label']}</div>
      <div class="future-price">{_fmt_price(row['label'], row['price'])}</div>
      <div class="future-change">{delta}</div>
      <div class="future-note">{note or row['ticker']}</div>
    </div>
    """


def _market_pulse(rows: list[dict[str, Any]]) -> tuple[str, str, str]:
    values = {row["label"]: row["change"] for row in rows}
    equity_labels = ["S&P 500", "Nasdaq 100", "Dow", "Russell 2000"]
    equity_changes = [values.get(label) for label in equity_labels if values.get(label) is not None]
    equity_avg = sum(equity_changes) / len(equity_changes) if equity_changes else 0.0
    vix = values.get("VIX") or 0.0

    score = equity_avg - (vix * 0.12)
    if score >= 0.45:
        regime, css = "RISK-ON", "positive"
    elif score <= -0.45:
        regime, css = "RISK-OFF", "negative"
    else:
        regime, css = "MIXED", "neutral"

    nasdaq = values.get("Nasdaq 100")
    sp = values.get("S&P 500")
    pieces = []
    if nasdaq is not None:
        pieces.append(f"Nasdaq {nasdaq:+.2f}%")
    if sp is not None:
        pieces.append(f"S&P {sp:+.2f}%")
    if values.get("VIX") is not None:
        pieces.append(f"VIX {values['VIX']:+.2f}%")
    summary = " · ".join(pieces) if pieces else "Market data is temporarily unavailable."
    return regime, css, summary


def _section_cards(title: str, subtitle: str, rows: list[dict[str, Any]], notes: dict[str, str] | None = None) -> None:
    st.markdown(
        f'<div class="market-section"><span>{subtitle}</span><h3>{title}</h3></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(len(rows))
    notes = notes or {}
    for col, row in zip(cols, rows):
        with col:
            st.markdown(_card_html(row, notes.get(row["label"], "")), unsafe_allow_html=True)


def render() -> None:
    st.markdown(
        """
        <style>
        .market-hero{padding:20px 22px;border-radius:18px;margin-bottom:16px;background:
          radial-gradient(circle at 88% 0%,rgba(79,140,255,.18),transparent 35%),
          linear-gradient(135deg,rgba(15,32,53,.98),rgba(7,18,31,.98));border:1px solid rgba(96,165,250,.18)}
        .market-hero-top{display:flex;justify-content:space-between;gap:20px;align-items:center}
        .market-hero-kicker,.market-section span{font-size:9px;letter-spacing:.17em;color:#718aa4;font-weight:900}
        .market-hero h1{font-size:30px;margin:3px 0 4px}.market-hero p{font-size:12px;color:#91a5bb;margin:0}
        .pulse-pill{white-space:nowrap;padding:9px 12px;border-radius:999px;font-size:10px;font-weight:900;letter-spacing:.12em;border:1px solid currentColor}
        .pulse-pill.positive{color:#4da3ff;background:rgba(77,163,255,.08)}
        .pulse-pill.negative{color:#ff6474;background:rgba(255,100,116,.08)}
        .pulse-pill.neutral{color:#f3c969;background:rgba(243,201,105,.08)}
        .pulse-summary{margin-top:12px;padding-top:12px;border-top:1px solid rgba(148,163,184,.12);font-size:12px;color:#b7c5d5}
        .market-section{margin:24px 0 10px}.market-section h3{font-size:21px;margin:2px 0 0!important}
        .future-card{min-height:125px;padding:15px;border-radius:15px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid rgba(148,163,184,.14);border-top:2px solid #8fa2b8}
        .future-card.up{border-top-color:#4da3ff}.future-card.down{border-top-color:#ff6474}
        .future-label{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#7f94aa;font-weight:800}
        .future-price{font-size:22px;font-weight:900;margin-top:9px;letter-spacing:-.035em;font-variant-numeric:tabular-nums}
        .future-change{font-size:12px;font-weight:900;margin-top:3px;color:#a9b4c4}
        .future-card.up .future-change{color:#4da3ff}.future-card.down .future-change{color:#ff6474}
        .future-note{font-size:9px;color:#64798f;margin-top:9px}
        @media(max-width:900px){.market-hero-top{display:block}.pulse-pill{display:inline-block;margin-top:14px}.future-card{min-height:auto}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    futures = _fetch_group(FUTURES)
    regime, pulse_css, pulse_summary = _market_pulse(futures)

    st.markdown(
        f"""
        <div class="market-hero">
          <div class="market-hero-top">
            <div>
              <div class="market-hero-kicker">PRE-MARKET COMMAND VIEW</div>
              <h1>Futures & Market Pulse</h1>
              <p>US index futures, volatility, macro and Korea in one morning screen.</p>
            </div>
            <div class="pulse-pill {pulse_css}">{regime}</div>
          </div>
          <div class="pulse-summary">{pulse_summary}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _section_cards(
        "US Futures",
        "OVERNIGHT DIRECTION",
        futures,
        {"VIX": "Volatility index · rising VIX means more risk"},
    )

    macro = _fetch_group(MACRO)
    _section_cards(
        "Macro",
        "RATES · FX · COMMODITIES",
        macro,
        {
            "US 10Y": "Higher yields can pressure growth stocks",
            "US Dollar": "Dollar Index",
            "WTI Oil": "Front-month futures",
        },
    )

    korea = _fetch_group(KOREA)
    _section_cards(
        "Korea",
        "KOSPI · FX · US-LISTED PROXIES",
        korea,
        {
            "EWY": "iShares MSCI South Korea ETF",
            "KORU": "3× daily South Korea bull ETF",
            "SKHY": "US-listed SK hynix reference",
        },
    )

    with st.expander("More market detail"):
        for title, items in OTHER_GROUPS.items():
            st.markdown(f"### {title}")
            rows = []
            for label, ticker in items.items():
                q = quote(ticker)
                rows.append(
                    {
                        "Asset": label,
                        "Ticker": ticker,
                        "Price": q.get("price"),
                        "Change %": q.get("change_pct"),
                        "Trend Score": trend_score(history(ticker, "6mo")),
                    }
                )
            colored_change_table(
                pd.DataFrame(rows),
                price_col="Price",
                change_col="Change %",
                score_col="Trend Score",
            )

    st.caption("Futures and market quotes are provided by Yahoo Finance and may be delayed. Use the sidebar refresh button to clear cached data.")
