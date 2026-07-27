import pandas as pd
import streamlit as st

from components.charts import candlestick
from components.cards import stars
from engine.market_data import quote, history
from engine.analysis import analyze
from utils.storage import load_json, save_json
from utils.formatters import money, pct, compact

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","SMH","CEG","VRT","ETN","ANET","SKHY","SPCX"]

PERIODS = {
    "1D": ("1d", "5m"),
    "5D": ("5d", "15m"),
    "1M": ("1mo", "1h"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "YTD": ("ytd", "1d"),
    "1Y": ("1y", "1d"),
}

def colored_delta(value):
    if value is None:
        return '<span class="delta-flat">—</span>'
    css = "delta-up" if value > 0 else "delta-down" if value < 0 else "delta-flat"
    arrow = "▲" if value > 0 else "▼" if value < 0 else "•"
    return f'<span class="{css}">{arrow} {value:+.2f}%</span>'

def stat_box(label, value, tone=""):
    st.markdown(
        f'<div class="statbox"><div class="statlabel">{label}</div>'
        f'<div class="statvalue {tone}">{value}</div></div>',
        unsafe_allow_html=True,
    )

def period_return(df):
    if df.empty or "Close" not in df:
        return None
    close = df["Close"].dropna()
    if len(close) < 2:
        return None
    return (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

def render():
    st.title("Watchlist")
    tickers = load_json("watchlist.json", DEFAULT)

    c1, c2 = st.columns([5, 1])
    new = c1.text_input("Add ticker", placeholder="GOOGL").strip().upper()
    if c2.button("Add", use_container_width=True) and new:
        if new not in tickers:
            tickers.append(new)
            save_json("watchlist.json", tickers)
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
            "Volume": q["volume"],
        })

    df = pd.DataFrame(rows).sort_values("Score", ascending=False)
    st.dataframe(
        df,
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

    st.markdown("## Detailed Chart")
    top = st.columns([2.1, 2.8, 1, 1, 1, 1])
    selected = top[0].selectbox("Ticker", tickers)
    period_label = top[1].radio("Range", list(PERIODS.keys()), horizontal=True, index=6)
    show_ma20 = top[2].toggle("MA20", value=True)
    show_ma50 = top[3].toggle("MA50", value=True)
    show_ma200 = top[4].toggle("MA200", value=True)
    show_volume = top[5].toggle("Volume", value=True)

    period, interval = PERIODS[period_label]
    chart_df = history(selected, period, interval)
    one_year_df = history(selected, "1y", "1d")
    q = quote(selected)
    a = analyze(one_year_df)

    range_return = period_return(chart_df)
    year_return = period_return(one_year_df)

    high_52 = None
    low_52 = None
    avg_volume_20 = None
    latest_volume = q["volume"]
    ma200 = None

    if not one_year_df.empty:
        high_52 = float(one_year_df["High"].max())
        low_52 = float(one_year_df["Low"].min())
        if "Volume" in one_year_df and not one_year_df["Volume"].dropna().empty:
            avg_volume_20 = float(one_year_df["Volume"].tail(20).mean())
        if len(one_year_df) >= 200:
            ma200 = float(one_year_df["Close"].rolling(200).mean().iloc[-1])

    row1 = st.columns(6)
    with row1[0]:
        stat_box("Current Price", money(q["price"]), "blue")
    with row1[1]:
        stat_box(f"{period_label} Return", colored_delta(range_return))
    with row1[2]:
        stat_box("1Y Return", colored_delta(year_return))
    with row1[3]:
        stat_box("52W Low", money(low_52))
    with row1[4]:
        stat_box("52W High", money(high_52))
    with row1[5]:
        stat_box("MA200", money(ma200), "purple")

    row2 = st.columns(6)
    with row2[0]:
        stat_box("Daily Change", colored_delta(q["change_pct"]))
    with row2[1]:
        stat_box("Volume", compact(latest_volume))
    with row2[2]:
        stat_box("20D Avg Volume", compact(avg_volume_20))
    with row2[3]:
        volume_ratio = (latest_volume / avg_volume_20) if latest_volume and avg_volume_20 else None
        stat_box("Volume Ratio", "—" if volume_ratio is None else f"{volume_ratio:.2f}x")
    with row2[4]:
        stat_box("RSI 14", "—" if a["rsi"] is None else f'{a["rsi"]:.1f}')
    with row2[5]:
        stat_box("Trend Score", f'{a["score"]:.0f}/100')

    st.plotly_chart(
        candlestick(
            chart_df,
            selected,
            show_ma20=show_ma20,
            show_ma50=show_ma50,
            show_ma200=show_ma200,
            show_volume=show_volume,
        ),
        use_container_width=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Action", a["action"])
    c2.metric("Risk", a["risk"])
    c3.metric("Support (60D)", money(a["support"]))
    c4.metric("Resistance (60D)", money(a["resistance"]))

    st.info(
        f'{selected}: {a["action"]} · Trend score {a["score"]:.0f} · '
        f'Risk {a["risk"]} · {period_label} return '
        f'{"—" if range_return is None else f"{range_return:+.2f}%"}'
    )

    if st.button(f"Remove {selected}"):
        save_json("watchlist.json", [x for x in tickers if x != selected])
        st.rerun()
