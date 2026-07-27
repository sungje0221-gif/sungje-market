import numpy as np
import pandas as pd

def rsi(series,period=14):
    s=series.dropna()
    if len(s)<=period: return None
    delta=s.diff(); gain=delta.clip(lower=0).rolling(period).mean(); loss=(-delta.clip(upper=0)).rolling(period).mean()
    value=100-(100/(1+gain/loss.replace(0,np.nan))); last=value.iloc[-1]
    return None if pd.isna(last) else float(last)

def trend_score(df):
    if df.empty or 'Close' not in df: return 50.0
    c=df['Close'].dropna()
    if len(c)<20: return 50.0
    last=float(c.iloc[-1]); ma20=float(c.rolling(20).mean().iloc[-1]); ma50=float(c.rolling(50).mean().iloc[-1]) if len(c)>=50 else ma20
    mom=(last/float(c.iloc[-20])-1)*100
    score=50+(12 if last>ma20 else -12)+(10 if last>ma50 else -10)+max(-15,min(15,mom))
    return max(0,min(100,score))

def support_resistance(df,window=60):
    if df.empty or 'Low' not in df or 'High' not in df: return None,None
    r=df.tail(window); return float(r['Low'].min()),float(r['High'].max())
