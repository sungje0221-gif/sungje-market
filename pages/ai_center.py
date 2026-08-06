from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from engine.analysis import analyze
from engine.indicators import rsi_series, trend_score
from engine.market_data import batch_history, batch_quotes, history, quote
from utils.formatters import money, pct
from utils.watchlist_store import load_watchlist_data

FALLBACK = ["QQQM", "SMH", "GOOGL", "SKHY", "KORU", "JPM", "HOOD", "RKLB"]


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


def _detail(ticker: str) -> None:
    h = history(ticker, "1y", "1d")
    q = quote(ticker)
    a = analyze(h)
    cols = st.columns(5)
    cols[0].metric("Price", money(q.get("price")), pct(q.get("change_pct")))
    cols[1].metric("Score", f'{a.get("score", 0):.0f}/100')
    cols[2].metric("Rating", stars(a.get("score", 0)))
    cols[3].metric("Action", a.get("action", "—"))
    cols[4].metric("Risk", a.get("risk", "—"))
    if not h.empty and "Close" in h:
        st.line_chart(h["Close"].tail(180), height=260)
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
