import pandas as pd
import streamlit as st
from engine.fundamentals import next_earnings_date, ticker_info
from engine.market_data import history
from utils.watchlist_store import load_watchlist_data

@st.cache_data(ttl=21600, show_spinner=False)
def _dates(tickers):
    now = pd.Timestamp.now(tz="UTC"); rows = []
    for ticker in tickers:
        ts = next_earnings_date(ticker)
        dday = None if ts is None else int((ts.normalize() - now.normalize()).days)
        rows.append({"Ticker": ticker, "Date": "—" if ts is None else ts.strftime("%Y-%m-%d"), "D-Day": dday})
    return pd.DataFrame(rows)

def render():
    st.title("Earnings Radar")
    st.caption("Dates are cached for 6 hours. Detailed company data loads only after you choose a ticker.")
    tickers = tuple(x["ticker"] for x in load_watchlist_data([]))
    if not tickers:
        st.info("Watchlist에 종목을 추가하세요."); return
    df = _dates(tickers).sort_values("D-Day", na_position="last")
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(420, 38 + 35 * len(df)))
    selected = st.selectbox("Open earnings detail", ["Select a ticker"] + list(tickers))
    if selected == "Select a ticker": return
    with st.spinner(f"Loading {selected} detail..."):
        info = ticker_info(selected)
        chart = history(selected, "2y", "1d")
    cols = st.columns(5)
    cols[0].metric("Forward EPS", f'${info.get("forwardEps"):.2f}' if info.get("forwardEps") is not None else "—")
    cols[1].metric("Trailing EPS", f'${info.get("trailingEps"):.2f}' if info.get("trailingEps") is not None else "—")
    cols[2].metric("Revenue Growth", f'{(info.get("revenueGrowth") or 0)*100:+.1f}%')
    cols[3].metric("Earnings Growth", f'{(info.get("earningsGrowth") or 0)*100:+.1f}%')
    cols[4].metric("Target", f'${info.get("targetMeanPrice"):.2f}' if info.get("targetMeanPrice") else "—")
    if not chart.empty and "Close" in chart:
        st.line_chart(chart["Close"], height=330)
    st.markdown("### Company context")
    st.write(info.get("longBusinessSummary") or "Detailed company summary is temporarily unavailable.")
