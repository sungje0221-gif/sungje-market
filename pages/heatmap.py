from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from components.charts import advanced_chart, market_breadth_bar, performance_matrix, stock_heatmap
from components.colored_tables import style_signed_columns
from engine.fundamentals import ticker_info
from engine.market_data import batch_quotes, history, intraday_history, quote
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


CHART_RANGES = {
    "1D": "1d",
    "5D": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
}

CANDLES_BY_RANGE = {
    "1D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "5D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "1M": ["5m", "15m", "30m", "60m", "1d"],
    "3M": ["60m", "1d"],
    "6M": ["1d"],
    "1Y": ["1d"],
    "5Y": ["1d"],
}

DEFAULT_CANDLE = {
    "1D": "1m",
    "5D": "5m",
    "1M": "60m",
    "3M": "1d",
    "6M": "1d",
    "1Y": "1d",
    "5Y": "1d",
}

SECTOR_ETFS = {
    "Technology": "XLK", "Communication": "XLC", "Consumer Discretionary": "XLY",
    "Financials": "XLF", "Industrials": "XLI", "Healthcare": "XLV",
    "Energy": "XLE", "Utilities": "XLU", "Real Estate": "XLRE",
    "Consumer Staples": "XLP", "Materials": "XLB", "Semiconductors": "SMH",
}


@st.cache_data(ttl=20, show_spinner=False)
def build_rows(tickers: tuple[str, ...], sector_name: str | None = None) -> pd.DataFrame:
    # Heatmap loading must stay fast: use a single batch quote request and equal
    # tile sizes. Fundamentals are fetched only after the user selects a symbol.
    quote_map = batch_quotes(tickers)
    rows = []
    for ticker in tickers:
        q = quote_map.get(ticker, {})
        rows.append({
            "Ticker": ticker,
            "Price": q.get("price"),
            "Change %": q.get("change_pct"),
            "Weight": q.get("market_cap") or 1.0,
            "Source": q.get("source") or "Unavailable",
            "Sector": sector_name or "Market",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=20, show_spinner=False)
def sector_snapshot() -> pd.DataFrame:
    tickers = tuple(SECTOR_ETFS.values())
    quote_map = batch_quotes(tickers)
    rows = []
    for sector, ticker in SECTOR_ETFS.items():
        q = quote_map.get(ticker, {})
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




def _money(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _number(value, suffix=""):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(number) >= 1_000_000_000_000:
        return f"{number / 1_000_000_000_000:.2f}T{suffix}"
    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B{suffix}"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M{suffix}"
    return f"{number:,.2f}{suffix}"


def _pct(value):
    try:
        return f"{float(value) * 100:+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _render_ticker_detail(ticker: str):
    q = quote(ticker)
    info = ticker_info(ticker)
    change = q.get("change_pct")
    company = info.get("shortName") or info.get("longName") or ticker

    st.markdown("---")
    header_left, header_right = st.columns([5, 1])
    with header_left:
        st.markdown(f"### {ticker} · {company}")
    with header_right:
        if st.button("닫기", key=f"close_heat_detail_{ticker}", use_container_width=True):
            st.session_state.pop("heatmap_selected_ticker", None)
            st.rerun()

    cols = st.columns(4)
    cols[0].metric("현재가", _money(q.get("price")), f"{change:+.2f}%" if isinstance(change, (int, float)) else None)
    cols[1].metric("시가총액", _number(info.get("marketCap")))
    cols[2].metric("Forward P/E", _number(info.get("forwardPE")))
    cols[3].metric("거래량", _number(q.get("volume")))

    range_col, candle_col = st.columns([2, 1])
    with range_col:
        range_label = st.radio(
            "기간",
            list(CHART_RANGES),
            horizontal=True,
            index=0,
            key=f"heat_range_{ticker}",
        )
    candle_options = CANDLES_BY_RANGE[range_label]
    with candle_col:
        interval = st.selectbox(
            "봉",
            candle_options,
            index=candle_options.index(DEFAULT_CANDLE[range_label]),
            key=f"heat_candle_{ticker}_{range_label}",
        )

    period = CHART_RANGES[range_label]
    is_intraday = interval.endswith("m") or interval.endswith("h")
    chart_data = intraday_history(ticker, period, interval) if is_intraday else history(ticker, period, interval)

    if not chart_data.empty:
        st.plotly_chart(
            advanced_chart(
                chart_data,
                ticker,
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
            config={"displayModeBar": True, "displaylogo": False},
        )
        if is_intraday:
            st.caption(f"실제 {interval} OHLCV · 정규장 기준 · 30초 캐시")
    else:
        st.warning(f"{ticker}의 {range_label} / {interval} 데이터가 없습니다. 다른 봉을 선택하세요.")

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("#### 기본 정보")
        details = pd.DataFrame([
            ["Sector", info.get("sector") or "—"],
            ["Industry", info.get("industry") or "—"],
            ["Revenue Growth", _pct(info.get("revenueGrowth"))],
            ["Earnings Growth", _pct(info.get("earningsGrowth"))],
            ["Operating Margin", _pct(info.get("operatingMargins"))],
            ["Analyst Target", _money(info.get("targetMeanPrice"))],
        ], columns=["Item", "Value"])
        st.dataframe(details, use_container_width=True, hide_index=True)
    with right:
        st.markdown("#### 바로가기")
        st.link_button("Yahoo Finance", f"https://finance.yahoo.com/quote/{ticker}", use_container_width=True)
        st.link_button("TradingView", f"https://www.tradingview.com/symbols/{ticker.replace('-', '')}/", use_container_width=True)
        if st.button("☆ Watchlist에 추가", key=f"heat_add_{ticker}", use_container_width=True):
            current = load_json("watchlist.json", [])
            normalized = []
            for item in current:
                normalized.append(item if isinstance(item, dict) else str(item).upper())
            existing = {str(item.get("ticker", "")).upper() if isinstance(item, dict) else str(item).upper() for item in normalized}
            if ticker.upper() not in existing:
                normalized.append(ticker.upper())
                from utils.storage import save_json
                save_json("watchlist.json", normalized)
                st.success(f"{ticker}를 Watchlist에 추가했습니다.")
            else:
                st.info(f"{ticker}는 이미 Watchlist에 있습니다.")


def render():
    st.markdown('<div class="page-kicker">LIVE MARKET MAP · VERSION 3.18.5</div>', unsafe_allow_html=True)
    st.title("Market Heatmap")
    st.caption("현재가와 전일 종가 기준 등락률을 사용합니다. Schwab 연결 시 Schwab 실시간 시세를 우선하고, 나머지는 Yahoo chart의 동일 세션 현재가와 전일 종가를 사용합니다.")

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

        heatmap_fig = stock_heatmap(df, title)
        # Native Streamlit chart selection (Streamlit >=1.35) instead of the
        # third-party streamlit-plotly-events package. That package ships its
        # own separate frontend bundle that can fail to load on Streamlit
        # Cloud (silently breaking every click), which is what was happening
        # here. st.plotly_chart's built-in on_select is maintained by
        # Streamlit itself and needs no extra component to load.
        event = st.plotly_chart(
            heatmap_fig,
            use_container_width=True,
            on_select="rerun",
            selection_mode=("points",),
            key=f"heatmap_chart_{mode}_{title}",
            config={"displayModeBar": False},
        )

        selected_from_click = None
        points = (event or {}).get("selection", {}).get("points", []) if hasattr(event, "get") else []
        if points:
            point = points[0]
            selected_from_click = str(
                point.get("label") or point.get("id") or point.get("text") or ""
            ).upper()

        if selected_from_click and selected_from_click in set(df["Ticker"].astype(str).str.upper()):
            st.session_state["heatmap_selected_ticker"] = selected_from_click

        source_col, fallback_col = st.columns([1, 2])
        with source_col:
            sources = sorted({str(v) for v in df.get("Source", pd.Series(dtype=str)).dropna() if str(v)})
            st.caption("Data source: " + (", ".join(sources) if sources else "Unavailable"))
        with fallback_col:
            fallback = st.selectbox(
                "종목 직접 선택",
                ["선택하세요"] + df["Ticker"].astype(str).tolist(),
                key=f"heatmap_detail_select_{mode}_{title}",
                label_visibility="collapsed",
            )
            if fallback != "선택하세요":
                st.session_state["heatmap_selected_ticker"] = fallback.upper()

        selected_ticker = st.session_state.get("heatmap_selected_ticker")
        if selected_ticker and selected_ticker in set(df["Ticker"].astype(str).str.upper()):
            _render_ticker_detail(selected_ticker)

        st.plotly_chart(market_breadth_bar(df), use_container_width=True, config={"displayModeBar": False})

        leaders, laggards = st.columns(2, gap="large")
        display_cols = ["Ticker", "Price", "Change %", "Sector"]
        with leaders:
            st.markdown("#### Momentum Leaders")
            leaders_df = df[display_cols].sort_values("Change %", ascending=False).head(10)
            st.dataframe(style_signed_columns(leaders_df, ["Change %"]), use_container_width=True, hide_index=True,
                         column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.NumberColumn(format="%+.2f%%")})
        with laggards:
            st.markdown("#### Pressure List")
            laggards_df = df[display_cols].sort_values("Change %").head(10)
            st.dataframe(style_signed_columns(laggards_df, ["Change %"]), use_container_width=True, hide_index=True,
                         column_config={"Price": st.column_config.NumberColumn(format="$%.2f"), "Change %": st.column_config.NumberColumn(format="%+.2f%%")})

    with tab_sectors:
        sector_map_df = pd.DataFrame({
            "Ticker": sector_df["Sector"],
            "Price": sector_df["Price"],
            "Change %": sector_df["Change %"],
            "Weight": 1.0,
            "Sector": "US Sectors",
        })
        st.plotly_chart(
            stock_heatmap(sector_map_df, "US Sector Rotation"),
            use_container_width=True,
            config={"staticPlot": True, "displayModeBar": False, "displaylogo": False},
        )
        st.plotly_chart(
            market_breadth_bar(sector_map_df),
            use_container_width=True,
            config={"displayModeBar": False},
        )
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
