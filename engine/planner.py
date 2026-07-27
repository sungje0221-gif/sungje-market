def build_plan(current_price, budget, steps=3, spacing_pct=4.0):
    weights = [0.35,0.35,0.30]
    rows = []
    for i in range(steps):
        price = current_price*(1-(spacing_pct/100)*i)
        allocation = budget*weights[i]
        shares = int(allocation//price) if price > 0 else 0
        rows.append({
            "Stage":f"{i+1}차",
            "Buy Price":round(price,2),
            "Allocation":round(allocation,2),
            "Shares":shares,
            "Estimated Cost":round(shares*price,2),
        })
    return rows
