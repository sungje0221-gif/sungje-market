from engine.indicators import rsi,macd,trend_score,support_resistance,volatility

def analyze(df):
    if df.empty:return {"score":50,"action":"NO DATA","risk":"UNKNOWN","rsi":None,"macd":None,"support":None,"resistance":None,"volatility":None}
    score=trend_score(df);rv=rsi(df["Close"]);m,ms,mh=macd(df["Close"]);sup,res=support_resistance(df);vol=volatility(df)
    if rv is not None:
        if rv>72:score-=8
        elif rv<32:score+=6
    if mh is not None:score+=4 if mh>0 else -4
    score=max(0,min(100,score))
    action="BUY / HOLD" if score>=78 else "WATCH TO BUY" if score>=62 else "WAIT" if score>=45 else "REDUCE RISK"
    risk="HIGH" if (vol or 0)>55 else "MEDIUM" if (vol or 0)>30 else "LOW"
    return {"score":round(score,1),"action":action,"risk":risk,"rsi":rv,"macd":mh,"support":sup,"resistance":res,"volatility":vol}

def market_brief(score,vix,ten,dollar):
    notes=[]
    if score>=70:notes.append("시장 추세는 강한 편입니다.")
    elif score>=52:notes.append("시장 추세는 중립 이상입니다.")
    else:notes.append("시장 위험이 높은 상태입니다.")
    if vix is not None:
        notes.append("VIX가 높아 변동성 관리가 필요합니다." if vix>22 else "VIX는 비교적 안정적입니다.")
    if ten is not None and ten>4.5:notes.append("10년물 금리가 성장주에 부담을 줄 수 있습니다.")
    if dollar is not None and dollar>104:notes.append("강달러가 위험자산에 부담입니다.")
    return " ".join(notes)
