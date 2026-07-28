import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.fundamentals import days_to_earnings, ticker_info, fundamental_score
from engine.market_data import history, quote
from utils.formatters import compact, money
from utils.watchlist_store import (
    delete_watchlist_item,
    load_watchlist_data,
    save_watchlist_data,
    storage_status,
)

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]
TAGS = ["Watch", "Long-term", "Swing", "Trade", "ETF", "AI", "Dividend", "High Risk"]
PERIODS = {"1D": ("1d", "5m"), "5D": ("5d", "15m"), "1M": ("1mo", "1h"), "3M": ("3mo", "1d"), "6M": ("6mo", "1d"), "YTD": ("ytd", "1d"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk")}


def period_return(df):
    if df.empty or "Close" not in df:
        return None
    close = df["Close"].dropna()
    return None if len(close) < 2 else (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100


def _signal(price, target, stop, action):
    if price is not None and stop is not None and price <= stop:
        return "STOP ALERT"
    if price is not None and target is not None and price <= target:
        return "BUY ZONE"
    return action or "WAIT"


def render():
    st.title("Watchlist Pro")
    mode, source = storage_status()
    st.caption(f"{mode} · {source} · 종목, 메모, 목표가, 손절가, 태그가 모든 기기에서 동기화됩니다.")
    sync_error = st.session_state.get("watchlist_sync_error")
    if sync_error:
        st.warning(f"Supabase 연결에 실패해 로컬 파일로 작동 중입니다: {sync_error}")

    records = load_watchlist_data(DEFAULT)
    tickers = [r["ticker"] for r in records]

    with st.expander("＋ Add ticker", expanded=not bool(records)):
        c1, c2, c3 = st.columns([2, 1, 2])
        new = c1.text_input("Ticker", placeholder="GOOGL").strip().upper()
        tag = c2.selectbox("Tag", TAGS)
        memo = c3.text_input("Memo", placeholder="Why is this on my watchlist?")
        c4, c5, c6 = st.columns(3)
        target = c4.number_input("Target / Buy price", min_value=0.0, value=0.0, step=0.5)
        stop = c5.number_input("Stop price", min_value=0.0, value=0.0, step=0.5)
        pinned = c6.toggle("Pin to top", value=False)
        if st.button("Add to Watchlist", type="primary", use_container_width=True) and new:
            if new not in tickers:
                records.append({"ticker": new, "pinned": pinned, "target_price": target or None, "stop_price": stop or None, "tag": tag, "memo": memo})
                save_watchlist_data(records)
                st.rerun()
            else:
                st.info(f"{new} is already in the watchlist.")

    toolbar = st.columns([2, 1, 1, 1])
    search = toolbar[0].text_input("Search", placeholder="Ticker or memo", label_visibility="collapsed").strip().lower()
    tag_filter = toolbar[1].selectbox("Tag filter", ["All"] + TAGS, label_visibility="collapsed")
    sort_by = toolbar[2].selectbox("Sort", ["Pinned", "Score", "Ticker", "Target proximity"], label_visibility="collapsed")
    if toolbar[3].button("↻ Sync", use_container_width=True):
        st.session_state.pop("watchlist_pro_records_v2", None)
        load_watchlist_data(DEFAULT, force=True)
        st.rerun()

    rows = []
    for item in records:
        ticker = item["ticker"]
        q = quote(ticker)
        a = analyze(history(ticker, "1y"))
        price = q.get("price")
        target_price = item.get("target_price")
        proximity = abs(price - target_price) / price * 100 if price and target_price else 9999
        rows.append({
            **item,
            "price": price,
            "daily_pct": q.get("change_pct"),
            "score": a.get("score"),
            "action": a.get("action"),
            "signal": _signal(price, target_price, item.get("stop_price"), a.get("action")),
            "rsi": a.get("rsi"),
            "earnings": days_to_earnings(ticker),
            "proximity": proximity,
        })

    filtered = [r for r in rows if (not search or search in r["ticker"].lower() or search in r.get("memo", "").lower()) and (tag_filter == "All" or r.get("tag") == tag_filter)]
    if sort_by == "Pinned":
        filtered.sort(key=lambda x: (not x.get("pinned", False), x["ticker"]))
    elif sort_by == "Score":
        filtered.sort(key=lambda x: x.get("score") or -1, reverse=True)
    elif sort_by == "Target proximity":
        filtered.sort(key=lambda x: x["proximity"])
    else:
        filtered.sort(key=lambda x: x["ticker"])

    st.markdown("### Watchlist Cards")
    if not filtered:
        st.info("No matching tickers.")
    else:
        for start_idx in range(0, len(filtered), 4):
            cols = st.columns(4)
            for col, row in zip(cols, filtered[start_idx:start_idx + 4]):
                daily = row.get("daily_pct") or 0
                css = "up" if daily >= 0 else "down"
                html = (f'<div class="watch-card"><div class="watch-head"><b>{row["ticker"]}</b>'
                        f'<span class="score-pill">{row.get("score") or 0:.0f}</span></div>'
                        f'<div class="watch-price">{money(row.get("price"))}</div>'
                        f'<div class="watch-change {css}">{daily:+.2f}%</div>'
                        f'<div style="font-size:10px;color:#8fa2b8;margin-top:9px">'
                        f'{row.get("signal") or "WAIT"} · {row.get("tag", "Watch")}</div></div>')
                with col:
                    st.markdown(html, unsafe_allow_html=True)

    st.markdown("### Edit & Details")
    for row in filtered:
        price_text = money(row.get("price"))
        daily_pct = row.get("daily_pct")
        day_text = "" if daily_pct is None else f" · {daily_pct:+.2f}%"
        direction = "⚪" if daily_pct is None or daily_pct == 0 else ("🟢" if daily_pct > 0 else "🔴")
        title = f"{direction} {'★' if row.get('pinned') else '☆'} {row['ticker']} · {price_text}{day_text} · {row['signal']}"
        with st.expander(title, expanded=False):
            m = st.columns(6)
            m[0].metric("Price", money(row.get("price")), None if row.get("daily_pct") is None else f"{row['daily_pct']:+.2f}%")
            m[1].metric("AI", row.get("action") or "—")
            m[2].metric("Score", f"{row.get('score', 0):.0f}/100")
            m[3].metric("Target", money(row.get("target_price")))
            m[4].metric("Stop", money(row.get("stop_price")))
            m[5].metric("Earnings", "—" if row.get("earnings") is None else f"D{row['earnings']:+d}")
            st.caption(f"Tag: {row.get('tag', 'Watch')} · Rating: {stars(row.get('score') or 0)}")
            if row.get("memo"):
                st.write(row["memo"])
            with st.form(f"edit_{row['ticker']}"):
                e1, e2, e3 = st.columns([1, 1, 1.4])
                epin = e1.toggle("Pinned", value=bool(row.get("pinned")))
                etag = e2.selectbox("Tag", TAGS, index=TAGS.index(row.get("tag")) if row.get("tag") in TAGS else 0)
                etarget = e3.number_input("Target / Buy", min_value=0.0, value=float(row.get("target_price") or 0), step=0.5)
                e4, e5 = st.columns([1, 3])
                estop = e4.number_input("Stop", min_value=0.0, value=float(row.get("stop_price") or 0), step=0.5)
                ememo = e5.text_area("Memo / Investment thesis", value=row.get("memo", ""), height=90)
                b1, b2 = st.columns([4, 1])
                saved = b1.form_submit_button("Save changes", type="primary", use_container_width=True)
                removed = b2.form_submit_button("Delete", use_container_width=True)
                if saved:
                    for item in records:
                        if item["ticker"] == row["ticker"]:
                            item.update({"pinned": epin, "tag": etag, "target_price": etarget or None, "stop_price": estop or None, "memo": ememo})
                    save_watchlist_data(records)
                    st.rerun()
                if removed:
                    delete_watchlist_item(row["ticker"], records)
                    st.rerun()

    if not tickers:
        return

    st.markdown("## Advanced Chart")
    top = st.columns([1.8, 3.4])
    selected = top[0].selectbox("Ticker", tickers)
    period_label = top[1].radio("Range", list(PERIODS.keys()), horizontal=True, index=6)
    controls = st.columns(8)
    show_ma20 = controls[0].toggle("MA20", value=True); show_ma50 = controls[1].toggle("MA50", value=True)
    show_ma100 = controls[2].toggle("MA100", value=False); show_ma200 = controls[3].toggle("MA200", value=True)
    show_bollinger = controls[4].toggle("Bollinger", value=False); show_volume = controls[5].toggle("Volume", value=True)
    show_rsi = controls[6].toggle("RSI", value=True); show_macd = controls[7].toggle("MACD", value=True)

    period, interval = PERIODS[period_label]
    chart_df = history(selected, period, interval); one_year = history(selected, "1y", "1d")
    q = quote(selected); a = analyze(one_year); info = ticker_info(selected)
    range_return = period_return(chart_df); year_return = period_return(one_year)
    high_52 = float(one_year["High"].max()) if not one_year.empty else None
    low_52 = float(one_year["Low"].min()) if not one_year.empty else None
    ma200 = float(one_year["Close"].rolling(200).mean().iloc[-1]) if len(one_year) >= 200 else None
    avg_volume = float(one_year["Volume"].tail(20).mean()) if not one_year.empty and "Volume" in one_year else None
    volume_ratio = (q["volume"] / avg_volume) if q.get("volume") and avg_volume else None
    stats = st.columns(8)
    stats[0].metric("Current", money(q.get("price")), f'{q["change_pct"]:+.2f}%' if q.get("change_pct") is not None else None)
    stats[1].metric(f"{period_label} Return", "—" if range_return is None else f"{range_return:+.2f}%")
    stats[2].metric("1Y Return", "—" if year_return is None else f"{year_return:+.2f}%")
    stats[3].metric("52W Low", money(low_52)); stats[4].metric("52W High", money(high_52)); stats[5].metric("MA200", money(ma200))
    stats[6].metric("Volume Ratio", "—" if volume_ratio is None else f"{volume_ratio:.2f}x"); stats[7].metric("RSI", "—" if a.get("rsi") is None else f'{a["rsi"]:.1f}')
    st.plotly_chart(advanced_chart(chart_df, selected, show_ma20=show_ma20, show_ma50=show_ma50, show_ma100=show_ma100, show_ma200=show_ma200, show_bollinger=show_bollinger, show_volume=show_volume, show_rsi=show_rsi, show_macd=show_macd), use_container_width=True)

    st.markdown("### Fundamentals")
    fscore = fundamental_score(info)
    score_col, label_col = st.columns([1, 5]); score_col.metric("Fundamental Score", f'{fscore["score"]:.0f}/100')
    label_col.markdown(f'<div class="panel"><b>{fscore["label"]}</b> · Yahoo가 일부 항목을 누락할 경우 이용 가능한 항목만으로 계산됩니다.</div>', unsafe_allow_html=True)
    f = st.columns(8)
    f[0].metric("Market Cap", compact(info.get("marketCap"))); f[1].metric("Trailing P/E", "—" if info.get("trailingPE") is None else f'{info.get("trailingPE"):.1f}')
    f[2].metric("Forward P/E", "—" if info.get("forwardPE") is None else f'{info.get("forwardPE"):.1f}'); f[3].metric("EPS", "—" if info.get("trailingEps") is None else f'${info.get("trailingEps"):.2f}')
    f[4].metric("Dividend Yield", "—" if info.get("dividendYield") is None else f'{info.get("dividendYield") * 100:.2f}%'); f[5].metric("Beta", "—" if info.get("beta") is None else f'{info.get("beta"):.2f}')
    f[6].metric("Target Mean", money(info.get("targetMeanPrice"))); earnings_days = days_to_earnings(selected); f[7].metric("Earnings", "—" if earnings_days is None else f"D{earnings_days:+d}")
