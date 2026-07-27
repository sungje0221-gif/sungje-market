import pandas as pd
import streamlit as st

from engine.portfolio import enrich
from engine.schwab import (
    SchwabError,
    account_summary,
    accounts_with_positions,
    clear_cache,
    connection_status,
    flatten_positions,
)
from utils.storage import load_csv, save_csv
from utils.formatters import money

COLS = ["Account", "Ticker", "Shares", "Avg Cost", "Category"]


def schwab_portfolio():
    status = connection_status()
    if not status["connected"]:
        st.info("Schwab Connection 메뉴에서 먼저 계좌를 연결하세요.")
        return

    c1, c2 = st.columns([5, 1])
    c1.caption("Schwab 계좌의 포지션과 잔액을 직접 불러옵니다.")
    if c2.button("Refresh", use_container_width=True):
        clear_cache()
        st.cache_data.clear()
        st.rerun()

    try:
        accounts = accounts_with_positions()
    except SchwabError as exc:
        st.error(str(exc))
        return

    positions = pd.DataFrame(flatten_positions(accounts))
    summaries = pd.DataFrame(account_summary(accounts))

    if not summaries.empty:
        st.markdown("### Account Summary")
        total_value = pd.to_numeric(summaries["Liquidation Value"], errors="coerce").sum()
        total_cash = pd.to_numeric(summaries["Cash"], errors="coerce").sum()
        buying_power = pd.to_numeric(summaries["Buying Power"], errors="coerce").sum()
        long_value = pd.to_numeric(summaries["Long Market Value"], errors="coerce").sum()

        c = st.columns(4)
        c[0].metric("Total Account Value", money(total_value))
        c[1].metric("Cash", money(total_cash))
        c[2].metric("Buying Power", money(buying_power))
        c[3].metric("Long Market Value", money(long_value))

        st.dataframe(
            summaries,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Liquidation Value": st.column_config.NumberColumn(format="$%.2f"),
                "Cash": st.column_config.NumberColumn(format="$%.2f"),
                "Cash Available": st.column_config.NumberColumn(format="$%.2f"),
                "Buying Power": st.column_config.NumberColumn(format="$%.2f"),
                "Long Market Value": st.column_config.NumberColumn(format="$%.2f"),
                "Short Market Value": st.column_config.NumberColumn(format="$%.2f"),
                "Day Trading Buying Power": st.column_config.NumberColumn(format="$%.2f"),
            },
        )

    if positions.empty:
        st.info("Schwab 계좌에서 포지션을 찾지 못했습니다.")
        return

    total_mv = positions["Market Value"].sum()
    total_cost = positions["Cost Basis"].sum()
    total_pl = positions["Unrealized P/L"].sum()
    total_day_pl = positions["Day P/L"].sum()
    total_return = (total_mv / total_cost - 1) * 100 if total_cost else 0

    st.markdown("### Live Positions")
    c = st.columns(4)
    c[0].metric("Position Value", money(total_mv))
    c[1].metric("Unrealized P/L", money(total_pl), f"{total_return:+.2f}%")
    c[2].metric("Today's P/L", money(total_day_pl))
    c[3].metric("Positions", len(positions))

    st.dataframe(
        positions[
            ["Account", "Ticker", "Description", "Shares", "Avg Cost",
             "Market Value", "Unrealized P/L", "Unrealized P/L %",
             "Day P/L", "Day P/L %"]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Shares": st.column_config.NumberColumn(format="%.4f"),
            "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
            "Market Value": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P/L": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Day P/L": st.column_config.NumberColumn(format="$%.2f"),
            "Day P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    concentration = positions.groupby("Ticker", as_index=False)["Market Value"].sum()
    concentration["Weight %"] = concentration["Market Value"] / concentration["Market Value"].sum() * 100
    concentration = concentration.sort_values("Weight %", ascending=False)
    st.markdown("### Concentration")
    st.bar_chart(concentration.set_index("Ticker")["Weight %"])

    largest = concentration.iloc[0]
    if largest["Weight %"] > 25:
        st.warning(f'{largest["Ticker"]} 비중이 {largest["Weight %"]:.1f}%로 높습니다.')


def manual_portfolio():
    df = load_csv("portfolio.csv", COLS)
    with st.expander("Add position", expanded=df.empty):
        with st.form("manual_position"):
            c = st.columns(5)
            acc = c[0].text_input("Account", "Taxable")
            ticker = c[1].text_input("Ticker").upper().strip()
            shares = c[2].number_input("Shares", min_value=0.0, step=1.0)
            avg = c[3].number_input("Avg Cost", min_value=0.0, step=.01)
            category = c[4].selectbox(
                "Category",
                ["ETF", "Mega Cap", "AI", "Semiconductor", "Power", "Defense", "Healthcare", "Other"],
            )
            if st.form_submit_button("Add") and ticker and shares > 0:
                new = pd.DataFrame([[acc, ticker, shares, avg, category]], columns=COLS)
                save_csv("portfolio.csv", pd.concat([df, new], ignore_index=True))
                st.rerun()

    if df.empty:
        st.info("No manual positions yet.")
        return

    e = enrich(df)
    st.dataframe(e, use_container_width=True, hide_index=True)


def csv_import():
    st.caption("Schwab 웹사이트에서 내려받은 Positions CSV를 분석합니다.")
    uploaded = st.file_uploader("Schwab Positions CSV", type=["csv"])
    if not uploaded:
        return
    try:
        raw = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"CSV를 읽지 못했습니다: {exc}")
        return
    st.dataframe(raw, use_container_width=True, hide_index=True)


def render():
    st.title("Portfolio")
    tab1, tab2, tab3 = st.tabs(["Charles Schwab Live", "Manual Portfolio", "CSV Import"])
    with tab1:
        schwab_portfolio()
    with tab2:
        manual_portfolio()
    with tab3:
        csv_import()
