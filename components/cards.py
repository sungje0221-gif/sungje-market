def score_badge(score):
    if score >= 80: return 'STRONG'
    if score >= 65: return 'POSITIVE'
    if score >= 50: return 'NEUTRAL'
    if score >= 35: return 'CAUTION'
    return 'RISK OFF'

def stars(score):
    n=max(1,min(5,round(score/20)))
    return '★'*n+'☆'*(5-n)
