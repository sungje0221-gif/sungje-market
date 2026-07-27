import pandas as pd
import streamlit as st

def colored_change_table(df, price_col="Price", change_col="Change %", score_col=None):
    work = df.copy()

    def fmt_change(v):
        if pd.isna(v):
            return '<span class="delta-flat">—</span>'
        css = "delta-up" if v > 0 else "delta-down" if v < 0 else "delta-flat"
        arrow = "▲" if v > 0 else "▼" if v < 0 else "•"
        return f'<span class="{css}">{arrow} {v:+.2f}%</span>'

    if price_col in work:
        work[price_col] = work[price_col].map(lambda v: "—" if pd.isna(v) else f"{v:,.2f}")
    if change_col in work:
        work[change_col] = work[change_col].map(fmt_change)
    if score_col and score_col in work:
        work[score_col] = work[score_col].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}")

    st.markdown(
        work.to_html(index=False, escape=False, classes="smcc-html-table"),
        unsafe_allow_html=True,
    )
    st.markdown("""
    <style>
    table.smcc-html-table{width:100%;border-collapse:separate;border-spacing:0;background:#0c1828;
      border:1px solid rgba(255,255,255,.07);border-radius:14px;overflow:hidden}
    table.smcc-html-table th{background:#111d2d;text-align:left;padding:11px 12px;font-size:12px;opacity:.75}
    table.smcc-html-table td{padding:10px 12px;border-top:1px solid rgba(255,255,255,.055);font-size:13px}
    </style>
    """, unsafe_allow_html=True)
