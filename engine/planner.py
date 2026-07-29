def build(base,budget,spacing,weights=(.35,.35,.30)):
    rows=[]
    for i,w in enumerate(weights):
        price=base*(1-(spacing/100)*i);alloc=budget*w;shares=int(alloc//price) if price>0 else 0
        rows.append({"Stage":f"{i+1}차","Buy Price":round(price,2),"Allocation":round(alloc,2),
                     "Shares":shares,"Estimated Cost":round(shares*price,2)})
    return rows
