def money(v):
    return '—' if v is None else f'${v:,.2f}'
def pct(v):
    return '—' if v is None else f'{v:+.2f}%'
