import streamlit as st
from utils.storage import load_json,save_json
DEFAULT={'name':'Sungje','risk_profile':'Balanced','default_budget':5000,'notes':'No crypto, no biotech. Prefer staged entries.'}

def render():
    st.title('Settings'); s=load_json('settings.json',DEFAULT)
    with st.form('settings'):
        name=st.text_input('Name',s.get('name','Sungje')); options=['Conservative','Balanced','Aggressive']; risk=st.selectbox('Risk Profile',options,index=options.index(s.get('risk_profile','Balanced'))); budget=st.number_input('Default Buy Budget',min_value=100.0,value=float(s.get('default_budget',5000)),step=100.0); notes=st.text_area('Investment Rules',s.get('notes',''))
        if st.form_submit_button('Save'):
            save_json('settings.json',{'name':name,'risk_profile':risk,'default_budget':budget,'notes':notes}); st.success('저장했습니다.')
    st.write('현재 버전은 Yahoo Finance 기반이며 완전한 실시간 시세를 보장하지 않습니다.')
    if st.button('가격 캐시 새로고침'): st.cache_data.clear(); st.success('캐시를 비웠습니다.')
