from __future__ import annotations

import io
import json
import platform
import sys
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.schwab import connection_status
from utils.storage import load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT = {
    "name": "Sungje",
    "risk_profile": "Balanced",
    "default_budget": 5000,
    "rules": "No crypto. No biotech. Prefer staged entries.",
}


def _backup_zip() -> bytes:
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ["portfolio.csv", "watchlist.json", "journal.json", "settings.json"]:
            path = DATA_DIR / name
            if path.exists():
                archive.write(path, arcname=f"data/{name}")
    return memory.getvalue()


def _diagnostics() -> pd.DataFrame:
    from utils.storage import cloud_configured
    checks = []
    for label, path in [
        ("Portfolio file", DATA_DIR / "portfolio.csv"),
        ("Watchlist file", DATA_DIR / "watchlist.json"),
        ("Journal file", DATA_DIR / "journal.json"),
        ("Settings file", DATA_DIR / "settings.json"),
    ]:
        checks.append({"Check": label, "Status": "OK" if path.exists() else "MISSING", "Detail": str(path.name)})
    checks.append({
        "Check": "Cloud Sync (Supabase)",
        "Status": "OK" if cloud_configured() else "NOT SET",
        "Detail": "Watchlist/Portfolio/Journal survive restarts" if cloud_configured() else "로컬 파일만 사용 — 재부팅 시 소실 위험",
    })
    checks.extend([
        {"Check": "Python", "Status": "OK", "Detail": sys.version.split()[0]},
        {"Check": "Platform", "Status": "OK", "Detail": platform.system()},
        {"Check": "App Version", "Status": "OK", "Detail": "1.00"},
    ])
    return pd.DataFrame(checks)


def render() -> None:
    st.title("Settings")
    st.caption("Investment OS v1.00 · configuration, backup and diagnostics")

    status = connection_status()
    st.markdown("### Data Source Diagnostics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Schwab Credentials", "READY" if status["configured"] else "NOT SET")
    c2.metric("Schwab Account", "CONNECTED" if status["connected"] else "DISCONNECTED")
    c3.metric("Quote Priority", "Schwab → Yahoo" if status["connected"] else "Yahoo Finance")
    from engine.claude_advisor import configured as _ai_ready
    c4.metric("AI Advisor", "READY" if _ai_ready() else "NOT SET")
    st.caption("Schwab 연결 전에는 Yahoo Finance가 기본 가격 공급원입니다. 시세는 지연될 수 있습니다.")
    if not _ai_ready():
        st.caption("AI 브리핑/코멘터리/채팅을 쓰려면 Streamlit Secrets에 [anthropic] api_key를 추가하세요.")

    x = load_json("settings.json", DEFAULT)
    st.markdown("### Personal Preferences")
    with st.form("settings_form"):
        name = st.text_input("Name", x.get("name", "Sungje"))
        options = ["Conservative", "Balanced", "Aggressive"]
        current_risk = x.get("risk_profile", "Balanced")
        risk = st.selectbox("Risk Profile", options, index=options.index(current_risk) if current_risk in options else 1)
        budget = st.number_input("Default Budget", min_value=100.0, value=float(x.get("default_budget", 5000)), step=100.0)
        rules = st.text_area("Investment Rules", x.get("rules", ""), height=110)
        if st.form_submit_button("Save Settings", type="primary"):
            save_json("settings.json", {"name": name, "risk_profile": risk, "default_budget": budget, "rules": rules})
            st.success("Settings saved.")

    st.markdown("### Backup")
    st.download_button(
        "Download Personal Data Backup",
        data=_backup_zip(),
        file_name="InvestmentOS-personal-data-backup.zip",
        mime="application/zip",
        use_container_width=True,
    )

    st.markdown("### System Check")
    st.dataframe(_diagnostics(), use_container_width=True, hide_index=True)
    if st.button("Refresh market cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared.")
