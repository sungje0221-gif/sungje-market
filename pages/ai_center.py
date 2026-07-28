from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from engine.analysis import analyze
from engine.indicators import rsi_series, trend_score
from engine.market_data import batch_quotes, history, quote
from utils.formatters import money, pct
from utils.storage import load_json

FALLBACK = ["QQQM", "SMH", "GOOGL", "SKHY", "KORU", "JPM", "HOOD", "RKLB"]


def _watchlist(limit: int = 20) -> list[str]:
    raw = load_json("watchlist.json", [])
    out: list[str] = []
    for item in raw:
        ticker = item.get("ticker") if isinstance(item, dict) else item
        ticker = str(ticker or "").strip().upper()
        if ticker and ticker not in out:
            out.append(ticker)
    return (out or FALLBACK)[:limit]


def _signal(ticker: str, q: dict | None = None) -> dict:
    frame = history(ticker, "1y", "1d")
    q = q or quote(ticker)
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
    rows = [_signal(t, quotes.get(t, {})) for t in tickers]
    rank = {"BUY": 0, "TRIM": 1, "SELL": 2, "HOLD": 3, "WAIT": 4}
    return pd.DataFrame(rows).assign(_rank=lambda x: x["Signal"].map(rank)).sort_values(["_rank", "Score"], ascending=[True, False]).drop(columns="_rank")


def _signed(value: float | None) -> str:
    value = float(value or 0)
    css = "delta-up" if value >= 0 else "delta-down"
    return f'<span class="{css}">{value:+.2f}%</span>'


def render() -> None:
    st.markdown('<div class="page-kicker">INTELLIGENCE · ONE WORKSPACE</div>', unsafe_allow_html=True)
    st.title("AI Center")
    st.caption("Watchlist 우선순위, 개별 종목 분석, 비교를 한 화면에 모았습니다.")

    radar_tab, analyze_tab, compare_tab = st.tabs(["Today’s Radar", "Analyze", "Compare"])

    with radar_tab:
        tickers = _watchlist()
        signals = _radar(tuple(tickers))
        st.markdown("### Today’s Priority")
        top = signals.head(6)
        for start in range(0, len(top), 3):
            cols = st.columns(3)
            for col, (_, row) in zip(cols, top.iloc[start:start+3].iterrows()):
                tone = {"BUY": "buy", "HOLD": "hold", "TRIM": "watch", "SELL": "avoid", "WAIT": "watch"}.get(row["Signal"], "watch")
                with col:
                    st.markdown(
                        f'''<div class="action-card {tone}"><div class="action-top"><div class="action-label">{row['Signal']}</div><span>{row['Score']}/100</span></div>
                        <div style="font-size:20px;font-weight:900;margin-top:8px">{row['Ticker']} · {money(row['Price'])}</div>
                        <div class="action-copy">{row['Reason']}<br>{_signed(row.get('Daily %'))}</div></div>''',
                        unsafe_allow_html=True,
                    )
        with st.expander("Full watchlist signal table"):
            st.dataframe(signals, use_container_width=True, hide_index=True)

    with analyze_tab:
        ticker = st.text_input("Ticker", "NVDA", key="ai_analyze_ticker").upper().strip()
        if ticker:
            h = history(ticker, "1y")
            q = quote(ticker)
            a = analyze(h)
            cols = st.columns(5)
            cols[0].metric("Price", money(q.get("price")), pct(q.get("change_pct")))
            cols[1].metric("Score", f'{a["score"]:.0f}/100')
            cols[2].metric("Rating", stars(a["score"]))
            cols[3].metric("Action", a["action"])
            cols[4].metric("Risk", a["risk"])
            st.markdown(
                f'''<div class="panel"><div class="klabel">AI DECISION</div><div style="font-size:26px;font-weight:850;margin:9px 0">{a['action']}</div>
                <div style="line-height:1.8">Support {money(a['support'])} · Resistance {money(a['resistance'])} · Volatility {('—' if a['volatility'] is None else format(a['volatility'], '.1f') + '%')}.</div></div>''',
                unsafe_allow_html=True,
            )
            if not h.empty and "Close" in h:
                st.line_chart(h["Close"].tail(180), height=300)

    with compare_tab:
        c1, c2 = st.columns(2)
        left = c1.text_input("Ticker A", "NVDA", key="compare_a").upper().strip()
        right = c2.text_input("Ticker B", "AMD", key="compare_b").upper().strip()
        if left and right:
            rows = [_signal(left), _signal(right)]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
