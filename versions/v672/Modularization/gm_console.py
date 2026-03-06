"""carmine.gm_console — GM console command parser"""
import re, random
from constants import *
from economy import (compute_gtc_debt, apply_gtc_debt_service, price_shock_delta,
                     compute_church_tithe, compute_tithe_income, fmt_cr)
from events import apply_tithes, roll_market_events, _MARKET_SHOCK
from npc import npc_military_ai, _NPC_UNITS, _VET_LADDER
from discord_export import _discord_export, _discord_market_export

# ── GM console ────────────────────────────────────────────────────────────────
def run_gm_command(cmd, sm):
    """
    Commands:
      set "<nation>" <field> <value>
      give "<nation>" <resource> <amount>
      setmodel "<nation>" <PLANNED|MARKET|MIXED|COLONY_START>
      advance <n>
      tithe
      list nations
      help
    """
    cmd=cmd.strip()
    if not cmd: return "No command."
    parts=cmd.split()
    verb=parts[0].lower()

    if verb=="help":
        return ('set "Nation" field value\n'
                'give "Nation" resource amount\n'
                'setmodel "Nation" PLANNED|MARKET|MIXED|COLONY_START\n'
                'advance N\n'
                'tithe  (manually apply tithes)\n'
                'market discord  (export galactic market report)\n'
                'shock <resource> <pct>  (e.g. shock Energy +25)\n'
                'setnpc "Nation"  /  setplayer "Nation"\n'
                'npc automate  (run military AI for all NPC nations now)\n'
                'list nations')

    if verb=="list" and len(parts)>1 and parts[1]=="nations":
        return "\n".join(sm.nation_names())

    if verb=="tithe":
        evs=apply_tithes(sm.state); sm.mark_dirty(); sm.autosave()
        return f"Tithe applied. {len(evs)} transactions."

    if verb=="market" and len(parts)>1 and parts[1]=="discord":
        path=_discord_market_export(sm.state)
        return f"Galactic Market Report -> {path}"

    if verb=="shock":
        # shock <resource> <pct>   e.g.  shock Energy +25   or  shock Food -15
        if len(parts)<3: return "Usage: shock <resource> <pct>  e.g. shock Energy +25"
        rname=" ".join(parts[1:-1]); pct_s=parts[-1]
        matched=next((r for r in _RESOURCES if r.lower()==rname.lower()),None)
        if not matched: return f"Unknown resource. Options: {_RESOURCES}"
        try: pct=float(pct_s)/100.0
        except: return f"Invalid pct: {pct_s}"
        market=sm.state.setdefault("market",{})
        mods=market.setdefault("market_modifier",{})
        base=market.get("price_base",{}).get(matched,RES_BASE_PRICE[matched])
        old=mods.get(matched,base)
        new=round(max(base*0.2, old*(1.0+pct)),4); mods[matched]=new
        ph=market.setdefault("price_history",{}); ph.setdefault(matched,[]).append(new)
        t=sm.state.get("turn",1); y=sm.state.get("year",2200); q=sm.state.get("quarter",1)
        sm.state.setdefault("events_log",[]).append({"turn":t,"year":y,"quarter":q,"type":"Market",
            "resource":matched,"roll":"GM","label":"GM Shock",
            "description":f"{matched}: GM Shock ({pct*100:+.1f}%) {old:.4f} -> {new:.4f} cr",
            "col_rgb":list(GOLD)})
        sm.mark_dirty(); sm.autosave()
        return f"Price shock applied: {matched} {pct*100:+.1f}%  {old:.4f} -> {new:.4f} cr"

    if verb in ("setnpc","setplayer"):
        m2=re.search(r'"([^"]+)"',cmd)
        if not m2: return f'Usage: {verb} "Nation Name"'
        nname=m2.group(1); nation=sm.get_nation(nname)
        if not nation: return f"Nation '{nname}' not found."
        nation["is_npc"]=(verb=="setnpc")
        sm.mark_dirty(); sm.autosave()
        status="NPC (automated)" if nation["is_npc"] else "Player (manual)"
        return f"{nname} set to {status}."

    if verb=="npc" and len(parts)>1 and parts[1]=="automate":
        t=sm.state.get("turn",1); y=sm.state.get("year",2200); q=sm.state.get("quarter",1)
        evs=[]; count=0
        for nation in sm.state.get("nations",[]):
            if nation.get("is_npc") and not is_colony(nation):
                evs.extend(npc_military_ai(nation,sm.state,t,y,q)); count+=1
        sm.state.setdefault("events_log",[]).extend(evs)
        sm.mark_dirty(); sm.autosave()
        return f"NPC military AI run for {count} nations. {len(evs)} events generated."

    if verb=="advance" and len(parts)>1:
        try: n=int(parts[1])
        except: return "Usage: advance N"
        evs=advance_turns(sm,n)
        return f"Advanced {n} turns. {len(evs)} events."

    # parse quoted nation name
    import re
    m=re.match(r'(\w+)\s+"([^"]+)"\s*(.*)',cmd)
    if not m: return f"Unknown command or bad syntax. Type 'help'."
    verb2=m.group(1).lower(); nname=m.group(2); rest=m.group(3).strip().split()
    nation=sm.get_nation(nname)
    if not nation: return f"Nation '{nname}' not found."

    if verb2=="setmodel":
        if not rest: return "Usage: setmodel \"Nation\" MODEL"
        model=rest[0].upper()
        if model not in ECON_MODELS: return f"Model must be one of: {ECON_MODELS}"
        nation["economic_model"]=model
        if model=="COLONY_START": nation["is_colony_start"]=True
        else: nation["is_colony_start"]=False
        sm.mark_dirty(); sm.autosave()
        return f"{nname} economic model set to {model}."

    if verb2=="give":
        if len(rest)<2: return "Usage: give \"Nation\" resource amount"
        rname=" ".join(rest[:-1]); amt_s=rest[-1]
        # handle "Consumer Goods" etc
        try: amt=float(amt_s)
        except: return f"Invalid amount: {amt_s}"
        matched=next((r for r in _RESOURCES if r.lower()==rname.lower()),None)
        if not matched: return f"Unknown resource. Options: {_RESOURCES}"
        sp=nation.get("resource_stockpiles",{})
        if not isinstance(sp.get(matched),dict): sp[matched]={"stockpile":0.0}
        sp[matched]["stockpile"]=sp[matched].get("stockpile",0.0)+amt
        nation["resource_stockpiles"]=sp; sm.mark_dirty(); sm.autosave()
        return f"Gave {fmt_res(amt)} {matched} to {nname}."

    if verb2=="set":
        if len(rest)<2: return "Usage: set \"Nation\" field value"
        field=rest[0]; val_s=" ".join(rest[1:])
        try: val=float(val_s)
        except: val=val_s
        nation[field]=val; sm.mark_dirty(); sm.autosave()
        return f"{nname}.{field} = {val}"

    return f"Unknown command '{verb2}'. Type 'help'."

