
            import json, fcntl, time, os, hashlib
            BASE="/data/data/com.termux/files/home/BIRTH_EDGE"
            LOG=f"{BASE}/data/event_log.jsonl"
            TREAS=f"{BASE}/data/treasury.jsonl"
            BAL=f"{BASE}/data/balance.json"
            def get_bal():
                try: return json.load(open(BAL))["balance"]
                except: return 1.5
            def set_bal(b): json.dump({"balance":b,"t":int(time.time())}, open(BAL,"w"))
            def load():
                s={}
                for l in open(LOG):
                    try:
                        ev=json.loads(l)
                        if ev.get("symbol"): s[ev["symbol"]]=ev
                    except: pass
                return s
            def opens():
                o={}
                for l in open(TREAS):
                    try:
                        ev=json.loads(l); sym=ev.get("symbol")
                        if not sym: continue
                        if ev["type"]=="trade_open": o[sym]=ev
                        if ev["type"] in ("profit","loss"): o.pop(sym,None)
                    except: pass
                return o
            st=load(); op=opens()
            print(f"[EXIT] {len(op)} open bal {get_bal():.4f}", flush=True)
            for sym,pos in list(op.items()):
                cur=st.get(sym)
                if not cur: continue
                e=pos["mcap_cents"]; n=cur["mcap_cents"]; r=n/max(1,e)
                if r>=2 or r<=0.5:
                    amt=pos["amount_sol"]; pnl=amt*(r-1); side="profit" if r>=2 else "loss"
                    ret=amt*2 if r>=2 else amt*0.5
                    before=get_bal()
                    after=before+amt if side=="profit" else before-amt*0.5
                    ev={"type":side,"t":int(time.time()),"symbol":sym,"mcap_cents":n,"entry_mcap":e,"exit_mcap":n,"amount_sol":ret,"pnl_sol":pnl,"ratio":r,"balance_before":before,"balance_after":after,"proof":hashlib.sha256(f"{sym}{n}{time.time()}".encode()).hexdigest()[:8]}
                    for p in [TREAS,LOG]:
                        with open(p,"a") as f:
                            fcntl.flock(f,fcntl.LOCK_EX); f.write(json.dumps(ev)+"
"); fcntl.flock(f,fcntl.LOCK_UN)
                    set_bal(after)
                    print(f"[EXIT] {side} {sym} x{r:.2f} bal {after:.4f}", flush=True)
