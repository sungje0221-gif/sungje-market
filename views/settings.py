import streamlit as st
from utils.storage import load_json,save_json

DEFAULT={"name":"Sungje","risk_profile":"Balanced","default_budget":5000,
         "notes":"No crypto, no biotech. Prefer staged entries."}

def render():
    st.title("Settings")
    x=load_json("settings.json",DEFAULT)
    with st.form("settings"):
        name=st.text_input("Name",x.get("name","Sungje"))
        opts=["Conservative","Balanced","Aggressive"]; risk=st.selectbox("Risk Profile",opts,index=opts.index(x.get("risk_profile","Balanced")))
        budget=st.number_input("Default Buy Budget",min_value=100.0,value=float(x.get("default_budget",5000)),step=100.0)
        notes=st.text_area("Investment Rules",x.get("notes",""))
        if st.form_submit_button("Save"):
            save_json("settings.json",{"name":name,"risk_profile":risk,"default_budget":budget,"notes":notes})
            st.success("저장했습니다.")
    if st.button("가격 캐시 새로고침"):
        st.cache_data.clear(); st.success("캐시를 비웠습니다.")
