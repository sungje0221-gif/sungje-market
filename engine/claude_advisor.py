"""Thin wrapper around the Anthropic API for the app's AI features.

Uses `requests` directly (no extra dependency) against the Messages API.
The API key lives in Streamlit secrets under [anthropic] -> api_key, kept
entirely separate from the person's Claude.ai subscription.
"""
from __future__ import annotations

import requests
import streamlit as st

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-5"
ANTHROPIC_VERSION = "2023-06-01"


def configured() -> bool:
    try:
        return bool(st.secrets.get("anthropic", {}).get("api_key"))
    except Exception:
        return False


def ask(system: str, user: str, max_tokens: int = 900, model: str = MODEL) -> str:
    """Single-turn call. Returns Claude's text reply, or a Korean error string."""
    try:
        key = st.secrets.get("anthropic", {}).get("api_key")
    except Exception:
        key = None
    if not key:
        return "Anthropic API 키가 설정되지 않았습니다. Settings에서 확인해주세요."

    try:
        response = requests.post(
            API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        parts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
        return "".join(parts).strip() or "응답을 받지 못했습니다."
    except requests.exceptions.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return f"API 오류가 발생했습니다{f': {detail}' if detail else ''}."
    except requests.exceptions.Timeout:
        return "응답 시간이 초과됐습니다. 잠시 후 다시 시도해주세요."
    except Exception as exc:
        return f"오류가 발생했습니다: {exc}"


def chat(system: str, history: list[dict], max_tokens: int = 900, model: str = MODEL) -> str:
    """Multi-turn call. `history` is a list of {"role": "user"|"assistant", "content": str}."""
    try:
        key = st.secrets.get("anthropic", {}).get("api_key")
    except Exception:
        key = None
    if not key:
        return "Anthropic API 키가 설정되지 않았습니다. Settings에서 확인해주세요."

    try:
        response = requests.post(
            API_URL,
            headers={
                "x-api-key": key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": max_tokens, "system": system, "messages": history},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        parts = [block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"]
        return "".join(parts).strip() or "응답을 받지 못했습니다."
    except requests.exceptions.HTTPError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        return f"API 오류가 발생했습니다{f': {detail}' if detail else ''}."
    except Exception as exc:
        return f"오류가 발생했습니다: {exc}"
