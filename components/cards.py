import streamlit as st

def stars(score):
    n=max(1,min(5,round(score/20)))
    return "★"*n+"☆"*(5-n)

def badge(score):
    if score>=80:return "VERY STRONG"
    if score>=65:return "BULLISH"
    if score>=50:return "NEUTRAL"
    if score>=35:return "CAUTION"
    return "RISK OFF"

def card(label,value,note="",tone="blue"):
    st.markdown(f"""
    <div class="kcard">
      <div class="klabel">{label}</div>
      <div class="kvalue {tone}">{value}</div>
      <div class="knote">{note}</div>
    </div>
    """,unsafe_allow_html=True)
