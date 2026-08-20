from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from engine.schwab import SchwabError, access_token, connection_status

SCHWAB_MARKETDATA_BASE_URL = "https://api.schwabapi.com/marketdata/v1"


# Korean market data is intentionally isolated from Yahoo Finance.
# Naver Finance's domestic realtime endpoint is used because it is deployable
# from Streamlit Cloud and exposes the exchange-local price/change timestamp.
NAVER_REALTIME_BASE_URL = "https://polling.finance.naver.com/api/realtime/domestic"
NAVER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; InvestmentOS/3.16)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://finance.naver.com/",
}


def _empty_quote(source: str = "Unavailable") -> dict[str, Any]:
    return {
        "price": None, "change_pct": None, "change_abs": None, "day_low": None, "day_high": None, "volume": None,
        "bid": None, "ask": None, "last": None, "mark": None,
        "source": source, "as_of": None,
    }


def _number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text in {"-", "--", "—"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_mapping(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        for key in ("datas", "data", "result"):
            value = payload.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
            if isinstance(value, dict):
                return value
        return payload
    return {}


def _naver_quote(kind: str, code: str) -> dict[str, Any]:
    source = "Naver Finance"
    try:
        response = requests.get(
            f"{NAVER_REALTIME_BASE_URL}/{kind}/{code}",
            headers=NAVER_HEADERS,
            timeout=12,
        )
        response.raise_for_status()
        item = _first_mapping(response.json())
        price = _number(
            item.get("closePrice")
            or item.get("currentPrice")
            or item.get("nowVal")
            or item.get("lastPrice")
        )
        change_pct = _number(
            item.get("fluctuationsRatio")
            or item.get("changeRate")
            or item.get("rate")
        )
        volume = _number(item.get("accumulatedTradingVolume") or item.get("volume"))
        as_of = (
            item.get("localTradedAt")
            or item.get("tradeDateTime")
            or item.get("updatedAt")
            or item.get("date")
        )
        if price is None:
            return _empty_quote(f"{source} unavailable")
        return {
            "price": price, "change_pct": change_pct, "volume": volume,
            "bid": None, "ask": None, "last": price, "mark": price,
            "source": source, "as_of": str(as_of) if as_of else None,
        }
    except (requests.RequestException, ValueError, TypeError):
        return _empty_quote(f"{source} unavailable")


@st.cache_data(ttl=60, show_spinner=False)
def korea_quotes_naver() -> dict[str, dict[str, Any]]:
    """Return Naver Finance quotes for KOSPI/KOSDAQ/Samsung/SK hynix.

    The function fails closed. It never falls back to Yahoo Finance, so a
    blocked/invalid response is shown as unavailable rather than stale data.
    """
    return {
        "KOSPI": _naver_quote("index", "KOSPI"),
        "KOSDAQ": _naver_quote("index", "KOSDAQ"),
        "005930": _naver_quote("stock", "005930"),
        "000660": _naver_quote("stock", "000660"),
    }


def _normalize_download(data: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    return data.dropna(how="all")


@st.cache_data(ttl=30, show_spinner=False)
def intraday_history(ticker: str, period: str = "1d", interval: str = "1m") -> pd.DataFrame:
    """Short-cache intraday OHLCV for detailed charts.

    Yahoo supports 1-minute data only for recent sessions, so this function is
    deliberately separate from the longer-lived daily-history cache.
    """
    allowed = {
        "1d": {"1m", "2m", "5m", "15m", "30m", "60m"},
        "5d": {"1m", "2m", "5m", "15m", "30m", "60m"},
        "1mo": {"5m", "15m", "30m", "60m"},
        "3mo": {"60m"},
    }
    if interval not in allowed.get(period, set()):
        return pd.DataFrame()
    try:
        data = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            prepost=False,
            threads=False,
        )
        return _normalize_download(data)
    except Exception:
        return pd.DataFrame()


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

        change_abs = quote_data.get("netChange")
        if change_abs is None and price is not None and previous_close is not None:
            change_abs = float(price) - float(previous_close)
        return {
            "price": float(price) if price is not None else None,
            "change_pct": float(net_pct) if net_pct is not None else None,
            "change_abs": float(change_abs) if change_abs is not None else None,
            "day_low": quote_data.get("lowPrice"),
            "day_high": quote_data.get("highPrice"),
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
    day_low = float(data["Low"].dropna().iloc[-1]) if "Low" in data and not data["Low"].dropna().empty else None
    day_high = float(data["High"].dropna().iloc[-1]) if "High" in data and not data["High"].dropna().empty else None
    return {
        "price": price,
        "change_pct": ((price / previous) - 1) * 100 if previous else 0,
        "change_abs": price - previous,
        "day_low": day_low,
        "day_high": day_high,
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
        "price": None, "change_pct": None, "change_abs": None, "day_low": None, "day_high": None, "volume": None,
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
                    low_series = data["Low"][ticker].dropna() if "Low" in data.columns.get_level_values(0) else pd.Series(dtype=float)
                    high_series = data["High"][ticker].dropna() if "High" in data.columns.get_level_values(0) else pd.Series(dtype=float)
                    volume_series = data["Volume"][ticker].dropna() if "Volume" in data.columns.get_level_values(0) else pd.Series(dtype=float)
                else:
                    close = data["Close"].dropna()
                    low_series = data["Low"].dropna() if "Low" in data else pd.Series(dtype=float)
                    high_series = data["High"].dropna() if "High" in data else pd.Series(dtype=float)
                    volume_series = data["Volume"].dropna() if "Volume" in data else pd.Series(dtype=float)
                if close.empty:
                    continue
                price = float(close.iloc[-1])
                previous = float(close.iloc[-2]) if len(close) > 1 else price
                volume = float(volume_series.iloc[-1]) if not volume_series.empty else None
                results[ticker] = {
                    "price": price,
                    "change_pct": ((price / previous) - 1) * 100 if previous else 0.0,
                    "change_abs": price - previous,
                    "day_low": float(low_series.iloc[-1]) if not low_series.empty else None,
                    "day_high": float(high_series.iloc[-1]) if not high_series.empty else None,
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
        "price": None, "change_pct": None, "change_abs": None, "day_low": None, "day_high": None, "volume": None,
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
