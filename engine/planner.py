def build_plan(current_price,budget,spacing_pct=4.0):
    weights=[.35,.35,.30]; rows=[]
    for i,w in enumerate(weights):
        price=current_price*(1-(spacing_pct/100)*i); allocation=budget*w; shares=int(allocation//price) if price>0 else 0
        rows.append({'Stage':f'{i+1}차','Buy Price':round(price,2),'Allocation':round(allocation,2),'Shares':shares,'Estimated Cost':round(shares*price,2)})
    return rows
