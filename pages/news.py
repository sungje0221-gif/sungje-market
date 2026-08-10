from __future__ import annotations

import requests
import streamlit as st
import yfinance as yf

from utils.watchlist_store import load_watchlist_data

DEFAULT = ["GOOGL", "META", "AMZN", "MSFT", "AVGO", "CEG"]
YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
HEADERS = {"User-Agent": "Mozilla/5.0 InvestmentOS/2.05"}


def _normalize_yf_item(item):
    content = item.get("content", item) if isinstance(item, dict) else {}
    provider = content.get("provider", {})
    canonical = content.get("canonicalUrl", {})
    clickthrough = content.get("clickThroughUrl", {})
    return {
        "title": content.get("title") or "Untitled",
        "provider": provider.get("displayName", "Unknown") if isinstance(provider, dict) else str(provider or "Unknown"),
        "summary": content.get("summary") or content.get("description") or "",
        "url": (canonical.get("url") if isinstance(canonical, dict) else canonical)
               or (clickthrough.get("url") if isinstance(clickthrough, dict) else clickthrough)
               or content.get("link"),
        "published": content.get("pubDate") or content.get("providerPublishTime"),
    }


@st.cache_data(ttl=900, show_spinner=False)
def news(ticker):
    errors = []
    try:
        response = requests.get(
            YAHOO_SEARCH_URL,
            params={"q": ticker, "quotesCount": 1, "newsCount": 20, "enableFuzzyQuery": "false"},
            headers=HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        items = response.json().get("news", [])
        normalized = []
        for item in items:
            normalized.append({
                "title": item.get("title") or "Untitled",
                "provider": item.get("publisher") or "Unknown",
                "summary": item.get("summary") or "",
                "url": item.get("link"),
                "published": item.get("providerPublishTime"),
            })
        if normalized:
            return normalized, "Yahoo Finance Search", None
    except Exception as exc:
        errors.append(str(exc))

    try:
        items = yf.Ticker(ticker).news or []
        normalized = [_normalize_yf_item(item) for item in items]
        normalized = [item for item in normalized if item.get("title")]
        if normalized:
            return normalized, "yfinance", None
    except Exception as exc:
        errors.append(str(exc))

    return [], "Unavailable", "; ".join(errors[-2:])


@st.cache_data(ttl=900, show_spinner=False)
def news_ko(ticker):
    """Same as news(), but title/summary translated to Korean when possible."""
    items, source, error = news(ticker)
    if not items:
        return items, source, error
    try:
        from engine.claude_advisor import configured, ask
        if not configured():
            return items, source, error
        import json
        subset = items[:15]
        payload = [{"i": i, "title": it["title"], "summary": (it.get("summary") or "")[:400]} for i, it in enumerate(subset)]
        system = (
            "너는 금융 뉴스 번역기다. 입력된 JSON 배열의 각 항목에서 title과 summary를 "
            "자연스러운 한국어로 번역해라. 고유명사(회사명, 티커)는 그대로 두거나 병기해도 된다. "
            "다른 설명 없이, 입력과 정확히 같은 구조의 JSON 배열만 출력해라."
        )
        user = json.dumps(payload, ensure_ascii=False)
        raw = ask(system, user, max_tokens=2500)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        translated = json.loads(cleaned)
        by_index = {t.get("i"): t for t in translated if isinstance(t, dict)}
        for i, it in enumerate(subset):
            t = by_index.get(i)
            if t:
                it["title"] = t.get("title") or it["title"]
                if it.get("summary"):
                    it["summary"] = t.get("summary") or it["summary"]
        return items, source, error
    except Exception:
        # Any translation failure just falls back to the original English feed.
        return items, source, error


def render():
    st.title("News & AI Briefing")
    records = load_watchlist_data(DEFAULT)
    tickers = [item.get("ticker") for item in records if item.get("ticker")]
    if not tickers:
        st.info("No watchlist tickers available.")
        return

    ticker = st.selectbox("Ticker", tickers)
    items, source, error = news(ticker)
    st.caption(f"Source: {source} · cached for 15 minutes")
    if not items:
        st.warning("No news could be retrieved right now. Yahoo may be rate-limiting the request; try Refresh in a few minutes.")
        if error:
            with st.expander("Technical details"):
                st.code(error)
        return

    for item in items[:15]:
        st.markdown(f"#### {item['title']}")
        st.caption(item.get("provider") or "Unknown")
        if item.get("summary"):
            st.write(item["summary"][:700])
        if item.get("url"):
            st.link_button("Open article", item["url"])
        st.divider()
