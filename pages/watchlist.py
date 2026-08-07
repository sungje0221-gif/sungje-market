from __future__ import annotations

from urllib.parse import quote

import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.fundamentals import days_to_earnings, fundamental_score, ticker_info
from engine.market_data import batch_history, batch_quotes, history, intraday_history, quote
from utils.formatters import compact, money
from utils.watchlist_store import delete_watchlist_item, load_watchlist_data, save_watchlist_data, storage_status

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]
TAGS = ["Watch", "Long-term", "Swing", "Trade", "ETF", "AI", "Dividend", "High Risk"]
RANGES = {
    "1D": "1d",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
}

CANDLES_BY_RANGE = {
    "1D": ["1m", "2m", "5m", "15m", "30m", "60m"],
    "5D": ["1m", "2m", "5m", "15m", "30m", "60m"],
    "1M": ["5m", "15m", "30m", "60m", "1d"],
    "3M": ["60m", "1d"],
    "6M": ["1d", "1wk"],
    "1Y": ["1d", "1wk"],
    "5Y": ["1d", "1wk", "1mo"],
}

DEFAULT_CANDLE = {
    "1D": "1m",
    "5D": "5m",
    "1M": "60m",
    "3M": "1d",
    "6M": "1d",
    "1Y": "1d",
    "5Y": "1wk",
}


def _color(value: float | None) -> str:
    if value is None:
        return "#a9b7c9"
    return "#45a3ff" if value >= 0 else "#ff5b6e"


def _detail(ticker: str, records: list[dict]) -> None:
    row = next((r for r in records if r["ticker"] == ticker), None)
    if row is None:
        return
    q = quote(ticker)
    one_year = history(ticker, "1y", "1d")
    a = analyze(one_year)
    info = ticker_info(ticker)
    st.markdown(f"## {ticker} · Details")
    stats = st.columns(6)
    stats[0].metric("Price", money(q.get("price")), None if q.get("change_pct") is None else f'{q["change_pct"]:+.2f}%')
    stats[1].metric("AI", a.get("action", "—"))
    stats[2].metric("Score", "—" if a.get("score") is None else f'{a["score"]:.0f}/100')
    stats[3].metric("Rating", "—" if a.get("score") is None else stars(a["score"]))
    stats[4].metric("Target", money(row.get("target_price")))
    stats[5].metric("Earnings", "—" if days_to_earnings(ticker) is None else f'D{days_to_earnings(ticker):+d}')

    range_stats = st.columns(4)
    range_stats[0].metric("52W High", money(info.get("fiftyTwoWeekHigh")))
    range_stats[1].metric("52W Low", money(info.get("fiftyTwoWeekLow")))
    range_stats[2].metric("Day Change $", "—" if q.get("change_abs") is None else f'{q["change_abs"]:+.2f}')
    range_stats[3].metric("Volume", _fmt_volume(q.get("volume")))

    range_col, candle_col = st.columns([2, 1])
    with range_col:
        range_label = st.radio("Range", list(RANGES), horizontal=True, index=0, key=f"range_{ticker}")
    candle_options = CANDLES_BY_RANGE[range_label]
    candle_key = f"candle_{ticker}_{range_label}"
    with candle_col:
        interval = st.selectbox(
            "Candle",
            candle_options,
            index=candle_options.index(DEFAULT_CANDLE[range_label]),
            key=candle_key,
        )
    period = RANGES[range_label]
    is_intraday = interval.endswith("m") or interval.endswith("h")
    chart_df = intraday_history(ticker, period, interval) if is_intraday else history(ticker, period, interval)

    if not chart_df.empty:
        if is_intraday:
            latest = chart_df.index[-1]
            latest_text = latest.strftime("%b %d, %I:%M %p") if hasattr(latest, "strftime") else str(latest)
            st.caption(f"Actual {interval} OHLCV candles · Regular session · Latest bar: {latest_text} · 30-second cache")
        st.plotly_chart(
            advanced_chart(
                chart_df, ticker,
                show_ma20=True,
                show_ma50=not is_intraday,
                show_ma100=False,
                show_ma200=not is_intraday,
                show_bollinger=False,
                show_volume=True,
                show_rsi=not is_intraday,
                show_macd=False,
                intraday=is_intraday,
            ),
            use_container_width=True,
        )
    else:
        st.warning(f"No {interval} chart data is currently available for {ticker} in the selected range. Choose another candle interval.")

    with st.expander("Edit investment card", expanded=False):
        with st.form(f"edit_{ticker}"):
            c1, c2, c3, c4 = st.columns(4)
            pinned = c1.toggle("Pinned", value=bool(row.get("pinned")))
            tag = c2.selectbox("Tag", TAGS, index=TAGS.index(row.get("tag")) if row.get("tag") in TAGS else 0)
            target = c3.number_input("Target / Buy", min_value=0.0, value=float(row.get("target_price") or 0), step=0.5)
            stop = c4.number_input("Stop", min_value=0.0, value=float(row.get("stop_price") or 0), step=0.5)
            memo = st.text_area("Memo / Investment thesis", value=row.get("memo", ""), height=80)
            b1, b2 = st.columns([4, 1])
            if b1.form_submit_button("Save", type="primary", use_container_width=True):
                row.update({"pinned": pinned, "tag": tag, "target_price": target or None, "stop_price": stop or None, "memo": memo})
                save_watchlist_data(records)
                st.rerun()
            if b2.form_submit_button("Delete", use_container_width=True):
                delete_watchlist_item(ticker, records)
                st.session_state.pop("watch_selected", None)
                st.rerun()

    fscore = fundamental_score(info)
    st.markdown("### Fundamentals")
    f = st.columns(6)
    f[0].metric("Fundamental", f'{fscore["score"]:.0f}/100')
    f[1].metric("Market Cap", compact(info.get("marketCap")))
    f[2].metric("Trailing P/E", "—" if info.get("trailingPE") is None else f'{info.get("trailingPE"):.1f}')
    f[3].metric("Forward P/E", "—" if info.get("forwardPE") is None else f'{info.get("forwardPE"):.1f}')
    f[4].metric("EPS", "—" if info.get("trailingEps") is None else f'${info.get("trailingEps"):.2f}')
    f[5].metric("Target Mean", money(info.get("targetMeanPrice")))

    st.markdown("### Related News")
    from pages.news import news as _fetch_news
    items, source, error = _fetch_news(ticker)
    st.caption(f"Source: {source} · cached for 15 minutes")
    if not items:
        st.caption("지금은 관련 뉴스를 가져오지 못했습니다.")
    else:
        for item in items[:5]:
            st.markdown(f"**{item['title']}**")
            st.caption(item.get("provider") or "Unknown")
            if item.get("url"):
                st.link_button("Open article", item["url"], key=f"wl_news_{ticker}_{item['title'][:40]}")
            st.divider()


def _fmt_volume(value: float | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"


def _sparkline_svg(frame: pd.DataFrame, positive: bool) -> str:
    if frame is None or frame.empty or "Close" not in frame:
        return '<div class="watch-spark-empty">—</div>'
    values = frame["Close"].dropna().tail(30).astype(float).tolist()
    if len(values) < 2:
        return '<div class="watch-spark-empty">—</div>'
    low, high = min(values), max(values)
    spread = high - low or 1.0
    width, height = 150, 38
    pts = []
    for i, val in enumerate(values):
        x = i * width / (len(values) - 1)
        y = height - ((val - low) / spread) * (height - 5) - 2
        pts.append(f"{x:.1f},{y:.1f}")
    color = "#45a3ff" if positive else "#ff5b6e"
    return f'''<svg class="watch-spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="{' '.join(pts)}" fill="none" stroke="{color}" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''


def _mover_table(rows: list[dict], quotes: dict[str, dict]) -> None:
    table_rows = []
    for row in rows:
        ticker = row["ticker"]
        q = quotes.get(ticker, {})
        table_rows.append({
            "Ticker": ticker,
            "Price": q.get("price"),
            "Day %": q.get("change_pct"),
            "Day Chg $": q.get("change_abs"),
            "Low": q.get("day_low"),
            "High": q.get("day_high"),
            "Volume": q.get("volume"),
            "Tag": row.get("tag", "Watch"),
            "Memo": row.get("memo") or "",
        })
    frame = pd.DataFrame(table_rows)
    if frame.empty:
        st.info("No matching tickers.")
        return

    def color_move(value):
        if pd.isna(value):
            return ""
        return "color: #45a3ff; font-weight: 700" if float(value) >= 0 else "color: #ff5b6e; font-weight: 700"

    styled = frame.style.map(color_move, subset=["Day %", "Day Chg $"])
    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=min(500, 38 + len(frame) * 35),
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
            "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%", width="small"),
            "Day Chg $": st.column_config.NumberColumn("Day Chg $", format="%+.2f", width="small"),
            "Low": st.column_config.NumberColumn("Low", format="$%.2f", width="small"),
            "High": st.column_config.NumberColumn("High", format="$%.2f", width="small"),
            "Volume": st.column_config.NumberColumn("Volume", format="compact", width="small"),
            "Tag": st.column_config.TextColumn("Tag", width="small"),
            "Memo": st.column_config.TextColumn("Memo", width="medium"),
        },
    )


def render() -> None:
    st.title("Watchlist")
    mode, source = storage_status()
    st.caption(f"{mode} · {source} · Movers 표와 compact card를 함께 제공합니다.")
    records = load_watchlist_data(DEFAULT)
    tickers = [r["ticker"] for r in records]

    with st.expander("＋ Add ticker", expanded=False):
        c1, c2, c3 = st.columns([1.2, 1, 2])
        new = c1.text_input("Ticker", placeholder="NVDA").strip().upper()
        tag = c2.selectbox("Tag", TAGS)
        memo = c3.text_input("Memo", placeholder="Why is this on my watchlist?")
        if st.button("Add", type="primary") and new:
            if new not in tickers:
                records.append({"ticker": new, "pinned": False, "target_price": None, "stop_price": None, "tag": tag, "memo": memo})
                save_watchlist_data(records)
                st.rerun()
            else:
                st.info(f"{new} is already in the watchlist.")

    toolbar = st.columns([2, 1, 1, 1])
    search = toolbar[0].text_input("Search", placeholder="Ticker or memo", label_visibility="collapsed").strip().lower()
    tag_filter = toolbar[1].selectbox("Tag", ["All"] + TAGS, label_visibility="collapsed")
    sort_by = toolbar[2].selectbox(
        "Sort",
        ["Biggest losers", "Biggest gainers", "Largest move", "Pinned", "Ticker"],
        label_visibility="collapsed",
    )
    view_options = ["Table + Cards", "Table only", "Cards only", "Compact List"]
    default_view = st.query_params.get("view") or st.session_state.get("watch_view") or "Table + Cards"
    if default_view not in view_options:
        default_view = "Table + Cards"
    view = toolbar[3].selectbox(
        "View", view_options, index=view_options.index(default_view),
        label_visibility="collapsed", key="watch_view_select",
    )
    st.session_state["watch_view"] = view

    filtered = [
        r for r in records
        if (not search or search in r["ticker"].lower() or search in r.get("memo", "").lower())
        and (tag_filter == "All" or r.get("tag") == tag_filter)
    ]
    quotes = batch_quotes(tuple(r["ticker"] for r in filtered))

    if sort_by == "Biggest losers":
        filtered.sort(key=lambda r: float(quotes.get(r["ticker"], {}).get("change_pct") if quotes.get(r["ticker"], {}).get("change_pct") is not None else 999999))
    elif sort_by == "Biggest gainers":
        filtered.sort(key=lambda r: float(quotes.get(r["ticker"], {}).get("change_pct") if quotes.get(r["ticker"], {}).get("change_pct") is not None else -999999), reverse=True)
    elif sort_by == "Largest move":
        filtered.sort(key=lambda r: abs(float(quotes.get(r["ticker"], {}).get("change_pct") or 0)), reverse=True)
    elif sort_by == "Pinned":
        filtered.sort(key=lambda r: (not r.get("pinned", False), r["ticker"]))
    else:
        filtered.sort(key=lambda r: r["ticker"])

    if view in ("Table + Cards", "Table only"):
        st.markdown("### Daily Movers")
        st.caption("기본적으로 가장 많이 내린 종목부터 정렬됩니다. 위 Sort 메뉴에서 바로 변경할 수 있습니다.")
        _mover_table(filtered, quotes)
        st.markdown("#### 종목 삭제")
        remove_col1, remove_col2 = st.columns([3, 1])
        to_remove = remove_col1.multiselect(
            "삭제할 종목 선택",
            [r["ticker"] for r in filtered],
            key="watch_bulk_remove_select",
        )
        if remove_col2.button("삭제하기", type="primary", disabled=not to_remove, key="watch_bulk_remove_btn"):
            for ticker in to_remove:
                delete_watchlist_item(ticker, records)
            st.session_state.pop("watch_selected", None)
            st.rerun()

    if view in ("Table + Cards", "Cards only"):
        st.markdown("### My Investment Cards")
        st.caption("카드 아무 곳이나 누르면 상세 화면이 열립니다. 미니 차트는 실제 최근 30거래일 종가이며, 점수는 추세·20일 모멘텀·RSI·MACD 기반 규칙 점수입니다.")

        histories = batch_history(tuple(r["ticker"] for r in filtered), period="6mo", interval="1d")
        analytics = {ticker: analyze(histories.get(ticker, pd.DataFrame())) for ticker in (r["ticker"] for r in filtered)}

        selected = st.query_params.get("watch") or st.session_state.get("watch_selected")
        st.markdown('''<style>
        .watch-card-link{display:block;text-decoration:none!important;color:inherit!important;margin-bottom:10px}
        .watch-card-v310{background:#0d1c2e;border:1px solid #263b54;border-radius:11px;padding:12px 13px 10px;min-height:176px;transition:all .14s ease;box-shadow:0 1px 0 rgba(255,255,255,.02)}
        .watch-card-v310:hover{transform:translateY(-2px);border-color:#4d78aa;background:#10233a;box-shadow:0 7px 18px rgba(0,0,0,.20)}
        .wc-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}.wc-ticker{font-size:15px;font-weight:850;color:#f4f8ff}.wc-tag{font-size:8px;letter-spacing:.7px;color:#78aee8;text-transform:uppercase}
        .wc-main{display:flex;justify-content:space-between;align-items:baseline}.wc-price{font-size:20px;font-weight:800;color:#fff}.wc-change{font-size:13px;font-weight:850}
        .wc-range{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px;font-size:10px;color:#8297af}.wc-range b{display:block;margin-top:1px;color:#cdd9e8;font-size:11px}
        .watch-spark{width:100%;height:38px;margin:7px 0 4px}.watch-spark-empty{height:38px;display:flex;align-items:center;justify-content:center;color:#61758e}
        .wc-footer{display:flex;justify-content:space-between;align-items:center;border-top:1px solid #20344b;padding-top:7px}.wc-ai{font-size:10px;color:#8fa4bb}.wc-ai b{color:#e9f1fb;font-size:12px}.wc-action{font-size:10px;font-weight:900;border:1px solid #38526f;border-radius:999px;padding:3px 7px;color:#dcecff}
        .wc-volume{font-size:9px;color:#71869f;margin-top:3px}.wc-signal{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:4px;font-size:9px;color:#71869f}.wc-signal b{display:block;color:#cdd9e8;font-size:10px;margin-top:1px}.wc-source{font-size:8px;color:#60758e;margin-top:5px;text-align:right}
        </style>''', unsafe_allow_html=True)

        for start in range(0, len(filtered), 5):
            cols = st.columns(5, gap="small")
            for col, row in zip(cols, filtered[start:start + 5]):
                ticker = row["ticker"]
                q = quotes.get(ticker, {})
                change = q.get("change_pct")
                positive = bool(change is not None and change >= 0)
                color = _color(change)
                analysis = analytics.get(ticker, {})
                score = analysis.get("score")
                action = str(analysis.get("action", "NO DATA") or "NO DATA").upper()
                rsi_value = analysis.get("rsi")
                return_20d = analysis.get("return_20d")
                pin = "★ " if row.get("pinned") else ""
                spark = _sparkline_svg(histories.get(ticker, pd.DataFrame()), positive)
                day_change = q.get("change_abs")
                href = f"?watch={ticker}&view={quote(view)}"
                with col:
                    top_l, top_r = st.columns([3, 2])
                    with top_r:
                        if st.button("✕ 삭제", key=f"watch_del_{ticker}"):
                            delete_watchlist_item(ticker, records)
                            st.session_state.pop("watch_selected", None)
                            st.rerun()
                    st.markdown(f'''<a class="watch-card-link" href="{href}" target="_self">
                    <div class="watch-card-v310">
                      <div class="wc-head"><span class="wc-ticker">{pin}{ticker}</span><span class="wc-tag">{row.get("tag", "Watch")}</span></div>
                      <div class="wc-main"><span class="wc-price">{money(q.get("price"))}</span><span class="wc-change" style="color:{color}">{"—" if change is None else f"{change:+.2f}%"}</span></div>
                      <div class="wc-volume">Day change {"—" if day_change is None else f"${day_change:+.2f}"} · Vol {_fmt_volume(q.get("volume"))}</div>
                      {spark}
                      <div class="wc-range"><span>LOW<b>{money(q.get("day_low"))}</b></span><span>HIGH<b>{money(q.get("day_high"))}</b></span></div>
                      <div class="wc-signal"><span>20D RETURN<b>{"—" if return_20d is None else f"{return_20d:+.1f}%"}</b></span><span>RSI 14<b>{"—" if rsi_value is None else f"{rsi_value:.0f}"}</b></span></div>
                      <div class="wc-footer"><span class="wc-ai">RULE SCORE <b>{"—" if score is None else f"{score:.0f}"}</b></span><span class="wc-action">{action}</span></div>
                      <div class="wc-source">Chart: actual last 30 closes · no random data</div>
                    </div></a>''', unsafe_allow_html=True)

    if view == "Compact List":
        selected = (
            st.query_params.get("watch")
            or st.session_state.get("watch_selected")
            or (filtered[0]["ticker"] if filtered else None)
        )
        if selected in tickers:
            st.session_state["watch_selected"] = selected

        histories = batch_history(tuple(r["ticker"] for r in filtered), period="1mo", interval="1d")
        left_col, right_col = st.columns([2.3, 1], gap="medium")

        with right_col:
            st.markdown("#### Watchlist")
            st.markdown('''<style>
            .cl-row-link{display:block;text-decoration:none!important;color:inherit!important}
            .cl-row{display:grid;grid-template-columns:1fr 95px;align-items:center;gap:8px;padding:9px 8px;border-bottom:1px solid #1d2f45;border-radius:8px}
            .cl-row:hover{background:#0e1e30}
            .cl-row-active{background:#152943;border:1px solid #3f6c9e}
            .cl-ticker{font-size:13px;font-weight:850;color:#f4f8ff;display:block}.cl-tag{font-size:8px;color:#78aee8;letter-spacing:.6px;text-transform:uppercase}
            .cl-vol{font-size:9px;color:#71869f;margin-top:2px;grid-column:1/2}
            .cl-price-wrap{text-align:right}.cl-price{font-size:13px;font-weight:800;color:#fff;display:block}.cl-change{font-size:10px;font-weight:850;display:block;margin-top:1px}
            .cl-spark{width:100%;height:20px;margin-top:4px;grid-column:1/-1}
            </style>''', unsafe_allow_html=True)
            with st.container(height=640):
                for row in filtered:
                    ticker = row["ticker"]
                    q = quotes.get(ticker, {})
                    change = q.get("change_pct")
                    day_change = q.get("change_abs")
                    positive = bool(change is not None and change >= 0)
                    color = _color(change)
                    spark = _sparkline_svg(histories.get(ticker, pd.DataFrame()), positive).replace('class="watch-spark"', 'class="cl-spark"').replace('class="watch-spark-empty"', 'class="cl-spark"')
                    pin = "★ " if row.get("pinned") else ""
                    href = f"?watch={ticker}&view={quote(view)}"
                    active_cls = " cl-row-active" if ticker == selected else ""
                    st.markdown(f'''<a class="cl-row-link" href="{href}" target="_self">
                    <div class="cl-row{active_cls}">
                      <div><span class="cl-ticker">{pin}{ticker}</span><span class="cl-tag">{row.get("tag", "Watch")}</span></div>
                      <div class="cl-price-wrap">
                        <span class="cl-price">{money(q.get("price"))}</span>
                        <span class="cl-change" style="color:{color}">{"—" if change is None else f"{change:+.2f}%"}</span>
                      </div>
                      <div class="cl-vol">{"—" if day_change is None else f"{day_change:+.2f}"} · Vol {_fmt_volume(q.get("volume"))}</div>
                      {spark}
                    </div></a>''', unsafe_allow_html=True)

        with left_col:
            if selected and selected in tickers:
                _detail(selected, records)
            else:
                st.info("오른쪽 목록에서 종목을 선택하세요.")
        return

    selected = st.query_params.get("watch") or st.session_state.get("watch_selected")
    if selected and selected in tickers:
        st.session_state["watch_selected"] = selected
        st.divider()
        _detail(selected, records)

