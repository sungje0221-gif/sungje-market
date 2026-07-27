import numpy as np,pandas as pd

def rsi(s,period=14):
    s=s.dropna()
    if len(s)<=period:return None
    d=s.diff();g=d.clip(lower=0).rolling(period).mean();l=(-d.clip(upper=0)).rolling(period).mean()
    rs=g/l.replace(0,np.nan);v=100-(100/(1+rs));x=v.iloc[-1]
    return None if pd.isna(x) else float(x)

def macd(s):
    if len(s)<35:return None,None,None
    e12=s.ewm(span=12,adjust=False).mean();e26=s.ewm(span=26,adjust=False).mean()
    m=e12-e26;sig=m.ewm(span=9,adjust=False).mean();hist=m-sig
    return float(m.iloc[-1]),float(sig.iloc[-1]),float(hist.iloc[-1])

def trend_score(df):
    if df.empty or "Close" not in df:return 50.0
    c=df["Close"].dropna()
    if len(c)<20:return 50.0
    last=float(c.iloc[-1]);m20=float(c.rolling(20).mean().iloc[-1])
    m50=float(c.rolling(50).mean().iloc[-1]) if len(c)>=50 else m20
    m200=float(c.rolling(200).mean().iloc[-1]) if len(c)>=200 else m50
    mom=(last/float(c.iloc[-20])-1)*100
    score=50+(10 if last>m20 else -10)+(10 if last>m50 else -10)+(8 if last>m200 else -8)+max(-14,min(14,mom))
    return max(0,min(100,score))

def support_resistance(df,window=60):
    if df.empty:return None,None
    r=df.tail(window)
    return float(r["Low"].min()),float(r["High"].max())

def volatility(df,window=20):
    if df.empty or len(df)<window:return None
    ret=df["Close"].pct_change().dropna()
    return float(ret.tail(window).std()*252**.5*100)
