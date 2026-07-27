def money(value):
    return "—" if value is None else f"${value:,.2f}"

def pct(value):
    return "—" if value is None else f"{value:+.2f}%"
