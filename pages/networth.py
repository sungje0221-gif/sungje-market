from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from utils.formatters import money
from utils.storage import load_cloud_json, save_cloud_json, cloud_configured

BANK_COLS = ["Institution", "Account Name", "Type", "Balance", "Updated"]
ACCOUNT_TYPES = ["Checking", "Savings", "Money Market", "CD", "Credit Card (negative)", "Other"]
ET = ZoneInfo("America/New_York")


def _et_today_str() -> str:
    """Current date in US Eastern Time, matching Schwab's own trading-day
    boundary. Snapshots keyed by server/local date instead would risk an
    after-hours price move landing on the wrong day whenever local midnight
    and ET midnight don't line up."""
    return datetime.now(ET).strftime("%Y-%m-%d")


def _load_snapshots() -> pd.DataFrame:
    rows = load_cloud_json("networth_snapshots", [])
    if not rows:
        return pd.DataFrame(columns=["Date", "Bank", "Investment", "NetWorth"])
    df = pd.DataFrame(rows)
    for col in ["Bank", "Investment", "NetWorth"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.sort_values("Date")


def _upsert_snapshot(bank_total: float, invest_total: float) -> None:
    """Overwrite today's (ET) snapshot with the latest totals. Since the app
    only runs on-demand rather than as a background service, this naturally
    settles to whatever the last visit of the day saw -- closest thing to an
    end-of-day mark without needing a scheduled job."""
    today = _et_today_str()
    rows = load_cloud_json("networth_snapshots", [])
    rows = [r for r in rows if r.get("Date") != today]
    rows.append({"Date": today, "Bank": bank_total, "Investment": invest_total, "NetWorth": bank_total + invest_total})
    save_cloud_json("networth_snapshots", rows)


def _load_cashflows() -> pd.DataFrame:
    rows = load_cloud_json("networth_cashflows", [])
    if not rows:
        return pd.DataFrame(columns=["Date", "Amount", "Note"])
    df = pd.DataFrame(rows)
    if "Amount" in df:
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    return df.sort_values("Date")


def _add_cashflow(amount: float, note: str) -> tuple[bool, str | None]:
    rows = load_cloud_json("networth_cashflows", [])
    rows.append({"Date": _et_today_str(), "Amount": amount, "Note": note})
    return save_cloud_json("networth_cashflows", rows)


def _load_bank_accounts() -> pd.DataFrame:
    rows = load_cloud_json("bank_accounts", [])
    if not rows:
        return pd.DataFrame(columns=BANK_COLS)
    return pd.DataFrame(rows, columns=BANK_COLS)


def _save_bank_accounts(df: pd.DataFrame) -> tuple[bool, str | None]:
    return save_cloud_json("bank_accounts", df.to_dict("records"))


def _investment_total() -> tuple[float, str]:
    """Investment total from Schwab if connected (live, most accurate),
    otherwise Manual Portfolio. Never both, to avoid double-counting."""
    try:
        from engine.schwab import connection_status, accounts_with_positions, account_summary
        if connection_status().get("connected"):
            summaries = pd.DataFrame(account_summary(accounts_with_positions()))
            if not summaries.empty and "Liquidation Value" in summaries:
                total = pd.to_numeric(summaries["Liquidation Value"], errors="coerce").sum()
                return float(total), "Schwab (실시간)"
    except Exception:
        pass
    try:
        from utils.portfolio_store import load as load_manual_portfolio
        from engine.portfolio import enrich
        df = load_manual_portfolio()
        if df is not None and not df.empty:
            e = enrich(df)
            if not e.empty and "Market Value" in e:
                return float(e["Market Value"].sum()), "Manual Portfolio"
    except Exception:
        pass
    return 0.0, "데이터 없음"


def _investment_breakdown() -> tuple[pd.DataFrame, str]:
    """Per-account investment breakdown (same source priority as _investment_total)."""
    try:
        from engine.schwab import connection_status, accounts_with_positions, account_summary
        if connection_status().get("connected"):
            summaries = pd.DataFrame(account_summary(accounts_with_positions()))
            if not summaries.empty and "Liquidation Value" in summaries:
                account_col = "Account" if "Account" in summaries else summaries.columns[0]
                out = pd.DataFrame({
                    "Name": "Schwab · " + summaries[account_col].astype(str),
                    "Amount": pd.to_numeric(summaries["Liquidation Value"], errors="coerce").fillna(0),
                })
                return out, "Schwab (실시간)"
    except Exception:
        pass
    try:
        from utils.portfolio_store import load as load_manual_portfolio
        from engine.portfolio import enrich
        df = load_manual_portfolio()
        if df is not None and not df.empty:
            e = enrich(df)
            if not e.empty and "Market Value" in e and "Account" in e:
                grouped = e.groupby("Account", as_index=False)["Market Value"].sum()
                out = pd.DataFrame({
                    "Name": "Portfolio · " + grouped["Account"].astype(str),
                    "Amount": grouped["Market Value"],
                })
                return out, "Manual Portfolio"
    except Exception:
        pass
    return pd.DataFrame(columns=["Name", "Amount"]), "데이터 없음"


def render() -> None:
    st.title("Net Worth")
    st.caption("은행 계좌 잔액 + 투자 자산을 합쳐서 전체 순자산을 봅니다.")
    if not cloud_configured():
        st.caption("⚠️ Supabase가 설정되지 않아 은행 계좌는 로컬 임시저장만 됩니다 — 서버 재시작 시 사라질 수 있어요.")

    bank_df = _load_bank_accounts()
    bank_total = pd.to_numeric(bank_df["Balance"], errors="coerce").fillna(0).sum() if not bank_df.empty else 0.0
    invest_total, invest_source = _investment_total()
    net_worth = bank_total + invest_total

    c1, c2, c3 = st.columns(3)
    c1.metric("총 순자산", money(net_worth))
    c2.metric("은행 계좌 합계", money(bank_total))
    c3.metric(f"투자 자산 ({invest_source})", money(invest_total))
    st.caption("투자 자산은 Schwab 연결 시 그 값을 우선 쓰고, 연결이 없으면 Manual Portfolio 합계를 씁니다 (중복 합산 방지).")

    # Keep today's (ET) snapshot up to date every time this page is visited.
    _upsert_snapshot(bank_total, invest_total)

    st.divider()
    st.markdown("### Daily Report")
    st.caption("스냅샷은 미국 동부시간(ET) 기준 날짜로 기록됩니다 — Schwab 시세의 애프터마켓 반영 시점과 맞추기 위해서입니다. 오늘부터 쌓이는 기록이라, 시간이 지날수록 더 정확해집니다.")

    snapshots = _load_snapshots()
    cashflows = _load_cashflows()
    today_str = _et_today_str()

    with st.expander("오늘 입금 / 출금 기록"):
        st.caption("계좌에 새로 넣거나 뺀 돈을 기록해두면, 아래 '오늘의 변동'이 실제 투자 손익만 보여주도록 자동으로 빼줍니다 (입금을 수익으로 착각하지 않게).")
        cf_col1, cf_col2, cf_col3 = st.columns([1, 2, 1])
        cf_amount = cf_col1.number_input("금액 (출금은 음수)", step=100.0, format="%.2f", key="cf_amount")
        cf_note = cf_col2.text_input("메모", key="cf_note", placeholder="예: 월급 입금, 생활비 출금")
        if cf_col3.button("기록 추가", use_container_width=True) and cf_amount:
            ok, err = _add_cashflow(cf_amount, cf_note)
            if not ok:
                st.error(f"저장 실패: {err}")
            else:
                st.rerun()
        today_flows = cashflows[cashflows["Date"] == today_str] if not cashflows.empty else pd.DataFrame()
        if not today_flows.empty:
            st.dataframe(today_flows[["Amount", "Note"]], use_container_width=True, hide_index=True)

    if len(snapshots) < 2:
        st.info("비교할 과거 기록이 아직 없습니다. 내일부터 '오늘의 변동'이 보이기 시작해요.")
    else:
        def _change_since(days_ago: int) -> tuple[float | None, float | None]:
            """(raw change, flow-adjusted change) vs the closest snapshot at
            least `days_ago` calendar days back. None if no snapshot exists
            far enough back yet."""
            cutoff = (datetime.now(ET) - pd.Timedelta(days=days_ago)).strftime("%Y-%m-%d")
            past = snapshots[snapshots["Date"] <= cutoff]
            if past.empty:
                return None, None
            past_value = float(past.iloc[-1]["NetWorth"])
            raw_change = net_worth - past_value
            flows_since = cashflows[cashflows["Date"] > past.iloc[-1]["Date"]]["Amount"].sum() if not cashflows.empty else 0.0
            return raw_change, raw_change - flows_since

        day_raw, day_adj = _change_since(1)
        week_raw, week_adj = _change_since(7)

        rc1, rc2 = st.columns(2)
        with rc1:
            if day_adj is None:
                st.metric("오늘의 변동", "—")
            else:
                st.metric("오늘의 변동 (입출금 제외 순수 투자 손익)", money(day_adj))
                st.caption(f"참고: 입출금 포함 실제 잔고 변동은 {money(day_raw)}")
        with rc2:
            if week_adj is None:
                st.metric("이번주 변동", "—")
            else:
                st.metric("최근 7일 변동 (입출금 제외)", money(week_adj))
                st.caption(f"참고: 입출금 포함 실제 잔고 변동은 {money(week_raw)}")

        st.markdown("#### 순자산 추이")
        st.line_chart(snapshots.set_index("Date")["NetWorth"])

    if not bank_df.empty:
        st.markdown("#### 은행 계좌 상세")
        bank_names = []
        for i, r in bank_df.reset_index(drop=True).iterrows():
            inst_raw = str(r["Institution"]).strip()
            inst = inst_raw if inst_raw and inst_raw.lower() != "none" else f"계좌 {i+1}"
            acct = str(r["Account Name"]).strip()
            label = f"{inst} · {acct}" if acct and acct.lower() != "none" else inst
            bank_names.append(label)
        bank_chart_df = pd.DataFrame({
            "Name": bank_names,
            "Amount": pd.to_numeric(bank_df["Balance"], errors="coerce").fillna(0).values,
        })
        # Guard against duplicate labels (e.g. two accounts with the same
        # institution and no account name) silently summing into one bar.
        seen: dict[str, int] = {}
        unique_names = []
        for name in bank_chart_df["Name"]:
            seen[name] = seen.get(name, 0) + 1
            unique_names.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
        bank_chart_df["Name"] = unique_names
        st.bar_chart(bank_chart_df.sort_values("Amount").set_index("Name")["Amount"], horizontal=True)

    invest_breakdown, _ = _investment_breakdown()
    if not invest_breakdown.empty:
        st.markdown("#### 투자 계좌 상세")
        st.bar_chart(invest_breakdown.sort_values("Amount").set_index("Name")["Amount"], horizontal=True)

    st.divider()
    st.markdown("### 은행 계좌")
    if bank_df.empty:
        st.info("등록된 은행 계좌가 없습니다. 아래에서 추가하세요.")
    else:
        display = bank_df.copy()
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={"Balance": st.column_config.NumberColumn(format="$%.2f")},
        )

    with st.expander("계좌 추가 / 편집 / 삭제", expanded=bank_df.empty):
        st.caption("표 안의 셀을 클릭해서 바로 수정할 수 있습니다. 새 행을 추가하려면 표 맨 아래 + 버튼을 누르세요.")
        edited = st.data_editor(
            bank_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Type": st.column_config.SelectboxColumn("Type", options=ACCOUNT_TYPES),
                "Balance": st.column_config.NumberColumn(format="$%.2f", step=0.01),
                "Updated": st.column_config.TextColumn("Updated", help="YYYY-MM-DD"),
            },
            key="bank_accounts_editor",
        )
        if st.button("변경사항 저장", type="primary"):
            clean = edited.copy()
            clean = clean.dropna(subset=["Institution"])
            clean = clean[clean["Institution"].astype(str).str.strip() != ""]
            clean["Balance"] = pd.to_numeric(clean["Balance"], errors="coerce").fillna(0)
            for col in ["Institution", "Account Name", "Type", "Updated"]:
                if col in clean:
                    clean[col] = clean[col].apply(lambda v: "" if pd.isna(v) else str(v))
            if "Updated" in clean:
                clean["Updated"] = clean["Updated"].apply(lambda v: v if v.strip() else str(date.today()))
            cloud_saved, error = _save_bank_accounts(clean[BANK_COLS])
            if not cloud_saved:
                st.error(f"⚠️ Supabase 저장에 실패했습니다 — 지금은 로컬에만 저장되어 서버가 재시작되면 사라질 수 있습니다.\n\n{error}")
            else:
                st.rerun()
