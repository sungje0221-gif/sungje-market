"""Persistent watchlist storage.

The server-side JSON file is kept as a fallback and as the shared source used by
other pages. The browser's localStorage is the durable source for Streamlit
Community Cloud because the app filesystem may be reset during a restart or
redeploy.
"""
from __future__ import annotations

import json
from typing import Iterable

import streamlit as st

from utils.storage import load_json, save_json

STORAGE_KEY = "sungje_investment_os_watchlist_v1"
SESSION_KEY = "persistent_watchlist"

try:
    from streamlit_local_storage import LocalStorage
except Exception:  # pragma: no cover - file fallback still works
    LocalStorage = None


def _normalize(values: Iterable[str] | None, default: list[str]) -> list[str]:
    source = values if isinstance(values, (list, tuple)) else default
    result: list[str] = []
    for value in source:
        ticker = str(value).strip().upper()
        if ticker and ticker not in result:
            result.append(ticker)
    return result


def _decode(value) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, list) else None
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _local_storage():
    if LocalStorage is None:
        return None
    try:
        return LocalStorage()
    except Exception:
        return None


def load_watchlist(default: list[str]) -> list[str]:
    """Load from browser storage, then session, then JSON fallback."""
    fallback = _normalize(load_json("watchlist.json", default), default)

    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = fallback

    local = _local_storage()
    if local is not None:
        try:
            stored = local.getItem(STORAGE_KEY, key="watchlist_local_get")
            decoded = _decode(stored)
            if decoded is not None:
                durable = _normalize(decoded, default)
                if durable != st.session_state[SESSION_KEY]:
                    st.session_state[SESSION_KEY] = durable
                    save_json("watchlist.json", durable)
        except Exception:
            pass

    current = _normalize(st.session_state.get(SESSION_KEY), default)
    # Keep the server fallback synchronized for Command Center, Heatmap, etc.
    if current != fallback:
        save_json("watchlist.json", current)
    return current


def save_watchlist(tickers: list[str]) -> list[str]:
    """Persist immediately to session, JSON fallback, and browser localStorage."""
    clean = _normalize(tickers, [])
    st.session_state[SESSION_KEY] = clean
    save_json("watchlist.json", clean)

    local = _local_storage()
    if local is not None:
        try:
            local.setItem(STORAGE_KEY, json.dumps(clean), key="watchlist_local_set")
        except TypeError:
            # Older component releases do not expose the optional Streamlit key.
            local.setItem(STORAGE_KEY, json.dumps(clean))
        except Exception:
            pass
    return clean
