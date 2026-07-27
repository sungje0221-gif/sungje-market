import pandas as pd
import streamlit as st

from components.cards import stars
from components.colored_tables import style_signed_columns
from components.charts import advanced_chart
from engine.analysis import analyze
from engine.fundamentals import days_to_earnings, ticker_info, fundamental_score
from engine.market_data import history, quote
from utils.formatters import compact, money
from utils.watchlist_store import load_watchlist, save_watchlist

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]

PERIODS = {
    "1D": ("1d", "5m"),
    "5D": ("5d", "15m"),
    "1M": ("1mo", "1h"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
}


def period_return(df):
    if df.empty or "Close" not in df:
        return None
    close = df["Close"].dropna()
    if len(close) < 2:
        return None
    return (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100


def render():
    st.title("Watchlist & Advanced Chart")
    st.caption("추가한 종목은 이 브라우저에 자동 저장되어 새로고침·앱 재시작·재배포 후에도 복원됩니다.")
    tickers = load_watchlist(DEFAULT)

    c1, c2 = st.columns([5, 1])
    new = c1.text_input("Add ticker", placeholder="GOOGL").strip().upper()
    if c2.button("Add", use_container_width=True) and new:
        if new not in tickers:
            tickers.append(new)
            save_watchlist(tickers)
            st.rerun()

    rows = []
    for ticker in tickers:
        q = quote(ticker)
        a = analyze(history(ticker, "1y"))
        rows.append({
            "Ticker": ticker,
            "Price": q["price"],
            "Daily %": q["change_pct"],
            "Score": a["score"],
            "Rating": stars(a["score"]),
            "Action": a["action"],
            "Risk": a["risk"],
            "RSI": a["rsi"],
            "Bid": q.get("bid"),
            "Ask": q.get("ask"),
            "Volume": q["volume"],
            "Source": q.get("source"),
            "Earnings D-Day": days_to_earnings(ticker),
        })

    watch_df = pd.DataFrame(rows).sort_values("Score", ascending=False)
    watch_style = style_signed_columns(watch_df, ["Daily %"])
    st.dataframe(
        watch_style,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "Daily %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Score": st.column_config.ProgressColumn(min_value=0, max_value=100),
            "RSI": st.column_config.NumberColumn(format="%.1f"),
            "Volume": st.column_config.NumberColumn(format="compact"),
        },
    )

    st.markdown("## Advanced Chart")
    top = st.columns([1.8, 3.4])
    selected = top[0].selectbox("Ticker", tickers)
    period_label = top[1].radio("Range", list(PERIODS.keys()), horizontal=True, index=6)

    controls = st.columns(8)
    show_ma20 = controls[0].toggle("MA20", value=True)
    show_ma50 = controls[1].toggle("MA50", value=True)
    show_ma100 = controls[2].toggle("MA100", value=False)
    show_ma200 = controls[3].toggle("MA200", value=True)
    show_bollinger = controls[4].toggle("Bollinger", value=False)
    show_volume = controls[5].toggle("Volume", value=True)
    show_rsi = controls[6].toggle("RSI", value=True)
    show_macd = controls[7].toggle("MACD", value=True)

    period, interval = PERIODS[period_label]
    chart_df = history(selected, period, interval)
    one_year = history(selected, "1y", "1d")
    q = quote(selected)
    a = analyze(one_year)
    info = ticker_info(selected)

    range_return = period_return(chart_df)
    year_return = period_return(one_year)

    high_52 = float(one_year["High"].max()) if not one_year.empty else None
    low_52 = float(one_year["Low"].min()) if not one_year.empty else None
    ma200 = float(one_year["Close"].rolling(200).mean().iloc[-1]) if len(one_year) >= 200 else None
    avg_volume = float(one_year["Volume"].tail(20).mean()) if not one_year.empty and "Volume" in one_year else None
    volume_ratio = (q["volume"] / avg_volume) if q["volume"] and avg_volume else None

    stats = st.columns(8)
    stats[0].metric("Current", money(q["price"]), f'{q["change_pct"]:+.2f}%' if q["change_pct"] is not None else None)
    stats[1].metric(f"{period_label} Return", "—" if range_return is None else f"{range_return:+.2f}%")
    stats[2].metric("1Y Return", "—" if year_return is None else f"{year_return:+.2f}%")
    stats[3].metric("52W Low", money(low_52))
    stats[4].metric("52W High", money(high_52))
    stats[5].metric("MA200", money(ma200))
    stats[6].metric("Volume Ratio", "—" if volume_ratio is None else f"{volume_ratio:.2f}x")
    stats[7].metric("RSI", "—" if a["rsi"] is None else f'{a["rsi"]:.1f}')

    st.plotly_chart(
        advanced_chart(
            chart_df,
            selected,
            show_ma20=show_ma20,
            show_ma50=show_ma50,
            show_ma100=show_ma100,
            show_ma200=show_ma200,
            show_bollinger=show_bollinger,
            show_volume=show_volume,
            show_rsi=show_rsi,
            show_macd=show_macd,
        ),
        use_container_width=True,
    )

    st.markdown("### Fundamentals")
    fscore = fundamental_score(info)
    score_col, label_col = st.columns([1, 5])
    score_col.metric("Fundamental Score", f'{fscore["score"]:.0f}/100')
    label_col.markdown(
        f'<div class="panel"><b>{fscore["label"]}</b> · '
        'Yahoo가 일부 항목을 누락할 경우 이용 가능한 항목만으로 계산됩니다.</div>',
        unsafe_allow_html=True,
    )
    f = st.columns(8)
    f[0].metric("Market Cap", compact(info.get("marketCap")))
    f[1].metric("Trailing P/E", "—" if info.get("trailingPE") is None else f'{info.get("trailingPE"):.1f}')
    f[2].metric("Forward P/E", "—" if info.get("forwardPE") is None else f'{info.get("forwardPE"):.1f}')
    f[3].metric("EPS", "—" if info.get("trailingEps") is None else f'${info.get("trailingEps"):.2f}')
    f[4].metric("Dividend Yield", "—" if info.get("dividendYield") is None else f'{info.get("dividendYield") * 100:.2f}%')
    f[5].metric("Beta", "—" if info.get("beta") is None else f'{info.get("beta"):.2f}')
    f[6].metric("Target Mean", money(info.get("targetMeanPrice")))
    earnings_days = days_to_earnings(selected)
    f[7].metric("Earnings", "—" if earnings_days is None else f"D{earnings_days:+d}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Action", a["action"])
    c2.metric("Risk", a["risk"])
    c3.metric("Support", money(a["support"]))
    c4.metric("Resistance", money(a["resistance"]))

    if st.button(f"Remove {selected}"):
        save_watchlist([x for x in tickers if x != selected])
        st.rerun()
