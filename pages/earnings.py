from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

from components.charts import advanced_chart
from components.colored_tables import style_signed_columns
from engine.fundamentals import earnings_history, next_earnings_date, ticker_info
from engine.market_data import history, intraday_history, quote
from utils.formatters import money
from utils.watchlist_store import load_watchlist_data

DEFAULT = ["GOOGL", "META", "AMZN", "MSFT", "AAPL", "NVDA", "AVGO", "TSLA"]

# Same range/candle options as the Heatmap detail chart, so every chart in
# the app behaves the same way.
CHART_RANGES = {"1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
CANDLES_BY_RANGE = {
    "1D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "5D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "1M": ["5m", "15m", "30m", "60m", "1d"],
    "3M": ["60m", "1d"],
    "6M": ["1d"],
    "1Y": ["1d"],
    "5Y": ["1d"],
}
DEFAULT_CANDLE = {"1D": "1m", "5D": "5m", "1M": "60m", "3M": "1d", "6M": "1d", "1Y": "1d", "5Y": "1d"}


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
    st.markdown(f"## {ticker} · Earnings Detail")

    cols = st.columns(6)
    cols[0].metric("Price", money(q.get("price")), None if q.get("change_pct") is None else f'{q["change_pct"]:+.2f}%')
    cols[1].metric("Forward EPS", "—" if info.get("forwardEps") is None else f'${float(info.get("forwardEps")):.2f}')
    cols[2].metric("Trailing EPS", "—" if info.get("trailingEps") is None else f'${float(info.get("trailingEps")):.2f}')
    cols[3].metric("Revenue Growth", "—" if info.get("revenueGrowth") is None else f'{float(info.get("revenueGrowth"))*100:.1f}%')
    cols[4].metric("Earnings Growth", "—" if info.get("earningsGrowth") is None else f'{float(info.get("earningsGrowth"))*100:.1f}%')
    cols[5].metric("Forward P/E", "—" if info.get("forwardPE") is None else f'{float(info.get("forwardPE")):.1f}')

    st.markdown("#### Analyst Targets")
    tcols = st.columns(5)
    tcols[0].metric("Target Mean", money(info.get("targetMeanPrice")))
    tcols[1].metric("Target High", money(info.get("targetHighPrice")))
    tcols[2].metric("Target Low", money(info.get("targetLowPrice")))
    n_analysts = info.get("numberOfAnalystOpinions")
    tcols[3].metric("Analysts", "—" if n_analysts is None else int(n_analysts))
    rec = info.get("recommendationKey")
    tcols[4].metric("Consensus", (rec or "—").upper().replace("_", " "))
    upside = None
    price, target = q.get("price"), info.get("targetMeanPrice")
    if price and target:
        upside = (float(target) / float(price) - 1) * 100
    if upside is not None:
        st.caption(f"현재가 대비 목표주가 괴리: {upside:+.1f}%")

    st.markdown("#### Past Earnings — Estimate vs. Actual")
    hist = earnings_history(ticker)
    if not hist.empty:
        st.dataframe(
            style_signed_columns(hist, ["Surprise %"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "EPS Estimate": st.column_config.NumberColumn(format="$%.2f"),
                "Reported EPS": st.column_config.NumberColumn(format="$%.2f"),
                "Surprise %": st.column_config.NumberColumn(format="%+.1f%%"),
            },
        )
        beats = int((hist["Surprise %"] > 0).sum())
        st.caption(f"최근 {len(hist)}분기 중 {beats}번 예상치 상회 (Surprise % 양수)")
    else:
        st.caption("과거 실적 서프라이즈 데이터를 가져오지 못했습니다.")

    st.markdown("#### Price Chart")
    range_col, candle_col = st.columns([2, 1])
    with range_col:
        range_label = st.radio("기간", list(CHART_RANGES), horizontal=True, index=5, key=f"earn_range_{ticker}")
    candle_options = CANDLES_BY_RANGE[range_label]
    with candle_col:
        interval = st.selectbox(
            "봉", candle_options, index=candle_options.index(DEFAULT_CANDLE[range_label]),
            key=f"earn_candle_{ticker}_{range_label}",
        )
    period = CHART_RANGES[range_label]
    is_intraday = interval.endswith("m") or interval.endswith("h")
    chart_data = intraday_history(ticker, period, interval) if is_intraday else history(ticker, period, interval)

    if not chart_data.empty:
        st.plotly_chart(
            advanced_chart(
                chart_data, ticker,
                show_ma20=True, show_ma50=not is_intraday, show_ma100=False,
                show_ma200=not is_intraday, show_bollinger=False, show_volume=True,
                show_rsi=not is_intraday, show_macd=False, intraday=is_intraday,
            ),
            use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False},
        )
        returns = chart_data["Close"].pct_change().dropna() * 100
        if not returns.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Typical Daily Move", f'{returns.abs().median():.2f}%')
            c2.metric("90th % Move", f'{returns.abs().quantile(.90):.2f}%')
            c3.metric("Worst Day", f'{returns.min():.2f}%')
    else:
        st.warning(f"{ticker}의 {range_label} / {interval} 데이터가 없습니다. 다른 봉을 선택하세요.")

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
