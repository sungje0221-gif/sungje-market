from engine.market_data import quote
def enrich(df):
    if df.empty:return df.copy()
    x=df.copy()
    x["Current Price"]=[quote(str(t).upper())["price"] for t in x["Ticker"]]
    x["Market Value"]=x["Shares"]*x["Current Price"]
    x["Cost Basis"]=x["Shares"]*x["Avg Cost"]
    x["P/L"]=x["Market Value"]-x["Cost Basis"]
    x["P/L %"]=(x["Market Value"]/x["Cost Basis"]-1)*100
    total=x["Market Value"].sum()
    x["Weight %"]=x["Market Value"]/total*100 if total else 0
    return x
