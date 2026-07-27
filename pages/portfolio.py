import pandas as pd,streamlit as st
from engine.portfolio import enrich
from utils.storage import load_csv,save_csv
from utils.formatters import money

COLS=["Account","Ticker","Shares","Avg Cost","Category"]
def render():
    st.title("Portfolio")
    df=load_csv("portfolio.csv",COLS)
    with st.expander("Add position",expanded=df.empty):
        with st.form("p"):
            c=st.columns(5)
            acc=c[0].text_input("Account","Taxable");t=c[1].text_input("Ticker").upper().strip()
            sh=c[2].number_input("Shares",min_value=0.0,step=1.0);avg=c[3].number_input("Avg Cost",min_value=0.0,step=.01)
            cat=c[4].selectbox("Category",["ETF","Mega Cap","AI","Semiconductor","Power","Defense","Healthcare","Other"])
            if st.form_submit_button("Add") and t and sh>0:
                df=pd.concat([df,pd.DataFrame([[acc,t,sh,avg,cat]],columns=COLS)],ignore_index=True);save_csv("portfolio.csv",df);st.rerun()
    if df.empty:st.info("No positions yet.");return
    e=enrich(df);mv=e["Market Value"].sum();cost=e["Cost Basis"].sum();pl=e["P/L"].sum();ret=(mv/cost-1)*100 if cost else 0
    c=st.columns(4);c[0].metric("Market Value",money(mv));c[1].metric("Total P/L",money(pl),f"{ret:+.2f}%");c[2].metric("Positions",len(e))
    largest=e.loc[e["Weight %"].idxmax()];c[3].metric("Largest Position",largest["Ticker"],f'{largest["Weight %"]:.1f}%')
    st.dataframe(e,use_container_width=True,hide_index=True,
      column_config={"Avg Cost":st.column_config.NumberColumn(format="$%.2f"),"Current Price":st.column_config.NumberColumn(format="$%.2f"),
      "Market Value":st.column_config.NumberColumn(format="$%.2f"),"P/L":st.column_config.NumberColumn(format="$%.2f"),
      "P/L %":st.column_config.NumberColumn(format="%.2f%%"),"Weight %":st.column_config.ProgressColumn(min_value=0,max_value=100)})
    st.markdown("### Allocation")
    alloc=e.groupby("Category")["Market Value"].sum();st.bar_chart(alloc/alloc.sum()*100)
    if largest["Weight %"]>25:st.warning(f'{largest["Ticker"]} 비중이 {largest["Weight %"]:.1f}%로 높습니다.')
    t=st.selectbox("Remove position",e["Ticker"].tolist())
    if st.button("Remove"):
        save_csv("portfolio.csv",df[df["Ticker"]!=t]);st.rerun()
