from engine.indicators import rsi, trend_score, support_resistance

def analyze_ticker(df):
    if df.empty or "Close" not in df:
        return {"score":50,"action":"NO DATA","risk":"UNKNOWN","rsi":None,
                "support":None,"resistance":None,"comment":"가격 데이터를 불러오지 못했습니다."}
    score = trend_score(df)
    current_rsi = rsi(df["Close"])
    support, resistance = support_resistance(df)
    if current_rsi is not None:
        if current_rsi > 72: score -= 10
        elif current_rsi < 32: score += 7
    score = max(0, min(100, score))
    action = "BUY / HOLD" if score >= 78 else "WATCH TO BUY" if score >= 62 else "WAIT" if score >= 45 else "REDUCE RISK"
    risk = "HIGH" if current_rsi is not None and (current_rsi > 75 or current_rsi < 25) else "MEDIUM"
    if 40 <= score <= 75 and current_rsi is not None and 35 <= current_rsi <= 65: risk = "LOW"
    comment = f"추세 점수 {score:.0f}점" + (f", RSI {current_rsi:.1f}" if current_rsi is not None else "")
    return {"score":round(score,1),"action":action,"risk":risk,"rsi":current_rsi,
            "support":support,"resistance":resistance,"comment":comment}
