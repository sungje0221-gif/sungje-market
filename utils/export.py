"""Shared Excel export helper -- one call turns any dataframe into a
download button, so every page can offer the same "엑셀로 다운로드" affordance
without repeating the BytesIO/ExcelWriter boilerplate.
"""
from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st


def excel_download_button(
    df: pd.DataFrame,
    base_filename: str,
    label: str = "⬇ Excel 다운로드",
    key: str | None = None,
    sheet_name: str = "Sheet1",
) -> None:
    """Render a download button that exports `df` as an .xlsx file.

    `base_filename` should be a short name without extension or date --
    today's date (ET-agnostic, just local) is appended automatically so
    repeated downloads don't overwrite each other in the person's Downloads
    folder.
    """
    if df is None or df.empty:
        return
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    st.download_button(
        label,
        data=buffer.getvalue(),
        file_name=f"{base_filename}_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
    )
