from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from components.colored_tables import style_signed_columns
from engine.indicators import rsi_series, trend_score
from engine.market_data import history, quote
from engine.schwab import SchwabError, accounts_with_positions, connection_status, flatten_positions
from utils.formatters import money

PRIORITY = ["VOO", "VXF", "GOOGL", "CEG", "SKHY", "KORU", "QQQM", "SMH"]
PORTFOLIO_PATH = Path(__file__).resolve().parents[1] / "data" / "portfolio.csv"


def classify(symbol: str, description: str = "", asset_type: str = "") -> str:
    text = f"{symbol} {description} {asset_type}".upper()
    if symbol in {"VOO", "SPY", "QQQ", "QQQM", "VXF", "IJH", "IWM", "SCHD", "VYM", "DGRO"}:
        return "ETF"
    if any(x in text for x in ["GOOGL", "META", "MSFT", "AMZN", "AAPL", "NVDA", "AVGO", "AI", "SEMICONDUCTOR"]):
        return "AI / Mega Cap"
    if any(x in text for x in ["CEG", "VST", "NLR", "POWER", "UTILITY", "ENERGY"]):
        return "Power / Energy"
    if any(x in text for x in ["ITA", "KTOS", "DEFENSE", "AEROSPACE"]):
        return "Defense"
    if any(x in text for x in ["XLV", "ABBV", "UNH", "LLY", "HEALTH"]):
        return "Healthcare"
    if any(x in text for x in ["GLD", "SLV", "GOLD", "SILVER", "COPPER"]):
        return "Metals"
    return "Other"


def _signal(ticker: str) -> dict:
    frame = history(ticker, "1y", "1d")
    q = quote(ticker)
    if frame.empty or "Close" not in frame:
        return {"Ticker": ticker, "Price": q.get("price"), "Signal": "WAIT", "Score": 50, "RSI": None, "Reason": "가격 데이터 부족"}

    close = frame["Close"].dropna().astype(float)
    score = float(trend_score(frame) or 50)
    rsi = float(rsi_series(close).dropna().iloc[-1]) if len(close) >= 20 else None
    price = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else price
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else price
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else price

    if score >= 68 and price >= ma20 >= ma50 and (rsi is None or rsi < 72):
        signal = "BUY"
        reason = "상승 추세 유지 · 과열 전 분할매수 구간"
    elif score >= 55 and price >= ma50:
        signal = "HOLD"
        reason = "추세는 유효하지만 신규 추격보다 보유 우선"
    elif score < 38 or price < ma200:
        signal = "SELL"
        reason = "중장기 추세 훼손 · 비중 축소 검토"
    elif rsi is not None and rsi >= 72:
        signal = "TRIM"
        reason = "단기 과열 · 추가매수보다 일부 차익실현"
    else:
        signal = "WAIT"
        reason = "방향 확인 필요 · 지지선 부근까지 대기"

    return {
        "Ticker": ticker,
        "Price": q.get("price") or price,
        "Daily %": q.get("change_pct"),
        "Signal": signal,
        "Score": round(score),
        "RSI": round(rsi, 1) if rsi is not None else None,
        "Reason": reason,
    }


@st.cache_data(ttl=300, show_spinner=False)
def _advisor_table(tickers: tuple[str, ...]) -> pd.DataFrame:
    return pd.DataFrame([_signal(t) for t in tickers])


def _local_positions() -> pd.DataFrame:
    if not PORTFOLIO_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(PORTFOLIO_PATH)
    except Exception:
        return pd.DataFrame()
    if df.empty:
        return df
    rename = {c.lower().strip(): c for c in df.columns}
    ticker_col = rename.get("ticker") or rename.get("symbol")
    qty_col = rename.get("shares") or rename.get("quantity") or rename.get("qty")
    cost_col = rename.get("avg cost") or rename.get("average cost") or rename.get("cost basis")
    if not ticker_col:
        return pd.DataFrame()
    out = pd.DataFrame({"Ticker": df[ticker_col].astype(str).str.upper().str.strip()})
    out["Quantity"] = pd.to_numeric(df[qty_col], errors="coerce").fillna(0) if qty_col else 0
    out["Avg Cost"] = pd.to_numeric(df[cost_col], errors="coerce").fillna(0) if cost_col else 0
    rows = []
    for _, row in out.iterrows():
        q = quote(row["Ticker"])
        price = q.get("price") or 0
        market_value = float(row["Quantity"]) * float(price)
        cost_value = float(row["Quantity"]) * float(row["Avg Cost"])
        rows.append({
            "Ticker": row["Ticker"], "Description": "Local portfolio", "Asset Type": "",
            "Market Value": market_value, "Unrealized P/L": market_value - cost_value,
            "Unrealized P/L %": ((market_value / cost_value) - 1) * 100 if cost_value else 0,
        })
    return pd.DataFrame(rows)


def _positions() -> tuple[pd.DataFrame, str]:
    if connection_status().get("connected"):
        try:
            return pd.DataFrame(flatten_positions(accounts_with_positions())), "Schwab"
        except SchwabError:
            pass
    return _local_positions(), "Local CSV"


def render() -> None:
    st.markdown('<div class="page-kicker">AI ADVISOR 2.0 · VERSION 1.00</div>', unsafe_allow_html=True)
    st.title("Portfolio AI Advisor")
    st.caption("추세·RSI·이동평균을 결합한 규칙 기반 신호입니다. 매수는 항상 분할로 실행하세요.")

    st.markdown("### Priority Radar")
    signals = _advisor_table(tuple(PRIORITY))
    cols = st.columns(4)
    for idx, row in signals.iterrows():
        tone = {"BUY": "buy", "HOLD": "hold", "TRIM": "watch", "SELL": "avoid", "WAIT": "watch"}.get(row["Signal"], "watch")
        with cols[idx % 4]:
            st.markdown(
                f'''<div class="action-card {tone}"><div class="action-top"><div class="action-label">{row['Signal']}</div><span>{row['Score']}/100</span></div>
                <div style="font-size:20px;font-weight:900;margin-top:9px">{row['Ticker']} · {money(row['Price'])}</div>
                <div class="action-copy">{row['Reason']}<br><span style="color:#7f94aa">RSI {row['RSI'] if pd.notna(row['RSI']) else '—'} · Daily {row.get('Daily %', 0) or 0:+.2f}%</span></div></div>''',
                unsafe_allow_html=True,
            )

    st.markdown("### Signal Table")
    st.dataframe(
        signals,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "Daily %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "RSI": st.column_config.NumberColumn(format="%.1f"),
        },
    )

    positions, source = _positions()
    st.markdown(f"### Portfolio Snapshot · {source}")
    if positions.empty:
        st.info("Schwab을 연결하거나 data/portfolio.csv에 보유 종목을 입력하면 포트폴리오 비중 분석이 표시됩니다.")
        return

    positions["Category"] = positions.apply(lambda r: classify(str(r.get("Ticker", "")), str(r.get("Description", "")), str(r.get("Asset Type", ""))), axis=1)
    total = pd.to_numeric(positions["Market Value"], errors="coerce").fillna(0).sum()
    if total <= 0:
        st.info("유효한 포트폴리오 평가금액이 없습니다.")
        return
    positions["Weight %"] = pd.to_numeric(positions["Market Value"], errors="coerce").fillna(0) / total * 100
    largest = positions.sort_values("Weight %", ascending=False).iloc[0]
    allocation = positions.groupby("Category", as_index=False)["Market Value"].sum()
    allocation["Weight %"] = allocation["Market Value"] / total * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", money(total))
    c2.metric("Largest Position", largest["Ticker"], f'{largest["Weight %"]:.1f}%')
    c3.metric("ETF Weight", f'{allocation.loc[allocation["Category"] == "ETF", "Weight %"].sum():.1f}%')
    c4.metric("AI / Mega Cap", f'{allocation.loc[allocation["Category"] == "AI / Mega Cap", "Weight %"].sum():.1f}%')

    advisor_display = positions[["Ticker", "Description", "Category", "Market Value", "Weight %", "Unrealized P/L", "Unrealized P/L %"]].copy()
    st.dataframe(
        style_signed_columns(advisor_display, ["Unrealized P/L", "Unrealized P/L %"]),
        use_container_width=True, hide_index=True,
        column_config={
            "Market Value": st.column_config.NumberColumn(format="$%.2f"),
            "Weight %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            "Unrealized P/L": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )
