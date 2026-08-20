import pandas as pd
import streamlit as st
import yfinance as yf

from engine.portfolio import enrich
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
from components.colored_tables import style_signed_columns

COLS = ["Account", "Ticker", "Shares", "Avg Cost", "Category", "Sector", "Industry"]


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


@st.cache_data(ttl=86400, show_spinner=False)
def _security_profile(ticker: str) -> dict:
    """Best-effort sector/industry lookup. Manual values always remain editable."""
    try:
        info = yf.Ticker(ticker).get_info() or {}
        quote_type = str(info.get("quoteType") or "").upper()
        if quote_type in {"ETF", "MUTUALFUND"}:
            return {"Sector": "ETF / Fund", "Industry": str(info.get("category") or info.get("fundFamily") or "Diversified ETF")}
        return {
            "Sector": str(info.get("sector") or "Unknown"),
            "Industry": str(info.get("industry") or "Unknown"),
        }
    except Exception:
        return {"Sector": "Unknown", "Industry": "Unknown"}


def _portfolio_dashboard(e: pd.DataFrame, settings: dict):
    invested = float(e["Market Value"].sum())
    cash = float(settings.get("cash", 0))
    buying_power = float(settings.get("buying_power", 0))
    total_value = invested + cash
    total_cost = float(e["Cost Basis"].sum())
    total_pl = float(e["P/L"].sum())
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0.0
    day_pl = float((e["Shares"] * e.get("Day Change $", 0)).sum()) if "Day Change $" in e else 0.0
    cash_pct = cash / total_value * 100 if total_value else 0
    target_cash = float(settings.get("target_cash_pct", 20))
    top_weight = float(e["Weight %"].max()) if not e.empty else 0
    top3 = float(e.nlargest(3, "Weight %")["Weight %"].sum()) if len(e) else 0
    sectors = int(e["Sector"].replace("Unknown", pd.NA).dropna().nunique()) if "Sector" in e else 0
    risk = "HIGH" if top_weight >= 25 or top3 >= 60 else "MEDIUM" if top_weight >= 15 or top3 >= 45 else "LOW"

    c=st.columns(7)
    c[0].metric("Total Value", money(total_value))
    c[1].metric("Invested", money(invested))
    c[2].metric("Cash", money(cash), f"{cash_pct:.1f}%")
    c[3].metric("Buying Power", money(buying_power))
    c[4].metric("Total P/L", money(total_pl), f"{total_pl_pct:+.2f}%")
    c[5].metric("Today's P/L", money(day_pl))
    c[6].metric("Risk", risk)

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
        for _,r in weak.head(3).iterrows(): attention.append(("warning",f"{r['Ticker']} 누적 손실 {r['P/L %']:.1f}%"))
        if not attention: attention=[("success","현재 즉시 경고할 집중도·현금·손실 항목이 없습니다.")]
        for kind,text in attention: getattr(st,kind)(text)
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

    with st.expander("Cash / Buying Power", expanded=False):
        with st.form("portfolio_cash_settings"):
            c=st.columns(3)
            cash=c[0].number_input("Cash balance",min_value=0.0,value=float(settings.get("cash",0)),step=100.0)
            bp=c[1].number_input("Buying power",min_value=0.0,value=float(settings.get("buying_power",0)),step=100.0)
            target=c[2].number_input("Target cash %",min_value=0.0,max_value=100.0,value=float(settings.get("target_cash_pct",20)),step=1.0)
            if st.form_submit_button("Save cash settings",type="primary"):
                save_settings({"cash":cash,"buying_power":bp,"target_cash_pct":target}); st.rerun()

    categories=["Core ETF","Dividend ETF","Growth ETF","Sector ETF","Mega Cap","AI Software","Semiconductor","Cloud / Data Center","Cybersecurity","Power / Grid","Nuclear","Defense / Aerospace","Space","Healthcare","Financials","Consumer","Industrials","Materials / Mining","Energy","Real Estate","International","Speculative","Other"]
    sectors=["Auto detect","Communication Services","Consumer Discretionary","Consumer Staples","Energy","Financial Services","Healthcare","Industrials","Real Estate","Technology","Utilities","Basic Materials","ETF / Fund","Unknown"]
    with st.expander("Add / Edit position", expanded=df.empty):
        with st.form("manual_position"):
            c = st.columns(7)
            acc = c[0].text_input("Account", "Taxable")
            ticker = c[1].text_input("Ticker").upper().strip()
            shares = c[2].number_input("Shares", min_value=0.0, step=1.0)
            avg = c[3].number_input("Avg Cost", min_value=0.0, step=.01)
            category = c[4].selectbox("Strategy", categories)
            sector_choice = c[5].selectbox("Sector", sectors)
            industry_manual = c[6].text_input("Industry", "")
            if st.form_submit_button("Save position") and ticker and shares > 0:
                prof=_security_profile(ticker) if sector_choice=="Auto detect" else {"Sector":sector_choice,"Industry":industry_manual or "Unknown"}
                if industry_manual: prof["Industry"]=industry_manual
                keep=df[~((df["Account"]==acc)&(df["Ticker"]==ticker))]
                new=pd.DataFrame([[acc,ticker,shares,avg,category,prof["Sector"],prof["Industry"]]],columns=COLS)
                save_portfolio(pd.concat([keep,new],ignore_index=True)); st.rerun()

    if df.empty:
        st.info("No manual positions yet. CSV Import에서 불러오거나 직접 추가하세요.")
        return

    unknown=df[df["Sector"].isin(["Unknown",""]) ]
    if not unknown.empty and st.button(f"Auto-detect missing sectors ({len(unknown)})"):
        updated=df.copy()
        with st.spinner("Sector / industry 정보를 불러오는 중..."):
            for i,row in updated.iterrows():
                if row["Sector"] in ["Unknown",""]:
                    prof=_security_profile(row["Ticker"]); updated.at[i,"Sector"]=prof["Sector"]; updated.at[i,"Industry"]=prof["Industry"]
        save_portfolio(updated); st.rerun()

    e = enrich(df)
    _portfolio_dashboard(e, settings)
    st.markdown("### Holdings")
    display=e[[c for c in ["Account","Ticker","Shares","Avg Cost","Category","Sector","Industry","Current Price","Day %","Market Value","Cost Basis","P/L","P/L %","Weight %"] if c in e.columns]].copy()
    edited=st.data_editor(display,use_container_width=True,hide_index=True,disabled=["Current Price","Day %","Market Value","Cost Basis","P/L","P/L %","Weight %"],key="portfolio_holdings_editor")
    if st.button("Save holdings edits"):
        base=edited[["Account","Ticker","Shares","Avg Cost","Category","Sector","Industry"]].copy(); save_portfolio(base); st.rerun()

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
    category = st.selectbox("Default Strategy", ["Core ETF", "Dividend ETF", "Growth ETF", "Sector ETF", "Mega Cap", "AI Software", "Semiconductor", "Cloud / Data Center", "Cybersecurity", "Power / Grid", "Nuclear", "Defense / Aerospace", "Space", "Healthcare", "Financials", "Consumer", "Industrials", "Materials / Mining", "Energy", "Real Estate", "International", "Speculative", "Other"])
    auto_classify = st.checkbox("Auto-detect sector and industry", value=True)

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
