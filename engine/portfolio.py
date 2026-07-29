import pandas as pd
from engine.market_data import quote

def enrich(df):
    if df.empty:return df.copy()
    x=df.copy(); quotes=[quote(str(t).upper()) for t in x["Ticker"]]
    x["Current Price"]=[q.get("price") or 0 for q in quotes]
    x["Day %"]=[q.get("change_pct") for q in quotes]
    x["Day Change $"]=[q.get("change_abs") or 0 for q in quotes]
    x["Market Value"]=pd.to_numeric(x["Shares"],errors="coerce").fillna(0)*x["Current Price"]
    x["Cost Basis"]=pd.to_numeric(x["Shares"],errors="coerce").fillna(0)*pd.to_numeric(x["Avg Cost"],errors="coerce").fillna(0)
    x["P/L"]=x["Market Value"]-x["Cost Basis"]
    x["P/L %"]=x["P/L"].div(x["Cost Basis"].replace(0,pd.NA))*100
    total=x["Market Value"].sum(); x["Weight %"]=x["Market Value"]/total*100 if total else 0
    return x
