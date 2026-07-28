import pandas as pd
import streamlit as st

from components.colored_tables import style_signed_columns
from engine.fundamentals import next_earnings_date, ticker_info
from engine.market_data import history
from utils.watchlist_store import load_watchlist_data

DEFAULT = ["GOOGL", "META", "AMZN", "MSFT", "AAPL", "NVDA", "AVGO", "TSLA"]


@st.cache_data(ttl=3600, show_spinner=False)
def post_earnings_moves(ticker):
    df = history(ticker, "5y", "1d")
    if df.empty or "Close" not in df:
        return None
    returns = df["Close"].pct_change().abs().dropna()
    return float(returns.quantile(0.90) * 100) if not returns.empty else None


def render():
    st.title("Earnings Radar")
    records = load_watchlist_data(DEFAULT)
    tickers = [item.get("ticker") for item in records if item.get("ticker")]
    now = pd.Timestamp.now(tz="UTC")
    rows = []

    with st.spinner("Loading earnings dates..."):
        for ticker in tickers:
            ts = next_earnings_date(ticker)
            info = ticker_info(ticker)
            dday = None
            date_text = "—"
            if ts is not None:
                dday = int((ts.normalize() - now.normalize()).days)
                date_text = ts.strftime("%Y-%m-%d")

            revenue_growth = info.get("revenueGrowth")
            if revenue_growth is not None:
                try:
                    revenue_growth = float(revenue_growth) * 100
                except (TypeError, ValueError):
                    revenue_growth = None

            rows.append({
                "Ticker": ticker,
                "Date": date_text,
                "D-Day": dday,
                "EPS Estimate": info.get("forwardEps") or info.get("epsForward"),
                "Revenue Growth": revenue_growth,
                "90th % Daily Move": post_earnings_moves(ticker),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No watchlist tickers available.")
        return

    df = df.sort_values("D-Day", na_position="last")
    found = int(df["D-Day"].notna().sum())
    st.caption(f"Earnings dates found for {found} of {len(df)} watchlist tickers. Yahoo may temporarily omit some dates.")
    earnings_style = style_signed_columns(df, ["Revenue Growth", "90th % Daily Move"])
    st.dataframe(
        earnings_style,
        use_container_width=True,
        hide_index=True,
        column_config={
            "EPS Estimate": st.column_config.NumberColumn(format="$%.2f"),
            "Revenue Growth": st.column_config.NumberColumn(format="%.2f%%"),
            "90th % Daily Move": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    upcoming = df[df["D-Day"].notna() & (df["D-Day"] >= 0) & (df["D-Day"] <= 14)]
    if not upcoming.empty:
        st.warning("One or more watchlist companies report within 14 days. Confirm the exact release time before trading.")
