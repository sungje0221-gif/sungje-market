def money(v):
    return "—" if v is None else f"${v:,.2f}"
def pct(v):
    return "—" if v is None else f"{v:+.2f}%"
def compact(v):
    if v is None:return "—"
    n=float(v)
    for u in ["","K","M","B","T"]:
        if abs(n)<1000:return f"{n:,.1f}{u}"
        n/=1000
    return f"{n:,.1f}P"

def period_return(chart_data):
    """% return from the first to the last close in a price history frame."""
    if chart_data is None or chart_data.empty or "Close" not in chart_data:
        return None
    closes = chart_data["Close"].dropna()
    if len(closes) < 2 or closes.iloc[0] == 0:
        return None
    return (closes.iloc[-1] / closes.iloc[0] - 1) * 100

