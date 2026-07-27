import pandas as pd
import streamlit as st

from engine.schwab import SchwabError, accounts_with_positions, connection_status, flatten_positions
from utils.formatters import money


def classify(symbol, description, asset_type):
    text = f"{symbol} {description} {asset_type}".upper()
    if symbol in {"VOO","SPY","QQQ","QQQM","VXF","IJH","IWM","SCHD","VYM","DGRO"}:
        return "ETF"
    if any(x in text for x in ["GOOGL","META","MSFT","AMZN","AAPL","NVDA","AVGO","AI","SEMICONDUCTOR"]):
        return "AI / Mega Cap"
    if any(x in text for x in ["CEG","VST","NLR","POWER","UTILITY","ENERGY"]):
        return "Power / Energy"
    if any(x in text for x in ["ITA","KTOS","DEFENSE","AEROSPACE"]):
        return "Defense"
    if any(x in text for x in ["XLV","ABBV","UNH","LLY","HEALTH"]):
        return "Healthcare"
    if any(x in text for x in ["GLD","SLV","GOLD","SILVER","COPPER"]):
        return "Metals"
    return "Other"


def render():
    st.title("Portfolio AI Advisor")

    if not connection_status()["connected"]:
        st.info("Schwab Connection 메뉴에서 계좌를 연결하면 자동 분석됩니다.")
        return

    try:
        positions = pd.DataFrame(flatten_positions(accounts_with_positions()))
    except SchwabError as exc:
        st.error(str(exc))
        return

    if positions.empty:
        st.info("분석할 포지션이 없습니다.")
        return

    positions["Category"] = positions.apply(
        lambda r: classify(r["Ticker"], r["Description"], r["Asset Type"]), axis=1
    )

    total = positions["Market Value"].sum()
    positions["Weight %"] = positions["Market Value"] / total * 100

    allocation = positions.groupby("Category", as_index=False)["Market Value"].sum()
    allocation["Weight %"] = allocation["Market Value"] / total * 100
    allocation = allocation.sort_values("Weight %", ascending=False)

    largest = positions.sort_values("Weight %", ascending=False).iloc[0]
    ai_weight = allocation.loc[allocation["Category"] == "AI / Mega Cap", "Weight %"].sum()
    etf_weight = allocation.loc[allocation["Category"] == "ETF", "Weight %"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio Value", money(total))
    c2.metric("Largest Position", largest["Ticker"], f'{largest["Weight %"]:.1f}%')
    c3.metric("AI / Mega Cap", f"{ai_weight:.1f}%")
    c4.metric("ETF Weight", f"{etf_weight:.1f}%")

    st.markdown("### Allocation")
    st.bar_chart(allocation.set_index("Category")["Weight %"])

    st.markdown("### Advisor")
    messages = []
    if largest["Weight %"] > 25:
        messages.append(f'{largest["Ticker"]} 비중이 {largest["Weight %"]:.1f}%로 높습니다. 추가매수보다 분산을 우선하세요.')
    if ai_weight > 45:
        messages.append(f'AI·메가캡 비중이 {ai_weight:.1f}%입니다. Power, Healthcare 또는 broad ETF로 분산하는 편이 좋습니다.')
    if etf_weight < 20:
        messages.append(f'ETF 비중이 {etf_weight:.1f}%로 낮습니다. VOO, VXF, IJH 같은 코어 자산을 늘리면 변동성이 줄어듭니다.')
    if not messages:
        messages.append("현재 포트폴리오는 한쪽으로 심하게 치우치지 않았습니다. 신규 매수는 기존 비중보다 시장 상황을 우선 보세요.")

    for message in messages:
        st.info(message)

    st.markdown("### Position Weights")
    st.dataframe(
        positions[["Ticker","Description","Category","Market Value","Weight %","Unrealized P/L","Unrealized P/L %"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Market Value": st.column_config.NumberColumn(format="$%.2f"),
            "Weight %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            "Unrealized P/L": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )
