from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

try:
    from streamlit_plotly_events import plotly_events
except ImportError:
    plotly_events = None

from components.charts import market_breadth_bar, performance_matrix, stock_heatmap
from engine.fundamentals import ticker_info
from engine.market_data import batch_quotes, history, quote
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
            "Weight": 1.0,
            "Sector": sector_name or "Market",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
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
    tone = "#ff5d73" if isinstance(change, (int, float)) and change < 0 else "#31d6a0"
    company = info.get("shortName") or info.get("longName") or ticker

    st.markdown("---")
    st.markdown(f"### {ticker} · {company}")
    st.caption("Heatmap에서 선택한 종목의 핵심 정보입니다.")

    cols = st.columns(6)
    cols[0].metric("현재가", _money(q.get("price")), f"{change:+.2f}%" if isinstance(change, (int, float)) else None)
    cols[1].metric("시가총액", _number(info.get("marketCap")))
    cols[2].metric("Forward P/E", _number(info.get("forwardPE")))
    cols[3].metric("52주 고가", _money(info.get("fiftyTwoWeekHigh")))
    cols[4].metric("52주 저가", _money(info.get("fiftyTwoWeekLow")))
    cols[5].metric("거래량", _number(q.get("volume")))

    chart_data = history(ticker, "6mo", "1d")
    if not chart_data.empty and "Close" in chart_data:
        close = chart_data["Close"].dropna()
        if not close.empty:
            fig = go.Figure(go.Scatter(
                x=close.index, y=close.values, mode="lines",
                line={"width": 2, "color": tone},
                hovertemplate=f"<b>{ticker}</b><br>%{{x|%b %d, %Y}}<br>$%{{y:,.2f}}<extra></extra>",
            ))
            fig.update_layout(
                height=330, margin=dict(l=8, r=8, t=20, b=8),
                paper_bgcolor="#0c1828", plot_bgcolor="#0c1828",
                template="plotly_dark", xaxis_title=None, yaxis_title=None,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

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
                if isinstance(item, dict):
                    normalized.append(item)
                else:
                    normalized.append(str(item).upper())
            existing = {str(item.get("ticker", "")).upper() if isinstance(item, dict) else str(item).upper() for item in normalized}
            if ticker.upper() not in existing:
                normalized.append(ticker.upper())
                from utils.storage import save_json
                save_json("watchlist.json", normalized)
                st.success(f"{ticker}를 Watchlist에 추가했습니다.")
            else:
                st.info(f"{ticker}는 이미 Watchlist에 있습니다.")


def render():
    st.markdown('<div class="page-kicker">LIVE MARKET MAP · VERSION 3.00</div>', unsafe_allow_html=True)
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

        heatmap_fig = stock_heatmap(df, title)
        selected_ticker = st.session_state.get("heatmap_selected_ticker")
        if plotly_events is not None:
            clicks = plotly_events(
                heatmap_fig,
                click_event=True,
                hover_event=False,
                select_event=False,
                override_height=560,
                key=f"heatmap_click_{mode}_{title}",
            )
            if clicks:
                point = clicks[0]
                label = point.get("label") or point.get("text")
                if not label and point.get("pointNumber") is not None:
                    try:
                        label = str(df.iloc[int(point["pointNumber"])]["Ticker"])
                    except Exception:
                        label = None
                if label:
                    st.session_state["heatmap_selected_ticker"] = str(label).upper()
                    selected_ticker = str(label).upper()
        else:
            st.plotly_chart(heatmap_fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": False})
            selected_ticker = st.selectbox(
                "종목 상세 보기",
                ["선택하세요"] + df["Ticker"].astype(str).tolist(),
                key=f"heatmap_detail_select_{mode}_{title}",
            )
            if selected_ticker == "선택하세요":
                selected_ticker = None

        if selected_ticker and selected_ticker in set(df["Ticker"].astype(str).str.upper()):
            _render_ticker_detail(selected_ticker)

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
            config={"displaylogo": False},
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
