from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf


def _first(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def ticker_info(ticker: str) -> dict[str, Any]:
    t = yf.Ticker(ticker)
    result: dict[str, Any] = {}

    try:
        result.update(t.info or {})
    except Exception:
        pass

    try:
        fast = dict(t.fast_info)
    except Exception:
        fast = {}

    result["marketCap"] = _first(result.get("marketCap"), fast.get("market_cap"))
    result["fiftyTwoWeekHigh"] = _first(result.get("fiftyTwoWeekHigh"), fast.get("year_high"))
    result["fiftyTwoWeekLow"] = _first(result.get("fiftyTwoWeekLow"), fast.get("year_low"))
    result["previousClose"] = _first(result.get("previousClose"), fast.get("previous_close"))
    result["regularMarketPrice"] = _first(result.get("regularMarketPrice"), fast.get("last_price"))

    # Derive trailing P/E when Yahoo gives EPS but omits the ratio.
    if result.get("trailingPE") is None:
        price = result.get("regularMarketPrice")
        eps = result.get("trailingEps")
        try:
            if price is not None and eps not in (None, 0):
                result["trailingPE"] = float(price) / float(eps)
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    # Derive forward P/E when forward EPS is present.
    if result.get("forwardPE") is None:
        price = result.get("regularMarketPrice")
        eps = result.get("forwardEps")
        try:
            if price is not None and eps not in (None, 0):
                result["forwardPE"] = float(price) / float(eps)
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    return result


@st.cache_data(ttl=3600, show_spinner=False)
def earnings_calendar(ticker: str) -> dict[str, Any]:
    try:
        calendar = yf.Ticker(ticker).calendar
        return calendar if isinstance(calendar, dict) else {}
    except Exception:
        return {}


def next_earnings_date(ticker: str):
    calendar = earnings_calendar(ticker)
    value = calendar.get("Earnings Date")
    if isinstance(value, list) and value:
        value = value[0]
    if value is None:
        return None
    try:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts
    except Exception:
        return None


def days_to_earnings(ticker: str):
    ts = next_earnings_date(ticker)
    if ts is None:
        return None
    now = pd.Timestamp.now(tz="UTC")
    return int((ts.normalize() - now.normalize()).days)


def fundamental_score(info: dict[str, Any]) -> dict[str, float | str]:
    score = 50.0

    forward_pe = info.get("forwardPE")
    revenue_growth = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")
    operating_margin = info.get("operatingMargins")
    roe = info.get("returnOnEquity")
    debt_equity = info.get("debtToEquity")
    recommendation = info.get("recommendationMean")

    try:
        if forward_pe is not None:
            pe = float(forward_pe)
            score += 8 if 0 < pe <= 22 else 3 if pe <= 35 else -5
    except (TypeError, ValueError):
        pass

    for value, positive_points in [
        (revenue_growth, 10),
        (earnings_growth, 10),
        (operating_margin, 8),
        (roe, 8),
    ]:
        try:
            if value is not None:
                numeric = float(value)
                score += positive_points if numeric >= 0.15 else positive_points / 2 if numeric > 0 else -positive_points / 2
        except (TypeError, ValueError):
            pass

    try:
        if debt_equity is not None:
            de = float(debt_equity)
            score += 5 if de < 75 else 0 if de < 150 else -6
    except (TypeError, ValueError):
        pass

    try:
        if recommendation is not None:
            rec = float(recommendation)
            score += 6 if rec <= 2 else 2 if rec <= 3 else -4
    except (TypeError, ValueError):
        pass

    score = max(0.0, min(100.0, score))
    label = "STRONG" if score >= 75 else "GOOD" if score >= 60 else "NEUTRAL" if score >= 45 else "WEAK"
    return {"score": score, "label": label}
