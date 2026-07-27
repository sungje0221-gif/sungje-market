import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def candlestick(df,ticker):
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.74,.26],vertical_spacing=.03)
    if df.empty:return fig
    fig.add_trace(go.Candlestick(
        x=df.index,open=df["Open"],high=df["High"],low=df["Low"],close=df["Close"],name=ticker
    ),row=1,col=1)
    for w in (20,50,200):
        if len(df)>=w:
            fig.add_trace(go.Scatter(x=df.index,y=df["Close"].rolling(w).mean(),name=f"MA{w}",mode="lines"),row=1,col=1)
    if "Volume" in df:
        fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="Volume"),row=2,col=1)
    fig.update_layout(height=620,template="plotly_dark",xaxis_rangeslider_visible=False,
                      margin=dict(l=5,r=5,t=30,b=5),paper_bgcolor="#0c1828",plot_bgcolor="#0c1828",
                      legend_orientation="h")
    return fig

def sector_treemap(df):
    fig=go.Figure(go.Treemap(
        labels=df["Sector"],parents=[""]*len(df),values=[1]*len(df),
        marker=dict(colors=df["Daily %"],colorscale="RdYlGn",cmid=0),
        text=df["Daily %"].map(lambda x:"—" if pd.isna(x) else f"{x:+.2f}%"),
        textinfo="label+text",
        hovertemplate="<b>%{label}</b><br>Daily: %{text}<extra></extra>"
    ))
    fig.update_layout(height=390,margin=dict(l=0,r=0,t=0,b=0),paper_bgcolor="#0c1828")
    return fig

def gauge(value,title,max_value=100):
    fig=go.Figure(go.Indicator(
        mode="gauge+number",value=value,title={"text":title},
        gauge={"axis":{"range":[0,max_value]},
               "bar":{"color":"#60A5FA"},
               "steps":[{"range":[0,max_value*.35],"color":"#3a1520"},
                        {"range":[max_value*.35,max_value*.65],"color":"#3a3516"},
                        {"range":[max_value*.65,max_value],"color":"#12372f"}]}
    ))
    fig.update_layout(height=220,margin=dict(l=20,r=20,t=45,b=15),paper_bgcolor="#0c1828")
    return fig
