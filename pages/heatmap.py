from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import stock_heatmap
from engine.market_data import quote
from engine.fundamentals import ticker_info
from utils.storage import load_json


GROUPS = {
    "NASDAQ 100": [
        "NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","TSLA","COST","NFLX",
        "AMD","PLTR","CSCO","TMUS","LIN","PEP","ADBE","INTU","AMGN","QCOM",
        "TXN","BKNG","AMAT","PANW","GILD","HON","MU","SBUX","MELI","ADI",
    ],
    "S&P 500 Leaders": [
        "NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","BRK-B","JPM","LLY",
        "V","XOM","WMT","MA","COST","JNJ","NFLX","HD","PG","ORCL",
        "ABBV","BAC","KO","CRM","CVX","PM","IBM","GE","CAT","UNH",
    ],
    "DOW 30": [
        "AAPL","AMGN","AMZN","AXP","BA","CAT","CRM","CSCO","CVX","DIS",
        "GS","HD","HON","IBM","JNJ","JPM","KO","MCD","MMM","MRK",
        "MSFT","NKE","NVDA","PG","SHW","TRV","UNH","V","VZ","WMT",
    ],
    "Russell 2000 Leaders": [
        "RKLB","IONQ","OKLO","ASTS","CAVA","HIMS","CELH","CRDO","APPF","KTOS",
        "SOUN","UPST","RGTI","QBTS","SMFL","TMDX","INOD","LUNR","PL","ACHR",
        "JOBY","SMR","NNE","RXST","VICR","BOOT","FIVE","MARA","RIOT","CLSK",
    ],
    "AI & Infrastructure": [
        "NVDA","AVGO","AMD","MU","TSM","ASML","AMAT","LRCX","KLAC","SMCI",
        "VRT","ETN","ANET","GLW","MSFT","GOOGL","META","AMZN","ORCL","PLTR",
        "CEG","VST","GEV","PWR","DELL","HPE","MRVL","ARM","CRDO","ALAB",
    ],
    "ETFs": [
        "VOO","SPY","QQQ","QQQM","VXF","IWM","IJH","SMH","SOXX","XLK",
        "XLC","XLY","XLF","XLI","XLV","XLE","XLU","XLRE","XLP","XLB",
        "ITA","NLR","SCHD","VYM","DGRO","GLD","SLV","COPX","EWY","KORU",
    ],
}

SECTOR_GROUPS = {
    "Technology": ["AAPL","MSFT","NVDA","AVGO","ORCL","CRM","AMD","ADBE","CSCO","IBM","QCOM","TXN","AMAT","ANET","PLTR"],
    "Communication": ["GOOGL","META","NFLX","TMUS","DIS","T","VZ","CMCSA","SPOT","RDDT","PINS","SNAP"],
    "Consumer Cyclical": ["AMZN","TSLA","HD","MCD","BKNG","TJX","LOW","SBUX","NKE","COST","CAVA","CMG"],
    "Financials": ["JPM","BAC","WFC","GS","MS","V","MA","AXP","BLK","SCHW","COF","C"],
    "Healthcare": ["LLY","UNH","JNJ","ABBV","MRK","AMGN","TMO","ABT","ISRG","GILD","VRTX","PFE"],
    "Industrials": ["GE","CAT","RTX","HON","UNP","ETN","PWR","GEV","BA","LMT","DE","UPS"],
    "Energy": ["XOM","CVX","COP","EOG","SLB","OXY","MPC","VLO","PSX","WMB","OKE","FANG"],
    "Utilities & Power": ["CEG","VST","NEE","SO","DUK","AEP","SRE","D","EXC","PCG","NRG","AES"],
    "Semiconductors": ["NVDA","AVGO","AMD","TSM","ASML","MU","AMAT","LRCX","KLAC","QCOM","TXN","ARM","MRVL","ALAB"],
    "Space & Defense": ["RKLB","ASTS","LUNR","PL","KTOS","LMT","RTX","NOC","GD","BA","ACHR","JOBY"],
}


def market_cap_weight(ticker):
    info = ticker_info(ticker)
    value = info.get("marketCap")
    try:
        return max(float(value), 1.0)
    except (TypeError, ValueError):
        return 1.0


def build_rows(tickers, sector_name=None):
    rows = []
    for ticker in tickers:
        q = quote(ticker)
        info = ticker_info(ticker)
        rows.append({
            "Ticker": ticker,
            "Price": q.get("price"),
            "Change %": q.get("change_pct"),
            "Weight": market_cap_weight(ticker),
            "Sector": sector_name or info.get("sector") or "Market",
        })
    return pd.DataFrame(rows)


def render():
    st.title("Market & Sector Heat Maps")
    st.caption("사각형 크기는 시가총액, 색상은 당일 등락률을 나타냅니다. Yahoo Finance 데이터는 지연될 수 있습니다.")

    mode = st.radio("View", ["Major Indexes", "Sectors", "My Watchlist"], horizontal=True)

    if mode == "Major Indexes":
        selected = st.selectbox("Index / Theme", list(GROUPS.keys()))
        tickers = GROUPS[selected]
        df = build_rows(tickers)
        st.plotly_chart(stock_heatmap(df, selected), use_container_width=True)

    elif mode == "Sectors":
        selected = st.selectbox("Sector", list(SECTOR_GROUPS.keys()))
        tickers = SECTOR_GROUPS[selected]
        df = build_rows(tickers, selected)
        st.plotly_chart(stock_heatmap(df, f"{selected} Heat Map"), use_container_width=True)

    else:
        tickers = load_json("watchlist.json", [])
        if not tickers:
            st.info("Watchlist에 종목을 먼저 추가하세요.")
            return
        df = build_rows(tickers, "My Watchlist")
        st.plotly_chart(stock_heatmap(df, "My Watchlist Heat Map"), use_container_width=True)

    if not df.empty:
        st.dataframe(
            df[["Ticker","Price","Change %","Sector"]].sort_values("Change %", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price": st.column_config.NumberColumn(format="$%.2f"),
                "Change %": st.column_config.NumberColumn(format="%+.2f%%"),
            },
        )
