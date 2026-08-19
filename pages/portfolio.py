import os
import uuid
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from engine.portfolio import enrich
from engine.market_data import batch_quotes, history, intraday_history, quote
from engine.fundamentals import ticker_info
from components.charts import advanced_chart
from engine.schwab import (
    SchwabError,
    account_summary,
    accounts_with_positions,
    clear_cache,
    connection_status,
    flatten_positions,
)
from utils.portfolio_store import (load as load_portfolio, save as save_portfolio, status as portfolio_status, cloud_enabled, load_settings, save_settings)
from utils.formatters import money
from utils.export import excel_download_button
from components.colored_tables import style_signed_columns

COLS = ["Account", "Ticker", "Shares", "Avg Cost", "Category", "Sector", "Industry"]

STRATEGIES = [
    "Core ETF", "Broad Market ETF", "Dividend ETF", "Covered Call ETF",
    "Growth ETF", "Sector ETF", "International ETF", "Bond ETF",
    "Commodity ETF", "Leveraged ETF", "Inverse ETF",
    "Mega Cap", "AI Software", "AI Infrastructure", "Cloud / Data Center",
    "Cybersecurity", "Networking", "Semiconductor - Memory",
    "Semiconductor - Equipment", "Semiconductor - Foundry",
    "Semiconductor - Design", "Power / Grid", "Utilities", "Nuclear",
    "Oil & Gas", "Defense / Aerospace", "Space", "Drone / Robotics",
    "Healthcare", "Pharma", "Medical Devices", "Biotech",
    "Financials", "Insurance", "Payments / Fintech", "Consumer Staples",
    "Consumer Discretionary", "Retail", "Industrials",
    "Materials / Mining", "Gold", "Silver", "Real Estate",
    "Speculative", "Other",
]

TRANSACTION_COLS = [
    "ID", "Date", "Account", "Action", "Ticker", "Shares",
    "Price", "Cost Basis", "Fee", "Notes",
]
TRANSACTIONS_PATH = Path("data") / "transactions.csv"


def _empty_transactions() -> pd.DataFrame:
    return pd.DataFrame(columns=TRANSACTION_COLS)


def _load_transactions() -> pd.DataFrame:
    """Load the local transaction ledger. The CSV is created on first save."""
    try:
        if not TRANSACTIONS_PATH.exists():
            return _empty_transactions()
        df = pd.read_csv(TRANSACTIONS_PATH, dtype={"ID": str, "Account": str, "Action": str, "Ticker": str, "Notes": str})
    except Exception as exc:
        st.session_state["transactions_load_error"] = str(exc)
        return _empty_transactions()

    for col in TRANSACTION_COLS:
        if col not in df.columns:
            df[col] = "" if col in {"ID", "Date", "Account", "Action", "Ticker", "Notes"} else 0.0
    for col in ["Shares", "Price", "Cost Basis", "Fee"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date.astype(str)
    df["Action"] = df["Action"].astype(str).str.upper().str.strip()
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Account"] = df["Account"].astype(str).str.strip()
    df["ID"] = df["ID"].astype(str)
    return df[TRANSACTION_COLS].copy()


def _save_transactions(df: pd.DataFrame) -> None:
    TRANSACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean = df.copy()
    for col in TRANSACTION_COLS:
        if col not in clean.columns:
            clean[col] = "" if col in {"ID", "Date", "Account", "Action", "Ticker", "Notes"} else 0.0
    clean = clean[TRANSACTION_COLS]
    clean.to_csv(TRANSACTIONS_PATH, index=False)


def _transaction_calculations(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate cash flow and FIFO realized P/L by account and ticker.

    SELL rows consume earlier BUY lots in FIFO order. When a SELL predates the
    transaction ledger or exceeds recorded BUY lots, the row's Cost Basis value
    is used only for the unmatched shares as an opening-position fallback.
    """
    calc = df.copy()
    extra_cols = [
        "Gross Amount", "Net Cash Flow", "FIFO Cost Basis", "Matched Shares",
        "Unmatched Shares", "Realized P/L", "Return %", "Open Shares",
        "Open Cost Basis",
    ]
    if calc.empty:
        for col in extra_cols:
            calc[col] = pd.Series(dtype=float)
        return calc

    calc = calc.reset_index(drop=True)
    calc["_row_order"] = range(len(calc))
    calc["_date_sort"] = pd.to_datetime(calc["Date"], errors="coerce")
    for col in ["Shares", "Price", "Cost Basis", "Fee"]:
        calc[col] = pd.to_numeric(calc[col], errors="coerce").fillna(0.0)

    calc["Gross Amount"] = calc["Shares"] * calc["Price"]
    calc["Net Cash Flow"] = 0.0
    calc["FIFO Cost Basis"] = 0.0
    calc["Matched Shares"] = 0.0
    calc["Unmatched Shares"] = 0.0
    calc["Realized P/L"] = 0.0
    calc["Return %"] = 0.0
    calc["Open Shares"] = 0.0
    calc["Open Cost Basis"] = 0.0

    lots: dict[tuple[str, str], list[dict[str, float]]] = {}
    ordered = calc.sort_values(["_date_sort", "_row_order"], kind="stable")

    for idx, row in ordered.iterrows():
        action = str(row["Action"]).upper().strip()
        key = (str(row["Account"]).strip(), str(row["Ticker"]).upper().strip())
        shares = max(float(row["Shares"]), 0.0)
        price = max(float(row["Price"]), 0.0)
        fee = max(float(row["Fee"]), 0.0)
        gross = shares * price
        book = lots.setdefault(key, [])

        if action == "BUY":
            unit_cost = ((gross + fee) / shares) if shares > 0 else 0.0
            book.append({"shares": shares, "unit_cost": unit_cost})
            calc.at[idx, "Net Cash Flow"] = -(gross + fee)
        elif action == "SELL":
            remaining = shares
            matched = 0.0
            fifo_basis_total = 0.0

            while remaining > 1e-9 and book:
                lot = book[0]
                used = min(remaining, lot["shares"])
                fifo_basis_total += used * lot["unit_cost"]
                matched += used
                lot["shares"] -= used
                remaining -= used
                if lot["shares"] <= 1e-9:
                    book.pop(0)

            fallback_basis = max(float(row["Cost Basis"]), 0.0)
            if remaining > 1e-9 and fallback_basis > 0:
                fifo_basis_total += remaining * fallback_basis

            proceeds = gross - fee
            realized = proceeds - fifo_basis_total
            basis_shares = matched + (remaining if fallback_basis > 0 else 0.0)
            effective_basis = fifo_basis_total / basis_shares if basis_shares > 0 else 0.0

            calc.at[idx, "Net Cash Flow"] = proceeds
            calc.at[idx, "FIFO Cost Basis"] = effective_basis
            calc.at[idx, "Matched Shares"] = matched
            calc.at[idx, "Unmatched Shares"] = remaining
            calc.at[idx, "Realized P/L"] = realized
            calc.at[idx, "Return %"] = (realized / fifo_basis_total * 100) if fifo_basis_total > 0 else 0.0

        open_shares = sum(lot["shares"] for lot in book)
        open_basis_total = sum(lot["shares"] * lot["unit_cost"] for lot in book)
        calc.at[idx, "Open Shares"] = open_shares
        calc.at[idx, "Open Cost Basis"] = open_basis_total / open_shares if open_shares > 0 else 0.0

    return calc.drop(columns=["_row_order", "_date_sort"])

def _realized_pl_total() -> float:
    tx = _transaction_calculations(_load_transactions())
    return float(tx["Realized P/L"].sum()) if not tx.empty else 0.0


def _default_cost_basis(account: str, ticker: str) -> float:
    holdings = load_portfolio()
    if holdings.empty:
        return 0.0
    match = holdings[
        holdings["Account"].astype(str).eq(str(account))
        & holdings["Ticker"].astype(str).str.upper().eq(str(ticker).upper())
    ]
    if match.empty:
        return 0.0
    return float(pd.to_numeric(match.iloc[0]["Avg Cost"], errors="coerce") or 0.0)


def _apply_transaction_to_holdings(account: str, action: str, ticker: str, shares: float, price: float) -> tuple[bool, str]:
    """Apply a transaction to Manual Portfolio without touching Schwab live data."""
    df = load_portfolio().copy()
    ticker = ticker.upper().strip()
    account = account.strip()
    mask = df["Account"].astype(str).eq(account) & df["Ticker"].astype(str).str.upper().eq(ticker) if not df.empty else pd.Series(dtype=bool)

    if action == "BUY":
        if not df.empty and mask.any():
            idx = df.index[mask][0]
            old_shares = float(df.at[idx, "Shares"])
            old_avg = float(df.at[idx, "Avg Cost"])
            new_shares = old_shares + shares
            new_avg = ((old_shares * old_avg) + (shares * price)) / new_shares if new_shares else 0.0
            df.at[idx, "Shares"] = new_shares
            df.at[idx, "Avg Cost"] = new_avg
        else:
            prof = _security_profile(ticker)
            new = pd.DataFrame([[
                account, ticker, shares, price, _suggest_strategy(ticker, prof),
                prof.get("Sector", "Unknown"), prof.get("Industry", "Unknown"),
            ]], columns=COLS)
            df = pd.concat([df, new], ignore_index=True)
        save_portfolio(df)
        return True, "Manual Portfolio의 수량과 평균단가를 업데이트했습니다."

    if df.empty or not mask.any():
        return False, "Manual Portfolio에서 해당 계좌/종목을 찾지 못했습니다."
    idx = df.index[mask][0]
    old_shares = float(df.at[idx, "Shares"])
    if shares > old_shares + 1e-9:
        return False, f"보유 수량 {old_shares:g}주보다 많이 매도할 수 없습니다."
    remaining = old_shares - shares
    if remaining <= 1e-9:
        df = df.drop(index=idx).reset_index(drop=True)
    else:
        df.at[idx, "Shares"] = remaining
    save_portfolio(df)
    return True, "Manual Portfolio의 보유 수량을 업데이트했습니다."


def transactions_page():
    st.caption("매수·매도 거래를 기록하고 FIFO 방식으로 실현손익을 계산합니다. 거래내역은 data/transactions.csv에 저장됩니다.")
    load_error = st.session_state.pop("transactions_load_error", None)
    if load_error:
        st.error(f"거래내역을 읽지 못했습니다: {load_error}")

    tx = _load_transactions()
    holdings = load_portfolio()
    account_options = sorted(set(holdings["Account"].astype(str))) if not holdings.empty else ["Taxable"]
    if not account_options:
        account_options = ["Taxable"]

    with st.expander("Add transaction", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        tx_date = c1.date_input("Date", value=date.today(), key="tx_date")
        account = c2.selectbox("Account", account_options + ["Other..."], key="tx_account")
        custom_account = c2.text_input("Other account", "", key="tx_custom_account") if account == "Other..." else ""
        action = c3.selectbox("Action", ["BUY", "SELL"], key="tx_action")
        ticker = c4.text_input("Ticker", key="tx_ticker").upper().strip()

        c5, c6, c7, c8 = st.columns(4)
        shares = c5.number_input("Shares", min_value=0.0, step=1.0, format="%.4f", key="tx_shares")
        price = c6.number_input("Transaction price", min_value=0.0, step=0.01, format="%.4f", key="tx_price")
        resolved_account = custom_account.strip() if account == "Other..." else account
        suggested_basis = _default_cost_basis(resolved_account, ticker) if action == "SELL" and ticker else price
        basis = c7.number_input(
            "Opening cost basis / share", min_value=0.0, value=float(suggested_basis), step=0.01, format="%.4f",
            help="FIFO 매수기록이 부족한 매도분에만 사용되는 보조 원가입니다. 기존 보유분을 처음 기록할 때 유용합니다.",
            key=f"tx_basis_{action}_{ticker}_{resolved_account}",
        )
        fee = c8.number_input("Fee", min_value=0.0, step=0.01, format="%.2f", key="tx_fee")
        notes = st.text_input("Notes", key="tx_notes")
        update_holdings = st.checkbox("Also update Manual Portfolio holdings", value=True, key="tx_update_holdings")

        if st.button("Save transaction", type="primary", use_container_width=True):
            if not resolved_account:
                st.error("Account를 입력하세요.")
            elif not ticker:
                st.error("Ticker를 입력하세요.")
            elif shares <= 0 or price <= 0:
                st.error("Shares와 Transaction price는 0보다 커야 합니다.")
            elif action == "SELL" and basis <= 0:
                st.error("SELL 거래에는 Cost basis / share가 필요합니다.")
            else:
                if update_holdings:
                    ok, message = _apply_transaction_to_holdings(resolved_account, action, ticker, shares, price)
                    if not ok:
                        st.error(message)
                        st.stop()
                row = pd.DataFrame([[
                    uuid.uuid4().hex, tx_date.isoformat(), resolved_account, action, ticker,
                    shares, price, price if action == "BUY" else basis, fee, notes.strip(),
                ]], columns=TRANSACTION_COLS)
                _save_transactions(pd.concat([tx, row], ignore_index=True))
                st.success("거래를 저장했습니다." + (f" {message}" if update_holdings else ""))
                st.rerun()

    calc = _transaction_calculations(tx)
    sells = calc[calc["Action"].eq("SELL")].copy() if not calc.empty else calc.copy()
    total_buys = float(calc.loc[calc["Action"].eq("BUY"), "Gross Amount"].sum()) if not calc.empty else 0.0
    total_sales = float(calc.loc[calc["Action"].eq("SELL"), "Gross Amount"].sum()) if not calc.empty else 0.0
    realized = float(sells["Realized P/L"].sum()) if not sells.empty else 0.0
    winners = int((sells["Realized P/L"] > 0).sum()) if not sells.empty else 0
    win_rate = winners / len(sells) * 100 if len(sells) else 0.0

    m = st.columns(5)
    m[0].metric("Buy Amount", money(total_buys))
    m[1].metric("Sell Amount", money(total_sales))
    m[2].metric("Realized P/L", money(realized))
    m[3].metric("Sell Trades", len(sells))
    m[4].metric("Win Rate", f"{win_rate:.1f}%")

    if tx.empty:
        st.info("아직 저장된 거래가 없습니다.")
        return

    st.markdown("### Transaction History")
    display_cols = ["Date", "Account", "Action", "Ticker", "Shares", "Price", "FIFO Cost Basis", "Fee", "Gross Amount", "Realized P/L", "Return %", "Unmatched Shares", "Notes"]
    history = calc.sort_values(["Date", "ID"], ascending=[False, False])[display_cols].copy()
    st.dataframe(
        style_signed_columns(history, ["Realized P/L", "Return %"]),
        use_container_width=True, hide_index=True,
        column_config={
            "Shares": st.column_config.NumberColumn(format="%.4f"),
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "FIFO Cost Basis": st.column_config.NumberColumn(format="$%.2f"),
            "Fee": st.column_config.NumberColumn(format="$%.2f"),
            "Gross Amount": st.column_config.NumberColumn(format="$%.2f"),
            "Realized P/L": st.column_config.NumberColumn(format="$%.2f"),
            "Return %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    if not sells.empty:
        st.markdown("### Realized P/L by Ticker")
        by_ticker = sells.groupby("Ticker", as_index=False).agg(
            **{"Sell Trades": ("Ticker", "size"), "Shares Sold": ("Shares", "sum"), "Realized P/L": ("Realized P/L", "sum")}
        ).sort_values("Realized P/L", ascending=False)
        st.dataframe(style_signed_columns(by_ticker, ["Realized P/L"]), use_container_width=True, hide_index=True)

    with st.expander("Delete transactions"):
        labels = {
            f"{r.Date} · {r.Account} · {r.Action} · {r.Ticker} · {r.Shares:g} @ ${r.Price:,.2f} · {str(r.ID)[:8]}": r.ID
            for r in tx.itertuples(index=False)
        }
        selected = st.multiselect("Select transactions to delete", list(labels.keys()))
        st.warning("거래 삭제는 Transaction History에서만 제거합니다. 이미 반영된 Manual Portfolio 보유수량은 자동으로 되돌리지 않습니다.")
        if st.button("Delete selected transactions", disabled=not selected):
            delete_ids = {labels[label] for label in selected}
            _save_transactions(tx[~tx["ID"].isin(delete_ids)].reset_index(drop=True))
            st.rerun()


POSITION_CHART_RANGES = {"1D": "1d", "5D": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
POSITION_CANDLES_BY_RANGE = {
    "1D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "5D": ["1m", "2m", "5m", "15m", "30m", "60m", "1d"],
    "1M": ["5m", "15m", "30m", "60m", "1d"],
    "3M": ["60m", "1d"],
    "6M": ["1d"],
    "1Y": ["1d"],
    "5Y": ["1d"],
}
POSITION_DEFAULT_CANDLE = {"1D": "1m", "5D": "5m", "1M": "60m", "3M": "1d", "6M": "1d", "1Y": "1d", "5Y": "1d"}


def _position_detail(ticker: str, row: pd.Series, state_key: str = "portfolio_selected_ticker") -> None:
    """Same chart pattern as Heatmap/Earnings/AI Center, plus this account's actual position numbers."""
    q = quote(ticker)
    info = ticker_info(ticker)
    company = info.get("shortName") or info.get("longName") or ticker

    header_left, header_right = st.columns([5, 1])
    with header_left:
        st.markdown(f"#### {ticker} · {company}")
    with header_right:
        if st.button("닫기", key=f"close_pos_detail_{state_key}_{ticker}", use_container_width=True):
            st.session_state.pop(state_key, None)
            st.rerun()

    cols = st.columns(6)
    cols[0].metric("현재가", money(q.get("price")), None if q.get("change_pct") is None else f'{q["change_pct"]:+.2f}%')
    cols[1].metric("보유수량", f'{row["Shares"]:g}')
    cols[2].metric("평단가", money(row["Avg Cost"]))
    cols[3].metric("평가금액", money(row["Market Value"]))
    pl_value = row.get("Unrealized P/L", row.get("P/L"))
    pl_pct = row.get("Unrealized P/L %", row.get("P/L %"))
    cols[4].metric("평가손익", money(pl_value), None if pl_pct is None else f'{pl_pct:+.2f}%')
    cols[5].metric("계좌 내 비중", f'{row["Weight %"]:.1f}%')

    range_col, candle_col = st.columns([2, 1])
    with range_col:
        range_label = st.radio("기간", list(POSITION_CHART_RANGES), horizontal=True, index=5, key=f"pos_range_{state_key}_{ticker}")
    candle_options = POSITION_CANDLES_BY_RANGE[range_label]
    with candle_col:
        interval = st.selectbox(
            "봉", candle_options, index=candle_options.index(POSITION_DEFAULT_CANDLE[range_label]),
            key=f"pos_candle_{state_key}_{ticker}_{range_label}",
        )
    period = POSITION_CHART_RANGES[range_label]
    is_intraday = interval.endswith("m") or interval.endswith("h")
    chart_data = intraday_history(ticker, period, interval) if is_intraday else history(ticker, period, interval)

    if not chart_data.empty:
        from utils.formatters import period_return
        pr = period_return(chart_data)
        if pr is not None:
            st.metric(f"{range_label} 수익률", f"{pr:+.2f}%")
        st.plotly_chart(
            advanced_chart(
                chart_data, ticker,
                show_ma20=True, show_ma50=not is_intraday, show_ma100=False,
                show_ma200=not is_intraday, show_bollinger=False, show_volume=True,
                show_rsi=not is_intraday, show_macd=False, intraday=is_intraday,
            ),
            use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False},
        )
    else:
        st.warning(f"{ticker}의 {range_label} / {interval} 데이터가 없습니다. 다른 봉을 선택하세요.")


SECTORS = [
    "Auto detect", "Communication Services", "Consumer Discretionary",
    "Consumer Staples", "Energy", "Financial Services", "Healthcare",
    "Industrials", "Real Estate", "Technology", "Utilities",
    "Basic Materials", "ETF / Fund", "Unknown",
]


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

    if positions.empty:
        st.info("Schwab 계좌에서 포지션을 찾지 못했습니다.")
        return

    with st.spinner("종목별 섹터 · 전략 분류 중..."):
        profiles = {t: _security_profile(t) for t in positions["Ticker"].dropna().unique()}
    positions["Sector"] = positions["Ticker"].map(lambda t: profiles.get(t, {}).get("Sector", "Unknown"))
    positions["Category"] = positions["Ticker"].map(lambda t: _suggest_strategy(t, profiles.get(t, {})))

    shares_safe = positions["Shares"].replace(0, pd.NA)
    # Schwab's own positions endpoint (currentDayProfitLoss / -Percentage) is
    # unreliable for options and for any lot traded earlier the same day, and
    # can show wildly wrong day-change numbers as a result. Live quotes (the
    # same source Heatmap/Watchlist already use successfully) are trustworthy
    # for regular equities/ETFs, so prefer those and only fall back to
    # Schwab's own math for tickers a normal quote lookup can't resolve
    # (mainly option contracts).
    equity_tickers = tuple(
        t for t in positions["Ticker"].dropna().unique()
        if " " not in str(t) and str(t).isascii()
    )
    quotes = batch_quotes(equity_tickers) if equity_tickers else {}

    def _current_price(row):
        q = quotes.get(row["Ticker"], {})
        return q.get("price") if q.get("price") is not None else (row["Market Value"] / row["Shares"] if row["Shares"] else 0)

    def _day_pct(row):
        q = quotes.get(row["Ticker"], {})
        return q.get("change_pct") if q.get("change_pct") is not None else row["Day P/L %"]

    def _day_change_dollar(row):
        q = quotes.get(row["Ticker"], {})
        if q.get("change_abs") is not None:
            return q["change_abs"]
        return row["Day P/L"] / row["Shares"] if row["Shares"] else 0

    positions["Current Price"] = positions.apply(_current_price, axis=1)
    positions["Day %"] = positions.apply(_day_pct, axis=1)
    positions["Day Change $"] = positions.apply(_day_change_dollar, axis=1)
    positions["Weight %"] = positions["Market Value"] / positions["Market Value"].sum() * 100 if positions["Market Value"].sum() else 0

    from pages.ai_center import _radar as _ai_radar
    equity_only = tuple(t for t in positions["Ticker"].dropna().unique() if " " not in str(t) and str(t).isascii())
    signal_map = _ai_radar(equity_only).set_index("Ticker")["Signal"].to_dict() if equity_only else {}
    positions["Signal"] = positions["Ticker"].map(signal_map).fillna("—")

    dashboard_df = positions.rename(columns={
        "Unrealized P/L": "P/L",
        "Unrealized P/L %": "P/L %",
    })

    total_cash = pd.to_numeric(summaries["Cash"], errors="coerce").sum() if not summaries.empty else 0.0
    total_buying_power = pd.to_numeric(summaries["Buying Power"], errors="coerce").sum() if not summaries.empty else 0.0
    settings = {"cash": float(total_cash), "buying_power": float(total_buying_power), "target_cash_pct": 10}

    st.markdown("### All Accounts — Overview & Signals")
    st.caption("아래 경고/제안은 규칙 기반입니다 (집중도, 현금 비중, 손실 종목 감지). Manual Portfolio와 동일한 로직을 씁니다.")
    _portfolio_dashboard(dashboard_df, settings, realized_pl=0.0, key_prefix="schwab")

    if not summaries.empty:
        st.divider()
        st.markdown("### Account Balances")
        st.dataframe(
            summaries,
            use_container_width=True,
            hide_index=True,
            key="schwab_account_balances_table",
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

    st.divider()
    st.markdown("### Positions by Account")
    position_cols = [
        "Ticker", "Signal", "Shares", "Current Price", "Day %", "Day Change $", "Weight %",
        "Description", "Avg Cost", "Market Value", "Unrealized P/L", "Unrealized P/L %",
        "Sector", "Category",
    ]
    for account_number in sorted(positions["Account"].dropna().unique()):
        sub = positions[positions["Account"] == account_number].copy()
        sub["Weight %"] = sub["Market Value"] / sub["Market Value"].sum() * 100 if sub["Market Value"].sum() else 0
        header = f"Account {account_number}  ·  {money(sub['Market Value'].sum())}  ·  {len(sub)} positions"
        with st.expander(header, expanded=True):
            sub_display = sub[position_cols].sort_values("Weight %", ascending=False)
            sub_style = style_signed_columns(
                sub_display, ["Unrealized P/L", "Unrealized P/L %", "Day Change $", "Day %"]
            )
            event = st.dataframe(
                sub_style,
                use_container_width=True,
                hide_index=True,
                key=f"positions_table_{account_number}",
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Shares": st.column_config.NumberColumn(format="%.4f"),
                    "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
                    "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                    "Weight %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Unrealized P/L": st.column_config.NumberColumn(format="$%.2f"),
                    "Unrealized P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Day Change $": st.column_config.NumberColumn("Day Change $", format="%+.2f"),
                    "Day %": st.column_config.NumberColumn("Day %", format="%+.2f%%"),
                },
            )
            rows_selected = (event or {}).get("selection", {}).get("rows", []) if hasattr(event, "get") else []
            if rows_selected:
                clicked_ticker = str(sub_display.iloc[rows_selected[0]]["Ticker"])
                st.session_state["portfolio_selected_ticker_schwab"] = clicked_ticker
                st.session_state["portfolio_selected_row_schwab"] = sub_display.iloc[rows_selected[0]].to_dict()
            excel_download_button(sub_display, f"schwab_{account_number}_positions", key=f"xl_schwab_{account_number}")

    selected_ticker = st.session_state.get("portfolio_selected_ticker_schwab")
    if selected_ticker and st.session_state.get("portfolio_selected_row_schwab"):
        st.divider()
        _position_detail(selected_ticker, pd.Series(st.session_state["portfolio_selected_row_schwab"]), state_key="portfolio_selected_ticker_schwab")


@st.cache_data(ttl=86400, show_spinner=False)
def _security_profile(ticker: str) -> dict:
    """Best-effort classification lookup. Manual edits always take priority."""
    try:
        info = yf.Ticker(ticker).get_info() or {}
        quote_type = str(info.get("quoteType") or "").upper()
        if quote_type in {"ETF", "MUTUALFUND"}:
            industry = str(info.get("category") or info.get("fundFamily") or "Diversified ETF")
            return {
                "Sector": "ETF / Fund",
                "Industry": industry,
                "Quote Type": quote_type,
            }
        return {
            "Sector": str(info.get("sector") or "Unknown"),
            "Industry": str(info.get("industry") or "Unknown"),
            "Quote Type": quote_type or "EQUITY",
        }
    except Exception:
        return {"Sector": "Unknown", "Industry": "Unknown", "Quote Type": "Unknown"}


def _suggest_strategy(ticker: str, profile: dict) -> str:
    text = f"{ticker} {profile.get('Sector', '')} {profile.get('Industry', '')}".lower()
    if profile.get("Sector") == "ETF / Fund":
        if any(k in text for k in ["leveraged", "2x", "3x", "ultra"]): return "Leveraged ETF"
        if any(k in text for k in ["inverse", "short"]): return "Inverse ETF"
        if any(k in text for k in ["covered call", "buywrite", "income"]): return "Covered Call ETF"
        if any(k in text for k in ["dividend", "value"]): return "Dividend ETF"
        if any(k in text for k in ["bond", "treasury", "fixed income"]): return "Bond ETF"
        if any(k in text for k in ["gold", "silver", "commodity"]): return "Commodity ETF"
        if any(k in text for k in ["international", "emerging", "korea", "china", "europe"]): return "International ETF"
        if any(k in text for k in ["growth", "nasdaq", "technology"]): return "Growth ETF"
        return "Broad Market ETF"
    if "semiconductor" in text or "chip" in text:
        if any(k in text for k in ["memory", "dram", "nand"]): return "Semiconductor - Memory"
        if any(k in text for k in ["equipment", "wafer", "lithography"]): return "Semiconductor - Equipment"
        if any(k in text for k in ["foundry", "fabrication"]): return "Semiconductor - Foundry"
        return "Semiconductor - Design"
    if any(k in text for k in ["artificial intelligence", "software", "application software"]): return "AI Software"
    if any(k in text for k in ["data center", "server", "electrical equipment"]): return "AI Infrastructure"
    if "cyber" in text: return "Cybersecurity"
    if any(k in text for k in ["network", "communication equipment"]): return "Networking"
    if any(k in text for k in ["aerospace", "defense"]): return "Defense / Aerospace"
    if any(k in text for k in ["space", "satellite"]): return "Space"
    if any(k in text for k in ["utility", "electric", "power", "grid"]): return "Power / Grid"
    if "nuclear" in text or "uranium" in text: return "Nuclear"
    if profile.get("Sector") == "Healthcare": return "Healthcare"
    if profile.get("Sector") == "Financial Services": return "Financials"
    if profile.get("Sector") == "Consumer Staples": return "Consumer Staples"
    if profile.get("Sector") == "Consumer Discretionary": return "Consumer Discretionary"
    if profile.get("Sector") == "Industrials": return "Industrials"
    if profile.get("Sector") == "Basic Materials": return "Materials / Mining"
    if profile.get("Sector") == "Energy": return "Oil & Gas"
    if profile.get("Sector") == "Real Estate": return "Real Estate"
    return "Other"


def _portfolio_dashboard(e: pd.DataFrame, settings: dict, realized_pl: float = 0.0, key_prefix: str = "default"):
    invested = float(e["Market Value"].sum())
    cash = float(settings.get("cash", 0))
    buying_power = float(settings.get("buying_power", 0))
    total_value = invested + cash
    total_cost = float(e["Cost Basis"].sum())
    unrealized_pl = float(e["P/L"].sum())
    total_pl = unrealized_pl + realized_pl
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0.0
    day_pl = float((e["Shares"] * e.get("Day Change $", 0)).sum()) if "Day Change $" in e else 0.0
    cash_pct = cash / total_value * 100 if total_value else 0
    target_cash = float(settings.get("target_cash_pct", 20))
    top_weight = float(e["Weight %"].max()) if not e.empty else 0
    top3 = float(e.nlargest(3, "Weight %")["Weight %"].sum()) if len(e) else 0
    sectors = int(e["Sector"].replace("Unknown", pd.NA).dropna().nunique()) if "Sector" in e else 0
    risk = "HIGH" if top_weight >= 25 or top3 >= 60 else "MEDIUM" if top_weight >= 15 or top3 >= 45 else "LOW"

    c=st.columns(8)
    c[0].metric("Total Value", money(total_value))
    c[1].metric("Invested", money(invested))
    c[2].metric("Cash", money(cash), f"{cash_pct:.1f}%")
    c[3].metric("Buying Power", money(buying_power))
    c[4].metric("Unrealized P/L", money(unrealized_pl))
    c[5].metric("Realized P/L", money(realized_pl))
    c[6].metric("Total P/L", money(total_pl), f"{total_pl_pct:+.2f}%")
    c[7].metric("Risk", risk)
    st.caption(f"Today's P/L: {money(day_pl)}")

    if key_prefix != "manual":
        st.markdown("### Today's Changes")
        movers=e.sort_values("Day %", ascending=True).copy() if "Day %" in e else e.copy()
        movers=movers[[c for c in ["Ticker","Current Price","Day %","Day Change $","Market Value","Weight %"] if c in movers.columns]]
        st.dataframe(style_signed_columns(movers,["Day %","Day Change $"]),use_container_width=True,hide_index=True,height=min(330,38*(len(movers)+1)))

    left,right=st.columns([1.2,1])
    with left:
        st.markdown("### Need Attention")
        attention=[]
        if top_weight > 20:
            row=e.loc[e["Weight %"].idxmax()]; attention.append(("warning",f"{row['Ticker']} 비중 {row['Weight %']:.1f}% — 단일 종목 집중도가 높습니다."))
        if top3 > 55: attention.append(("warning",f"상위 3종목 비중 {top3:.1f}% — 포트폴리오가 몇 종목에 몰려 있습니다."))
        if cash_pct < target_cash-5: attention.append(("warning",f"현금 {cash_pct:.1f}% — 목표 {target_cash:.1f}%보다 낮습니다."))
        elif cash_pct > target_cash+10: attention.append(("info",f"현금 {cash_pct:.1f}% — 목표보다 높아 매수 여력이 큽니다."))
        weak=e[e["P/L %"] <= -10].sort_values("P/L %") if "P/L %" in e else pd.DataFrame()
        # Schwab's cost basis can be wash-sale adjusted, which distorts
        # displayed P/L % and makes a "누적 손실" warning misleading (it may
        # not reflect real economic loss). Manual Portfolio's cost basis is
        # entered directly by the user, so it stays a reliable warning there.
        if key_prefix != "schwab":
            for _,r in weak.head(3).iterrows(): attention.append(("warning",f"{r['Ticker']} 누적 손실 {r['P/L %']:.1f}%"))
        if not attention: attention=[("success","현재 즉시 경고할 집중도·현금 항목이 없습니다." if key_prefix=="schwab" else "현재 즉시 경고할 집중도·현금·손실 항목이 없습니다.")]
        for kind,text in attention: getattr(st,kind)(text)

        if key_prefix == "schwab" and not weak.empty:
            with st.expander(f"참고 — 평가손익 -10% 이하 종목 {len(weak)}개 (Wash Sale 영향 가능)"):
                st.caption("Schwab의 평단가는 wash sale 규정으로 조정될 수 있어, 아래 손익률이 실제 매수 대비 손익과 다를 수 있습니다. 그래서 위 경고 목록에는 포함하지 않았습니다.")
                st.dataframe(
                    weak[["Ticker","P/L %"]],
                    use_container_width=True, hide_index=True,
                    column_config={"P/L %": st.column_config.NumberColumn(format="%+.1f%%")},
                )

        from engine.claude_advisor import configured as _ai_configured, ask as _ai_ask
        if _ai_configured():
            attn_key = "|".join(t for _, t in attention)
            if st.button("🤖 AI 리밸런싱 조언", key=f"ai_rebalance_btn_{key_prefix}"):
                top_holdings = e.nlargest(8, "Weight %")[["Ticker", "Weight %", "P/L %"]] if "Weight %" in e and "P/L %" in e else pd.DataFrame()
                holdings_text = "\n".join(
                    f"- {r['Ticker']}: 비중 {r['Weight %']:.1f}%, 손익 {r['P/L %']:+.1f}%"
                    for _, r in top_holdings.iterrows()
                ) if not top_holdings.empty else "보유 종목 정보 없음"
                attention_text = "\n".join(f"- {t}" for _, t in attention)
                system = (
                    "너는 개인 투자 대시보드에 내장된 한국어 포트폴리오 리밸런싱 어시스턴트다. "
                    "제공된 규칙 기반 경고와 보유 비중만 근거로, 실제로 어떤 순서로 무엇부터 조정하면 좋을지 "
                    "3~5개의 구체적이고 실행 가능한 제안을 우선순위 순으로 작성해라. "
                    "확정적 지시가 아니라 근거와 함께 제안하는 톤을 유지해라."
                )
                user = f"규칙 기반 경고:\n{attention_text}\n\n비중 상위 보유종목:\n{holdings_text}\n\n리밸런싱 조언을 작성해줘."
                with st.spinner("AI 조언 생성 중..."):
                    st.session_state[f"ai_rebalance_text_{key_prefix}"] = _ai_ask(system, user, max_tokens=1400)
                    st.session_state[f"ai_rebalance_key_{key_prefix}"] = attn_key
            if st.session_state.get(f"ai_rebalance_text_{key_prefix}"):
                with st.expander("🤖 AI 리밸런싱 제안", expanded=True):
                    st.markdown(st.session_state[f"ai_rebalance_text_{key_prefix}"])
    with right:
        st.markdown("### Target vs Current")
        comp=pd.DataFrame({"Allocation":["Invested","Cash"],"Current %":[100-cash_pct,cash_pct],"Target %":[100-target_cash,target_cash]})
        st.dataframe(comp,use_container_width=True,hide_index=True)
        gap=cash-target_cash/100*total_value
        if abs(gap) >= 100:
            if gap>0: st.info(f"현금 목표를 맞추려면 약 {money(gap)}를 투자할 수 있습니다.")
            else: st.warning(f"현금 목표를 맞추려면 약 {money(abs(gap))}를 확보해야 합니다.")

    a,b=st.columns(2)
    with a:
        st.markdown("### Allocation by Sector")
        sec=e.groupby("Sector",as_index=False)["Market Value"].sum().sort_values("Market Value",ascending=False)
        sec["Weight %"]=sec["Market Value"]/invested*100 if invested else 0
        st.bar_chart(sec.set_index("Sector")["Weight %"], horizontal=True)
    with b:
        st.markdown("### Allocation by Strategy")
        cat=e.groupby("Category",as_index=False)["Market Value"].sum().sort_values("Market Value",ascending=False)
        cat["Weight %"]=cat["Market Value"]/invested*100 if invested else 0
        st.bar_chart(cat.set_index("Category")["Weight %"], horizontal=True)


def manual_portfolio():
    df = load_portfolio()
    settings = load_settings()
    mode, backend = portfolio_status()
    st.caption(f"{mode} · {backend} · " + ("같은 Supabase profile로 접속하면 다른 기기에서도 유지됩니다." if cloud_enabled() else "현재는 로컬 저장이라 재배포 시 사라질 수 있습니다."))
    sync_error=st.session_state.get("portfolio_sync_error")
    if sync_error: st.error(f"Portfolio cloud sync failed: {sync_error}")
    settings_error=st.session_state.get("portfolio_settings_sync_error")
    if settings_error: st.error(f"Cash settings sync failed: {settings_error}")

    with st.expander("Cash / Buying Power", expanded=True):
        with st.form("portfolio_cash_settings"):
            c=st.columns(3)
            cash=c[0].number_input("Cash balance",min_value=0.0,value=float(settings.get("cash",0)),step=100.0)
            bp=c[1].number_input("Buying power",min_value=0.0,value=float(settings.get("buying_power",0)),step=100.0)
            target=c[2].number_input("Target cash %",min_value=0.0,max_value=100.0,value=float(settings.get("target_cash_pct",20)),step=1.0)
            if st.form_submit_button("Save cash settings",type="primary"):
                save_settings({"cash":cash,"buying_power":bp,"target_cash_pct":target}); st.rerun()

    if df.empty:
        st.info("No manual positions yet. CSV Import에서 불러오거나 직접 추가하세요.")
        with st.expander("종목 추가", expanded=True):
            with st.form("manual_position_first"):
                c = st.columns(7)
                acc = c[0].text_input("Account", "Taxable")
                ticker = c[1].text_input("Ticker").upper().strip()
                shares = c[2].number_input("Shares", min_value=0.0, step=1.0)
                avg = c[3].number_input("Avg Cost", min_value=0.0, step=.01)
                category = c[4].selectbox("Strategy", STRATEGIES)
                sector_choice = c[5].selectbox("Sector", SECTORS)
                industry_manual = c[6].text_input("Industry", "")
                if st.form_submit_button("Save position") and ticker and shares > 0:
                    prof=_security_profile(ticker) if sector_choice=="Auto detect" else {"Sector":sector_choice,"Industry":industry_manual or "Unknown"}
                    if industry_manual:
                        prof["Industry"] = industry_manual
                    final_category = _suggest_strategy(ticker, prof) if category == "Other" and sector_choice == "Auto detect" else category
                    new=pd.DataFrame([[acc,ticker,shares,avg,final_category,prof["Sector"],prof["Industry"]]],columns=COLS)
                    save_portfolio(new); st.rerun()
        return

    unknown=df[df["Sector"].isin(["Unknown",""]) ]
    b1, b2 = st.columns(2)
    if not unknown.empty and b1.button(f"Auto-detect missing classifications ({len(unknown)})", use_container_width=True):
        updated=df.copy()
        with st.spinner("Sector / industry 정보를 불러오는 중..."):
            for i,row in updated.iterrows():
                if row["Sector"] in ["Unknown",""]:
                    prof=_security_profile(row["Ticker"])
                    updated.at[i,"Sector"] = prof["Sector"]
                    updated.at[i,"Industry"] = prof["Industry"]
                    if row["Category"] in ["Other", "", None]:
                        updated.at[i,"Category"] = _suggest_strategy(row["Ticker"], prof)
        save_portfolio(updated); st.rerun()
    if b2.button("Refresh all sector / industry data", use_container_width=True):
        updated=df.copy()
        with st.spinner("전체 종목 분류 정보를 새로 불러오는 중..."):
            for i,row in updated.iterrows():
                prof=_security_profile(row["Ticker"])
                updated.at[i,"Sector"] = prof["Sector"]
                updated.at[i,"Industry"] = prof["Industry"]
                if row["Category"] in ["Other", "", None]:
                    updated.at[i,"Category"] = _suggest_strategy(row["Ticker"], prof)
        save_portfolio(updated); st.rerun()

    e = enrich(df)
    from pages.ai_center import _radar as _ai_radar_manual
    equity_only_manual = tuple(t for t in e["Ticker"].dropna().unique() if " " not in str(t) and str(t).isascii())
    signal_map_manual = _ai_radar_manual(equity_only_manual).set_index("Ticker")["Signal"].to_dict() if equity_only_manual else {}
    e["Signal"] = e["Ticker"].map(signal_map_manual).fillna("—")
    _portfolio_dashboard(e, settings, _realized_pl_total(), key_prefix="manual")

    st.markdown("### Holdings")
    holding_cols = [
        "Ticker", "Signal", "Shares", "Current Price", "Day %", "Avg Cost",
        "Market Value", "Cost Basis", "P/L", "P/L %", "Weight %",
        "Category", "Sector", "Industry",
    ]
    holding_cols = [c for c in holding_cols if c in e.columns]
    for account_name in sorted(e["Account"].dropna().unique()) if "Account" in e else []:
        sub = e[e["Account"] == account_name].copy()
        if "Weight %" in sub and sub["Market Value"].sum():
            sub["Weight %"] = sub["Market Value"] / sub["Market Value"].sum() * 100
        header = f"{account_name}  ·  {money(sub['Market Value'].sum()) if 'Market Value' in sub else ''}  ·  {len(sub)} positions"
        with st.expander(header, expanded=True):
            sub_display = sub[holding_cols].sort_values("Weight %", ascending=False) if "Weight %" in sub else sub[holding_cols]
            sub_style = style_signed_columns(sub_display, [c for c in ["Day %", "P/L", "P/L %"] if c in sub_display.columns])
            event = st.dataframe(
                sub_style,
                use_container_width=True,
                hide_index=True,
                key=f"manual_holdings_table_{account_name}",
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Shares": st.column_config.NumberColumn(format="%.4f"),
                    "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                    "Day %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
                    "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                    "Cost Basis": st.column_config.NumberColumn(format="$%.2f"),
                    "P/L": st.column_config.NumberColumn(format="$%.2f"),
                    "P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
                    "Weight %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Category": st.column_config.Column("Strategy"),
                },
            )
            rows_selected = (event or {}).get("selection", {}).get("rows", []) if hasattr(event, "get") else []
            if rows_selected:
                clicked_ticker = str(sub_display.iloc[rows_selected[0]]["Ticker"])
                st.session_state["portfolio_selected_ticker_manual"] = clicked_ticker
                st.session_state["portfolio_selected_row_manual"] = sub_display.iloc[rows_selected[0]].to_dict()
            excel_download_button(sub_display, f"manual_{account_name}_holdings", key=f"xl_manual_{account_name}")

    selected_ticker = st.session_state.get("portfolio_selected_ticker_manual")
    if selected_ticker and st.session_state.get("portfolio_selected_row_manual"):
        st.divider()
        _position_detail(selected_ticker, pd.Series(st.session_state["portfolio_selected_row_manual"]), state_key="portfolio_selected_ticker_manual")

    with st.expander("Holdings 편집 (수량/평단가/분류) · 종목 추가 · 삭제", expanded=False):
        st.caption("표 안의 셀을 클릭해서 수량, 평단가, 분류를 직접 수정할 수 있습니다.")
        display=e[[c for c in ["Account","Ticker","Signal","Shares","Avg Cost","Category","Sector","Industry","Current Price","Day %","Market Value","Cost Basis","P/L","P/L %","Weight %"] if c in e.columns]].copy()
        edited=st.data_editor(
            display,
            use_container_width=True,
            hide_index=True,
            disabled=["Signal","Current Price","Day %","Market Value","Cost Basis","P/L","P/L %","Weight %"],
            column_config={
                "Category": st.column_config.SelectboxColumn("Strategy", options=STRATEGIES),
                "Sector": st.column_config.SelectboxColumn("Sector", options=[x for x in SECTORS if x != "Auto detect"]),
                "Shares": st.column_config.NumberColumn(format="%.4f"),
                "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Current Price": st.column_config.NumberColumn(format="$%.2f"),
                "Day %": st.column_config.NumberColumn(format="%+.2f%%"),
                "Market Value": st.column_config.NumberColumn(format="$%.2f"),
                "P/L": st.column_config.NumberColumn(format="$%.2f"),
                "P/L %": st.column_config.NumberColumn(format="%+.2f%%"),
                "Weight %": st.column_config.NumberColumn(format="%.2f%%"),
            },
            key="portfolio_holdings_editor",
        )
        if st.button("변경사항 저장", type="primary"):
            base=edited[["Account","Ticker","Shares","Avg Cost","Category","Sector","Industry"]].copy(); save_portfolio(base); st.rerun()

        st.divider()
        st.markdown("##### 새 종목 추가")
        with st.form("manual_position"):
            c = st.columns(7)
            acc = c[0].text_input("Account", "Taxable")
            ticker = c[1].text_input("Ticker").upper().strip()
            shares = c[2].number_input("Shares", min_value=0.0, step=1.0)
            avg = c[3].number_input("Avg Cost", min_value=0.0, step=.01)
            category = c[4].selectbox("Strategy", STRATEGIES)
            sector_choice = c[5].selectbox("Sector", SECTORS)
            industry_manual = c[6].text_input("Industry", "")
            if st.form_submit_button("종목 추가") and ticker and shares > 0:
                prof=_security_profile(ticker) if sector_choice=="Auto detect" else {"Sector":sector_choice,"Industry":industry_manual or "Unknown"}
                if industry_manual:
                    prof["Industry"] = industry_manual
                final_category = _suggest_strategy(ticker, prof) if category == "Other" and sector_choice == "Auto detect" else category
                keep=df[~((df["Account"]==acc)&(df["Ticker"]==ticker))]
                new=pd.DataFrame([[acc,ticker,shares,avg,final_category,prof["Sector"],prof["Industry"]]],columns=COLS)
                save_portfolio(pd.concat([keep,new],ignore_index=True)); st.rerun()

    with st.expander("Manage positions"):
        remove=st.multiselect("Delete positions", [f"{r.Account} · {r.Ticker}" for r in df.itertuples()])
        if st.button("Delete selected", disabled=not remove):
            keys=set(tuple(x.split(" · ",1)) for x in remove)
            keep=df[[ (r["Account"],r["Ticker"]) not in keys for _,r in df.iterrows() ]]
            save_portfolio(keep); st.rerun()

def _clean_csv_number(series: pd.Series) -> pd.Series:
    """Convert brokerage-formatted money/quantity text into numbers."""
    cleaned = (
        series.astype(str)
        .str.strip()
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .replace({"--": None, "N/A": None, "nan": None, "None": None, "": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _read_broker_csv(uploaded) -> tuple[pd.DataFrame, str]:
    """Read normal CSVs and Schwab exports that begin with report-title rows."""
    payload = uploaded.getvalue()
    last_error = None

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = payload.decode(encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
    else:
        raise ValueError(f"지원하지 않는 CSV 문자 인코딩입니다: {last_error}")

    lines = text.splitlines()
    if not lines:
        raise ValueError("CSV 파일이 비어 있습니다.")

    # Schwab exports commonly start with a title such as
    # 'Positions for account ... as of ...' before the real header row.
    aliases = {
        "symbol", "ticker", "quantity", "qty", "shares", "cost basis",
        "average price", "avg cost", "price", "market value", "description",
    }
    header_row = 0
    best_score = -1
    for idx, line in enumerate(lines[:40]):
        cells = [c.strip().strip('"').lower() for c in line.split(",")]
        score = sum(any(alias == cell or alias in cell for alias in aliases) for cell in cells)
        has_symbol = any("symbol" in cell or "ticker" in cell for cell in cells)
        has_qty = any("quantity" in cell or cell == "qty" or "shares" in cell for cell in cells)
        if has_symbol and has_qty and score > best_score:
            header_row = idx
            best_score = score

    from io import StringIO
    try:
        frame = pd.read_csv(StringIO(text), skiprows=header_row, dtype=str)
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    # Remove fully empty columns/rows and Schwab footer rows.
    frame = frame.dropna(axis=1, how="all").dropna(axis=0, how="all")
    frame.columns = [str(c).strip() for c in frame.columns]
    if frame.empty or len(frame.columns) < 2:
        raise ValueError("실제 포지션 헤더 행을 찾지 못했습니다.")

    first_col = frame.columns[0]
    frame = frame[
        ~frame[first_col].astype(str).str.strip().str.lower().isin(
            {"account total", "cash & cash investments", "cash", "total", "nan", "none", ""}
        )
    ]
    return frame.reset_index(drop=True), f"header row {header_row + 1}"


def csv_import():
    st.caption("Schwab 또는 다른 증권사 CSV를 불러와 수동 포트폴리오 형식으로 저장합니다.")
    uploaded = st.file_uploader("Positions CSV", type=["csv"])
    if not uploaded:
        return

    try:
        raw, parse_note = _read_broker_csv(uploaded)
    except Exception as exc:
        st.error(f"CSV를 읽지 못했습니다: {exc}")
        return

    st.success(f"CSV 구조를 인식했습니다 · {parse_note} · {len(raw)} rows")
    st.dataframe(raw, use_container_width=True, hide_index=True)
    columns = list(raw.columns)
    if not columns:
        st.warning("CSV에 열이 없습니다.")
        return

    def guess(names, fallback=0):
        lowered = [str(c).lower().strip() for c in columns]
        # Exact/strong matches first so Schwab 'Price' is not mistaken for average cost.
        for name in names:
            for idx, key in enumerate(lowered):
                if key == name:
                    return idx
        for name in names:
            for idx, key in enumerate(lowered):
                if name in key:
                    return idx
        return min(fallback, len(columns) - 1)

    st.markdown("#### Column Mapping")
    c1, c2, c3, c4 = st.columns(4)
    ticker_col = c1.selectbox(
        "Ticker / Symbol",
        columns,
        index=guess(["symbol", "ticker"]),
    )
    shares_col = c2.selectbox(
        "Shares / Quantity",
        columns,
        index=guess(["quantity", "qty", "shares"]),
    )
    cost_col = c3.selectbox(
        "Average Cost / Cost Basis",
        columns,
        index=guess(["average price", "avg price", "avg cost", "cost basis per share", "cost basis"]),
    )
    account_col = c4.selectbox("Account (optional)", ["(Use Manual)"] + columns)
    manual_account = st.text_input("Default Account", "Taxable")
    category = st.selectbox("Default Strategy", STRATEGIES, index=STRATEGIES.index("Other"))
    auto_classify = st.checkbox("Auto-detect sector, industry, and strategy", value=True)

    cost_mode = st.radio(
        "Cost column meaning",
        ["Average cost per share", "Total cost basis"],
        horizontal=True,
        help="Schwab CSV의 Cost Basis가 총 취득원가라면 'Total cost basis'를 선택하세요.",
    )

    if st.button("Import into Manual Portfolio", type="primary", use_container_width=True):
        ticker = raw[ticker_col].astype(str).str.upper().str.strip()
        shares = _clean_csv_number(raw[shares_col]).fillna(0)
        cost_values = _clean_csv_number(raw[cost_col]).fillna(0)
        avg_cost = cost_values
        if cost_mode == "Total cost basis":
            avg_cost = cost_values.div(shares.replace(0, pd.NA)).fillna(0)

        converted = pd.DataFrame({
            "Ticker": ticker,
            "Shares": shares,
            "Avg Cost": avg_cost,
        })
        converted["Account"] = raw[account_col].astype(str).str.strip() if account_col != "(Use Manual)" else manual_account
        converted["Category"] = category
        converted["Sector"] = "Unknown"
        converted["Industry"] = "Unknown"
        if auto_classify:
            with st.spinner("Sector / industry 정보를 자동 분류하는 중..."):
                profiles = {t: _security_profile(t) for t in converted["Ticker"].dropna().unique()}
            converted["Sector"] = converted["Ticker"].map(lambda t: profiles.get(t, {}).get("Sector", "Unknown"))
            converted["Industry"] = converted["Ticker"].map(lambda t: profiles.get(t, {}).get("Industry", "Unknown"))
            if category == "Other":
                converted["Category"] = converted["Ticker"].map(lambda t: _suggest_strategy(t, profiles.get(t, {})))

        # Exclude totals, cash rows, option descriptions, and malformed symbols.
        invalid_symbols = {"", "NAN", "NONE", "ACCOUNT TOTAL", "CASH", "CASH & CASH INVESTMENTS"}
        converted = converted[
            ~converted["Ticker"].isin(invalid_symbols)
            & converted["Shares"].gt(0)
            & converted["Ticker"].str.match(r"^[A-Z0-9.\-/^]+$", na=False)
        ]
        converted = converted[COLS].reset_index(drop=True)

        if converted.empty:
            st.error("가져올 수 있는 유효한 포지션이 없습니다. 위 매핑에서 Symbol, Quantity, Cost Basis 열을 다시 확인하세요.")
        else:
            st.markdown("#### Import Preview")
            st.dataframe(converted, use_container_width=True, hide_index=True)
            existing = load_portfolio()
            save_portfolio(pd.concat([existing, converted], ignore_index=True))
            st.success(f"{len(converted)}개 포지션을 저장했습니다. Manual Portfolio 탭에서 확인하세요.")


def render():
    st.title("Portfolio")
    tab1, tab2, tab3, tab4 = st.tabs(["Charles Schwab Live", "Manual Portfolio", "Transactions", "CSV Import"])
    with tab1:
        schwab_portfolio()
    with tab2:
        manual_portfolio()
    with tab3:
        transactions_page()
    with tab4:
        csv_import()
