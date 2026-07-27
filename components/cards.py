import streamlit as st

def stars(score: float) -> str:
    n = max(1, min(5, round(score / 20)))
    return "★" * n + "☆" * (5 - n)

def score_badge(score: float) -> str:
    if score >= 80: return "STRONG"
    if score >= 65: return "POSITIVE"
    if score >= 50: return "NEUTRAL"
    if score >= 35: return "CAUTION"
    return "RISK OFF"

def html_card(label: str, value: str, note: str = "", state: str = "neutral"):
    klass = {
        "positive": "smcc-positive",
        "negative": "smcc-negative",
        "neutral": "smcc-neutral",
    }.get(state, "smcc-neutral")
    st.markdown(
        f"""
        <div class="smcc-card">
          <div class="smcc-label">{label}</div>
          <div class="smcc-value {klass}">{value}</div>
          <div class="smcc-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
