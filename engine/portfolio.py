from engine.market_data import quote

def enrich_portfolio(df):
    if df.empty: return df.copy()
    out = df.copy()
    out["Current Price"] = [quote(str(t).upper())["price"] for t in out["Ticker"]]
    out["Market Value"] = out["Shares"] * out["Current Price"]
    out["Cost Basis"] = out["Shares"] * out["Avg Cost"]
    out["P/L"] = out["Market Value"] - out["Cost Basis"]
    out["P/L %"] = (out["Market Value"]/out["Cost Basis"]-1)*100
    total = out["Market Value"].sum()
    out["Weight %"] = out["Market Value"]/total*100 if total else 0
    return out
