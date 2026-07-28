from __future__ import annotations
from datetime import datetime, timezone
import requests
import pandas as pd
import streamlit as st
from utils.storage import load_csv, save_csv

COLS = ["Account", "Ticker", "Shares", "Avg Cost", "Category", "Sector", "Industry"]
FILE_NAME = "portfolio.csv"
SESSION_KEY = "portfolio_positions_v2"
SETTINGS_KEY = "portfolio_settings_v1"


def _config():
    try:
        s = st.secrets.get("supabase", {})
        url = str(s.get("url", "")).rstrip("/")
        key = str(s.get("key", ""))
        table = str(s.get("portfolio_table", "portfolio_positions"))
        settings_table = str(s.get("portfolio_settings_table", "portfolio_settings"))
        profile = str(s.get("profile_id", "sungje"))
        if url and key:
            return {"url": url, "key": key, "table": table, "settings_table": settings_table, "profile": profile}
    except Exception:
        pass
    return None


def cloud_enabled(): return _config() is not None

def status(): return ("Cloud Sync", "Supabase") if cloud_enabled() else ("Local Fallback", "data/portfolio.csv")

def _headers(c, prefer=None):
    h={"apikey":c["key"],"Authorization":f"Bearer {c['key']}","Content-Type":"application/json"}
    if prefer: h["Prefer"]=prefer
    return h

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame(columns=COLS)
    x=df.copy()
    for c in COLS:
        if c not in x: x[c]=""
    x=x[COLS]
    x["Ticker"]=x["Ticker"].astype(str).str.upper().str.strip()
    x["Account"]=x["Account"].astype(str).str.strip().replace("", "Taxable")
    x["Category"]=x["Category"].astype(str).str.strip().replace("", "Other")
    x["Sector"]=x["Sector"].astype(str).str.strip().replace("", "Unknown")
    x["Industry"]=x["Industry"].astype(str).str.strip().replace("", "Unknown")
    x["Shares"]=pd.to_numeric(x["Shares"],errors="coerce").fillna(0)
    x["Avg Cost"]=pd.to_numeric(x["Avg Cost"],errors="coerce").fillna(0)
    x=x[(x["Ticker"]!="") & (x["Shares"]>0)]
    rows=[]
    for (account,ticker), group in x.groupby(["Account","Ticker"], dropna=False):
        total_shares=float(group["Shares"].sum())
        avg_cost=float((group["Shares"]*group["Avg Cost"]).sum()/total_shares) if total_shares else 0.0
        last=group.iloc[-1]
        rows.append({"Account":account,"Ticker":ticker,"Shares":total_shares,"Avg Cost":avg_cost,
                     "Category":last["Category"],"Sector":last["Sector"],"Industry":last["Industry"]})
    return pd.DataFrame(rows, columns=COLS)

def load(force=False):
    if SESSION_KEY in st.session_state and not force: return _clean(st.session_state[SESSION_KEY])
    fallback=_clean(load_csv(FILE_NAME,COLS)); c=_config(); out=fallback
    if c:
        try:
            r=requests.get(f"{c['url']}/rest/v1/{c['table']}",headers=_headers(c),params={"profile_id":f"eq.{c['profile']}","select":"account,ticker,shares,avg_cost,category,sector,industry","order":"account.asc,ticker.asc"},timeout=12)
            r.raise_for_status(); rows=r.json()
            if rows:
                out=_clean(pd.DataFrame([{"Account":z.get("account"),"Ticker":z.get("ticker"),"Shares":z.get("shares"),"Avg Cost":z.get("avg_cost"),"Category":z.get("category"),"Sector":z.get("sector"),"Industry":z.get("industry")} for z in rows]))
            elif not fallback.empty: save(fallback)
            st.session_state["portfolio_sync_error"]=""
        except Exception as e: st.session_state["portfolio_sync_error"]=str(e)
    st.session_state[SESSION_KEY]=out; save_csv(FILE_NAME,out); return out

def save(df):
    x=_clean(df); st.session_state[SESSION_KEY]=x; save_csv(FILE_NAME,x); c=_config()
    if c:
        try:
            ep=f"{c['url']}/rest/v1/{c['table']}"
            requests.delete(ep,headers=_headers(c,"return=minimal"),params={"profile_id":f"eq.{c['profile']}"},timeout=12).raise_for_status()
            if not x.empty:
                rows=[{"profile_id":c["profile"],"account":r["Account"],"ticker":r["Ticker"],"shares":float(r["Shares"]),"avg_cost":float(r["Avg Cost"]),"category":r["Category"],"sector":r["Sector"],"industry":r["Industry"],"updated_at":datetime.now(timezone.utc).isoformat()} for _,r in x.iterrows()]
                requests.post(ep,headers=_headers(c,"resolution=merge-duplicates,return=minimal"),params={"on_conflict":"profile_id,account,ticker"},json=rows,timeout=12).raise_for_status()
            st.session_state["portfolio_sync_error"]=""
        except Exception as e: st.session_state["portfolio_sync_error"]=str(e)
    return x

def load_settings(force=False):
    if SETTINGS_KEY in st.session_state and not force: return dict(st.session_state[SETTINGS_KEY])
    out={"cash":0.0,"buying_power":0.0,"target_cash_pct":20.0}
    c=_config()
    if c:
        try:
            r=requests.get(f"{c['url']}/rest/v1/{c['settings_table']}",headers=_headers(c),params={"profile_id":f"eq.{c['profile']}","select":"cash,buying_power,target_cash_pct","limit":"1"},timeout=12)
            r.raise_for_status(); rows=r.json()
            if rows: out.update({k:float(rows[0].get(k) or 0) for k in out})
        except Exception as e: st.session_state["portfolio_settings_sync_error"]=str(e)
    st.session_state[SETTINGS_KEY]=out
    return out

def save_settings(settings):
    out={"cash":float(settings.get("cash",0)),"buying_power":float(settings.get("buying_power",0)),"target_cash_pct":float(settings.get("target_cash_pct",20))}
    st.session_state[SETTINGS_KEY]=out; c=_config()
    if c:
        try:
            row={"profile_id":c["profile"],**out,"updated_at":datetime.now(timezone.utc).isoformat()}
            requests.post(f"{c['url']}/rest/v1/{c['settings_table']}",headers=_headers(c,"resolution=merge-duplicates,return=minimal"),params={"on_conflict":"profile_id"},json=[row],timeout=12).raise_for_status()
            st.session_state["portfolio_settings_sync_error"]=""
        except Exception as e: st.session_state["portfolio_settings_sync_error"]=str(e)
    return out
