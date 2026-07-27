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
