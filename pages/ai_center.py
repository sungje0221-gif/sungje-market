from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.indicators import rsi_series, trend_score
from engine.market_data import batch_history, batch_quotes, history, intraday_history, quote
from utils.formatters import money, pct
from utils.watchlist_store import load_watchlist_data

FALLBACK = ["QQQM", "SMH", "GOOGL", "SKHY", "KORU", "JPM", "HOOD", "RKLB"]

# Same range/candle options as Heatmap and Earnings, so every chart in the
# app behaves the same way.
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


def _watchlist(limit: int = 40) -> list[str]:
    records = load_watchlist_data(FALLBACK)
    out: list[str] = []
    for item in records:
        ticker = str(item.get("ticker") or "").strip().upper()
        if ticker and ticker not in out:
            out.append(ticker)
    return (out or FALLBACK)[:limit]


def _signal_from_frame(ticker: str, frame: pd.DataFrame, q: dict) -> dict:
    if frame.empty or "Close" not in frame:
        return {"Ticker": ticker, "Price": q.get("price"), "Daily %": q.get("change_pct"), "Signal": "WAIT", "Score": 50, "RSI": None, "Reason": "가격 데이터 부족"}
    close = frame["Close"].dropna().astype(float)
    score = float(trend_score(frame) or 50)
    rsi = float(rsi_series(close).dropna().iloc[-1]) if len(close) >= 20 else None
    price = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else price
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else price
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else price
    if score >= 68 and price >= ma20 >= ma50 and (rsi is None or rsi < 72):
        signal, reason = "BUY", "상승 추세 유지 · 눌림목 분할 접근 후보"
    elif score >= 55 and price >= ma50:
        signal, reason = "HOLD", "추세 유효 · 신규 추격보다 보유 우선"
    elif score < 38 or price < ma200:
        signal, reason = "SELL", "중장기 추세 훼손 · 비중 축소 검토"
    elif rsi is not None and rsi >= 72:
        signal, reason = "TRIM", "단기 과열 · 일부 차익실현 검토"
    else:
        signal, reason = "WAIT", "방향 확인 필요 · 지지선까지 대기"
    return {"Ticker": ticker, "Price": q.get("price") or price, "Daily %": q.get("change_pct"), "Signal": signal, "Score": round(score), "RSI": round(rsi, 1) if rsi is not None else None, "Reason": reason}


@st.cache_data(ttl=300, show_spinner=False)
def _radar(tickers: tuple[str, ...]) -> pd.DataFrame:
    quotes = batch_quotes(tickers)
    histories = batch_history(tickers, "1y", "1d")
    rows = [_signal_from_frame(t, histories.get(t, pd.DataFrame()), quotes.get(t, {})) for t in tickers]
    rank = {"BUY": 0, "TRIM": 1, "SELL": 2, "HOLD": 3, "WAIT": 4}
    return pd.DataFrame(rows).assign(_rank=lambda x: x["Signal"].map(rank)).sort_values(["_rank", "Score"], ascending=[True, False]).drop(columns="_rank")


def _signed(value: float | None) -> str:
    value = float(value or 0)
    color = "#45a3ff" if value >= 0 else "#ff5b6e"
    return f'<span style="color:{color};font-weight:850">{value:+.2f}%</span>'


def _narrative(ticker: str, a: dict) -> list[str]:
    """Turn analyze()'s raw numbers into readable sentences, per ticker.

    Every clause is conditional on the actual computed values, so two
    different tickers with different RSI/MACD/trend readings get genuinely
    different text instead of a fixed template.
    """
    if a.get("score") is None:
        return [f"{ticker}의 가격 데이터가 부족해 분석할 수 없습니다."]
    lines = []
    score, action, risk = a["score"], a["action"], a["risk"]
    lines.append(f"현재 규칙 기반 점수는 {score:.0f}/100으로 **{action}** 구간이며, 변동성 기준 리스크는 **{risk}**입니다.")

    ma20, ma50 = a.get("above_ma20"), a.get("above_ma50")
    if ma20 is not None and ma50 is not None:
        if ma20 and ma50:
            lines.append("20일선과 50일선을 모두 상회하고 있어 단기·중기 추세가 함께 살아있는 상태입니다.")
        elif ma20 and not ma50:
            lines.append("20일선은 회복했지만 50일선 아래에 있어, 중기 추세 전환을 아직 확신하기는 이릅니다.")
        elif not ma20 and ma50:
            lines.append("50일선 위에 있지만 20일선 아래로 눌려 있어, 단기 조정이 진행 중일 수 있습니다.")
        else:
            lines.append("20일선·50일선을 모두 하회하고 있어 추세가 꺾인 모습입니다.")

    rsi_val = a.get("rsi")
    if rsi_val is not None:
        if rsi_val >= 72:
            lines.append(f"RSI {rsi_val:.0f}로 단기 과매수 구간이라, 신규 진입보다는 눌림목을 기다리는 편이 낫습니다.")
        elif rsi_val <= 32:
            lines.append(f"RSI {rsi_val:.0f}로 단기 과매도 구간이라, 기술적 반등 가능성을 열어둘 만합니다.")
        else:
            lines.append(f"RSI {rsi_val:.0f}로 특별히 과열되거나 과매도된 구간은 아닙니다.")

    macd_val = a.get("macd")
    if macd_val is not None:
        lines.append("MACD 히스토그램이 양(+)으로, 단기 모멘텀이 매수 우위입니다." if macd_val > 0
                      else "MACD 히스토그램이 음(-)으로, 단기 모멘텀이 매도 우위입니다.")

    r20 = a.get("return_20d")
    if r20 is not None:
        lines.append(f"최근 20거래일 수익률은 {r20:+.1f}%입니다.")

    return lines


def _detail(ticker: str) -> None:
    q = quote(ticker)
    a = analyze(history(ticker, "1y", "1d"))

    cols = st.columns(5)
    cols[0].metric("Price", money(q.get("price")), pct(q.get("change_pct")))
    cols[1].metric("Score", f'{a.get("score", 0):.0f}/100')
    cols[2].metric("Rating", stars(a.get("score", 0)))
    cols[3].metric("Action", a.get("action", "—"))
    cols[4].metric("Risk", a.get("risk", "—"))

    st.markdown("#### Signal Breakdown")
    bcols = st.columns(5)
    bcols[0].metric("RSI (14)", "—" if a.get("rsi") is None else f'{a["rsi"]:.0f}')
    bcols[1].metric("MACD Hist.", "—" if a.get("macd") is None else f'{a["macd"]:+.2f}')
    bcols[2].metric("20D Return", "—" if a.get("return_20d") is None else f'{a["return_20d"]:+.1f}%')
    bcols[3].metric("Volatility", "—" if a.get("volatility") is None else f'{a["volatility"]:.0f}')
    ma_state = "—"
    if a.get("above_ma20") is not None and a.get("above_ma50") is not None:
        ma_state = f'{"20↑" if a["above_ma20"] else "20↓"} / {"50↑" if a["above_ma50"] else "50↓"}'
    bcols[4].metric("MA20/50", ma_state)

    st.markdown("#### Why")
    for line in _narrative(ticker, a):
        st.markdown(f"- {line}")

    st.markdown("#### Price Chart")
    range_col, candle_col = st.columns([2, 1])
    with range_col:
        range_label = st.radio("기간", list(CHART_RANGES), horizontal=True, index=5, key=f"ai_range_{ticker}")
    candle_options = CANDLES_BY_RANGE[range_label]
    with candle_col:
        interval = st.selectbox(
            "봉", candle_options, index=candle_options.index(DEFAULT_CANDLE[range_label]),
            key=f"ai_candle_{ticker}_{range_label}",
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
                show_rsi=not is_intraday, show_macd=not is_intraday, intraday=is_intraday,
            ),
            use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False},
        )
    else:
        st.warning(f"{ticker}의 {range_label} / {interval} 데이터가 없습니다. 다른 봉을 선택하세요.")

    st.markdown(f'<div class="panel"><b>{a.get("action", "WAIT")}</b><br>Support {money(a.get("support"))} · Resistance {money(a.get("resistance"))}</div>', unsafe_allow_html=True)


def render() -> None:
    st.title("AI Center")
    st.caption("실제 My Watchlist와 연동되며, 카드 클릭 시 상세 분석을 표시합니다.")
    radar_tab, analyze_tab, compare_tab = st.tabs(["Today’s Radar", "Analyze", "Compare"])

    with radar_tab:
        tickers = _watchlist()
        signals = _radar(tuple(tickers))
        selected = st.session_state.get("ai_selected_ticker")
        st.markdown("### Today’s Priority")
        top = signals.head(9)
        for start in range(0, len(top), 3):
            cols = st.columns(3)
            for col, (_, row) in zip(cols, top.iloc[start:start+3].iterrows()):
                with col:
                    st.markdown(f'<div class="compact-stock-card"><div><b>{row["Ticker"]}</b><span>{row["Signal"]}</span></div><strong>{money(row["Price"])}</strong><small>{_signed(row.get("Daily %"))} · Score {row["Score"]}</small><p>{row["Reason"]}</p></div>', unsafe_allow_html=True)
                    if st.button("Details", key=f'ai_detail_{row["Ticker"]}', use_container_width=True):
                        st.session_state["ai_selected_ticker"] = row["Ticker"]
                        selected = row["Ticker"]
        if selected:
            st.divider(); st.subheader(f"{selected} · Detail")
            _detail(selected)
        with st.expander("Full watchlist signal table"):
            styled = signals.style.map(lambda v: "color:#45a3ff;font-weight:800" if isinstance(v,(int,float)) and v>0 else "color:#ff5b6e;font-weight:800" if isinstance(v,(int,float)) and v<0 else "", subset=["Daily %"])
            st.dataframe(styled, use_container_width=True, hide_index=True, height=360)

    with analyze_tab:
        ticker = st.text_input("Ticker", "NVDA", key="ai_analyze_ticker").upper().strip()
        if ticker: _detail(ticker)

    with compare_tab:
        c1, c2 = st.columns(2)
        left = c1.text_input("Ticker A", "NVDA", key="compare_a").upper().strip()
        right = c2.text_input("Ticker B", "AMD", key="compare_b").upper().strip()
        if left and right:
            data = _radar((left, right))
            st.dataframe(data, use_container_width=True, hide_index=True)
