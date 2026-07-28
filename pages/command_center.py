from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import streamlit as st
from engine.market_data import quote, history
from engine.indicators import trend_score
from engine.analysis import market_brief
from utils.watchlist_store import load_watchlist_data
from utils.preferences import load_market_groups
from utils.formatters import money, pct

@st.cache_data(ttl=300, show_spinner=False)
def _score(t):
    try:return float(trend_score(history(t,"6mo")) or 50)
    except Exception:return 50.0

def _card(label,ticker):
    q=quote(ticker); c=q.get("change_pct"); cls="up" if (c or 0)>=0 else "down"
    return f'<div class="watch-card"><div class="watch-head"><b>{escape(label)}</b><span>{ticker}</span></div><div class="watch-price">{money(q.get("price"))}</div><div class="watch-change {cls}">{pct(c)}</div></div>'

def render():
    now=datetime.now(ZoneInfo("America/Los_Angeles"))
    greeting="Morning" if now.hour<12 else "Afternoon" if now.hour<18 else "Evening"
    groups=load_market_groups(); core=list(groups.get("Futures",[]))[:5]
    vix=quote("^VIX")
    score=round((_score("SPY")+_score("QQQ"))/2)
    regime="RISK ON" if score>=60 and (vix.get("price") or 20)<25 else "DEFENSIVE" if score<42 else "SELECTIVE"
    st.markdown(f'''<div class="hero terminal-hero"><div class="hero-row"><div class="hero-copy"><div class="hero-kicker">COMMAND CENTER</div><div class="hero-title">Good {greeting}, Sungje</div><div class="hero-sub">{now.strftime('%A, %B %d · %I:%M %p')} Pacific Time</div><div class="market-regime neutral"><span></span>{regime}</div></div><div class="hero-market-strip">{''.join(_card(a,t) for a,t in core[:4])}</div></div></div>''',unsafe_allow_html=True)

    st.markdown('<div class="section-heading"><div><span>YOUR MARKET</span><h3>Today at a glance</h3></div><em>Editable in Markets</em></div>',unsafe_allow_html=True)
    cols=st.columns(len(core) or 1)
    for col,(label,ticker) in zip(cols,core):
        with col: st.markdown(_card(label,ticker),unsafe_allow_html=True)

    records=load_watchlist_data([]); ranked=[]
    for item in records:
        t=item["ticker"]; q=quote(t); sc=_score(t)
        ranked.append((abs(q.get("change_pct") or 0)+abs(sc-50)/25,t,q,sc,item))
    ranked=sorted(ranked,reverse=True)[:6]
    st.markdown('<div class="section-heading"><div><span>AI PRIORITY RADAR</span><h3>What deserves attention</h3></div><em>Calculated from your watchlist</em></div>',unsafe_allow_html=True)
    if not ranked:
        st.info("Watchlist에 종목을 추가하면 오늘 중요한 종목을 자동으로 골라줍니다.")
    else:
        cols=st.columns(3)
        for idx,(_,t,q,sc,item) in enumerate(ranked):
            c=q.get("change_pct") or 0; action="BUY/HOLD" if sc>=62 else "CAUTION" if sc<42 else "WATCH"
            tone="buy" if sc>=62 else "avoid" if sc<42 else "watch"
            with cols[idx%3]:
                st.markdown(f'<div class="action-card {tone}"><div class="action-top"><div class="action-label">{action}</div><span>{sc:.0f}/100</span></div><div style="font-size:20px;font-weight:900;margin-top:9px">{t} · {money(q.get("price"))}</div><div class="action-copy"><span class={"up" if c>=0 else "down"}>{c:+.2f}%</span> · {escape(item.get("tag") or "Watch")}<br>{escape(item.get("memo") or "Trend and daily movement priority")}</div></div>',unsafe_allow_html=True)

    left,right=st.columns([1.4,1])
    with left:
        st.markdown('### Quick watchlist')
        if ranked:
            for start in range(0,len(ranked),3):
                cc=st.columns(3)
                for col,(_,t,q,sc,item) in zip(cc,ranked[start:start+3]):
                    with col: st.markdown(_card(t,t),unsafe_allow_html=True)
    with right:
        st.markdown('### Decision context')
        brief=market_brief(score,vix.get("price"),quote("^TNX").get("price"),quote("DX-Y.NYB").get("price"))
        st.markdown(f'<div class="ai-brief-panel"><div class="ai-brief-head"><span>OS SIGNAL</span><b>{score}/100</b></div><div class="ai-brief-copy">{escape(str(brief))}</div></div>',unsafe_allow_html=True)
