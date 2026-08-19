from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.fundamentals import days_to_earnings, fundamental_score, ticker_info
from engine.market_data import batch_history, batch_quotes, history, intraday_history, quote
from utils.formatters import compact, money
from utils.export import excel_download_button
from utils.watchlist_store import delete_watchlist_item, load_watchlist_data, save_watchlist_data, storage_status
from pages.command_center import _score_from_frame, _priority_tag

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

    target_price = row.get("target_price")
    current_price = q.get("price")
    if target_price:
        if current_price and current_price <= target_price:
            st.success(f"🎯 목표가 도달! 현재가 {money(current_price)} ≤ 목표가 {money(target_price)}")
        else:
            gap = ((current_price / target_price - 1) * 100) if current_price and target_price else None
            st.info(f"목표가 {money(target_price)}까지 {'' if gap is None else f'{gap:+.1f}% 남음'}")

        st.markdown("##### 분할 매수 계획 (목표가 기준)")
        plan_cols = st.columns([1, 1, 2])
        plan_budget = plan_cols[0].number_input("예산", min_value=100.0, value=5000.0, step=100.0, key=f"plan_budget_{ticker}")
        plan_spacing = plan_cols[1].slider("분할 간격", 1.0, 15.0, 4.0, 0.5, format="%.1f%%", key=f"plan_spacing_{ticker}")
        from engine.planner import build as _build_plan
        plan_df = pd.DataFrame(_build_plan(float(target_price), plan_budget, plan_spacing))
        st.dataframe(
            plan_df, use_container_width=True, hide_index=True,
            column_config={
                "Buy Price": st.column_config.NumberColumn(format="$%.2f"),
                "Allocation": st.column_config.NumberColumn(format="$%.2f"),
                "Estimated Cost": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
    else:
        st.caption("아직 목표가가 설정되지 않았습니다. 아래에서 직접 정하거나, AI에게 제안받으세요.")
        from engine.claude_advisor import configured as _ai_configured, ask as _ai_ask
        if _ai_configured() and st.button("🤖 AI 목표가 제안", key=f"ai_target_{ticker}"):
            support = a.get("support")
            rsi_val = a.get("rsi")
            week52_low = info.get("fiftyTwoWeekLow")
            week52_high = info.get("fiftyTwoWeekHigh")
            system = (
                "너는 개인 투자 대시보드에 내장된 한국어 매수 목표가 제안 어시스턴트다. "
                "제공된 데이터만 근거로 적정 매수 목표가 하나를 제안하고, 왜 그 가격인지 2~3문장으로 짧게 설명해라. "
                "확정적 조언이 아니라 참고용 제안 톤을 유지해라. 마지막 줄에 '제안 목표가: $숫자' 형식으로 명확히 표기해라."
            )
            user = (
                f"종목: {ticker}\n현재가: {current_price}\n지지선(계산값): {support}\nRSI: {rsi_val}\n"
                f"52주 최저: {week52_low}\n52주 최고: {week52_high}\n목표가를 제안해줘."
            )
            with st.spinner("AI 목표가 계산 중..."):
                st.session_state[f"ai_target_text_{ticker}"] = _ai_ask(system, user, max_tokens=600)
        if st.session_state.get(f"ai_target_text_{ticker}"):
            with st.container(border=True):
                st.markdown(st.session_state[f"ai_target_text_{ticker}"])

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
        from utils.formatters import period_return
        pr = period_return(chart_df)
        if pr is not None:
            st.metric(f"{range_label} 수익률", f"{pr:+.2f}%")
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
    from pages.news import news_ko as _fetch_news
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
    width, height = 150, 40
    pad_top, pad_bottom = 4, 6
    pts = []
    for i, val in enumerate(values):
        x = i * width / (len(values) - 1)
        y = pad_top + (1 - (val - low) / spread) * (height - pad_top - pad_bottom)
        pts.append((x, y))

    # Smooth the jagged raw line into a soft curve: quadratic-bezier through
    # the midpoint of each consecutive pair of points. Cheap and dependency
    # free, but reads far better than a plain polyline at this size.
    path = f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        path += f" Q {pts[i][0]:.1f},{pts[i][1]:.1f} {mx:.1f},{my:.1f}"
    path += f" L {pts[-1][0]:.1f},{pts[-1][1]:.1f}"

    area_path = f"{path} L {pts[-1][0]:.1f},{height:.1f} L {pts[0][0]:.1f},{height:.1f} Z"
    color = "#4da3ff" if positive else "#ff6474"
    # Single-line output on purpose: a multi-line string here, once embedded
    # into another multi-line f-string, can produce a blank/whitespace-only
    # line inside the surrounding unsafe_allow_html block. Streamlit's
    # markdown parser treats that as the end of raw HTML and dumps
    # everything after it as literal escaped text instead of rendering it.
    return (
        f'<svg class="watch-spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">'
        f'<path d="{area_path}" fill="{color}" fill-opacity="0.16" stroke="none"/>'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )


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
    excel_download_button(frame, "watchlist", key="xl_watchlist")


def render() -> None:
    st.title("Watchlist")
    mode, source = storage_status()
    st.caption(f"{mode} · {source} · Movers 표 + 종목 리스트/상세 화면을 함께 제공합니다.")
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

    toolbar = st.columns([2, 1, 1])
    search = toolbar[0].text_input("Search", placeholder="Ticker or memo", label_visibility="collapsed").strip().lower()
    tag_filter = toolbar[1].selectbox("Tag", ["All"] + TAGS, label_visibility="collapsed")
    sort_by = toolbar[2].selectbox(
        "Sort",
        ["Biggest losers", "Biggest gainers", "Largest move", "Pinned", "Ticker"],
        label_visibility="collapsed",
    )

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

    st.divider()

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
        .wl-card{min-height:78px;padding:11px 12px;border-radius:12px;background:linear-gradient(180deg,rgba(14,30,49,.98),rgba(7,18,31,.98));border:1px solid rgba(148,163,184,.14);display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:10px;align-items:center}
        .wl-card.wl-active{border-color:#3f6c9e;background:linear-gradient(180deg,rgba(21,41,67,.98),rgba(10,24,40,.98))}
        .wl-left{min-width:0}.wl-right{display:flex;flex-direction:column;align-items:flex-end;justify-content:space-between;min-height:52px}
        .wl-top{display:flex;align-items:center;gap:6px}.wl-top b{font-size:13px;letter-spacing:.01em}
        .wl-score{font-size:8px;padding:2px 6px;border-radius:999px;color:#9cb2c8;border:1px solid rgba(148,163,184,.18)}
        .wl-price{font-size:16px;font-weight:850;line-height:1.15;margin-top:4px;white-space:nowrap}
        .wl-change{font-size:10px;font-weight:850;margin-top:2px}
        .wl-vol{font-size:8px;color:#71869f;margin-top:2px}
        .wl-spark{width:90px;height:26px;overflow:visible}
        .wl-spark path{fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
        .wl-tag{display:inline-block;font-size:8px;font-weight:900;letter-spacing:.08em;padding:2px 7px;border-radius:999px;background:rgba(100,166,255,.09);color:#64a6ff}
        .wl-tag.buy{color:#35d6a5;background:rgba(53,214,165,.09)}.wl-tag.risk{color:#ff6474;background:rgba(255,100,116,.09)}.wl-tag.move{color:#f3c969;background:rgba(243,201,105,.09)}
        div[data-testid="stVerticalBlockBorderWrapper"] button[kind="secondary"],
        div[data-testid="stVerticalBlockBorderWrapper"] button[kind="primary"]{padding:0!important;min-height:30px!important;height:30px!important;width:30px!important;font-size:11px!important}
        </style>''', unsafe_allow_html=True)
        with st.container(height=640):
            for row in filtered:
                ticker = row["ticker"]
                q = quotes.get(ticker, {})
                change = q.get("change_pct")
                day_change = q.get("change_abs")
                positive = bool(change is not None and change >= 0)
                score = _score_from_frame(histories.get(ticker))
                tag, tag_css = _priority_tag(score, change)
                spark = _sparkline_svg(histories.get(ticker, pd.DataFrame()), positive).replace('class="watch-spark"', 'class="wl-spark"').replace('class="watch-spark-empty"', 'class="wl-spark"')
                pin = "★ " if row.get("pinned") else ""
                is_active = ticker == selected

                card_col, btn_col = st.columns([6, 1])
                with card_col:
                    target_price = row.get("target_price")
                    price_now = q.get("price")
                    hit_target = bool(target_price and price_now and price_now <= target_price)
                    target_badge = '<div class="wl-tag" style="background:rgba(53,214,165,.15);color:#35d6a5;margin-top:3px">🎯 TARGET HIT</div>' if hit_target else ""
                    active_cls = " wl-active" if is_active else ""
                    change_txt = "—" if change is None else f"{change:+.2f}%"
                    day_change_txt = "—" if day_change is None else f"{day_change:+.2f}"
                    card_html = (
                        f'<div class="wl-card{active_cls}">'
                        f'<div class="wl-left">'
                        f'<div class="wl-top"><b>{pin}{ticker}</b><span class="wl-score">{score:.0f}</span></div>'
                        f'<div class="wl-price">{money(q.get("price"))}</div>'
                        f'<div class="wl-change" style="color:{_color(change)}">{change_txt}</div>'
                        f'<div class="wl-vol">{day_change_txt} · Vol {_fmt_volume(q.get("volume"))}</div>'
                        f'{target_badge}'
                        f'</div>'
                        f'<div class="wl-right">{spark}<div class="wl-tag {tag_css}">{tag}</div></div>'
                        f'</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)
                with btn_col:
                    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
                    # A real Streamlit button -- clicking this only triggers
                    # an internal rerun (no browser page reload), so scroll
                    # position stays put; only the left detail panel changes.
                    if st.button("●" if is_active else "›", key=f"cl_select_{ticker}", type="primary" if is_active else "secondary"):
                        st.session_state["watch_selected"] = ticker
                        st.rerun()

    with left_col:
        if selected and selected in tickers:
            _detail(selected, records)
        else:
            st.info("오른쪽 목록에서 종목을 선택하세요.")

