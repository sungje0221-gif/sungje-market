import plotly.graph_objects as go
import pandas as pd

def price_chart(df: pd.DataFrame, ticker: str):
    fig = go.Figure()
    if df.empty:
        return fig
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker
    ))
    for window in (20, 50):
        if len(df) >= window:
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df["Close"].rolling(window).mean(),
                mode="lines",
                name=f"MA{window}",
            ))
    fig.update_layout(
        height=520,
        margin=dict(l=5, r=5, t=30, b=5),
        xaxis_rangeslider_visible=False,
        legend_orientation="h",
        template="plotly_dark",
        paper_bgcolor="#0d1929",
        plot_bgcolor="#0d1929",
    )
    return fig

def sector_heatmap(df: pd.DataFrame):
    fig = go.Figure(go.Treemap(
        labels=df["Sector"],
        parents=[""] * len(df),
        values=[1] * len(df),
        marker=dict(colors=df["Score"], colorscale="RdYlGn", cmin=0, cmax=100),
        text=df["Daily %"].map(lambda x: "—" if pd.isna(x) else f"{x:+.2f}%"),
        textinfo="label+text",
        hovertemplate="<b>%{label}</b><br>Score: %{color:.0f}<extra></extra>",
    ))
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0d1929",
    )
    return fig
