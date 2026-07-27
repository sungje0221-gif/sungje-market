import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from engine.indicators import bollinger_bands, macd_series, rsi_series


def advanced_chart(
    df,
    ticker,
    show_ma20=True,
    show_ma50=True,
    show_ma100=True,
    show_ma200=True,
    show_bollinger=False,
    show_volume=True,
    show_rsi=True,
    show_macd=True,
):
    if df.empty:
        return go.Figure()

    rows = 1 + int(show_volume) + int(show_rsi) + int(show_macd)
    heights = [0.56]
    if show_volume:
        heights.append(0.14)
    if show_rsi:
        heights.append(0.15)
    if show_macd:
        heights.append(0.15)

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        row_heights=heights,
        vertical_spacing=0.025,
    )

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

    for window, enabled in [(20, show_ma20), (50, show_ma50), (100, show_ma100), (200, show_ma200)]:
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

    if show_bollinger and len(df) >= 20:
        middle, upper, lower = bollinger_bands(df["Close"])
        fig.add_trace(go.Scatter(x=df.index, y=upper, name="BB Upper", line=dict(width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=middle, name="BB Mid", line=dict(width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower, name="BB Lower", line=dict(width=1, dash="dot")), row=1, col=1)

    row = 2
    if show_volume:
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume", opacity=0.55), row=row, col=1)
        row += 1

    if show_rsi:
        rsi_values = rsi_series(df["Close"])
        fig.add_trace(go.Scatter(x=df.index, y=rsi_values, name="RSI 14", mode="lines"), row=row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_width=1, row=row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_width=1, row=row, col=1)
        fig.update_yaxes(range=[0, 100], row=row, col=1)
        row += 1

    if show_macd:
        macd_line, signal_line, histogram = macd_series(df["Close"])
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, name="MACD", mode="lines"), row=row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, name="Signal", mode="lines"), row=row, col=1)
        fig.add_trace(go.Bar(x=df.index, y=histogram, name="MACD Hist", opacity=0.55), row=row, col=1)

    fig.update_layout(
        height=820,
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
        hovertemplate="<b>%{label}</b><br>Daily: %{text}<extra></extra>",
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
