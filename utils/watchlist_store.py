"""Watchlist Pro persistence with optional Supabase cloud sync.

Supabase is the primary store when configured in Streamlit secrets. A local JSON
file remains available as an offline/development fallback. Existing ticker-only
watchlists are migrated automatically to the richer v2 record format.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import requests
import streamlit as st

from utils.storage import load_json, save_json

FILE_NAME = "watchlist.json"
SESSION_KEY = "watchlist_pro_records_v2"
DEFAULT_PROFILE = "sungje"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def _record(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        ticker = _clean_ticker(value)
        if not ticker:
            return None
        return {
            "ticker": ticker, "pinned": False, "target_price": None,
            "stop_price": None, "tag": "Watch", "memo": "", "updated_at": _now(),
        }
    if not isinstance(value, dict):
        return None
    ticker = _clean_ticker(value.get("ticker") or value.get("symbol"))
    if not ticker:
        return None
    def number(field: str):
        raw = value.get(field)
        if raw in (None, ""):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return {
        "ticker": ticker,
        "pinned": bool(value.get("pinned", False)),
        "target_price": number("target_price"),
        "stop_price": number("stop_price"),
        "tag": str(value.get("tag") or "Watch").strip()[:30],
        "memo": str(value.get("memo") or "").strip()[:1000],
        "updated_at": str(value.get("updated_at") or _now()),
    }


def _normalize(values: Iterable[Any] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values or []:
        item = _record(value)
        if item and item["ticker"] not in seen:
            seen.add(item["ticker"])
            result.append(item)
    return result


def _supabase_config() -> dict[str, str] | None:
    try:
        section = st.secrets.get("supabase", {})
        url = str(section.get("url", "")).rstrip("/")
        key = str(section.get("key", ""))
        table = str(section.get("watchlist_table", "watchlist_items"))
        profile = str(section.get("profile_id", DEFAULT_PROFILE))
        if url and key:
            return {"url": url, "key": key, "table": table, "profile": profile}
    except Exception:
        pass
    return None


def supabase_configured() -> bool:
    return _supabase_config() is not None


def _headers(config: dict[str, str], prefer: str | None = None) -> dict[str, str]:
    headers = {
        "apikey": config["key"],
        "Authorization": f"Bearer {config['key']}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _cloud_load(config: dict[str, str]) -> list[dict[str, Any]]:
    endpoint = f"{config['url']}/rest/v1/{config['table']}"
    response = requests.get(
        endpoint,
        headers=_headers(config),
        params={
            "profile_id": f"eq.{config['profile']}",
            "select": "ticker,pinned,target_price,stop_price,tag,memo,updated_at",
            "order": "pinned.desc,ticker.asc",
        },
        timeout=10,
    )
    response.raise_for_status()
    return _normalize(response.json())


def _cloud_upsert(config: dict[str, str], records: list[dict[str, Any]]) -> None:
    endpoint = f"{config['url']}/rest/v1/{config['table']}"
    payload = [{**item, "profile_id": config["profile"]} for item in records]
    if not payload:
        return
    response = requests.post(
        endpoint,
        headers=_headers(config, "resolution=merge-duplicates,return=minimal"),
        params={"on_conflict": "profile_id,ticker"},
        json=payload,
        timeout=10,
    )
    response.raise_for_status()


def _cloud_delete(config: dict[str, str], ticker: str) -> None:
    endpoint = f"{config['url']}/rest/v1/{config['table']}"
    response = requests.delete(
        endpoint,
        headers=_headers(config, "return=minimal"),
        params={"profile_id": f"eq.{config['profile']}", "ticker": f"eq.{ticker}"},
        timeout=10,
    )
    response.raise_for_status()


def storage_status() -> tuple[str, str]:
    if supabase_configured():
        return "Cloud Sync", "Supabase"
    return "Local Fallback", "data/watchlist.json"


def load_watchlist_data(default: list[str] | None = None, force: bool = False) -> list[dict[str, Any]]:
    if SESSION_KEY in st.session_state and not force:
        return _normalize(st.session_state[SESSION_KEY])

    fallback = _normalize(load_json(FILE_NAME, default or []))
    config = _supabase_config()
    records = fallback
    if config:
        try:
            cloud = _cloud_load(config)
            if cloud:
                records = cloud
            elif fallback:
                _cloud_upsert(config, fallback)
                records = fallback
            st.session_state["watchlist_sync_error"] = ""
        except Exception as exc:
            st.session_state["watchlist_sync_error"] = str(exc)

    st.session_state[SESSION_KEY] = records
    save_json(FILE_NAME, records)
    return records


def save_watchlist_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean = _normalize(records)
    for item in clean:
        item["updated_at"] = _now()
    st.session_state[SESSION_KEY] = clean
    save_json(FILE_NAME, clean)
    config = _supabase_config()
    if config:
        try:
            _cloud_upsert(config, clean)
            st.session_state["watchlist_sync_error"] = ""
        except Exception as exc:
            st.session_state["watchlist_sync_error"] = str(exc)
    return clean


def delete_watchlist_item(ticker: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ticker = _clean_ticker(ticker)
    clean = [item for item in _normalize(records) if item["ticker"] != ticker]
    st.session_state[SESSION_KEY] = clean
    save_json(FILE_NAME, clean)
    config = _supabase_config()
    if config:
        try:
            _cloud_delete(config, ticker)
            st.session_state["watchlist_sync_error"] = ""
        except Exception as exc:
            st.session_state["watchlist_sync_error"] = str(exc)
    return clean


# Backward-compatible helpers used by older pages.
def load_watchlist(default: list[str]) -> list[str]:
    return [item["ticker"] for item in load_watchlist_data(default)]


def save_watchlist(tickers: list[str]) -> list[str]:
    existing = {item["ticker"]: item for item in load_watchlist_data([])}
    records = [existing.get(_clean_ticker(t), _record(t)) for t in tickers]
    clean = save_watchlist_data([r for r in records if r])
    return [item["ticker"] for item in clean]
