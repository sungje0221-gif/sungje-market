import pandas as pd,streamlit as st
from engine.market_data import quote
from engine.planner import build
from utils.formatters import money
def render():
    st.title("Buy Planner")
    c=st.columns(4)
    t=c[0].text_input("Ticker","GOOGL").upper().strip()
    budget=c[1].number_input("Budget",min_value=100.0,value=5000.0,step=100.0)
    spacing=c[2].slider("Spacing",1.0,15.0,4.0,.5,format="%.1f%%")
    current=quote(t)["price"];base=c[3].number_input("Base Price",min_value=.01,value=float(current) if current else 100.0,step=.01)
    plan=pd.DataFrame(build(base,budget,spacing))
    st.dataframe(plan,use_container_width=True,hide_index=True,
      column_config={"Buy Price":st.column_config.NumberColumn(format="$%.2f"),"Allocation":st.column_config.NumberColumn(format="$%.2f"),
      "Estimated Cost":st.column_config.NumberColumn(format="$%.2f")})
    shares=int(plan["Shares"].sum());cost=float(plan["Estimated Cost"].sum());avg=cost/shares if shares else 0
    c=st.columns(4);c[0].metric("Current",money(current));c[1].metric("Total Shares",shares);c[2].metric("Expected Cost",money(cost));c[3].metric("Expected Avg",money(avg))
    if current and current<=plan.iloc[0]["Buy Price"]:st.success("Current price is inside the first buy zone.")
    else:st.info("Current price is above the first buy zone. Wait rather than chase.")
