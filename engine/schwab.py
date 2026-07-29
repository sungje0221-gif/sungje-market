from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qs

import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TOKEN_PATH = DATA_DIR / "schwab_token.json"

AUTHORIZE_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
TRADER_BASE_URL = "https://api.schwabapi.com/trader/v1"


class SchwabError(RuntimeError):
    pass


def _secret(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get("schwab", {}).get(key, default)).strip()
    except Exception:
        return default


def config() -> dict[str, str]:
    return {
        "client_id": _secret("client_id", os.getenv("SCHWAB_CLIENT_ID", "")),
        "client_secret": _secret("client_secret", os.getenv("SCHWAB_CLIENT_SECRET", "")),
        "redirect_uri": _secret("redirect_uri", os.getenv("SCHWAB_REDIRECT_URI", "")),
    }


def configured() -> bool:
    return all(config().values())


def save_token(token: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = dict(token)
    payload["saved_at"] = int(time.time())
    TOKEN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_token() -> dict[str, Any] | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def delete_token() -> None:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()


def authorization_url(state: str | None = None) -> str:
    c = config()
    if not configured():
        raise SchwabError("Schwab credentials are not configured.")
    params = {"client_id": c["client_id"], "redirect_uri": c["redirect_uri"]}
    if state:
        params["state"] = state
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def extract_code(value: str) -> str:
    value = value.strip()
    if not value:
        raise SchwabError("Authorization code or callback URL is empty.")
    if value.startswith("http://") or value.startswith("https://"):
        query = parse_qs(urlparse(value).query)
        code = query.get("code", [""])[0]
        if not code:
            raise SchwabError("No authorization code was found in the callback URL.")
        return code
    return value


def exchange_code(code_or_url: str) -> dict[str, Any]:
    c = config()
    response = requests.post(
        TOKEN_URL,
        auth=(c["client_id"], c["client_secret"]),
        data={
            "grant_type": "authorization_code",
            "code": extract_code(code_or_url),
            "redirect_uri": c["redirect_uri"],
        },
        timeout=30,
    )
    if not response.ok:
        raise SchwabError(f"Token exchange failed ({response.status_code}): {response.text[:500]}")
    token = response.json()
    save_token(token)
    return token


def refresh_access_token(token: dict[str, Any]) -> dict[str, Any]:
    c = config()
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        raise SchwabError("No refresh token is available. Reconnect Schwab.")
    response = requests.post(
        TOKEN_URL,
        auth=(c["client_id"], c["client_secret"]),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=30,
    )
    if not response.ok:
        raise SchwabError(f"Token refresh failed ({response.status_code}): {response.text[:500]}")
    refreshed = response.json()
    refreshed.setdefault("refresh_token", refresh_token)
    save_token(refreshed)
    return refreshed


def access_token() -> str:
    token = load_token()
    if not token:
        raise SchwabError("Schwab is not connected.")
    saved_at = int(token.get("saved_at", 0))
    expires_in = int(token.get("expires_in", 0))
    if expires_in and time.time() >= saved_at + expires_in - 90:
        token = refresh_access_token(token)
    value = token.get("access_token")
    if not value:
        raise SchwabError("The saved token has no access token.")
    return str(value)


def _request(method: str, path: str, **kwargs) -> Any:
    headers = kwargs.pop("headers", {})
    headers.update({"Authorization": f"Bearer {access_token()}", "Accept": "application/json"})
    response = requests.request(
        method, f"{TRADER_BASE_URL}{path}", headers=headers, timeout=30, **kwargs
    )
    if response.status_code == 401:
        token = load_token()
        if token:
            refresh_access_token(token)
            headers["Authorization"] = f"Bearer {access_token()}"
            response = requests.request(
                method, f"{TRADER_BASE_URL}{path}", headers=headers, timeout=30, **kwargs
            )
    if not response.ok:
        raise SchwabError(f"Schwab API error ({response.status_code}): {response.text[:700]}")
    return response.json() if response.content else None


@st.cache_data(ttl=300, show_spinner=False)
def account_numbers() -> list[dict[str, Any]]:
    data = _request("GET", "/accounts/accountNumbers")
    return data if isinstance(data, list) else []


@st.cache_data(ttl=120, show_spinner=False)
def accounts_with_positions() -> list[dict[str, Any]]:
    data = _request("GET", "/accounts", params={"fields": "positions"})
    return data if isinstance(data, list) else []


def clear_cache() -> None:
    account_numbers.clear()
    accounts_with_positions.clear()


def connection_status() -> dict[str, Any]:
    token = load_token()
    return {
        "configured": configured(),
        "connected": bool(token and token.get("access_token")),
        "has_refresh_token": bool(token and token.get("refresh_token")),
    }


def flatten_positions(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for wrapper in accounts:
        account = wrapper.get("securitiesAccount", wrapper)
        number = str(account.get("accountNumber", ""))
        balances = account.get("currentBalances", {}) or {}
        for position in account.get("positions", []) or []:
            instrument = position.get("instrument", {}) or {}
            symbol = str(instrument.get("symbol", "")).strip()
            if not symbol:
                continue
            qty = float(position.get("longQuantity", 0) or 0) - float(position.get("shortQuantity", 0) or 0)
            avg = float(position.get("averagePrice", 0) or 0)
            mv = float(position.get("marketValue", 0) or 0)
            cost = qty * avg
            rows.append({
                "Account": number[-4:] if number else "—",
                "Account Type": account.get("type", ""),
                "Ticker": symbol,
                "Description": instrument.get("description", ""),
                "Asset Type": instrument.get("assetType", ""),
                "Shares": qty,
                "Avg Cost": avg,
                "Market Value": mv,
                "Cost Basis": cost,
                "Unrealized P/L": mv - cost,
                "Unrealized P/L %": (mv / cost - 1) * 100 if cost else 0,
                "Day P/L": float(position.get("currentDayProfitLoss", 0) or 0),
                "Day P/L %": float(position.get("currentDayProfitLossPercentage", 0) or 0),
                "Cash Available": balances.get("cashAvailableForTrading"),
                "Buying Power": balances.get("buyingPower"),
            })
    return rows


def account_summary(accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for wrapper in accounts:
        account = wrapper.get("securitiesAccount", wrapper)
        number = str(account.get("accountNumber", ""))
        current = account.get("currentBalances", {}) or {}
        rows.append({
            "Account": number[-4:] if number else "—",
            "Type": account.get("type", ""),
            "Liquidation Value": current.get("liquidationValue"),
            "Cash": current.get("cashBalance"),
            "Cash Available": current.get("cashAvailableForTrading"),
            "Buying Power": current.get("buyingPower"),
            "Long Market Value": current.get("longMarketValue"),
            "Short Market Value": current.get("shortMarketValue"),
            "Day Trading Buying Power": current.get("dayTradingBuyingPower"),
        })
    return rows
