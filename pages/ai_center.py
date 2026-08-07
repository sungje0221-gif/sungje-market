from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.indicators import rsi_series, trend_score
from engine.market_data import batch_history, batch_quotes, history, intraday_history, quote
from utils.formatters import money, pct
from utils.watchlist_store import load_watchlist_data, load_watchlist, save_watchlist
from pages.heatmap import GROUPS as _DISCOVERY_GROUPS
from pages.news import news as fetch_news

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

    st.markdown("#### Related News")
    items, source, error = fetch_news(ticker)
    st.caption(f"Source: {source} · cached for 15 minutes")
    if not items:
        st.caption("지금은 관련 뉴스를 가져오지 못했습니다.")
        if error:
            with st.expander("Technical details"):
                st.code(error)
    else:
        for item in items[:6]:
            st.markdown(f"**{item['title']}**")
            st.caption(item.get("provider") or "Unknown")
            if item.get("summary"):
                st.write(item["summary"][:400])
            if item.get("url"):
                st.link_button("Open article", item["url"], key=f"news_link_{ticker}_{item['title'][:40]}")
            st.divider()

    st.markdown("#### AI Commentary")
    from engine.claude_advisor import configured, ask
    if not configured():
        st.info("Anthropic API 키가 설정되지 않아 AI 코멘터리를 쓸 수 없습니다.")
    else:
        if st.button("AI 코멘터리 생성", key=f"ai_comment_btn_{ticker}"):
            headlines = "\n".join(f"- {item['title']}" for item in items[:5]) if items else "관련 뉴스 없음"
            narrative_text = "\n".join(_narrative(ticker, a))
            system = (
                "너는 개인 투자 대시보드에 내장된 한국어 종목 분석 어시스턴트다. "
                "제공된 규칙 기반 지표와 최근 뉴스 헤드라인만 근거로 삼아, 왜 이런 신호가 나왔는지, "
                "지금 이 종목에서 조심할 점은 뭔지 3~5문장으로 설명해라. 확정적 매수/매도 지시는 피하고, "
                "뉴스 헤드라인만 있고 본문은 없으니 과도하게 단정하지 마라."
            )
            user = (
                f"종목: {ticker}\n점수: {a.get('score')}/100, 액션: {a.get('action')}, 리스크: {a.get('risk')}\n"
                f"지표 요약:\n{narrative_text}\n\n최근 뉴스 헤드라인:\n{headlines}\n\n코멘터리를 작성해줘."
            )
            with st.spinner("AI 코멘터리 생성 중..."):
                st.session_state[f"ai_comment_{ticker}"] = ask(system, user, max_tokens=900)
        if st.session_state.get(f"ai_comment_{ticker}"):
            with st.container(border=True):
                st.markdown(st.session_state[f"ai_comment_{ticker}"])


@st.cache_data(ttl=300, show_spinner=False)
def _discover(watchlist_tickers: tuple[str, ...], limit: int = 6) -> pd.DataFrame:
    """Strong-signal tickers from a broad universe, excluding ones already watched."""
    universe = []
    seen = set(watchlist_tickers)
    for group in _DISCOVERY_GROUPS.values():
        for t in group:
            if t not in seen:
                seen.add(t)
                universe.append(t)
    if not universe:
        return pd.DataFrame()
    scanned = _radar(tuple(universe))
    strong = scanned[scanned["Signal"].isin(["BUY"])].sort_values("Score", ascending=False)
    return strong.head(limit)


def _add_to_watchlist(ticker: str) -> None:
    current = load_watchlist([])
    if ticker.upper() not in {t.upper() for t in current}:
        save_watchlist(current + [ticker.upper()])
        st.toast(f"{ticker} Watchlist에 추가됨")
    else:
        st.toast(f"{ticker}는 이미 Watchlist에 있습니다")


def _portfolio_snapshot_text() -> str:
    """Best-effort summary of live Schwab positions, for the report prompt."""
    try:
        from engine.schwab import connection_status, accounts_with_positions, flatten_positions
        status = connection_status()
        if not status.get("connected"):
            return "Schwab 미연결 — 실시간 계좌 데이터 없음."
        positions = flatten_positions(accounts_with_positions())
        if not positions:
            return "Schwab 연결됨, 보유 포지션 없음."
        total = sum(p.get("Market Value") or 0 for p in positions) or 1
        lines = [
            f"- {p['Ticker']}: {p.get('Market Value', 0) / total * 100:.1f}% 비중, "
            f"미실현손익 {p.get('Unrealized P/L %', 0):+.1f}%"
            for p in sorted(positions, key=lambda p: p.get("Market Value") or 0, reverse=True)[:15]
        ]
        return "\n".join(lines)
    except Exception:
        return "계좌 데이터를 불러오지 못했습니다."


def render() -> None:
    st.title("AI Center")
    st.caption("종목 발굴·비교·종합 리포트를 위한 코너입니다. 개별 종목 리스트/목표가 관리는 Watchlist에서 하세요.")
    tickers = _watchlist()
    with st.spinner("종목 스캔 중..."):
        picks = _discover(tuple(tickers))

    analyze_tab, compare_tab, discover_tab, report_tab = st.tabs(["Analyze", "Compare", "Discover", "종합 리포트"])

    with analyze_tab:
        if "ai_analyze_ticker" not in st.session_state:
            st.session_state["ai_analyze_ticker"] = "NVDA"
        quick_tickers = list(dict.fromkeys(list(tickers) + (list(picks["Ticker"]) if not picks.empty else [])))
        if quick_tickers:
            st.caption("빠른 선택 (Watchlist + Discover)")
            qcols = st.columns(min(8, len(quick_tickers)) or 1)
            for i, t in enumerate(quick_tickers[:16]):
                if qcols[i % len(qcols)].button(t, key=f"quick_analyze_{t}", use_container_width=True):
                    st.session_state["ai_analyze_ticker"] = t
        ticker = st.text_input("Ticker", key="ai_analyze_ticker").upper().strip()
        if ticker: _detail(ticker)

    with compare_tab:
        c1, c2 = st.columns(2)
        left = c1.text_input("Ticker A", "NVDA", key="compare_a").upper().strip()
        right = c2.text_input("Ticker B", "AMD", key="compare_b").upper().strip()
        if left and right:
            data = _radar((left, right))
            st.dataframe(data, use_container_width=True, hide_index=True)

    with discover_tab:
        st.markdown("### Discover — Watchlist 밖 주목할 종목")
        st.caption("현재 Watchlist에 없는 종목 중, 규칙 기반 신호가 BUY로 나오는 종목입니다.")
        if picks.empty:
            st.info("지금은 Watchlist 밖에서 뚜렷한 BUY 신호가 나온 종목이 없습니다.")
        else:
            dcols = st.columns(3)
            for i, (_, row) in enumerate(picks.iterrows()):
                with dcols[i % 3]:
                    st.markdown(f'<div class="compact-stock-card"><div><b>{row["Ticker"]}</b><span>{row["Signal"]}</span></div><strong>{money(row["Price"])}</strong><small>{_signed(row.get("Daily %"))} · Score {row["Score"]}</small><p>{row["Reason"]}</p></div>', unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if b1.button("Details", key=f'disc_detail_{row["Ticker"]}', use_container_width=True):
                        st.session_state["ai_analyze_ticker"] = row["Ticker"]
                        st.toast(f'{row["Ticker"]}는 Analyze 탭에서 볼 수 있어요.')
                    if b2.button("+ Watch", key=f'disc_add_{row["Ticker"]}', use_container_width=True):
                        _add_to_watchlist(row["Ticker"])
                        st.rerun()

    with report_tab:
        st.markdown("### 종합 분석 리포트")
        st.caption("보유 종목(Schwab) + Watchlist + 신호를 종합해서, 지금 상황을 하나의 리포트로 정리합니다.")
        from engine.claude_advisor import configured as _ai_configured, ask as _ai_ask
        if not _ai_configured():
            st.info("Anthropic API 키가 설정되지 않아 종합 리포트를 쓸 수 없습니다.")
        else:
            signals = _radar(tuple(tickers))
            movers_text = "\n".join(
                f"- {r['Ticker']}: {r['Signal']}, 점수 {r['Score']}, 일간 {r.get('Daily %', 0):+.2f}%"
                for _, r in signals.head(15).iterrows()
            )
            portfolio_text = _portfolio_snapshot_text()
            if st.button("🤖 종합 리포트 생성", key="ai_full_report_btn"):
                system = (
                    "너는 개인 투자 대시보드에 내장된 한국어 종합 분석 어시스턴트다. "
                    "제공된 보유 종목 데이터와 Watchlist 신호만 근거로, 지금 포트폴리오 상태와 "
                    "Watchlist에서 눈여겨볼 종목을 종합해서 하나의 리포트로 작성해라. "
                    "섹션 구분(예: 포트폴리오 현황 / Watchlist 하이라이트 / 오늘 체크할 것)을 두고, "
                    "확정적 매수/매도 지시가 아니라 참고용 정리 톤을 유지해라."
                )
                user = f"보유 종목 (Schwab):\n{portfolio_text}\n\nWatchlist 신호 요약:\n{movers_text}\n\n종합 리포트를 작성해줘."
                with st.spinner("종합 리포트 생성 중..."):
                    st.session_state["ai_full_report_text"] = _ai_ask(system, user, max_tokens=1800)
            if st.session_state.get("ai_full_report_text"):
                with st.container(border=True):
                    st.markdown(st.session_state["ai_full_report_text"])
