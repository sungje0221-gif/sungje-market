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
from utils.portfolio_store import load as load_portfolio, save as save_portfolio, status as portfolio_status, cloud_enabled
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


def _portfolio_dashboard(e: pd.DataFrame):
    total_value = float(e["Market Value"].sum())
    total_cost = float(e["Cost Basis"].sum())
    total_pl = float(e["P/L"].sum())
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0.0
    day_pl = float((e["Shares"] * e.get("Day Change $", 0)).sum()) if "Day Change $" in e else 0.0
    top_weight = float(e["Weight %"].max()) if not e.empty else 0
    top3 = float(e.nlargest(3, "Weight %")["Weight %"].sum()) if len(e) else 0
    categories = int(e["Category"].nunique())
    diversification = max(0, min(100, round(100 - max(0, top_weight-15)*1.7 - max(0, top3-45)*0.8 + min(categories,6)*2)))
    risk = "HIGH" if top_weight >= 25 or top3 >= 60 else "MEDIUM" if top_weight >= 15 or top3 >= 45 else "LOW"

    c=st.columns(6)
    c[0].metric("Total Value", money(total_value))
    c[1].metric("Total Cost", money(total_cost))
    c[2].metric("Total P/L", money(total_pl), f"{total_pl_pct:+.2f}%")
    c[3].metric("Today's P/L", money(day_pl))
    c[4].metric("Risk", risk)
    c[5].metric("Diversification", f"{diversification}/100")

    left,right=st.columns([1.35,1])
    with left:
        st.markdown("### Largest Holdings")
        alloc=e.groupby("Ticker",as_index=False)["Market Value"].sum().sort_values("Market Value",ascending=False)
        alloc["Weight %"]=alloc["Market Value"]/total_value*100 if total_value else 0
        st.bar_chart(alloc.head(10).set_index("Ticker")["Weight %"], horizontal=True)
    with right:
        st.markdown("### Portfolio Health")
        best=e.loc[e["P/L %"].idxmax()] if not e.empty else None
        worst=e.loc[e["P/L %"].idxmin()] if not e.empty else None
        notes=[]
        notes.append(("warning" if top_weight>20 else "success", f"Largest position: {e.loc[e['Weight %'].idxmax(),'Ticker']} {top_weight:.1f}%"))
        notes.append(("warning" if top3>55 else "success", f"Top 3 concentration: {top3:.1f}%"))
        notes.append(("info", f"Categories: {categories} · Positions: {len(e)}"))
        if best is not None: notes.append(("success", f"Best: {best['Ticker']} {best['P/L %']:+.1f}%"))
        if worst is not None: notes.append(("warning", f"Weakest: {worst['Ticker']} {worst['P/L %']:+.1f}%"))
        for kind,text in notes: getattr(st,kind)(text)

    st.markdown("### Allocation by Category")
    cat=e.groupby("Category",as_index=False)["Market Value"].sum().sort_values("Market Value",ascending=False)
    cat["Weight %"]=cat["Market Value"]/total_value*100 if total_value else 0
    st.bar_chart(cat.set_index("Category")["Weight %"], horizontal=True)


def manual_portfolio():
    df = load_portfolio()
    mode, backend = portfolio_status()
    st.caption(f"{mode} · {backend} · " + ("같은 Supabase profile로 접속하면 다른 기기에서도 유지됩니다." if cloud_enabled() else "현재는 로컬 저장이라 재배포 시 사라질 수 있습니다."))
    sync_error=st.session_state.get("portfolio_sync_error")
    if sync_error: st.error(f"Portfolio cloud sync failed: {sync_error}")

    with st.expander("Add / Edit position", expanded=df.empty):
        with st.form("manual_position"):
            c = st.columns(5)
            acc = c[0].text_input("Account", "Taxable")
            ticker = c[1].text_input("Ticker").upper().strip()
            shares = c[2].number_input("Shares", min_value=0.0, step=1.0)
            avg = c[3].number_input("Avg Cost", min_value=0.0, step=.01)
            category = c[4].selectbox("Category", ["ETF", "Mega Cap", "AI", "Semiconductor", "Power", "Defense", "Healthcare", "Other"])
            if st.form_submit_button("Save position") and ticker and shares > 0:
                keep=df[~((df["Account"]==acc)&(df["Ticker"]==ticker))]
                new=pd.DataFrame([[acc,ticker,shares,avg,category]],columns=COLS)
                save_portfolio(pd.concat([keep,new],ignore_index=True)); st.rerun()

    if df.empty:
        st.info("No manual positions yet. CSV Import에서 불러오거나 직접 추가하세요.")
        return

    e = enrich(df)
    _portfolio_dashboard(e)
    st.markdown("### Holdings")
    display=e[[c for c in ["Account","Ticker","Shares","Avg Cost","Category","Current Price","Day %","Market Value","Cost Basis","P/L","P/L %","Weight %"] if c in e.columns]].copy()
    st.dataframe(style_signed_columns(display,["Day %","P/L","P/L %"]),use_container_width=True,hide_index=True)

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
    category = st.selectbox("Default Category", ["ETF", "Mega Cap", "AI", "Semiconductor", "Power", "Defense", "Healthcare", "Other"])

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
    tab1, tab2, tab3 = st.tabs(["Charles Schwab Live", "Manual Portfolio", "CSV Import"])
    with tab1:
        schwab_portfolio()
    with tab2:
        manual_portfolio()
    with tab3:
        csv_import()
