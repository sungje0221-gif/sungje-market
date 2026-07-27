import numpy as np
import pandas as pd


def rsi(series, period=14):
    s = series.dropna()
    if len(s) <= period:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    values = 100 - (100 / (1 + rs))
    last = values.iloc[-1]
    return None if pd.isna(last) else float(last)


def rsi_series(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series):
    if len(series) < 35:
        return None, None, None
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    histogram = line - signal
    return float(line.iloc[-1]), float(signal.iloc[-1]), float(histogram.iloc[-1])


def macd_series(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    line = ema12 - ema26
    signal = line.ewm(span=9, adjust=False).mean()
    histogram = line - signal
    return line, signal, histogram


def bollinger_bands(series, period=20, std_dev=2):
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return middle, upper, lower


def trend_score(df):
    if df.empty or "Close" not in df:
        return 50.0
    close = df["Close"].dropna()
    if len(close) < 20:
        return 50.0

    last = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ma20
    ma100 = float(close.rolling(100).mean().iloc[-1]) if len(close) >= 100 else ma50
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else ma100
    momentum = (last / float(close.iloc[-20]) - 1) * 100

    score = 50
    score += 8 if last > ma20 else -8
    score += 9 if last > ma50 else -9
    score += 7 if last > ma100 else -7
    score += 8 if last > ma200 else -8
    score += max(-14, min(14, momentum))
    return max(0, min(100, score))


def support_resistance(df, window=60):
    if df.empty:
        return None, None
    recent = df.tail(window)
    return float(recent["Low"].min()), float(recent["High"].max())


def volatility(df, window=20):
    if df.empty or len(df) < window:
        return None
    returns = df["Close"].pct_change().dropna()
    return float(returns.tail(window).std() * 252**0.5 * 100)
