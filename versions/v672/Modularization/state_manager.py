"""carmine.state_manager — StateManager (load/save/history) and advance_turns"""
import json, shutil, random
from pathlib import Path
from constants import *
from economy import (compute_resources, compute_trade, compute_planet_local_market,
                     compute_species_loyalty_happiness, econ_model_ipeu_modifier,
                     compute_debt, spending_effects, apply_gtc_debt_service,
                     compute_corp_income, advance_construction)
from events import (roll_market_events, roll_piracy_events,
                    roll_colony_events, roll_civic_events, apply_tithes,
                    roll_planetside_events, roll_resource_events)
from npc import npc_military_ai
from territory import _rng_name
from corporateAlpha0671 import (compute_corp_income, compute_corp_market_cap,
                                 roll_corp_events)

def advance_turns(sm,n_turns):
    all_evs=[]
    for _ in range(n_turns):
        t=sm.state.get("turn",1)+1; q=sm.state.get("quarter",1); y=sm.state.get("year",2200)
        q+=1
        if q>4: q=1; y+=1
        sm.state["turn"]=t; sm.state["quarter"]=q; sm.state["year"]=y
        for route in sm.state.get("trade_routes",[]): route["_piracy_loss_this_turn"]=0.0
        all_evs.extend(roll_market_events(sm.state))
        all_evs.extend(roll_piracy_events(sm.state))
        all_evs.extend(apply_tithes(sm.state))
        all_evs.extend(apply_gtc_debt_service(sm.state))
        for nation in sm.state.get("nations",[]):
            if is_colony(nation):
                # colony turn: vessel stockpiles tick, colony events
                vs=nation.get("vessel_stats",{}); vsp=nation.get("vessel_stockpiles",{})
                for rname in ["Food","Minerals","Alloys","Energy"]:
                    prod_key={"Food":"food_production","Minerals":"mineral_extraction",
                              "Alloys":"alloy_production","Energy":"energy_production"}.get(rname,"")
                    cons_key={"Food":"food_consumption","Energy":"energy_consumption"}.get(rname,"")
                    prod=vs.get(prod_key,0.0); cons=vs.get(cons_key,0.0) if cons_key else 0.0
                    vsp[rname]=max(0,vsp.get(rname,0.0)+prod-cons)
                nation["vessel_stockpiles"]=vsp
                all_evs.extend(roll_colony_events(nation,sm.state))
                all_evs.extend(roll_civic_events(nation,sm.state))
            else:
                ipeu=nation.get("base_ipeu",0.0); eco_mod=econ_model_ipeu_modifier(nation)
                g=nation.get("ipeu_growth",0.0)
                nation["base_ipeu"]=ipeu*(1.0+g)**0.25*(eco_mod**0.25)
                pg=nation.get("pop_growth",0.0); eff=spending_effects(nation,ipeu)
                pg_bonus=eff["popdev_growth_bonus"]/100.0
                nation["population"]=nation.get("population",0.0)*(1.0+(pg+pg_bonus))**0.25
                bal=nation.get("debt_balance",0.0)
                if bal>0:
                    qi=bal*nation.get("interest_rate",0.0)/4.0; rep=nation.get("debt_repayment",0.0)
                    nation["debt_balance"]=max(0,bal+qi-rep); nation["strategic_fund"]=nation.get("strategic_fund",0.0)-qi
                ipeu2=nation.get("base_ipeu",0.0); res=compute_resources(nation,ipeu2)
                sp=nation.get("resource_stockpiles") or {}
                if not isinstance(sp,dict): sp={}
                for rname,rd in res.items():
                    entry=sp.get(rname,{})
                    if not isinstance(entry,dict): entry={}
                    entry["stockpile"]=max(0.0,entry.get("stockpile",0.0)+rd["net"]); sp[rname]=entry
                nation["resource_stockpiles"]=sp
                compute_species_loyalty_happiness(nation,res)
                _,tax=compute_planet_local_market(nation,sm.state,ipeu2)
                trade_flow=compute_trade(nation,sm.state.get("trade_routes",[]))
                corp_inc=compute_corp_income(nation) if (nation.get("is_megacorp") or "corporate_data" in nation) else 0.0
                nation["strategic_fund"]=nation.get("strategic_fund",0.0)+tax+trade_flow["net"]+corp_inc
                if nation.get("is_megacorp") or "corporate_data" in nation:
                    _cd2=nation.setdefault("corporate_data",{})
                    _locs2=_cd2.get("locations") or []
                    _total_emp=sum(l.get("employees",0) for l in _locs2)
                    _contracts2=_cd2.get("contracts") or []
                    _cval=sum(c.get("value_per_turn",0.0) for c in _contracts2 if c.get("status")=="active")
                    _cd2.setdefault("corp_history",[]).append({"turn":t,"trust":_cd2.get("trust",0.5),
                        "income":round(corp_inc,2),"market_cap":round(compute_corp_market_cap(nation),2),
                        "contracts_value":round(_cval,2),"employees":_total_emp,"location_count":len(_locs2)})
                    _corp_evs=roll_corp_events(nation,sm.state)
                    for _ce in _corp_evs:
                        _cd2["trust"]=max(0.0,min(1.0,_cd2.get("trust",0.5)+_ce.get("trust_delta",0.0)))
                    _cd2.setdefault("corp_events",[]).extend(_corp_evs)
                    all_evs.extend([{**_ce,"type":"Corp","nation":nation["name"],
                        "col_rgb":_ce.get("col_rgb",list(PURPLE))} for _ce in _corp_evs])
                # tick economic projects
                eproj=nation.get("economic_projects") or []
                still_ep=[]
                for ep in eproj:
                    if ep.get("status")!="active": still_ep.append(ep); continue
                    cost=ep.get("cost_per_turn",0.0)
                    nation["strategic_fund"]=nation.get("strategic_fund",0.0)-cost
                    ef=ep.get("effect_field","none"); ev2=ep.get("effect_value",0.0)
                    # Apply effect once on first tick (when _applied not yet set)
                    if ef and ef!="none" and not ep.get("_applied"):
                        nation[ef]=nation.get(ef,0.0)+ev2
                        ep["_applied"]=True
                    ep["turns_remaining"]=ep.get("turns_remaining",1)-1
                    if ep["turns_remaining"]>0:
                        still_ep.append(ep)
                    else:
                        # Reverse the effect on completion
                        if ef and ef!="none" and ep.get("_applied"):
                            nation[ef]=nation.get(ef,0.0)-ev2
                        ep["status"]="completed"; still_ep.append(ep)
                        all_evs.append({"turn":t,"year":y,"quarter":q,"type":"Project",
                            "nation":nation["name"],"roll":"—","label":"Project Complete",
                            "description":f"{ep.get('name','?')} completed","col_rgb":list(GOLD)})
                nation["economic_projects"]=still_ep
                all_evs.extend(advance_construction(nation,sm.state))
                all_evs.extend(roll_civic_events(nation,sm.state))
                all_evs.extend(roll_planetside_events(nation,sm.state))
                all_evs.extend(roll_resource_events(nation,sm.state))
                # NPC military automation
                if nation.get("is_npc") and not is_colony(nation):
                    all_evs.extend(npc_military_ai(nation,sm.state,t,y,q))
            # update manpower pool
            nation["manpower_pool"]=compute_manpower(nation)
    sm.state.setdefault("events_log",[]).extend(all_evs)
    sm.mark_dirty(); sm.save()
    t2=sm.state.get("turn",1); y2=sm.state.get("year",2200); q2=sm.state.get("quarter",1)
    sm.save_history(t2,y2,q2,sm.state)
    return all_evs

# ── state manager ─────────────────────────────────────────────────────────────
class StateManager:
    def __init__(self,filepath):
        self.filepath=Path(filepath); self.state={}; self.dirty=False
    def load(self):
        try:
            with open(self.filepath) as f: self.state=json.load(f)
            self.dirty=False
            self._migration_warnings=[]
            for _mn in self.state.get("nations",[]):
                _cd=_mn.get("corporate_data")
                if _cd and (_cd.get("offices",0)>0 or _cd.get("stores",0)>0):
                    self._migration_warnings.append(_mn["name"])
                    _cd["offices"]=0; _cd["stores"]=0
            # ── is_npc migration: stamp every nation ──────────────────────────
            for _mn in self.state.get("nations",[]):
                if "is_npc" not in _mn:
                    _mn["is_npc"] = _mn["name"] not in PLAYER_NATIONS
            _gtc=self.state.setdefault("market",{}).setdefault("gtc",{})
            _ldg=_gtc.setdefault("debt_ledger",{})
            if "Regnum Dei" not in _ldg:
                _ldg["Regnum Dei"]={"balance":6e12,"interest_rate":0.04,
                                    "repayment":0.0,"creditor":"GTC","since_turn":1,
                                    "note":"Founding loan - Galactic Trade Confederation"}
            return True
        except Exception as e: print(f"[LOAD ERROR] {e}"); return False
    def save(self,path=None):
        target=Path(path) if path else self.filepath; self._rotate_backups(target)
        try:
            with open(target,"w") as f: json.dump(self.state,f,indent=2)
            self.dirty=False; return True
        except Exception as e: print(f"[SAVE ERROR] {e}"); return False
    def autosave(self): self.save()
    def mark_dirty(self): self.dirty=True
    def _rotate_backups(self,target):
        def bp(n): return target.with_suffix(f".bak{n}.json")
        if bp(BACKUP_COUNT-1).exists(): bp(BACKUP_COUNT-1).unlink()
        for i in range(BACKUP_COUNT-2,0,-1):
            if bp(i).exists(): bp(i).rename(bp(i+1))
        if target.exists():
            try: target.rename(bp(1))
            except: pass
    def save_history(self, turn, year, quarter, state):
        """Append a turn snapshot to carmine_history.json."""
        hpath = self.filepath.parent / "carmine_history.json"
        try:
            hist = json.loads(hpath.read_text()) if hpath.exists() else {"turns": []}
        except:
            hist = {"turns": []}
        market = state.get("market", {})
        snap = {
            "turn": turn, "year": year, "quarter": quarter,
            "market_prices": {k: round(v, 4) for k, v in market.get("market_modifier", {}).items()},
            "nations": {n["name"]: {
                "ipeu": round(n.get("base_ipeu", 0.0), 2),
                "population": round(n.get("population", 0.0), 0),
                "strategic_fund": round(n.get("strategic_fund", 0.0), 2),
            } for n in state.get("nations", [])}
        }
        hist["turns"].append(snap)
        try: hpath.write_text(json.dumps(hist, indent=2))
        except Exception as e: print(f"[HISTORY] {e}")
    def nation_names(self): return [n["name"] for n in self.state.get("nations",[])]
    def get_nation(self,name):
        for n in self.state.get("nations",[]):
            if n["name"]==name: return n
        return None

