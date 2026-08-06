from pathlib import Path
import json,pandas as pd
import streamlit as st
import requests
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def load_json(name,default):
    p=DATA/name
    if not p.exists():return default
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return default

def save_json(name,payload):
    (DATA/name).write_text(json.dumps(payload,indent=2),encoding="utf-8")

def load_csv(name,columns):
    p=DATA/name
    if not p.exists():return pd.DataFrame(columns=columns)
    try:return pd.read_csv(p)
    except:return pd.DataFrame(columns=columns)

def save_csv(name,df):
    df.to_csv(DATA/name,index=False)


# --- Generic Supabase-backed blob storage --------------------------------
# Local files under data/ don't survive a Streamlit Cloud container restart
# (git pull resets the filesystem). This mirrors that pattern used for the
# watchlist/Schwab token: store a JSON payload under (profile_id, key) in a
# generic table, with the local file kept only as an offline fallback.

def _blob_config() -> dict[str, str] | None:
    try:
        section = st.secrets.get("supabase", {})
        url = str(section.get("url", "")).rstrip("/")
        key = str(section.get("key", ""))
        table = str(section.get("blob_table", "app_blobs"))
        profile = str(section.get("profile_id", "sungje"))
        if url and key:
            return {"url": url, "key": key, "table": table, "profile": profile}
    except Exception:
        pass
    return None


def cloud_configured() -> bool:
    return _blob_config() is not None


def _blob_headers(config: dict[str, str], prefer: str | None = None) -> dict[str, str]:
    headers = {"apikey": config["key"], "Authorization": f"Bearer {config['key']}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    return headers


def load_cloud_json(key: str, default):
    """Cloud value if configured & present, else the local-file fallback."""
    config = _blob_config()
    if config:
        try:
            endpoint = f"{config['url']}/rest/v1/{config['table']}"
            response = requests.get(
                endpoint, headers=_blob_headers(config),
                params={"profile_id": f"eq.{config['profile']}", "key": f"eq.{key}", "select": "payload"},
                timeout=10,
            )
            response.raise_for_status()
            rows = response.json()
            if rows:
                return rows[0]["payload"]
        except Exception:
            pass
    return load_json(f"{key}.json", default)


def save_cloud_json(key: str, payload) -> None:
    """Always write the local fallback file, and mirror to Supabase if configured."""
    save_json(f"{key}.json", payload)
    config = _blob_config()
    if not config:
        return
    try:
        endpoint = f"{config['url']}/rest/v1/{config['table']}"
        response = requests.post(
            endpoint,
            headers=_blob_headers(config, "resolution=merge-duplicates,return=minimal"),
            params={"on_conflict": "profile_id,key"},
            json=[{"profile_id": config["profile"], "key": key, "payload": payload}],
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        pass  # local file above still keeps this usable for the session
