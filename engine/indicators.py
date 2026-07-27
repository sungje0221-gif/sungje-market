import numpy as np
import pandas as pd

def rsi(series, period=14):
    s = series.dropna()
    if len(s) <= period: return None
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    value = 100 - (100/(1+rs))
    last = value.iloc[-1]
    return None if pd.isna(last) else float(last)

def trend_score(df):
    if df.empty or "Close" not in df: return 50.0
    close = df["Close"].dropna()
    if len(close) < 20: return 50.0
    last = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ma20
    mom20 = (last/float(close.iloc[-20])-1)*100
    score = 50 + (12 if last > ma20 else -12) + (10 if last > ma50 else -10)
    score += max(-15, min(15, mom20))
    return max(0, min(100, score))

def support_resistance(df, window=60):
    if df.empty or "Low" not in df or "High" not in df: return None, None
    recent = df.tail(window)
    return float(recent["Low"].min()), float(recent["High"].max())
