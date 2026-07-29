import streamlit as st
from engine.market_data import history,quote
from engine.analysis import analyze
from components.cards import stars
from utils.formatters import money,pct
def render():
    st.title("AI Analysis Engine")
    t=st.text_input("Ticker","GOOGL").upper().strip()
    if not t:return
    h=history(t,"1y");q=quote(t);a=analyze(h)
    c=st.columns(6)
    c[0].metric("Price",money(q["price"]),pct(q["change_pct"]))
    c[1].metric("Score",f'{a["score"]:.0f}/100')
    c[2].metric("Rating",stars(a["score"]))
    c[3].metric("Action",a["action"])
    c[4].metric("Risk",a["risk"])
    c[5].metric("Volatility","—" if a["volatility"] is None else f'{a["volatility"]:.1f}%')
    if a["score"]>=78:msg="추세가 강합니다. 다만 급등한 날 추격하지 말고 눌림목에서 분할 접근하세요."
    elif a["score"]>=62:msg="매수 후보입니다. 지지선 근처에서 2~3단계로 나누는 전략이 적합합니다."
    elif a["score"]>=45:msg="방향이 명확하지 않습니다. 실적·금리·섹터 흐름 확인 후 기다리는 편이 낫습니다."
    else:msg="위험 관리가 우선입니다. 신규 매수보다 반등 시 비중 축소를 검토하세요."
    st.markdown(f"""<div class="panel"><div class="klabel">AI DECISION</div><div style="font-size:26px;font-weight:850;margin:9px 0">{a["action"]}</div>
    <div style="line-height:1.8">{msg}</div><span class="chip">Support {money(a["support"])}</span><span class="chip">Resistance {money(a["resistance"])}</span></div>""",unsafe_allow_html=True)
