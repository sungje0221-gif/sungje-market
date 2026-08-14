from datetime import date
import pandas as pd,streamlit as st
from utils.storage import load_cloud_json,save_cloud_json,cloud_configured
COLS=["Date","Ticker","Action","Price","Shares","Reason","Result","Lesson"]
def render():
    st.title("Trading Journal")
    if not cloud_configured():
        st.caption("⚠️ Supabase가 설정되지 않아 로컬 임시저장만 됩니다 — 서버 재시작 시 기록이 사라질 수 있어요.")
    rows=load_cloud_json("journal",[])
    df=pd.DataFrame(rows,columns=COLS) if rows else pd.DataFrame(columns=COLS)
    with st.form("j"):
        c=st.columns(5);d=c[0].date_input("Date",date.today());t=c[1].text_input("Ticker").upper().strip()
        a=c[2].selectbox("Action",["BUY","SELL","HOLD","WATCH"]);p=c[3].number_input("Price",min_value=0.0,step=.01);s=c[4].number_input("Shares",min_value=0.0,step=1.0)
        reason=st.text_area("Reason");result=st.selectbox("Result",["OPEN","WIN","LOSS","BREAKEVEN"]);lesson=st.text_area("Lesson")
        if st.form_submit_button("Save") and t:
            updated=pd.concat([df,pd.DataFrame([[str(d),t,a,p,s,reason,result,lesson]],columns=COLS)],ignore_index=True)
            cloud_saved,error=save_cloud_json("journal",updated.to_dict("records"))
            if not cloud_saved:
                st.error(f"⚠️ Supabase 저장에 실패했습니다 — 지금은 로컬에만 저장되어 서버가 재시작되면 사라질 수 있습니다.\n\n{error}")
            else:
                st.rerun()
    if df.empty:st.info("No journal entries.");return
    wins=(df["Result"]=="WIN").sum();losses=(df["Result"]=="LOSS").sum();closed=wins+losses
    c=st.columns(4);c[0].metric("Entries",len(df));c[1].metric("Closed",closed);c[2].metric("Win Rate",f"{wins/closed*100:.1f}%" if closed else "0.0%")
    top=df["Ticker"].value_counts().index[0];c[3].metric("Most Traded",top)
    st.dataframe(df.sort_values("Date",ascending=False),use_container_width=True,hide_index=True)
