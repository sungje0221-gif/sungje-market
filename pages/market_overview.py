from __future__ import annotations
import streamlit as st
from engine.market_data import quote
from utils.preferences import load_market_groups, save_market_groups, DEFAULT_MARKETS

def _fmt(label,p):
    if p is None:return "—"
    if label=="US 10Y":return f"{p:.3f}%"
    if label=="USD/KRW":return f"₩{p:,.2f}"
    return f"{p:,.2f}"

def _card(label,ticker):
    q=quote(ticker); c=q.get("change_pct")
    cls="up" if (c or 0)>0 else "down" if (c or 0)<0 else "flat"
    arrow="▲" if (c or 0)>0 else "▼" if (c or 0)<0 else "•"
    delta="—" if c is None else f"{arrow} {c:+.2f}%"
    return f'<div class="future-card {cls}"><div class="future-label">{label}</div><div class="future-price">{_fmt(label,q.get("price"))}</div><div class="future-change">{delta}</div><div class="future-note">{ticker}</div></div>'

def render():
    st.title("Markets")
    st.caption("Futures, macro and Korea widgets. Every item is editable.")
    groups=load_market_groups()
    with st.expander("⚙ Edit market widgets"):
        group=st.selectbox("Section",list(groups))
        rows=groups[group]
        text=st.text_area("One item per line: Label | Ticker",value="\n".join(f"{a} | {b}" for a,b in rows),height=170)
        c1,c2=st.columns(2)
        if c1.button("Save section",type="primary",use_container_width=True):
            parsed=[]
            for line in text.splitlines():
                if "|" in line:
                    a,b=[x.strip() for x in line.split("|",1)]
                    if a and b: parsed.append([a,b.upper()])
            groups[group]=parsed; save_market_groups(groups); st.cache_data.clear(); st.rerun()
        if c2.button("Restore defaults",use_container_width=True):
            save_market_groups(DEFAULT_MARKETS); st.rerun()
    for name,rows in groups.items():
        st.markdown(f'<div class="market-section"><span>EDITABLE MARKET GROUP</span><h3>{name}</h3></div>',unsafe_allow_html=True)
        for start in range(0,len(rows),5):
            cols=st.columns(min(5,len(rows)-start))
            for col,(label,ticker) in zip(cols,rows[start:start+5]):
                with col: st.markdown(_card(label,ticker),unsafe_allow_html=True)
