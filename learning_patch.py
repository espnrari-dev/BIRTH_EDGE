import os
path="learning.py"
t=open(path).read()
old="    conn = sqlite3.connect(LEARNING_DB)\n    cur = conn.cursor()\n    cur.execute(\"\"\"\n        INSERT OR REPLACE INTO learning_results"
new="""    # pull price from dict
    iprice = float(token_data.get('initial_price_usd') or token_data.get('priceUsd') or token_data.get('price_usd') or token_data.get('result',{}).get('initial_price_usd') or token_data.get('result',{}).get('priceUsd') or 0.0)
    if iprice==0:
        try: iprice=float(token_data.get('liquidity_usd',0))/1000000
        except: iprice=1e-05
    conn = sqlite3.connect(LEARNING_DB)
    cur = conn.cursor()
    cur.execute(\"\"\"
        INSERT OR REPLACE INTO learning_results"""
# second replace to use iprice
t=t.replace(old,new)
# replace the values tuple part
t=t.replace('        token_data.get("addr"),\n        token_data.get("chain"),\n        token_data.get("symbol", "?"),\n        initial_price_usd,', '        token_data.get("addr"),\n        token_data.get("chain"),\n        token_data.get("symbol", "?"),\n        iprice or initial_price_usd,')
open(path,'w').write(t)
print("patched learning.py")
