from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from utils.formatters import money
from utils.storage import load_cloud_json, save_cloud_json, cloud_configured

BANK_COLS = ["Institution", "Account Name", "Type", "Balance", "Updated"]
ACCOUNT_TYPES = ["Checking", "Savings", "Money Market", "CD", "Credit Card (negative)", "Other"]


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
            clean = clean[clean["Institution"].astype(str).str.strip() != ""]
            if "Updated" in clean:
                clean["Updated"] = clean["Updated"].apply(lambda v: v if v else str(date.today()))
            clean["Balance"] = pd.to_numeric(clean["Balance"], errors="coerce").fillna(0)
            cloud_saved, error = _save_bank_accounts(clean[BANK_COLS])
            if not cloud_saved:
                st.error(f"⚠️ Supabase 저장에 실패했습니다 — 지금은 로컬에만 저장되어 서버가 재시작되면 사라질 수 있습니다.\n\n{error}")
            else:
                st.rerun()
