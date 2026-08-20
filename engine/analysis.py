from __future__ import annotations

from engine.indicators import macd, rsi, support_resistance, trend_score, volatility


def analyze(df):
    """Rule-based technical score built only from the supplied price history.

    No random numbers or fabricated series are used. The score combines trend,
    20-day momentum, RSI and MACD. If history is missing, the result is NO DATA.
    """
    if df is None or df.empty or "Close" not in df:
        return {
            "score": None, "action": "NO DATA", "risk": "UNKNOWN",
            "rsi": None, "macd": None, "support": None,
            "resistance": None, "volatility": None,
            "return_20d": None, "above_ma20": None, "above_ma50": None,
            "method": "actual price history only",
        }

    close = df["Close"].dropna().astype(float)
    if len(close) < 20:
        return {
            "score": None, "action": "NO DATA", "risk": "UNKNOWN",
            "rsi": None, "macd": None, "support": None,
            "resistance": None, "volatility": None,
            "return_20d": None, "above_ma20": None, "above_ma50": None,
            "method": "actual price history only",
        }

    score = trend_score(df)
    rv = rsi(close)
    _m, _ms, mh = macd(close)
    sup, res = support_resistance(df)
    vol = volatility(df)

    last = float(close.iloc[-1])
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    return_20d = (last / float(close.iloc[-20]) - 1) * 100

    if rv is not None:
        if rv > 72:
            score -= 8
        elif rv < 32:
            score += 6
    if mh is not None:
        score += 4 if mh > 0 else -4

    score = max(0, min(100, score))
    action = (
        "BUY / HOLD" if score >= 78 else
        "WATCH TO BUY" if score >= 62 else
        "WAIT" if score >= 45 else
        "REDUCE RISK"
    )
    risk = "HIGH" if (vol or 0) > 55 else "MEDIUM" if (vol or 0) > 30 else "LOW"
    return {
        "score": round(score, 1), "action": action, "risk": risk,
        "rsi": rv, "macd": mh, "support": sup, "resistance": res,
        "volatility": vol, "return_20d": return_20d,
        "above_ma20": last > ma20,
        "above_ma50": None if ma50 is None else last > ma50,
        "method": "trend + 20D momentum + RSI + MACD",
    }


def blended_rating(technical_score, fundamental_score, weight_technical: float = 0.5):
    """Combine the technical (price-action) score with the fundamental score
    into one 'real-world' rating that reflects both how the stock is trading
    right now and how healthy the underlying business actually is.

    A pure technical score marks any stock in a fresh sell-off as weak, even
    if the drop was a one-day overreaction to a single soft metric inside an
    otherwise strong earnings report. Blending in fundamentals stops a single
    bad day from dominating the verdict, while still letting a real trend
    change pull the rating down.

    weight_technical: 0.0-1.0, how much weight the technical score gets.
    The rest goes to the fundamental score. Defaults to an even 50/50 split.
    """
    weight_technical = max(0.0, min(1.0, weight_technical))
    weight_fundamental = 1.0 - weight_technical

    if technical_score is None and fundamental_score is None:
        return {"score": None, "action": "NO DATA", "label": "NO DATA"}
    if technical_score is None:
        blended = fundamental_score
    elif fundamental_score is None:
        blended = technical_score
    else:
        blended = technical_score * weight_technical + fundamental_score * weight_fundamental

    blended = max(0.0, min(100.0, blended))
    action = (
        "BUY / HOLD" if blended >= 72 else
        "WATCH TO BUY" if blended >= 58 else
        "WAIT" if blended >= 42 else
        "REDUCE RISK"
    )
    label = (
        "STRONG" if blended >= 72 else
        "GOOD" if blended >= 58 else
        "NEUTRAL" if blended >= 42 else
        "WEAK"
    )
    return {"score": round(blended, 1), "action": action, "label": label}


def market_brief(score, vix, ten, dollar):
    notes = []
    if score >= 70:
        notes.append("시장 추세는 강한 편입니다.")
    elif score >= 52:
        notes.append("시장 추세는 중립 이상입니다.")
    else:
        notes.append("시장 위험이 높은 상태입니다.")
    if vix is not None:
        notes.append("VIX가 높아 변동성 관리가 필요합니다." if vix > 22 else "VIX는 비교적 안정적입니다.")
    if ten is not None and ten > 4.5:
        notes.append("10년물 금리가 성장주에 부담을 줄 수 있습니다.")
    if dollar is not None and dollar > 104:
        notes.append("강달러가 위험자산에 부담입니다.")
    return " ".join(notes)
