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
from components.colored_tables import style_signed_columns

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

    live_display = positions[
        ["Account", "Ticker", "Description", "Shares", "Avg Cost",
         "Market Value", "Unrealized P/L", "Unrealized P/L %",
         "Day P/L", "Day P/L %"]
    ].copy()
    live_style = style_signed_columns(
        live_display,
        ["Unrealized P/L", "Unrealized P/L %", "Day P/L", "Day P/L %"],
    )
    st.dataframe(
        live_style,
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
    manual_style = style_signed_columns(e, ["P/L", "P/L %"])
    st.dataframe(manual_style, use_container_width=True, hide_index=True)


def csv_import():
    st.caption("Schwab 또는 다른 증권사 CSV를 불러와 수동 포트폴리오 형식으로 저장합니다.")
    uploaded = st.file_uploader("Positions CSV", type=["csv"])
    if not uploaded:
        return
    try:
        raw = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"CSV를 읽지 못했습니다: {exc}")
        return

    st.dataframe(raw, use_container_width=True, hide_index=True)
    columns = list(raw.columns)
    if not columns:
        st.warning("CSV에 열이 없습니다.")
        return

    def guess(names, fallback=0):
        lowered = {str(c).lower().strip(): i for i, c in enumerate(columns)}
        for name in names:
            for key, idx in lowered.items():
                if name in key:
                    return idx
        return fallback

    st.markdown("#### Column Mapping")
    c1, c2, c3, c4 = st.columns(4)
    ticker_col = c1.selectbox("Ticker / Symbol", columns, index=guess(["symbol", "ticker"]))
    shares_col = c2.selectbox("Shares / Quantity", columns, index=guess(["quantity", "shares", "qty"]))
    cost_col = c3.selectbox("Average Cost", columns, index=guess(["average price", "avg cost", "price", "cost"]))
    account_col = c4.selectbox("Account (optional)", ["(Use Manual)"] + columns)
    manual_account = st.text_input("Default Account", "Taxable")
    category = st.selectbox("Default Category", ["ETF", "Mega Cap", "AI", "Semiconductor", "Power", "Defense", "Healthcare", "Other"])

    if st.button("Import into Manual Portfolio", type="primary", use_container_width=True):
        converted = pd.DataFrame({
            "Ticker": raw[ticker_col].astype(str).str.upper().str.strip(),
            "Shares": pd.to_numeric(raw[shares_col], errors="coerce").fillna(0),
            "Avg Cost": pd.to_numeric(raw[cost_col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False), errors="coerce").fillna(0),
        })
        converted["Account"] = raw[account_col].astype(str) if account_col != "(Use Manual)" else manual_account
        converted["Category"] = category
        converted = converted[converted["Ticker"].ne("") & converted["Shares"].gt(0)]
        converted = converted[COLS]
        if converted.empty:
            st.error("가져올 수 있는 유효한 포지션이 없습니다.")
        else:
            existing = load_csv("portfolio.csv", COLS)
            save_csv("portfolio.csv", pd.concat([existing, converted], ignore_index=True))
            st.success(f"{len(converted)}개 포지션을 저장했습니다.")


def render():
    st.title("Portfolio")
    tab1, tab2, tab3 = st.tabs(["Charles Schwab Live", "Manual Portfolio", "CSV Import"])
    with tab1:
        schwab_portfolio()
    with tab2:
        manual_portfolio()
    with tab3:
        csv_import()
