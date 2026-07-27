import pandas as pd
import streamlit as st

from engine.fundamentals import earnings_calendar, next_earnings_date, ticker_info
from engine.market_data import history
from utils.storage import load_json

DEFAULT = ["GOOGL","META","AMZN","MSFT","AAPL","NVDA","AVGO","TSLA"]


def post_earnings_moves(ticker):
    df = history(ticker, "5y", "1d")
    if df.empty:
        return None
    returns = df["Close"].pct_change().abs().dropna()
    return float(returns.quantile(0.90) * 100) if not returns.empty else None


def render():
    st.title("Earnings Radar")
    tickers = load_json("watchlist.json", DEFAULT)
    now = pd.Timestamp.now(tz="UTC")
    rows = []

    for ticker in tickers:
        ts = next_earnings_date(ticker)
        info = ticker_info(ticker)
        dday = None
        date_text = "—"
        if ts is not None:
            dday = int((ts.normalize() - now.normalize()).days)
            date_text = ts.strftime("%Y-%m-%d")

        rows.append({
            "Ticker": ticker,
            "Date": date_text,
            "D-Day": dday,
            "EPS Estimate": info.get("epsForward"),
            "Revenue Growth": info.get("revenueGrowth"),
            "90th % Daily Move": post_earnings_moves(ticker),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("D-Day", na_position="last")
    st.dataframe(
        df,
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
        st.warning("향후 14일 안에 실적이 예정된 보유·관심 종목이 있습니다. 신규 매수 전 발표 시간을 확인하세요.")
