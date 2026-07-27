import streamlit as st
from utils.storage import load_json,save_json
DEFAULT={"name":"Sungje","risk_profile":"Balanced","default_budget":5000,"rules":"No crypto. No biotech. Prefer staged entries."}
def render():
    st.title("Settings")
    x=load_json("settings.json",DEFAULT)
    with st.form("s"):
        name=st.text_input("Name",x.get("name","Sungje"));opts=["Conservative","Balanced","Aggressive"]
        risk=st.selectbox("Risk Profile",opts,index=opts.index(x.get("risk_profile","Balanced")))
        budget=st.number_input("Default Budget",min_value=100.0,value=float(x.get("default_budget",5000)),step=100.0)
        rules=st.text_area("Investment Rules",x.get("rules",""))
        if st.form_submit_button("Save"):
            save_json("settings.json",{"name":name,"risk_profile":risk,"default_budget":budget,"rules":rules});st.success("Saved")
    if st.button("Refresh market cache"):st.cache_data.clear();st.success("Cache cleared")
