from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

from engine.fundamentals import next_earnings_date, ticker_info
from engine.market_data import history, quote
from utils.formatters import money
from utils.watchlist_store import load_watchlist_data

DEFAULT = ["GOOGL", "META", "AMZN", "MSFT", "AAPL", "NVDA", "AVGO", "TSLA"]


@st.cache_data(ttl=21600, show_spinner=False)
def _earnings_rows(tickers: tuple[str, ...]) -> list[dict]:
    now = pd.Timestamp.now(tz="UTC")
    rows: list[dict] = []
    def one(ticker: str) -> dict:
        ts = next_earnings_date(ticker)
        if ts is None:
            return {"Ticker": ticker, "Date": "—", "D-Day": None}
        return {"Ticker": ticker, "Date": ts.strftime("%Y-%m-%d"), "D-Day": int((ts.normalize() - now.normalize()).days)}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(tickers)))) as pool:
        futures = {pool.submit(one, t): t for t in tickers}
        for future in as_completed(futures):
            try: rows.append(future.result())
            except Exception: rows.append({"Ticker": futures[future], "Date": "—", "D-Day": None})
    return rows


def _detail(ticker: str) -> None:
    q = quote(ticker)
    info = ticker_info(ticker)
    h = history(ticker, "5y", "1d")
    st.markdown(f"## {ticker} · Earnings Detail")
    cols = st.columns(6)
    cols[0].metric("Price", money(q.get("price")), None if q.get("change_pct") is None else f'{q["change_pct"]:+.2f}%')
    cols[1].metric("Forward EPS", "—" if info.get("forwardEps") is None else f'${float(info.get("forwardEps")):.2f}')
    cols[2].metric("Revenue Growth", "—" if info.get("revenueGrowth") is None else f'{float(info.get("revenueGrowth"))*100:.1f}%')
    cols[3].metric("Earnings Growth", "—" if info.get("earningsGrowth") is None else f'{float(info.get("earningsGrowth"))*100:.1f}%')
    cols[4].metric("Target Mean", money(info.get("targetMeanPrice")))
    cols[5].metric("Forward P/E", "—" if info.get("forwardPE") is None else f'{float(info.get("forwardPE")):.1f}')
    if not h.empty and "Close" in h:
        st.line_chart(h["Close"].tail(260), height=280)
        returns = h["Close"].pct_change().dropna() * 100
        c1, c2, c3 = st.columns(3)
        c1.metric("Typical Daily Move", f'{returns.abs().median():.2f}%')
        c2.metric("90th % Move", f'{returns.abs().quantile(.90):.2f}%')
        c3.metric("Worst Day", f'{returns.min():.2f}%')
    st.info("Yahoo의 실적일·추정치는 변경될 수 있으므로 거래 전 회사 IR 또는 브로커 일정에서 최종 확인하세요.")


def render() -> None:
    st.title("Earnings Radar")
    records = load_watchlist_data(DEFAULT)
    tickers = tuple(item.get("ticker") for item in records if item.get("ticker"))
    with st.spinner("Loading cached earnings calendar..."):
        rows = _earnings_rows(tickers)
    df = pd.DataFrame(rows).sort_values("D-Day", na_position="last")
    st.caption(f"My Watchlist {len(tickers)}개 종목 기준 · 날짜 목록은 6시간 캐시됩니다.")

    upcoming = df[df["D-Day"].notna() & (df["D-Day"] >= 0)]
    if not upcoming.empty:
        st.markdown("### Upcoming")
        for start in range(0, min(len(upcoming), 12), 4):
            cols = st.columns(4)
            for col, (_, row) in zip(cols, upcoming.iloc[start:start+4].iterrows()):
                with col:
                    dd = int(row["D-Day"])
                    st.markdown(f'<div class="compact-stock-card earnings-card"><div><b>{row["Ticker"]}</b><span>D{dd:+d}</span></div><strong>{row["Date"]}</strong><p>{"Today" if dd==0 else "Upcoming earnings"}</p></div>', unsafe_allow_html=True)
                    if st.button("Details", key=f'earn_{row["Ticker"]}', use_container_width=True):
                        st.session_state["earn_selected"] = row["Ticker"]
    with st.expander("All watchlist earnings dates"):
        st.dataframe(df, use_container_width=True, hide_index=True, height=380)

    selected = st.session_state.get("earn_selected")
    if selected:
        st.divider(); _detail(selected)
