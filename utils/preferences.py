from utils.storage import load_json, save_json
DEFAULT_MARKETS={
 "Futures":[["S&P 500","ES=F"],["Nasdaq 100","NQ=F"],["Dow","YM=F"],["Russell 2000","RTY=F"],["VIX","^VIX"]],
 "Macro":[["US Dollar","DX-Y.NYB"],["US 10Y","^TNX"],["Gold","GC=F"],["Silver","SI=F"],["WTI Oil","CL=F"]],
 "Korea":[["KOSPI","^KS11"],["KOSDAQ","^KQ11"],["USD/KRW","KRW=X"],["EWY","EWY"],["KORU","KORU"],["SKHY","SKHY"]],
}
def load_market_groups():
    data=load_json("market_groups.json",DEFAULT_MARKETS)
    return data if isinstance(data,dict) else DEFAULT_MARKETS
def save_market_groups(data):
    save_json("market_groups.json",data)
    return data
