import plotly.graph_objects as go

def price_chart(df,ticker):
    fig=go.Figure()
    if df.empty: return fig
    fig.add_trace(go.Candlestick(x=df.index,open=df['Open'],high=df['High'],low=df['Low'],close=df['Close'],name=ticker))
    for w in (20,50):
        if len(df)>=w:
            fig.add_trace(go.Scatter(x=df.index,y=df['Close'].rolling(w).mean(),mode='lines',name=f'MA{w}'))
    fig.update_layout(height=520,margin=dict(l=10,r=10,t=35,b=10),xaxis_rangeslider_visible=False,legend_orientation='h',template='plotly_dark')
    return fig
