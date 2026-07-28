from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from engine.schwab import SchwabError, access_token, connection_status

SCHWAB_MARKETDATA_BASE_URL = "https://api.schwabapi.com/marketdata/v1"


def _normalize_download(data: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(how="all")


@st.cache_data(ttl=300, show_spinner=False)
def history(ticker: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        return _normalize_download(data)
    except Exception:
        return pd.DataFrame()


def _schwab_quote(ticker: str) -> dict[str, Any] | None:
    if not connection_status().get("connected"):
        return None
    try:
        response = requests.get(
            f"{SCHWAB_MARKETDATA_BASE_URL}/quotes",
            params={"symbols": ticker, "fields": "quote,reference"},
            headers={
                "Authorization": f"Bearer {access_token()}",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if not response.ok:
            return None
        payload = response.json()
        item = payload.get(ticker) or payload.get(ticker.upper())
        if not isinstance(item, dict):
            return None

        quote_data = item.get("quote", {}) or {}
        reference = item.get("reference", {}) or {}
        price = (
            quote_data.get("lastPrice")
            or quote_data.get("mark")
            or quote_data.get("closePrice")
        )
        previous_close = (
            quote_data.get("closePrice")
            or reference.get("previousClose")
        )
        net_pct = quote_data.get("netPercentChange")
        if net_pct is None and price is not None and previous_close:
            net_pct = (float(price) / float(previous_close) - 1) * 100

        return {
            "price": float(price) if price is not None else None,
            "change_pct": float(net_pct) if net_pct is not None else None,
            "volume": quote_data.get("totalVolume"),
            "bid": quote_data.get("bidPrice"),
            "ask": quote_data.get("askPrice"),
            "last": quote_data.get("lastPrice"),
            "mark": quote_data.get("mark"),
            "source": "Schwab",
        }
    except (requests.RequestException, SchwabError, ValueError, TypeError):
        return None


@st.cache_data(ttl=30, show_spinner=False)
def quote(ticker: str) -> dict[str, Any]:
    schwab = _schwab_quote(ticker)
    if schwab and schwab.get("price") is not None:
        return schwab

    data = history(ticker, "5d", "1d")
    if data.empty or "Close" not in data:
        return {
            "price": None,
            "change_pct": None,
            "volume": None,
            "bid": None,
            "ask": None,
            "last": None,
            "mark": None,
            "source": "Unavailable",
        }

    close = data["Close"].dropna()
    if close.empty:
        return {
            "price": None,
            "change_pct": None,
            "volume": None,
            "bid": None,
            "ask": None,
            "last": None,
            "mark": None,
            "source": "Unavailable",
        }

    price = float(close.iloc[-1])
    previous = float(close.iloc[-2]) if len(close) > 1 else price
    volume = (
        float(data["Volume"].dropna().iloc[-1])
        if "Volume" in data and not data["Volume"].dropna().empty
        else None
    )
    return {
        "price": price,
        "change_pct": ((price / previous) - 1) * 100 if previous else 0,
        "volume": volume,
        "bid": None,
        "ask": None,
        "last": price,
        "mark": price,
        "source": "Yahoo Finance",
    }


@st.cache_data(ttl=900, show_spinner=False)
def info(ticker: str):
    try:
        return dict(yf.Ticker(ticker).fast_info)
    except Exception:
        return {}

@st.cache_data(ttl=60, show_spinner=False)
def batch_quotes(tickers: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Fetch many Yahoo quotes in one request.

    Used by dashboard/heatmap views to avoid one network round-trip per symbol.
    Individual detail pages can still call ``quote`` so Schwab remains available.
    """
    symbols = tuple(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    if not symbols:
        return {}

    empty = {
        "price": None, "change_pct": None, "volume": None,
        "bid": None, "ask": None, "last": None, "mark": None,
        "source": "Unavailable",
    }
    results = {ticker: dict(empty) for ticker in symbols}
    try:
        data = yf.download(
            list(symbols), period="5d", interval="1d", auto_adjust=False,
            progress=False, threads=True, group_by="column",
        )
        if data is None or data.empty:
            return results

        for ticker in symbols:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    close = data["Close"][ticker].dropna()
                    volume_series = data["Volume"][ticker].dropna() if "Volume" in data.columns.get_level_values(0) else pd.Series(dtype=float)
                else:
                    close = data["Close"].dropna()
                    volume_series = data["Volume"].dropna() if "Volume" in data else pd.Series(dtype=float)
                if close.empty:
                    continue
                price = float(close.iloc[-1])
                previous = float(close.iloc[-2]) if len(close) > 1 else price
                volume = float(volume_series.iloc[-1]) if not volume_series.empty else None
                results[ticker] = {
                    "price": price,
                    "change_pct": ((price / previous) - 1) * 100 if previous else 0.0,
                    "volume": volume,
                    "bid": None, "ask": None, "last": price, "mark": price,
                    "source": "Yahoo Finance batch",
                }
            except (KeyError, TypeError, ValueError, IndexError):
                continue
    except Exception:
        return results
    return results

@st.cache_data(ttl=300, show_spinner=False)
def batch_history(tickers: tuple[str, ...], period: str = "1y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Download price history for many symbols in one Yahoo request."""
    symbols = tuple(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    out = {ticker: pd.DataFrame() for ticker in symbols}
    if not symbols:
        return out
    try:
        data = yf.download(
            list(symbols), period=period, interval=interval, auto_adjust=False,
            progress=False, threads=True, group_by="column",
        )
        if data is None or data.empty:
            return out
        if len(symbols) == 1:
            out[symbols[0]] = _normalize_download(data.copy())
            return out
        if not isinstance(data.columns, pd.MultiIndex):
            return out
        ticker_level = 1 if set(symbols).intersection(set(map(str, data.columns.get_level_values(1)))) else 0
        for ticker in symbols:
            try:
                frame = data.xs(ticker, axis=1, level=ticker_level, drop_level=True).dropna(how="all")
                out[ticker] = frame
            except Exception:
                continue
    except Exception:
        pass
    return out


@st.cache_data(ttl=60, show_spinner=False)
def direct_daily_quote(ticker: str) -> dict[str, Any]:
    """Fetch one symbol independently and calculate change from adjacent daily closes.

    This is deliberately separate from the batch downloader for markets whose
    Yahoo multi-symbol response can occasionally map or refresh unevenly.
    """
    empty = {
        "price": None, "change_pct": None, "volume": None,
        "bid": None, "ask": None, "last": None, "mark": None,
        "source": "Unavailable",
    }
    try:
        frame = yf.Ticker(ticker).history(
            period="10d", interval="1d", auto_adjust=False, actions=False
        )
        if frame is None or frame.empty or "Close" not in frame:
            return dict(empty)
        close = frame["Close"].dropna()
        if close.empty:
            return dict(empty)
        price = float(close.iloc[-1])
        previous = float(close.iloc[-2]) if len(close) > 1 else price
        volume = None
        if "Volume" in frame and not frame["Volume"].dropna().empty:
            volume = float(frame["Volume"].dropna().iloc[-1])
        return {
            "price": price,
            "change_pct": ((price / previous) - 1) * 100 if previous else 0.0,
            "volume": volume,
            "bid": None, "ask": None, "last": price, "mark": price,
            "source": "Yahoo Finance individual daily",
        }
    except Exception:
        return dict(empty)
