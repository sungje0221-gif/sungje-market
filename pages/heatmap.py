from __future__ import annotations

import pandas as pd
import streamlit as st

from components.charts import market_breadth_bar, performance_matrix, stock_heatmap
from engine.fundamentals import ticker_info
from engine.market_data import quote
from utils.storage import load_json

GROUPS = {
    "S&P 500 Leaders": ["NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","BRK-B","JPM","LLY","V","XOM","WMT","MA","COST","JNJ","NFLX","HD","PG","ORCL","ABBV","BAC","KO","CRM","CVX","PM","IBM","GE","CAT","UNH"],
    "NASDAQ 100": ["NVDA","MSFT","AAPL","AMZN","GOOGL","META","AVGO","TSLA","COST","NFLX","AMD","PLTR","CSCO","TMUS","LIN","PEP","ADBE","INTU","AMGN","QCOM","TXN","BKNG","AMAT","PANW","GILD","HON","MU","SBUX","MELI","ADI"],
    "AI & Infrastructure": ["NVDA","AVGO","AMD","MU","TSM","ASML","AMAT","LRCX","KLAC","SMCI","VRT","ETN","ANET","GLW","MSFT","GOOGL","META","AMZN","ORCL","PLTR","CEG","VST","GEV","PWR","DELL","HPE","MRVL","ARM","CRDO","ALAB"],
    "ETF Dashboard": ["VOO","SPY","QQQ","QQQM","VXF","IWM","IJH","SMH","SOXX","XLK","XLC","XLY","XLF","XLI","XLV","XLE","XLU","XLRE","XLP","XLB","ITA","NLR","SCHD","VYM","DGRO","GLD","SLV","COPX","EWY","KORU"],
}

SECTOR_GROUPS = {
    "Technology": ["AAPL","MSFT","NVDA","AVGO","ORCL","CRM","AMD","ADBE","CSCO","IBM","QCOM","TXN","AMAT","ANET","PLTR"],
    "Communication": ["GOOGL","META","NFLX","TMUS","DIS","T","VZ","CMCSA","SPOT","RDDT","PINS","SNAP"],
    "Consumer": ["AMZN","TSLA","HD","MCD","BKNG","TJX","LOW","SBUX","NKE","COST","CAVA","CMG"],
    "Financials": ["JPM","BAC","WFC","GS","MS","V","MA","AXP","BLK","SCHW","COF","C"],
    "Healthcare": ["LLY","UNH","JNJ","ABBV","MRK","AMGN","TMO","ABT","ISRG","GILD","VRTX","PFE"],
    "Industrials": ["GE","CAT","RTX","HON","UNP","ETN","PWR","GEV","BA","LMT","DE","UPS"],
    "Energy": ["XOM","CVX","COP","EOG","SLB","OXY","MPC","VLO","PSX","WMB","OKE","FANG"],
    "Utilities & Power": ["CEG","VST","NEE","SO","DUK","AEP","SRE","D","EXC","PCG","NRG","AES"],
    "Semiconductors": ["NVDA","AVGO","AMD","TSM","ASML","MU","AMAT","LRCX","KLAC","QCOM","TXN","ARM","MRVL","ALAB"],
    "Space & Defense": ["RKLB","ASTS","LUNR","PL","KTOS","LMT","RTX","NOC","GD","BA","ACHR","JOBY"],
}

SECTOR_ETFS = {
    "Technology": "XLK", "Communication": "XLC", "Consumer Discretionary": "XLY",
    "Financials": "XLF", "Industrials": "XLI", "Healthcare": "XLV",
    "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE",
    "Consumer Staples": "XLP", "Materials": "XLB", "Semiconductors": "SMH",
}


@st.cache_data(ttl=300, show_spinner=False)
def build_rows(tickers: tuple[str, ...], sector_name: str | None = None) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        q = quote(ticker)
        info = ticker_info(ticker)
        try:
            weight = max(float(info.get("marketCap") or 1), 1.0)
        except (TypeError, ValueError):
            weight = 1.0
        rows.append({
            "Ticker": ticker,
            "Price": q.get("price"),
            "Change %": q.get("change_pct"),
            "Weight": weight,
            "Sector": sector_name or info.get("sector") or "Market",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def sector_snapshot() -> pd.DataFrame:
    rows = []
    for sector, ticker in SECTOR_ETFS.items():
        q = quote(ticker)
        rows.append({"Sector": sector, "Ticker": ticker, "Change %": q.get("change_pct"), "Price": q.get("price")})
    return pd.DataFrame(rows)


def _summary(df: pd.DataFrame):
    valid = df.dropna(subset=["Change %"])
    if valid.empty:
        return 0, 0, 0.0, "—", "—", 0.0
    adv = int((valid["Change %"] > 0).sum())
    dec = int((valid["Change %"] < 0).sum())
    flat = max(len(valid) - adv - dec, 0)
    breadth = (adv - dec) / max(len(valid), 1) * 100
    return (
        adv, dec, float(valid["Change %"].mean()),
        valid.loc[valid["Change %"].idxmax(), "Ticker"],
        valid.loc[valid["Change %"].idxmin(), "Ticker"],
        breadth,
    )


def _stat_card(label, value, note, tone="blue"):
    st.markdown(
        f'<div class="heat-stat {tone}"><span>{label}</span><b>{value}</b><em>{note}</em></div>',
        unsafe_allow_html=True,
    )


def render():
    st.markdown('<div class="page-kicker">LIVE MARKET MAP · VERSION 0.93</div>', unsafe_allow_html=True)
    st.title("Market Heatmap")
    st.caption("시가총액, 등락률, 시장 폭과 섹터 순환을 한 화면에서 확인합니다. 데이터는 Yahoo Finance 기준입니다.")

    sector_df = sector_snapshot()
    valid_sector = sector_df.dropna(subset=["Change %"]).sort_values("Change %", ascending=False)
    market_tone = "Risk-on" if not valid_sector.empty and valid_sector["Change %"].mean() > 0 else "Risk-off"
    lead_sector = valid_sector.iloc[0]["Sector"] if not valid_sector.empty else "—"
    weak_sector = valid_sector.iloc[-1]["Sector"] if not valid_sector.empty else "—"

    h1, h2, h3 = st.columns([1.2, 1, 1])
    with h1:
        st.markdown(
            f'''<div class="heat-hero">
                <div><span>MARKET REGIME</span><b>{market_tone}</b></div>
                <p>Leading sector <strong>{lead_sector}</strong> · Weakest <strong>{weak_sector}</strong></p>
            </div>''', unsafe_allow_html=True,
        )
    with h2:
        if not valid_sector.empty:
            _stat_card("SECTOR AVERAGE", f'{valid_sector["Change %"].mean():+.2f}%', "Equal-weight sector pulse", "green" if valid_sector["Change %"].mean() >= 0 else "red")
    with h3:
        positive = int((valid_sector["Change %"] > 0).sum()) if not valid_sector.empty else 0
        _stat_card("POSITIVE SECTORS", f"{positive}/{len(valid_sector)}", "Breadth across sector ETFs", "blue")

    tab_map, tab_sectors, tab_matrix = st.tabs(["▦ Stock Map", "◫ Sector Rotation", "▥ Performance Matrix"])

    with tab_map:
        control_a, control_b = st.columns([1, 2])
        with control_a:
            mode = st.radio("Universe", ["Major Indexes", "Sectors", "My Watchlist"], horizontal=True, label_visibility="collapsed")
        with control_b:
            if mode == "Major Indexes":
                selected = st.selectbox("Index / Theme", list(GROUPS.keys()), label_visibility="collapsed")
                df = build_rows(tuple(GROUPS[selected]))
                title = selected
            elif mode == "Sectors":
                selected = st.selectbox("Sector", list(SECTOR_GROUPS.keys()), label_visibility="collapsed")
                df = build_rows(tuple(SECTOR_GROUPS[selected]), selected)
                title = selected
            else:
                tickers = load_json("watchlist.json", [])
                if not tickers:
                    st.info("Watchlist에 종목을 먼저 추가하세요.")
                    return
                df = build_rows(tuple(tickers), "My Watchlist")
                title = "My Watchlist"

        adv, dec, avg, best, worst, breadth = _summary(df)
        stats = st.columns(6)
        with stats[0]: _stat_card("ADVANCERS", adv, "Positive", "green")
        with stats[1]: _stat_card("DECLINERS", dec, "Negative", "red")
        with stats[2]: _stat_card("AVERAGE", f"{avg:+.2f}%", "Equal weight", "green" if avg >= 0 else "red")
        with stats[3]: _stat_card("BREADTH", f"{breadth:+.0f}", "Advancers − decliners", "blue")
        with stats[4]: _stat_card("LEADER", best, "Top performer", "green")
        with stats[5]: _stat_card("LAGGARD", worst, "Weakest", "red")

        st.plotly_chart(stock_heatmap(df, title), use_container_width=True, config={"displaylogo": False, "scrollZoom": False})
        st.plotly_chart(market_breadth_bar(df), use_container_width=True, config={"displayModeBar": False})

        leaders, laggards = st.columns(2, gap="large")
        display_cols = ["Ticker", "Price", "Change %", "Sector"]
        with leaders:
            st.markdown("#### Momentum Leaders")
            st.dataframe(df[display_cols].sort_values("Change %", ascending=False).head(10), use_container_width=True, hide_index=True,
                         column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.NumberColumn(format="%+.2f%%")})
        with laggards:
            st.markdown("#### Pressure List")
            st.dataframe(df[display_cols].sort_values("Change %").head(10), use_container_width=True, hide_index=True,
                         column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.NumberColumn(format="%+.2f%%")})

    with tab_sectors:
        st.plotly_chart(stock_heatmap(
            sector_df.rename(columns={"Sector": "Ticker"}).assign(Weight=1, Sector="US Sectors"),
            "US Sector Rotation"
        ), use_container_width=True, config={"displaylogo": False})
        st.plotly_chart(market_breadth_bar(
            sector_df.rename(columns={"Sector": "Ticker"})
        ), use_container_width=True, config={"displayModeBar": False})
        st.dataframe(valid_sector, use_container_width=True, hide_index=True,
                     column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.ProgressColumn(min_value=-5, max_value=5, format="%+.2f%%")})

    with tab_matrix:
        matrix_groups = {
            "Core": ["VOO", "VXF", "QQQM", "IWM"],
            "AI": ["NVDA", "GOOGL", "MSFT", "AVGO"],
            "Power": ["CEG", "VST", "GEV", "NLR"],
            "Korea": ["EWY", "KORU", "SKHY"],
            "Metals": ["GLD", "SLV", "COPX"],
        }
        matrix_rows = []
        for group, tickers in matrix_groups.items():
            group_df = build_rows(tuple(tickers), group)
            matrix_rows.append(group_df)
        matrix_df = pd.concat(matrix_rows, ignore_index=True)
        st.plotly_chart(performance_matrix(matrix_df), use_container_width=True, config={"displayModeBar": False})
        st.caption("색이 진할수록 당일 움직임이 강합니다. 종목 간 상대 강도 비교용이며 매수 신호가 아닙니다.")
