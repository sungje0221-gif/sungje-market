from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import stars
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.fundamentals import days_to_earnings, fundamental_score, ticker_info
from engine.market_data import batch_quotes, history, quote
from utils.formatters import compact, money
from utils.watchlist_store import delete_watchlist_item, load_watchlist_data, save_watchlist_data, storage_status

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]
TAGS = ["Watch", "Long-term", "Swing", "Trade", "ETF", "AI", "Dividend", "High Risk"]
PERIODS = {"1M": ("1mo", "1d"), "3M": ("3mo", "1d"), "6M": ("6mo", "1d"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk")}


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
    stats[2].metric("Score", f'{a.get("score", 0):.0f}/100')
    stats[3].metric("Rating", stars(a.get("score", 0)))
    stats[4].metric("Target", money(row.get("target_price")))
    stats[5].metric("Earnings", "—" if days_to_earnings(ticker) is None else f'D{days_to_earnings(ticker):+d}')

    period_label = st.radio("Range", list(PERIODS), horizontal=True, index=3, key=f"range_{ticker}")
    period, interval = PERIODS[period_label]
    chart_df = history(ticker, period, interval)
    if not chart_df.empty:
        st.plotly_chart(
            advanced_chart(
                chart_df, ticker, show_ma20=True, show_ma50=True,
                show_ma100=False, show_ma200=True, show_bollinger=False,
                show_volume=True, show_rsi=True, show_macd=False,
            ),
            use_container_width=True,
        )

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


def _mover_table(rows: list[dict], quotes: dict[str, dict]) -> None:
    table_rows = []
    for row in rows:
        ticker = row["ticker"]
        q = quotes.get(ticker, {})
        table_rows.append({
            "Ticker": ticker,
            "Price": q.get("price"),
            "Day %": q.get("change_pct"),
            "Tag": row.get("tag", "Watch"),
            "Pinned": "★" if row.get("pinned") else "",
            "Memo": row.get("memo") or "",
        })
    frame = pd.DataFrame(table_rows)
    if frame.empty:
        st.info("No matching tickers.")
        return
    frame = frame.sort_values("Day %", ascending=True, na_position="last")
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        height=min(430, 38 + len(frame) * 35),
        column_config={
            "Ticker": st.column_config.TextColumn("Ticker", width="small"),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f", width="small"),
            "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%", width="small"),
            "Tag": st.column_config.TextColumn("Tag", width="small"),
            "Pinned": st.column_config.TextColumn("", width="small"),
            "Memo": st.column_config.TextColumn("Memo", width="large"),
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
    view = toolbar[3].selectbox("View", ["Table + Cards", "Table only", "Cards only"], label_visibility="collapsed")

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

    if view != "Cards only":
        st.markdown("### Daily Movers")
        st.caption("기본적으로 가장 많이 내린 종목부터 정렬됩니다. 위 Sort 메뉴에서 바로 변경할 수 있습니다.")
        _mover_table(filtered, quotes)

    if view != "Table only":
        st.markdown("### My Investment Cards")
        selected = st.session_state.get("watch_selected")
        for start in range(0, len(filtered), 5):
            cols = st.columns(5, gap="small")
            for col, row in zip(cols, filtered[start:start + 5]):
                ticker = row["ticker"]
                q = quotes.get(ticker, {})
                change = q.get("change_pct")
                color = _color(change)
                pin = "★ " if row.get("pinned") else ""
                memo = row.get("memo") or "No memo"
                with col:
                    st.markdown(
                        f'''<div class="compact-stock-card watch-grid-card-v309">
                        <div class="watch-card-head"><b>{pin}{ticker}</b><span>{row.get("tag", "Watch")}</span></div>
                        <div class="watch-card-body"><strong>{money(q.get("price"))}</strong>
                        <small style="color:{color}">{"—" if change is None else f"{change:+.2f}%"}</small></div>
                        <p>{memo}</p></div>''',
                        unsafe_allow_html=True,
                    )
                    if st.button("Details", key=f"open_{ticker}", use_container_width=True):
                        st.session_state["watch_selected"] = ticker
                        selected = ticker

        if selected and selected in tickers:
            st.divider()
            _detail(selected, records)
