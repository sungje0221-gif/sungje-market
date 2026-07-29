from __future__ import annotations

from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

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


@st.cache_data(ttl=20, show_spinner=False)
def quote(ticker: str) -> dict[str, Any]:
    """Return a live single-symbol quote using the provider previous close."""
    schwab = _schwab_quote(ticker)
    if schwab and schwab.get("price") is not None:
        return schwab

    try:
        fast = yf.Ticker(ticker).fast_info
        price = _number(fast.get("last_price"))
        previous = _number(fast.get("previous_close"))
        if price is None:
            return _empty_quote("Yahoo unavailable")
        return {
            "price": price,
            "previous_close": previous,
            "change_pct": (price / previous - 1) * 100 if previous else None,
            "change_abs": price - previous if previous is not None else None,
            "day_low": _number(fast.get("day_low")),
            "day_high": _number(fast.get("day_high")),
            "volume": _number(fast.get("last_volume") or fast.get("three_month_average_volume")),
            "bid": None, "ask": None, "last": price, "mark": price,
            "market_cap": _number(fast.get("market_cap")),
            "source": "Yahoo live",
            "as_of": None,
        }
    except Exception:
        return _empty_quote("Yahoo unavailable")


@st.cache_data(ttl=900, show_spinner=False)
def info(ticker: str):
    try:
        return dict(yf.Ticker(ticker).fast_info)
    except Exception:
        return {}

@st.cache_data(ttl=20, show_spinner=False)
def batch_quotes(tickers: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Return live quotes using authoritative previous-close fields.

    Schwab is preferred when connected. Remaining symbols fall back to
    ``yfinance.Ticker.fast_info``. Unlike the old implementation, this function
    never derives today's percentage from adjacent daily-history rows, because
    Yahoo daily downloads can omit or unevenly refresh the latest session.
    """
    symbols = tuple(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    if not symbols:
        return {}

    results = {ticker: _empty_quote() for ticker in symbols}

    # One Schwab request for the whole heatmap universe.
    if connection_status().get("connected"):
        try:
            response = requests.get(
                f"{SCHWAB_MARKETDATA_BASE_URL}/quotes",
                params={"symbols": ",".join(symbols), "fields": "quote,reference"},
                headers={
                    "Authorization": f"Bearer {access_token()}",
                    "Accept": "application/json",
                },
                timeout=20,
            )
            if response.ok:
                payload = response.json()
                for ticker in symbols:
                    item = payload.get(ticker) or payload.get(ticker.upper())
                    if not isinstance(item, dict):
                        continue
                    quote_data = item.get("quote", {}) or {}
                    reference = item.get("reference", {}) or {}
                    price = _number(quote_data.get("lastPrice") or quote_data.get("mark"))
                    previous_close = _number(reference.get("previousClose") or quote_data.get("closePrice"))
                    change_pct = _number(quote_data.get("netPercentChange"))
                    if change_pct is None and price is not None and previous_close:
                        change_pct = (price / previous_close - 1) * 100
                    if price is None:
                        continue
                    results[ticker] = {
                        "price": price,
                        "previous_close": previous_close,
                        "change_pct": change_pct,
                        "change_abs": _number(quote_data.get("netChange"))
                            if quote_data.get("netChange") is not None
                            else (price - previous_close if previous_close is not None else None),
                        "day_low": _number(quote_data.get("lowPrice")),
                        "day_high": _number(quote_data.get("highPrice")),
                        "volume": _number(quote_data.get("totalVolume")),
                        "bid": _number(quote_data.get("bidPrice")),
                        "ask": _number(quote_data.get("askPrice")),
                        "last": _number(quote_data.get("lastPrice")),
                        "mark": _number(quote_data.get("mark")),
                        "market_cap": None,
                        "source": "Schwab live",
                        "as_of": quote_data.get("quoteTime") or quote_data.get("tradeTime"),
                    }
        except (requests.RequestException, SchwabError, ValueError, TypeError):
            pass

    missing = [ticker for ticker in symbols if results[ticker].get("price") is None]

    def yahoo_fast_quote(ticker: str) -> tuple[str, dict[str, Any]]:
        try:
            fast = yf.Ticker(ticker).fast_info
            price = _number(fast.get("last_price"))
            previous_close = _number(fast.get("previous_close"))
            if price is None:
                return ticker, _empty_quote("Yahoo unavailable")
            change_pct = (price / previous_close - 1) * 100 if previous_close else None
            return ticker, {
                "price": price,
                "previous_close": previous_close,
                "change_pct": change_pct,
                "change_abs": price - previous_close if previous_close is not None else None,
                "day_low": _number(fast.get("day_low")),
                "day_high": _number(fast.get("day_high")),
                "volume": _number(fast.get("last_volume") or fast.get("three_month_average_volume")),
                "bid": None, "ask": None, "last": price, "mark": price,
                "market_cap": _number(fast.get("market_cap")),
                "source": "Yahoo live",
                "as_of": None,
            }
        except Exception:
            return ticker, _empty_quote("Yahoo unavailable")

    if missing:
        with ThreadPoolExecutor(max_workers=min(8, len(missing))) as executor:
            futures = [executor.submit(yahoo_fast_quote, ticker) for ticker in missing]
            for future in as_completed(futures):
                ticker, result = future.result()
                results[ticker] = result

    # Schwab does not supply market cap in the quote payload. Fill it only for
    # sizing; failure simply falls back to equal-size tiles.
    schwab_symbols = [ticker for ticker in symbols if results[ticker].get("price") is not None and results[ticker].get("market_cap") is None]
    def market_cap_only(ticker: str) -> tuple[str, float | None]:
        try:
            return ticker, _number(yf.Ticker(ticker).fast_info.get("market_cap"))
        except Exception:
            return ticker, None
    if schwab_symbols:
        with ThreadPoolExecutor(max_workers=min(8, len(schwab_symbols))) as executor:
            futures = [executor.submit(market_cap_only, ticker) for ticker in schwab_symbols]
            for future in as_completed(futures):
                ticker, market_cap = future.result()
                results[ticker]["market_cap"] = market_cap

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
