import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def candlestick(df, ticker, show_ma20=True, show_ma50=True, show_ma200=True, show_volume=True):
    rows = 2 if show_volume else 1
    row_heights = [.76, .24] if show_volume else [1.0]
    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=.035,
    )
    if df.empty:
        return fig

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
        ),
        row=1,
        col=1,
    )

    ma_options = [
        (20, show_ma20),
        (50, show_ma50),
        (200, show_ma200),
    ]
    for window, enabled in ma_options:
        if enabled and len(df) >= window:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Close"].rolling(window).mean(),
                    name=f"MA{window}",
                    mode="lines",
                    line=dict(width=1.5),
                ),
                row=1,
                col=1,
            )

    if show_volume and "Volume" in df:
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="Volume",
                opacity=.55,
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        height=650,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=5, r=5, t=35, b=5),
        paper_bgcolor="#0c1828",
        plot_bgcolor="#0c1828",
        legend_orientation="h",
        hovermode="x unified",
    )
    return fig

def sector_treemap(df):
    fig = go.Figure(go.Treemap(
        labels=df["Sector"],
        parents=[""] * len(df),
        values=[1] * len(df),
        marker=dict(colors=df["Daily %"], colorscale="RdYlGn", cmid=0),
        text=df["Daily %"].map(lambda x: "—" if pd.isna(x) else f"{x:+.2f}%"),
        textinfo="label+text",
        hovertemplate="<b>%{label}</b><br>Daily: %{text}<extra></extra>"
    ))
    fig.update_layout(height=390, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#0c1828")
    return fig

def gauge(value, title, max_value=100):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title},
        gauge={
            "axis": {"range": [0, max_value]},
            "bar": {"color": "#60A5FA"},
            "steps": [
                {"range": [0, max_value * .35], "color": "#3a1520"},
                {"range": [max_value * .35, max_value * .65], "color": "#3a3516"},
                {"range": [max_value * .65, max_value], "color": "#12372f"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(l=20, r=20, t=45, b=15), paper_bgcolor="#0c1828")
    return fig
