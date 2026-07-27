from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=3600, show_spinner=False)
def ticker_info(ticker: str) -> dict[str, Any]:
    try:
        return yf.Ticker(ticker).info or {}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def earnings_calendar(ticker: str) -> dict[str, Any]:
    try:
        calendar = yf.Ticker(ticker).calendar
        if isinstance(calendar, dict):
            return calendar
        return {}
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
