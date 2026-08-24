import os
path="main.py"
text=open(path).read()
# inject price into result before record
old="                result=await call_filters(addr, chain, liq, pair_obj or t)"
new="""                result=await call_filters(addr, chain, liq, pair_obj or t)
                try:
                    price = float((pair_obj or t).get('priceUsd',0) or (pair_obj or t).get('price_usd',0) or 0)
                    if price>0:
                        result['initial_price_usd']=price
                        result['priceUsd']=price
                except: pass"""
if old in text:
    text=text.replace(old,new)
    open(path,'w').write(text)
    print("patched main.py")
else:
    print("already patched or not found")
