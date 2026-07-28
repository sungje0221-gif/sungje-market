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
    intraday=False,
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
        height=720 if intraday else 820,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=5, r=5, t=35, b=5),
        paper_bgcolor="#0c1828",
        plot_bgcolor="#0c1828",
        legend_orientation="h",
        hovermode="x unified",
    )
    if intraday:
        # Remove overnight/weekend gaps so one trading session fills the chart.
        fig.update_xaxes(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),
                dict(bounds=[16, 9.5], pattern="hour"),
            ],
            tickformat="%I:%M %p",
            nticks=12,
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


def stock_heatmap(df, title="Market Heat Map"):
    """Render a stable flat treemap for Streamlit Cloud.

    A flat treemap is intentional here. The previous hierarchical version used
    sector names as parents without creating matching parent nodes, which could
    leave Plotly showing only the color bar and an empty chart area.
    """
    required = {"Ticker", "Change %"}
    if df is None or df.empty or not required.issubset(df.columns):
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_dark", height=650)
        return fig

    clean = df.loc[:, ~df.columns.duplicated()].copy()
    clean["Ticker"] = clean["Ticker"].astype(str).str.strip()
    clean = clean[clean["Ticker"].ne("") & clean["Ticker"].ne("nan")]

    clean["Price"] = pd.to_numeric(clean.get("Price", 0), errors="coerce").fillna(0.0)
    clean["Change %"] = pd.to_numeric(clean["Change %"], errors="coerce").fillna(0.0)
    clean["Weight"] = pd.to_numeric(clean.get("Weight", 1), errors="coerce").fillna(1.0).clip(lower=0.01)
    if "Sector" not in clean.columns:
        clean["Sector"] = "Market"
    clean["Sector"] = clean["Sector"].fillna("Market").astype(str)

    if clean.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_dark", height=650)
        return fig

    labels = clean["Ticker"].tolist()
    values = clean["Weight"].astype(float).tolist()
    changes = clean["Change %"].astype(float).tolist()
    customdata = clean[["Price", "Sector"]].to_numpy()
    change_text = [f"{value:+.2f}%" for value in changes]

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=[""] * len(labels),
        values=values,
        marker=dict(
            colors=changes,
            colorscale=[
                [0.00, "#8B1E2D"],
                [0.35, "#C94B58"],
                [0.49, "#5B6472"],
                [0.51, "#5B6472"],
                [0.65, "#2D8A70"],
                [1.00, "#0E5F4D"],
            ],
            cmid=0,
            colorbar=dict(title="Daily %"),
            line=dict(width=1, color="#071321"),
        ),
        text=change_text,
        customdata=customdata,
        texttemplate="<b>%{label}</b><br>%{text}",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Price: $%{customdata[0]:,.2f}<br>"
            "Sector: %{customdata[1]}<br>"
            "Daily: %{color:+.2f}%<extra></extra>"
        ),
        pathbar=dict(visible=False),
        tiling=dict(packing="squarify", pad=2),
    ))
    fig.update_layout(
        title=title,
        height=560,
        margin=dict(l=4, r=4, t=42, b=4),
        paper_bgcolor="#0c1828",
        plot_bgcolor="#0c1828",
        template="plotly_dark",
    )
    return fig

def market_breadth_bar(df):
    """Horizontal performance ranking used beneath heatmaps."""
    clean = df.dropna(subset=["Change %"]).sort_values("Change %")
    if clean.empty:
        return go.Figure()
    colors = ["#ff6677" if value < 0 else "#2fd39a" for value in clean["Change %"]]
    fig = go.Figure(go.Bar(
        x=clean["Change %"], y=clean["Ticker"], orientation="h",
        marker_color=colors,
        text=clean["Change %"].map(lambda value: f"{value:+.2f}%"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:+.2f}%<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1, line_color="rgba(255,255,255,.25)")
    fig.update_layout(
        height=max(300, min(720, 32 * len(clean))),
        margin=dict(l=8, r=55, t=28, b=10),
        title="Relative Strength Ranking",
        template="plotly_dark", paper_bgcolor="#071321", plot_bgcolor="#071321",
        xaxis_title="Daily change (%)", yaxis_title=None, showlegend=False,
    )
    return fig


def performance_matrix(df):
    """Group-by-ticker heat matrix for quick cross-theme comparison."""
    clean = df.dropna(subset=["Change %"]).copy()
    if clean.empty:
        return go.Figure()
    groups = list(dict.fromkeys(clean["Sector"].tolist()))
    tickers = list(dict.fromkeys(clean["Ticker"].tolist()))
    z = []
    text = []
    for group in groups:
        row = []
        labels = []
        subset = clean[clean["Sector"] == group].set_index("Ticker")
        for ticker in tickers:
            value = subset.loc[ticker, "Change %"] if ticker in subset.index else None
            row.append(value)
            labels.append("" if value is None or pd.isna(value) else f"{value:+.2f}%")
        z.append(row)
        text.append(labels)
    fig = go.Figure(go.Heatmap(
        z=z, x=tickers, y=groups, text=text, texttemplate="%{text}",
        colorscale=[[0, "#8B1E2D"], [.42, "#d45b68"], [.5, "#26384b"], [.58, "#2D8A70"], [1, "#0E5F4D"]],
        zmid=0, colorbar=dict(title="Daily %"),
        hovertemplate="<b>%{x}</b><br>%{y}<br>%{z:+.2f}%<extra></extra>",
        xgap=3, ygap=3,
    ))
    fig.update_layout(
        height=470, title="Cross-Theme Performance Matrix",
        margin=dict(l=12, r=12, t=55, b=35), template="plotly_dark",
        paper_bgcolor="#071321", plot_bgcolor="#071321",
        xaxis=dict(side="top", tickangle=-35), yaxis=dict(autorange="reversed"),
    )
    return fig
