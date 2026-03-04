#!/usr/bin/env python3
"""
Carmine NRP Engine - vAlpha0.4.0
Single-file GM tool: Pygame UI + engine + Discord export + 5-slot backup
Run: python3 carmine_nrp.py [state_file.json]
"""

import sys, os, json, shutil, math, time, random
import pygame
from pathlib import Path
from typing import Optional, List, Dict

# CONFIG
DEFAULT_STATE = str(Path(__file__).parent / "carmine_state_T5_Y2201Q1.json")
BACKUP_COUNT  = 5
DISCORD_DIR   = Path(__file__).parent / "discord_exports"
SW, SH        = 1280, 720
LWIDTH        = 240
TBAR_H        = 40
TABBAR_H      = 30
SBAR_H        = 22
FPS           = 60
MAIN_X = LWIDTH; MAIN_Y = TBAR_H + TABBAR_H
MAIN_W = SW - LWIDTH; MAIN_H = SH - TBAR_H - TABBAR_H - SBAR_H
TABS = ["OVERVIEW", "ECONOMY", "MILITARY", "TERRITORY", "MARKET", "EVENTS"]

BG=(8,12,20);PANEL=(12,18,28);BORDER=(28,52,80);BORDER2=(44,86,128);ACCENT=(190,38,25)
CYAN=(0,190,214);TEAL=(0,138,158);TEXT=(198,226,246);DIM=(84,114,136);DIM2=(50,72,92)
BRIGHT=(238,248,255);GREEN=(22,184,82);RED_C=(216,54,40);GOLD=(198,150,22)
SEL=(18,40,65);HOVER=(14,30,50);EDITBG=(5,14,28);EDITBDR=(0,172,194)
BTNBG=(18,36,56);BTNHOV=(28,54,82);BTNACC=(140,24,16);BTNACC2=(190,38,25);PURPLE=(130,60,200)

# FORMATTING
def fmt_cr(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e15: return f"{v/1e15:.3f} Qcr"
    if a>=1e12: return f"{v/1e12:.3f} Tcr"
    if a>=1e9:  return f"{v/1e9:.3f} Bcr"
    if a>=1e6:  return f"{v/1e6:.3f} Mcr"
    if a>=1e3:  return f"{v/1e3:.2f} Kcr"
    return f"{v:.0f} cr"

def fmt_pop(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e9: return f"{v/1e9:.3f}B"
    if a>=1e6: return f"{v/1e6:.3f}M"
    if a>=1e3: return f"{v/1e3:.2f}K"
    return f"{v:.0f}"

def fmt_res(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e9: return f"{v/1e9:.3f}B"
    if a>=1e6: return f"{v/1e6:.3f}M"
    if a>=1e3: return f"{v/1e3:.2f}K"
    return f"{v:.2f}"

def fmt_pct(v): return f"{v*100:+.2f}%" if v!=0 else "0.00%"

def bar_str(pct,w=18):
    pct=max(0.0,min(1.0,pct)); f=round(pct*w)
    return "█"*f+"░"*(w-f)

def nation_tag(name):
    words=name.split()
    if len(words)>=2: return "".join(w[0].upper() for w in words[:4])
    return name[:4].upper()

# ENGINE
def years_elapsed(state): return (state.get("turn",1)-1)*0.25
def current_ipeu(nation,ye): return nation.get("base_ipeu",0.0)*(1.0+nation.get("ipeu_growth",0.0))**ye
def current_population(nation,ye): return nation.get("population",0.0)*(1.0+nation.get("pop_growth",0.0))**ye

def compute_trade(nation,routes):
    name=nation["name"]; exports=imports=transit=0.0
    for r in routes:
        if r.get("status")!="active": continue
        cr=r.get("credits_per_turn",0.0); ts=r.get("transit_nations",[])
        if r["exporter"]==name:
            tax=sum(cr*t.get("tax_rate",0.0) for t in ts if t.get("status")=="active")
            exports+=cr-tax
        if r["importer"]==name: imports+=cr
        for t in ts:
            if t.get("nation")==name and t.get("status")=="active":
                transit+=cr*t.get("tax_rate",0.0)
    return {"exports":exports,"imports":imports,"transit_income":transit,"net":exports-imports+transit}

def compute_resources(nation,ipeu):
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    pop=nation.get("population",1.0); out={}
    for rname in ["Food","Minerals","Energy","Alloys","Consumer Goods"]:
        sd=(nation.get("resource_stockpiles") or {}).get(rname,{})
        if not isinstance(sd,dict): sd={}
        mode=sd.get("production_mode","derived"); stock=sd.get("stockpile",0.0)
        if mode=="flat":
            prod,cons,est=sd.get("flat_production",0.0),sd.get("flat_consumption",0.0),False
        else:
            agri=exp.get("Agriculture",0.0)*ipeu; ind=exp.get("Industry",0.0)*ipeu
            if rname=="Food":
                prod=agri*nation.get("food_efficiency",1.0)/1e6; cons=pop*nation.get("food_consumption_rate",0.01)
            elif rname=="Minerals":
                prod=ind*nation.get("mineral_workforce_pct",0.05)*nation.get("mineral_ipeu_factor",0.5)/1e3; cons=prod*0.4
            elif rname=="Energy":
                prod=ind*0.002/1e3; cons=prod*0.6
            elif rname=="Alloys":
                prod=ind*nation.get("mineral_to_alloy_ratio",0.0)*0.001/1e3; cons=prod*0.3
            else:
                prod=ind*nation.get("cg_efficiency",0.8)*0.0005/1e3; cons=pop*nation.get("cg_consumption_rate",0.005)
            est=True
        net=prod-cons
        out[rname]={"stockpile":stock,"production":prod,"consumption":cons,"net":net,
                    "trend":"▲" if net>0 else ("▼" if net<0 else "─"),"estimated":est}
    return out

def compute_debt(nation,ipeu):
    bal=nation.get("debt_balance",0.0); rate=nation.get("interest_rate",0.0); rep=nation.get("debt_repayment",0.0)
    qi=bal*rate/4.0 if bal>0 else 0.0
    return {"balance":bal,"rate":rate,"repayment":rep,"q_interest":qi,
            "load_pct":(bal/ipeu*100) if ipeu else 0.0,"is_debtor":bal>0}

# D20 EVENT TABLES
_RESOURCES=["Food","Minerals","Energy","Alloys","Consumer Goods"]
_MARKET_SHOCK=[
    (1,2,"MARKET CRASH",(-0.50,-0.30),RED_C),
    (3,5,"Price Drop",(-0.20,-0.10),(200,80,40)),
    (6,15,"Stable",(0.0,0.0),DIM),
    (16,18,"Price Surge",(0.10,0.20),GREEN),
    (19,20,"MARKET BOOM",(0.30,0.50),GOLD),
]
_PLANETSIDE=[
    (1,1,"Natural Disaster",{"devastation":(5,15),"unrest":(10,20)},RED_C),
    (2,3,"Infrastructure Fail",{"crime_rate":(5,10)},(200,80,40)),
    (4,6,"Minor Unrest",{"unrest":(5,15)},GOLD),
    (7,14,"Stable",{},DIM),
    (15,16,"Pop Boom",{},GREEN),
    (17,18,"Crime Crackdown",{"crime_rate":(-10,-5)},CYAN),
    (19,19,"Infrastructure Boom",{"unrest":(-10,-5)},CYAN),
    (20,20,"Golden Age",{"unrest":(-15,-10),"crime_rate":(-10,-5)},GOLD),
]
_RESOURCE_EV=[
    (1,2,"Resource Depletion","flat_production",(-0.30,-0.15),RED_C),
    (3,5,"Extraction Issues","flat_production",(-0.15,-0.05),(200,80,40)),
    (6,15,"Normal Output",None,(0.0,0.0),DIM),
    (16,18,"Rich Vein","flat_production",(0.10,0.25),GREEN),
    (19,20,"Motherlode","flat_production",(0.25,0.50),GOLD),
]
_CIVIC=[
    (1,2,"Mass Exodus","loyalty",(-20,-10),RED_C),
    (3,5,"Civic Unrest","loyalty",(-12,-5),(200,80,40)),
    (6,8,"Protests","loyalty",(-5,-2),GOLD),
    (9,14,"Civic Stability",None,(0,0),DIM),
    (15,17,"Community Programs","loyalty",(3,6),GREEN),
    (18,19,"Cultural Festival","loyalty",(5,10),CYAN),
    (20,20,"Loyalty Surge","loyalty",(10,20),GOLD),
]

def _d20(): return random.randint(1,20)
def _lookup(table,roll):
    for row in table:
        if row[0]<=roll<=row[1]: return row
    return table[len(table)//2]

def roll_market_events(state):
    market=state.get("market",{}); mods=market.get("market_modifier",{}); events=[]
    turn,year,qtr=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    for rname in _RESOURCES:
        roll=_d20(); row=_lookup(_MARKET_SHOCK,roll)
        _,_,label,(lo,hi),col=row
        delta=0.0 if lo==hi==0.0 else random.uniform(lo,hi)
        base={"Food":1.0,"Minerals":2.0,"Energy":4.0,"Alloys":5.0,"Consumer Goods":2.0}.get(rname,1.0)
        old=mods.get(rname,base); new=round(max(base*0.3,old*(1.0+delta)),4)
        mods[rname]=new
        events.append({"turn":turn,"year":year,"quarter":qtr,"type":"Market","resource":rname,
                        "roll":roll,"label":label,"description":f"{rname}: {label} ({1+delta:+.0%}) -> {new:.3f} cr",
                        "col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]})
    market["market_modifier"]=mods
    ph=market.get("price_history",{})
    for rname in _RESOURCES:
        ph.setdefault(rname,[]).append(round(mods.get(rname,1.0),3))
    market["price_history"]=ph
    return events

def roll_civic_events(nation,state):
    turn,year,qtr=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    species=nation.get("species_populations",[]) or []
    roll=_d20(); row=_lookup(_CIVIC,roll); _,_,label,field,(lo,hi),col=row
    desc=f"{nation['name']}: {label}"
    if field=="loyalty" and species:
        delta=random.randint(int(lo),int(hi))
        for s in species: s["loyalty"]=max(0,min(100,s.get("loyalty",50)+delta))
        desc+=f"  (loyalty {delta:+d})"
    return [{"turn":turn,"year":year,"quarter":qtr,"type":"Civic","nation":nation["name"],
             "roll":roll,"label":label,"description":desc,
             "col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]

def roll_planetside_events(nation,state):
    turn,year,qtr=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    for sys in (nation.get("star_systems",[]) or []):
        for planet in sys.get("planets",[]):
            roll=_d20(); row=_lookup(_PLANETSIDE,roll); _,_,label,effects,col=row
            desc=f"{nation['name']} / {planet['name']}: {label}"
            for efield,(lo,hi) in effects.items():
                delta=random.uniform(lo,hi); planet[efield]=round(max(0,planet.get(efield,0)+delta),2)
                desc+=f"  {efield}{delta:+.1f}"
            return [{"turn":turn,"year":year,"quarter":qtr,"type":"Planetside","nation":nation["name"],
                     "roll":roll,"label":label,"description":desc,
                     "col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]
    return []

def roll_resource_events(nation,state):
    turn,year,qtr=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    rname=random.choice(_RESOURCES); roll=_d20(); row=_lookup(_RESOURCE_EV,roll)
    _,_,label,field,(lo,hi),col=row
    desc=f"{nation['name']}: {rname} - {label}"
    if field:
        delta=random.uniform(lo,hi)
        sp=nation.get("resource_stockpiles") or {}
        if not isinstance(sp,dict): sp={}
        rd=sp.get(rname,{})
        if not isinstance(rd,dict): rd={}
        if rd.get("production_mode")=="flat":
            rd["flat_production"]=max(0,rd.get("flat_production",0)*(1.0+delta))
            sp[rname]=rd; nation["resource_stockpiles"]=sp
        desc+=f"  ({delta:+.0%})"
    return [{"turn":turn,"year":year,"quarter":qtr,"type":"Resource","nation":nation["name"],
             "roll":roll,"label":label,"description":desc,
             "col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]

# TURN ADVANCEMENT
def advance_turns(sm,n_turns):
    all_events=[]
    for _ in range(n_turns):
        t=sm.state.get("turn",1)+1; q=sm.state.get("quarter",1); y=sm.state.get("year",2200)
        q+=1
        if q>4: q=1; y+=1
        sm.state["turn"]=t; sm.state["quarter"]=q; sm.state["year"]=y
        evs=roll_market_events(sm.state); all_events.extend(evs)
        for nation in sm.state.get("nations",[]):
            g=nation.get("ipeu_growth",0.0); nation["base_ipeu"]=nation.get("base_ipeu",0.0)*(1.0+g)**0.25
            pg=nation.get("pop_growth",0.0); nation["population"]=nation.get("population",0.0)*(1.0+pg)**0.25
            bal=nation.get("debt_balance",0.0)
            if bal>0:
                qi=bal*nation.get("interest_rate",0.0)/4.0; rep=nation.get("debt_repayment",0.0)
                nation["debt_balance"]=max(0,bal+qi-rep)
                nation["strategic_fund"]=nation.get("strategic_fund",0.0)-qi
            ipeu=nation.get("base_ipeu",0.0); res=compute_resources(nation,ipeu)
            sp=nation.get("resource_stockpiles") or {}
            if not isinstance(sp,dict): sp={}
            for rname,rd in res.items():
                entry=sp.get(rname,{})
                if not isinstance(entry,dict): entry={}
                entry["stockpile"]=max(0.0,entry.get("stockpile",0.0)+rd["net"]); sp[rname]=entry
            nation["resource_stockpiles"]=sp
            all_events.extend(roll_civic_events(nation,sm.state))
            all_events.extend(roll_planetside_events(nation,sm.state))
            all_events.extend(roll_resource_events(nation,sm.state))
        sm.state.setdefault("events_log",[]).extend(all_events)
    sm.mark_dirty(); sm.save()
    return all_events

# TERRITORY TOOLS
_PLANET_TYPES=["Terrestrial","Continental","Arid","Desert","Ocean","Arctic","Toxic","Jungle","Barren","Gas Giant"]
_PLANET_SIZES=["Tiny","Small","Medium","Large","Huge"]
_CLIMATES=["Temperate","Arid","Oceanic","Arctic","Toxic","Jungle","Desert"]
_DISTRICT_TYPES=["Residential","Urban","Industrial Civilian","Industrial Military","Agricultural","Mining","Power","Military"]

def _rng_name(prefix,idx):
    suf=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Prime","Secundus","Tertius","IV","V","VI"]
    return f"{prefix} {suf[idx%len(suf)]}"

def randomize_planet(planet,total_pop):
    planet["type"]=random.choice(_PLANET_TYPES); planet["size"]=random.choice(_PLANET_SIZES)
    planet["climate"]=random.choice(_CLIMATES); planet["habitability"]=round(random.uniform(10,95),1)
    planet["devastation"]=round(random.uniform(0,15),1); planet["crime_rate"]=round(random.uniform(0,25),1)
    planet["unrest"]=round(random.uniform(0,20),1)
    sz_mult={"Tiny":0.05,"Small":0.10,"Medium":0.20,"Large":0.35,"Huge":0.50}
    planet_pop=total_pop*sz_mult.get(planet["size"],0.2)*(planet["habitability"]/100.0)
    planet["pop_assigned"]=round(planet_pop)
    n_s=random.randint(1,3); setts=[]; rem=planet_pop
    for i in range(n_s):
        s_pop=rem/(n_s-i)
        n_d=random.randint(2,6); districts=[{"type":random.choice(_DISTRICT_TYPES),"status":"active"} for _ in range(n_d)]
        setts.append({"name":_rng_name(planet.get("name","Settlement"),i),"population":round(s_pop),
                       "loyalty":round(random.uniform(40,85),1),"amenities":round(random.uniform(30,80),1),"districts":districts})
        rem-=s_pop
    planet["settlements"]=setts

def add_system(nation,name=""):
    si=len(nation.get("star_systems",[]));
    if not name: name=_rng_name("System",si)
    nation.setdefault("star_systems",[]).append({"name":name,"notes":"","coordinates":"","planets":[]})

def add_planet(system,nation_pop,name=""):
    pi=len(system.get("planets",[]));
    if not name: name=_rng_name(system["name"],pi)
    planet={"name":name,"type":"Terrestrial","size":"Medium","climate":"Temperate",
            "habitability":50.0,"devastation":0.0,"crime_rate":5.0,"unrest":5.0,"pop_assigned":0,"settlements":[]}
    randomize_planet(planet,nation_pop); system.setdefault("planets",[]).append(planet)

# STATE MANAGER
class StateManager:
    def __init__(self,filepath):
        self.filepath=Path(filepath); self.state={}; self.dirty=False
    def load(self):
        try:
            with open(self.filepath) as f: self.state=json.load(f)
            self.dirty=False; return True
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
    def nation_names(self): return [n["name"] for n in self.state.get("nations",[])]
    def get_nation(self,name):
        for n in self.state.get("nations",[]): 
            if n["name"]==name: return n
        return None

# DISCORD EXPORT
def _discord_export(nation,state):
    DISCORD_DIR.mkdir(exist_ok=True)
    ye=years_elapsed(state); ipeu=nation.get("base_ipeu",0.0); pop=current_population(nation,ye)
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    routes=state.get("trade_routes",[]); trade=compute_trade(nation,routes)
    res=compute_resources(nation,ipeu); debt=compute_debt(nation,ipeu)
    rb=nation.get("research_budget",0.0); sfund=nation.get("strategic_fund",0.0)
    species=nation.get("species_populations",[]) or []; star_sys=nation.get("star_systems",[]) or []
    projects=nation.get("projects",[]) or []; afd=nation.get("active_forces_detail",[]) or []
    ugroups={ug["ugid"]:ug for ug in (nation.get("unit_groups") or [])}
    active_r=nation.get("active_research_projects",[]) or []; done_r=nation.get("completed_techs",[]) or []
    qtr=state.get("quarter",1); year=state.get("year",2200); turn=state.get("turn",1)
    tag=nation_tag(nation["name"])
    homeworld="N/A"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl["name"]; break
        break
    sp_str=", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species) or "N/A"
    total_exp=sum(exp.values())*ipeu+rb; net_bal=ipeu+trade["net"]-total_exp-debt["q_interest"]
    per_cap=int(ipeu/pop) if pop else 0
    L=[]; A=L.append
    A(f"-# [{tag}] {nation['name'].upper()}")
    A(f"# NATIONAL PROFILE - Q{qtr} [{year}]"); A("```")
    A(f"  Species          : {sp_str}")
    A(f"  Population       : {fmt_pop(pop)}")
    A(f"  Pop Growth       : {fmt_pct(nation.get('pop_growth',0))} / yr")
    A(f"  Homeworld        : {homeworld}")
    A(f"  Civilisation     : {nation.get('civ_level','Interplanetary Industrial')}")
    A(f"  Tier             : {nation.get('civ_tier',2)}")
    A(f"  Economic Model   : {nation.get('economic_model','MIXED')}")
    A(f"  Status           : {nation.get('eco_status','Stable')}"); A("```")
    A("# ECONOMY"); A("```")
    A(f"  IPEU (base)      : {fmt_cr(ipeu)}")
    A(f"  IPEU Growth      : {fmt_pct(nation.get('ipeu_growth',0))} / yr")
    A(f"  IPEU per Capita  : {per_cap:,} cr")
    A(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
    A(f"   - Exports       : {fmt_cr(trade['exports'])}")
    A(f"   - Imports       : {fmt_cr(trade['imports'])}")
    A(f"  Total Expenditure: {fmt_cr(total_exp)}")
    A(f"  Research Budget  : {fmt_cr(rb)} / turn")
    A(f"  Net Balance      : {fmt_cr(net_bal)}"); A("```")
    A("## EXPENDITURE & BREAKDOWN"); A("```")
    mx=max(exp.values(),default=0.01)
    for cat,pct in exp.items(): A(f"  {cat:<22} {pct*100:5.1f}%  {bar_str(pct/mx,20)}  {fmt_cr(pct*ipeu)}")
    A(f"  {chr(9472)*61}")
    A(f"  {'TOTAL':<22} {sum(exp.values())*100:5.1f}%  {'':<20}  ({fmt_cr(total_exp)})"); A("```")
    A("## ECONOMIC PROJECTS"); A("```")
    ap=[p for p in projects if p.get("status") in ("active","in_progress","complete")]
    if ap:
        for p in ap:
            tl=p.get("duration_turns",0)-p.get("turns_elapsed",0)
            st="[COMPLETE]" if p.get("status")=="complete" else f"[{tl}t left]"
            A(f"  {p['name']} ({p.get('category','?')})  {st}")
    else: A("  None")
    A("```"); A("## FISCAL REPORT"); A("```")
    sf_icon="🟢" if sfund>=0 else "🔴"
    fd=-debt["q_interest"]
    A(f"  Debtor/ Creditor     : {'Debtor' if debt['is_debtor'] else 'Creditor'}")
    A(f"  Debt Balance         : {fmt_cr(debt['balance'])}")
    A(f"  Debt Load            : {debt['load_pct']:.1f}%")
    A(f"  Interest Rate        : {debt['rate']*100:.2f}%")
    A(f"  Quarterly Int.       : {fmt_cr(debt['q_interest'])}")
    A(f"  Debt Repayment       : {fmt_cr(debt['repayment'])}")
    A(f"  {chr(9472)*61}")
    A(f"  Strategic Fund   : {sf_icon} {fmt_cr(sfund)}")
    A(f"  Fund dt this turn: {('+' if fd>=0 else '')}{fmt_cr(fd)}"); A("```")
    A("## RESOURCES & STOCKPILES")
    for rname in ["Food","Minerals","Energy","Alloys","Consumer Goods"]:
        rd=res[rname]; ns=f"+{fmt_res(rd['net'])}" if rd["net"]>=0 else fmt_res(rd["net"])
        A("```")
        A(f"  {rname} Stockpile            : {fmt_res(rd['stockpile'])}")
        A(f"  {rname} Production per turn  : {fmt_res(rd['production'])}")
        A(f"  {rname} Consumption per turn : {fmt_res(rd['consumption'])}")
        A(f"  {rname} Net per turn         : {ns}")
        A(f"  {rname} Trend                : {rd['trend']}"); A("```")
    A("# TERRITORIES")
    if star_sys:
        A(f"Home System: {star_sys[0]['name']}")
        for planet in star_sys[0].get("planets",[]):
            A("```"); A(f"  Homeworld: {planet['name']}")
            A(f"    Population    : {fmt_pop(planet.get('pop_assigned',0))}")
            setts=planet.get("settlements",[])
            if setts:
                A(f"    Settlements   : {len(setts)}")
                for s in setts:
                    A(f"      - {s['name']}"); dc={}
                    for d in s.get("districts",[]): dt=d.get("type","?"); dc[dt]=dc.get(dt,0)+1
                    for dt,cnt in dc.items(): A(f"        [{dt}] x{cnt}")
            else: A("    Settlements   : None")
            A("```")
    else: A("No territorial data")
    A("# NATIONAL DEMOGRAPHICS"); A("```")
    A(f"  Total Population     : {fmt_pop(pop)}")
    A(f"  Loyalty Modifier     : {nation.get('loyalty_modifier_cg',1.0):.2f}"); A("```")
    for s in species:
        dom=s.get("status","") in ("dominant","majority")
        sp_p=s.get("population",0); shr=sp_p/pop*100 if pop else 0
        loy=s.get("loyalty",0); li="🟢" if loy>=70 else ("🟡" if loy>=40 else "🔴")
        A(f"**{s['name']}**  {chr(128081) if dom else chr(128101)} {s.get('status','').title()}"); A("```")
        A(f"  Population       : {fmt_pop(sp_p)}")
        A(f"  Share            : {shr:.1f}% - {s.get('status','?').title()}")
        A(f"  Growth Rate      : {fmt_pct(s.get('growth_rate',0))} / yr")
        A(f"  Culture          : {s.get('culture','N/A')}")
        A(f"  Language         : {s.get('language','N/A')}")
        A(f"  Religion         : {s.get('religion','N/A')}")
        A(f"  Loyalty          : {li} {loy}/100")
        A(f"  Happiness        : {s.get('happiness','N/A')}"); A("```")
    A("# MILITARY")
    for hdr,cats in [("## SPACEFLEET",["Spacefleet","Navy"]),
                      ("## AEROSPACE FORCES",["Air Force","Aerospace"]),
                      ("## GROUND FORCES",["Ground Forces","Ground","Army"])]:
        units=[u for u in afd if u.get("category") in cats]; A(hdr); A("```")
        if units:
            grouped={}
            for u in units:
                ugid=u.get("ugid"); grp=ugroups[ugid]["name"] if ugid and ugid in ugroups else "N/A"
                grouped.setdefault(grp,[]).append(u)
            for grp,us in grouped.items():
                if grp!="N/A": A(f"  {grp}")
                for u in us:
                    nm=u.get("custom_name") or u.get("unit","?"); mnt=u.get("maintenance",0)
                    A(f"    - {nm} | x{u.get('count',1)} | {u.get('veterancy','?')} | {fmt_cr(mnt) if isinstance(mnt,(int,float)) else mnt} maint")
        else: A("  None on record")
        A("```")
    A("# RESEARCH"); A("```")
    A(f"  RP per turn      : {fmt_cr(rb)}"); A(f"  {chr(9472)*61}")
    A("  Active Projects:")
    if active_r:
        for p in active_r:
            prog=p.get("progress",0.0); A(f"    {p.get('name','?')} [{p.get('field','?')}]  {prog:.1f}%  {bar_str(prog/100,20)}")
    else: A("    None")
    A("  Completed Projects:")
    if done_r:
        for t in done_r[-8:]: A(f"    v {t if isinstance(t,str) else t.get('name',str(t))}")
    else: A("    None")
    A("```")
    elog=state.get("events_log",[]) or []
    nation_name=nation["name"]
    recent=[e for e in elog if e.get("turn")==turn and (e.get("nation")==nation_name or e.get("type")=="Market")]
    if recent:
        A(f"# EVENTS - T{turn} Q{qtr} [{year}]"); A("```")
        for e in recent:
            A(f"  [{e['type']:<10}] d20:{e.get('roll','?'):>2}  {e.get('label','?'):<20}  {e.get('description','')}")
        A("```")
    text="\n".join(L)
    fname=DISCORD_DIR/f"discord_{nation_name.replace(' ','_')}_T{turn}.txt"
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
    return str(fname)

# FONT + DRAW
_fonts={}
def gf(size,mono=True):
    key=f"{'m' if mono else 's'}{size}"
    if key not in _fonts:
        if mono:
            for name in ("Courier New","Consolas","DejaVu Sans Mono","monospace"):
                try: _fonts[key]=pygame.font.SysFont(name,size); break
                except: pass
            else: _fonts[key]=pygame.font.Font(None,size)
        else: _fonts[key]=pygame.font.SysFont("Arial",size)
    return _fonts[key]

def tw(txt,font): return font.size(txt)[0]
def draw_text(surf,txt,x,y,font,col=TEXT,clip=None):
    if not txt: return
    s=font.render(str(txt),True,col)
    if clip:
        r=s.get_rect(topleft=(x,y)).clip(clip)
        if r.width>0: surf.blit(s,(x,y),area=pygame.Rect(0,0,r.width,r.height))
    else: surf.blit(s,(x,y))
def draw_rect(surf,rect,col,border=0,radius=0):
    if radius: pygame.draw.rect(surf,col,rect,border_radius=radius)
    else: pygame.draw.rect(surf,col,rect,border)

class Scrollbar:
    W=8
    def __init__(self,x,y,h):
        self.rect=pygame.Rect(x,y,self.W,h); self.scroll=0; self.content_h=h; self.view_h=h
        self._drag=False; self._dy=0
    def set_content(self,ch,vh):
        self.content_h=max(ch,vh); self.view_h=vh
        self.scroll=max(0,min(self.scroll,self.content_h-self.view_h))
    def clamp(self): self.scroll=max(0,min(self.scroll,max(0,self.content_h-self.view_h)))
    def draw(self,surf):
        draw_rect(surf,self.rect,(12,20,32))
        if self.content_h<=self.view_h: return
        ratio=self.view_h/self.content_h; th=max(24,int(self.rect.h*ratio))
        ty=min(self.rect.y+int((self.scroll/self.content_h)*self.rect.h),self.rect.bottom-th)
        draw_rect(surf,pygame.Rect(self.rect.x,ty,self.W,th),(44,88,130),radius=3)
    def on_event(self,ev,hover=True):
        if ev.type==pygame.MOUSEWHEEL and hover: self.scroll-=ev.y*22; self.clamp()
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and self.rect.collidepoint(ev.pos):
            self._drag=True; self._dy=ev.pos[1]
        if ev.type==pygame.MOUSEBUTTONUP and ev.button==1: self._drag=False
        if ev.type==pygame.MOUSEMOTION and self._drag:
            dy=ev.pos[1]-self._dy; self._dy=ev.pos[1]
            self.scroll+=int(dy*self.content_h/self.view_h); self.clamp()

class Button:
    def __init__(self,rect,label,accent=False,small=False,color=None):
        self.rect=pygame.Rect(rect); self.label=label; self.accent=accent
        self.small=small; self.color=color; self._hover=False
    def draw(self,surf):
        if self.color:
            bg=tuple(min(255,c+30) for c in self.color) if self._hover else self.color; bdr=BORDER2
        else:
            bg=(BTNACC2 if self._hover else BTNACC) if self.accent else (BTNHOV if self._hover else BTNBG)
            bdr=ACCENT if self.accent else BORDER2
        draw_rect(surf,self.rect,bg,radius=3); draw_rect(surf,self.rect,bdr,border=1,radius=3)
        s=gf(11 if self.small else 12).render(self.label,True,BRIGHT); surf.blit(s,s.get_rect(center=self.rect.center))
    def on_event(self,ev):
        if ev.type==pygame.MOUSEMOTION: self._hover=self.rect.collidepoint(ev.pos)
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1 and self.rect.collidepoint(ev.pos): return True
        return False

class EditOverlay:
    H=80
    def __init__(self): self.active=False; self.label=""; self.text=""; self.meta={}; self._blink=0.0
    def open(self,label,raw,meta):
        self.active=True; self.label=label; self.text=str(raw) if raw is not None else ""; self.meta=meta
        pygame.key.set_repeat(400,40)
    def close(self): self.active=False; self.text=""; self.meta={}; pygame.key.set_repeat(0,0)
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0; y=SH-self.H-SBAR_H; r=pygame.Rect(0,y,SW,self.H)
        draw_rect(surf,r,EDITBG); draw_rect(surf,r,EDITBDR,border=1)
        draw_text(surf,f"Edit: {self.label}",14,y+8,gf(12),CYAN)
        draw_text(surf,"Enter=confirm  Esc=cancel",SW-240,y+8,gf(11),DIM)
        bx=pygame.Rect(14,y+28,SW-28,32); draw_rect(surf,bx,(8,18,30)); draw_rect(surf,bx,EDITBDR,border=1)
        draw_text(surf,self.text,bx.x+6,bx.y+8,gf(12),BRIGHT)
        if self._blink<0.5:
            cx=bx.x+6+tw(self.text,gf(12)); pygame.draw.line(surf,CYAN,(cx,bx.y+6),(cx,bx.y+24),1)
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_RETURN: v=self.text; self.close(); return v
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif ev.unicode and ev.unicode.isprintable(): self.text+=ev.unicode
        return None

def apply_edit(nation,meta,raw):
    path=meta.get("path",[]); dtype=meta.get("type","float")
    try:
        if dtype=="float": val=float(raw.replace(",",""))
        elif dtype=="pct": val=float(raw.replace("%","").replace(",",""))/100.0
        elif dtype=="int": val=int(raw.replace(",",""))
        else: val=raw
    except: return False
    obj=nation
    for key in path[:-1]:
        obj=obj[key] if isinstance(key,int) else obj.setdefault(key,{})
    last=path[-1]
    if isinstance(obj,dict): obj[last]=val
    elif isinstance(obj,list): obj[last]=val
    return True

ROW_H=20; HDR1_H=32; HDR2_H=26; SEP_H=8; BTN_H=28
def _row(label,val,path=None,dtype="float",vcol=TEXT):
    meta={"path":path,"type":dtype} if path else None
    return {"type":"row","label":label,"val":str(val),"meta":meta,"vcol":vcol,"h":ROW_H}
def _hdr1(txt): return {"type":"hdr1","txt":txt,"h":HDR1_H}
def _hdr2(txt): return {"type":"hdr2","txt":txt,"h":HDR2_H}
def _sep(): return {"type":"sep","h":SEP_H}
def _bar(label,pct,txt,vcol=CYAN): return {"type":"bar","label":label,"pct":pct,"txt":txt,"vcol":vcol,"h":ROW_H}
def _btn(label,action,data=None,col=None): return {"type":"btn","label":label,"action":action,"data":data or {},"col":col,"h":BTN_H}
def _ev_row(ev):
    cr=tuple(ev.get("col_rgb",[84,114,136]))
    return {"type":"event_row","txt":f"  [{ev['type']:<10}] d20:{ev.get('roll','?'):>2}  {ev.get('label','?'):<20}  {ev.get('description','')}","col":cr,"h":ROW_H}

def build_rows(nation,state,tab):
    ye=years_elapsed(state); ipeu=nation.get("base_ipeu",0.0); pop=current_population(nation,ye)
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    trade=compute_trade(nation,state.get("trade_routes",[])); res=compute_resources(nation,ipeu)
    debt=compute_debt(nation,ipeu); rb=nation.get("research_budget",0.0); sf=nation.get("strategic_fund",0.0)
    total_exp=sum(exp.values())*ipeu+rb; net_bal=ipeu+trade["net"]-total_exp-debt["q_interest"]
    species=nation.get("species_populations",[]) or []; star_sys=nation.get("star_systems",[]) or []
    afd=nation.get("active_forces_detail",[]) or []
    ugroups={ug["ugid"]:ug for ug in (nation.get("unit_groups") or [])}
    active_r=nation.get("active_research_projects",[]) or []; done_r=nation.get("completed_techs",[]) or []
    projects=nation.get("projects",[]) or []; R=[]
    homeworld="N/A"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl["name"]; break
        break

    if tab=="OVERVIEW":
        sp_str=", ".join(s["name"] for s in species) if species else "N/A"
        R+=[_hdr1(f"  {nation['name']}"),_row("Species",sp_str),_row("Population",fmt_pop(pop)),
            _row("Pop Growth",fmt_pct(nation.get("pop_growth",0)),["pop_growth"],"pct",CYAN),
            _row("Homeworld",homeworld),_row("Civ Level",nation.get("civ_level","N/A"),["civ_level"],"str"),
            _row("Civ Tier",nation.get("civ_tier","N/A"),["civ_tier"],"int"),
            _row("Eco Model",nation.get("economic_model","MIXED"),["economic_model"],"str"),
            _row("Eco Status",nation.get("eco_status","Stable"),["eco_status"],"str"),_sep(),_hdr2("DEMOGRAPHICS"),
            _row("Total Pop",fmt_pop(pop)),_row("Loyalty Mod",f"{nation.get('loyalty_modifier_cg',1.0):.2f}",["loyalty_modifier_cg"],"float",CYAN)]
        for si,s in enumerate(species):
            sp_p=s.get("population",0); shr=sp_p/pop*100 if pop else 0
            loy=s.get("loyalty",0); lc=GREEN if loy>=70 else (GOLD if loy>=40 else RED_C)
            R+=[_sep(),{"type":"species_hdr","name":s["name"],"status":s.get("status",""),"h":HDR2_H},
                _row("  Population",fmt_pop(sp_p),["species_populations",si,"population"],"float",CYAN),
                _row("  Share",f"{shr:.1f}% - {s.get('status','?').title()}"),
                _row("  Status",s.get("status","?"),["species_populations",si,"status"],"str"),
                _row("  Growth",fmt_pct(s.get("growth_rate",0)),["species_populations",si,"growth_rate"],"pct",CYAN),
                _row("  Culture",s.get("culture","N/A"),["species_populations",si,"culture"],"str"),
                _row("  Language",s.get("language","N/A"),["species_populations",si,"language"],"str"),
                _row("  Religion",s.get("religion","N/A"),["species_populations",si,"religion"],"str"),
                _row("  Loyalty",f"{loy}/100  {bar_str(loy/100,12)}",["species_populations",si,"loyalty"],"float",lc),
                _row("  Happiness",str(s.get("happiness","N/A")),["species_populations",si,"happiness"],"str")]
        R+=[_sep(),_hdr2("RESEARCH"),_row("RP Budget/turn",fmt_cr(rb),["research_budget"],"float",CYAN)]
        for p in active_r: R.append(_bar(f"  {p.get('name','?')}",p.get("progress",0)/100,f"{p.get('progress',0):.1f}%",CYAN))
        if not active_r: R.append(_row("  Active","None",vcol=DIM))
        if done_r: R.append(_row("  Completed",f"{len(done_r)} techs",vcol=GREEN))

    elif tab=="ECONOMY":
        nc=GREEN if net_bal>=0 else RED_C
        R+=[_hdr1("ECONOMY"),_row("IPEU (base)",fmt_cr(ipeu),["base_ipeu"],"float",GOLD),
            _row("IPEU Growth",fmt_pct(nation.get("ipeu_growth",0)),["ipeu_growth"],"pct",CYAN),
            _row("IPEU/Capita",f"{int(ipeu/pop):,} cr" if pop else "N/A"),
            _row("Trade Revenue",fmt_cr(trade["net"])),_row("  Exports",fmt_cr(trade["exports"]),vcol=GREEN),
            _row("  Imports",fmt_cr(trade["imports"]),vcol=RED_C),_row("  Transit",fmt_cr(trade["transit_income"]),vcol=TEAL),
            _row("Research Bgt",fmt_cr(rb),["research_budget"],"float",CYAN),_row("Total Expend.",fmt_cr(total_exp)),
            _row("Net Balance",fmt_cr(net_bal),vcol=nc),_sep(),_hdr2("EXPENDITURE")]
        mx=max(exp.values(),default=0.01)
        for cat,pct in exp.items(): R.append(_bar(f"  {cat}",pct/mx,f"{pct*100:.1f}%  {fmt_cr(pct*ipeu)}"))
        R+=[_sep(),_hdr2("ECONOMIC PROJECTS")]
        ap=[p for p in projects if p.get("status") in ("active","in_progress","complete")]
        for p in ap:
            tl=p.get("duration_turns",0)-p.get("turns_elapsed",0)
            R.append(_row(f"  {p['name']}",f"[{'DONE' if p.get('status')=='complete' else f'{tl}t'}]  {p.get('category','?')}",vcol=GOLD))
        if not ap: R.append(_row("  None","N/A",vcol=DIM))
        R+=[_sep(),_hdr2("FISCAL REPORT")]
        dc=RED_C if debt["is_debtor"] else GREEN
        R+=[_row("Status","Debtor" if debt["is_debtor"] else "Creditor",vcol=dc),
            _row("Debt Balance",fmt_cr(debt["balance"]),["debt_balance"],"float"),
            _row("Debt Load",f"{debt['load_pct']:.1f}%"),
            _row("Interest Rate",f"{debt['rate']*100:.2f}%",["interest_rate"],"pct",CYAN),
            _row("Quarterly Int.",fmt_cr(debt["q_interest"])),_row("Debt Repayment",fmt_cr(debt["repayment"]),["debt_repayment"],"float")]
        sf_c=GREEN if sf>=0 else RED_C; fd=-debt["q_interest"]
        R+=[_row("Strategic Fund",fmt_cr(sf),["strategic_fund"],"float",sf_c),
            _row("Fund dt/turn",(f"+{fmt_cr(fd)}" if fd>=0 else fmt_cr(fd)),vcol=sf_c),_sep(),_hdr2("RESOURCES & STOCKPILES")]
        for rname in ["Food","Minerals","Energy","Alloys","Consumer Goods"]:
            rd=res[rname]; tc=GREEN if rd["net"]>0 else (RED_C if rd["net"]<0 else DIM)
            R+=[_row(f"  {rname}",""),_row("    Stockpile",fmt_res(rd["stockpile"])),
                _row("    Production",fmt_res(rd["production"])),_row("    Consumption",fmt_res(rd["consumption"])),
                _row("    Net/turn",fmt_res(rd["net"]),vcol=tc),_row("    Trend",rd["trend"],vcol=tc),_sep()]

    elif tab=="MILITARY":
        R.append(_hdr1("MILITARY"))
        for hdr,cats in [("SPACEFLEET",["Spacefleet","Navy"]),("AEROSPACE FORCES",["Air Force","Aerospace"]),("GROUND FORCES",["Ground Forces","Ground","Army"])]:
            units=[u for u in afd if u.get("category") in cats]; R.append(_hdr2(hdr))
            if units:
                gd={}
                for u in units:
                    ugid=u.get("ugid"); grp=ugroups[ugid]["name"] if ugid and ugid in ugroups else "Unassigned"
                    gd.setdefault(grp,[]).append(u)
                for grp,us in gd.items():
                    R.append(_row(f"  [{grp}]","",vcol=GOLD))
                    for u in us:
                        nm=u.get("custom_name") or u.get("unit","?"); mnt=u.get("maintenance",0)
                        R.append(_row(f"    {nm}",f"x{u.get('count',1)} | {u.get('veterancy','?')} | {fmt_cr(mnt) if isinstance(mnt,(int,float)) else mnt}",vcol=TEXT))
            else: R.append(_row("  None","",vcol=DIM))
            R.append(_sep())
        R.append(_hdr2("ARSENAL"))
        for a in (nation.get("arsenal",[]) or []):
            R.append(_row(f"  {a.get('name','?')}",f"{a.get('type','?')} | {a.get('size','?')} | Crew {a.get('crew','?')}"))
        if not (nation.get("arsenal") or []): R.append(_row("  None","",vcol=DIM))

    elif tab=="TERRITORY":
        R+=[_hdr1("TERRITORIES"),_btn("+ Add System","add_system",{},(22,60,36)),_sep()]
        if not star_sys: R.append(_row("No territorial data","",vcol=DIM))
        else:
            for si,sys in enumerate(star_sys):
                R+=[_hdr2(f"System: {sys['name']}"),_row("  Name",sys["name"],["star_systems",si,"name"],"str"),
                    _row("  Notes",sys.get("notes","N/A"),["star_systems",si,"notes"],"str"),
                    _row("  Coordinates",sys.get("coordinates","N/A"),["star_systems",si,"coordinates"],"str"),
                    _btn(f"  + Add Planet","add_planet",{"si":si},(22,50,70))]
                for pi,planet in enumerate(sys.get("planets",[])):
                    R+=[_sep(),{"type":"territory_planet","name":planet["name"],"si":si,"pi":pi,"h":HDR2_H},
                        _row("    Name",planet["name"],["star_systems",si,"planets",pi,"name"],"str"),
                        _row("    Type",planet.get("type","N/A"),["star_systems",si,"planets",pi,"type"],"str"),
                        _row("    Size",planet.get("size","N/A"),["star_systems",si,"planets",pi,"size"],"str"),
                        _row("    Climate",planet.get("climate","N/A"),["star_systems",si,"planets",pi,"climate"],"str"),
                        _row("    Habitability",planet.get("habitability","N/A"),["star_systems",si,"planets",pi,"habitability"],"float"),
                        _row("    Devastation",planet.get("devastation",0),["star_systems",si,"planets",pi,"devastation"],"float",RED_C),
                        _row("    Crime Rate",planet.get("crime_rate",0),["star_systems",si,"planets",pi,"crime_rate"],"float"),
                        _row("    Unrest",planet.get("unrest",0),["star_systems",si,"planets",pi,"unrest"],"float"),
                        _row("    Population",fmt_pop(planet.get("pop_assigned",0))),
                        _row("    Settlements",f"{len(planet.get('settlements',[]) or [])}",vcol=CYAN)]
                    for s in (planet.get("settlements",[]) or []):
                        R.append(_row(f"      o {s['name']}",f"Pop {fmt_pop(s.get('population',0))}  Loy {s.get('loyalty',0):.0f}%"))
                        dc={}
                        for d in s.get("districts",[]): dt=d.get("type","?"); dc[dt]=dc.get(dt,0)+1
                        if dc: R.append(_row("        Districts","  ".join(f"{t}x{c}" for t,c in dc.items()),vcol=DIM))
                    R+=[_btn(f"  Randomize {planet['name']}","randomize_planet",{"si":si,"pi":pi},(60,30,80)),_sep()]

    elif tab=="MARKET":
        market=state.get("market",{}); mods=market.get("market_modifier",{}); base_p=market.get("price_base",{})
        ph=market.get("price_history",{}); routes=state.get("trade_routes",[]) or []
        R+=[_hdr1("GALACTIC MARKET"),_hdr2("CURRENT PRICES")]
        for rname in _RESOURCES:
            base=base_p.get(rname,1.0); curr=mods.get(rname,base); mult=curr/base if base else 1.0
            col=GREEN if mult>1.05 else (RED_C if mult<0.95 else DIM)
            hist=ph.get(rname,[])
            trend="▲" if (len(hist)>1 and hist[-1]>hist[-2]) else ("▼" if (len(hist)>1 and hist[-1]<hist[-2]) else "─")
            R.append(_row(f"  {rname}",f"{curr:.3f} cr  (base {base:.2f})  x{mult:.2f}  {trend}",vcol=col))
            if hist:
                mn=min(hist[-8:]); mxh=max(hist[-8:],default=mn+0.001)
                bh="".join("_..,-+|#"[min(7,int((v-mn)/(mxh-mn+0.001)*8))] for v in hist[-8:])
                R.append(_row("    History (8t)",f"{bh}  lo:{mn:.3f} hi:{mxh:.3f}",vcol=DIM))
        R+=[_sep(),_hdr2(f"TRADE ROUTES  ({len(routes)} total)")]
        if routes:
            for r in routes:
                st=r.get("status","?"); sc=GREEN if st=="active" else RED_C
                R+=[_row(f"  [{r.get('id','?')}] {r.get('name',r.get('id','?'))}",
                          f"{r.get('resource','?')}  {fmt_cr(r.get('credits_per_turn',0))}/turn  [{st}]",vcol=sc),
                    _row(f"    {r.get('exporter','?')} -> {r.get('importer','?')}","",vcol=DIM)]
                if r.get("transit_nations"):
                    tns=", ".join(t.get("nation","?") for t in r["transit_nations"])
                    R.append(_row("    Transit",tns,vcol=DIM))
        else: R.append(_row("  No trade routes","",vcol=DIM))
        psst=market.get("psst_nations",[])
        if psst:
            R+=[_sep(),_hdr2("PSST NATIONS")]
            for n in psst: R.append(_row(f"  {n}","",vcol=GOLD))

    elif tab=="EVENTS":
        elog=state.get("events_log",[]) or []
        nname=nation["name"]
        R+=[_hdr1("EVENTS LOG"),_btn("Roll Events for This Nation","roll_events",{"nation":nname},(60,30,90)),_sep()]
        relevant=[e for e in reversed(elog) if e.get("nation")==nname or e.get("type")=="Market"]
        if not relevant: R.append(_row("No events recorded","",vcol=DIM))
        else:
            cur_t=None
            for e in relevant[:80]:
                t=e.get("turn","?")
                if t!=cur_t:
                    cur_t=t; R.append(_hdr2(f"Turn {t}  .  {e.get('year','?')} Q{e.get('quarter','?')}"))
                R.append(_ev_row(e))
    return R

class LeftPanel:
    PAD=8
    def __init__(self):
        bw=LWIDTH-self.PAD*2; BTN_Y=SH-SBAR_H-118
        self.nations=[]; self.selected=0; self._hover=-1; self.adv_n=1
        list_h=BTN_Y-TBAR_H-46
        self.scroll=Scrollbar(LWIDTH-Scrollbar.W-2,TBAR_H+4,list_h)
        hw=(bw-4)//2
        self.btn_minus=Button((self.PAD,BTN_Y,hw,24),"- ",small=True)
        self.btn_plus=Button((self.PAD+hw+4,BTN_Y,hw,24)," +",small=True)
        self.btn_adv=Button((self.PAD,BTN_Y+28,bw,26),"[ ADVANCE ]",accent=True)
        self.btn_save=Button((self.PAD,BTN_Y+58,bw,24),"[ SAVE  S ]",color=(22,54,38))
        self.btn_disc=Button((self.PAD,BTN_Y+86,bw,24),"[ DISCORD  D ]")
    def set_nations(self,names,sel=0):
        self.nations=names; self.selected=sel
        BTN_Y=SH-SBAR_H-118; list_h=BTN_Y-TBAR_H-46
        self.scroll.set_content(len(names)*22,list_h)
    def draw(self,surf,turn,year,quarter):
        draw_rect(surf,pygame.Rect(0,0,LWIDTH,SH),PANEL); draw_rect(surf,pygame.Rect(LWIDTH-1,0,1,SH),BORDER)
        f12=gf(12); f10=gf(10)
        draw_text(surf,f"T{turn} . {year} Q{quarter}",self.PAD,TBAR_H+4,f12,CYAN)
        draw_text(surf,f"{len(self.nations)} nations",self.PAD,TBAR_H+20,f10,DIM)
        BTN_Y=SH-SBAR_H-118; list_h=BTN_Y-TBAR_H-46
        clip=pygame.Rect(0,TBAR_H+40,LWIDTH-Scrollbar.W-2,list_h)
        surf.set_clip(clip); y0=TBAR_H+40-int(self.scroll.scroll); mx,my=pygame.mouse.get_pos(); self._hover=-1
        for i,name in enumerate(self.nations):
            yr=pygame.Rect(self.PAD,y0+i*22,LWIDTH-Scrollbar.W-self.PAD*2,20)
            if yr.collidepoint(mx,my): self._hover=i
            if i==self.selected: draw_rect(surf,yr,SEL,radius=2); draw_rect(surf,yr,BORDER2,border=1,radius=2)
            elif self._hover==i: draw_rect(surf,yr,HOVER,radius=2)
            draw_text(surf,f"[{nation_tag(name)}]",yr.x+2,yr.y+3,f10,ACCENT)
            draw_text(surf,name[:22],yr.x+36,yr.y+3,f10,BRIGHT if i==self.selected else TEXT)
        surf.set_clip(None); self.scroll.draw(surf)
        draw_text(surf,f"Advance {self.adv_n} turn{'s' if self.adv_n!=1 else ''}",self.PAD,BTN_Y-16,f10,DIM)
        self.btn_minus.draw(surf); self.btn_plus.draw(surf)
        self.btn_adv.draw(surf); self.btn_save.draw(surf); self.btn_disc.draw(surf)
    def on_event(self,ev):
        mx,my=pygame.mouse.get_pos(); BTN_Y=SH-SBAR_H-118; list_h=BTN_Y-TBAR_H-46
        in_list=mx<LWIDTH and my>TBAR_H+40 and my<TBAR_H+40+list_h
        self.scroll.on_event(ev,in_list)
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            for i,name in enumerate(self.nations):
                yr=pygame.Rect(self.PAD,TBAR_H+40-int(self.scroll.scroll)+i*22,LWIDTH-Scrollbar.W-self.PAD*2,20)
                if yr.collidepoint(ev.pos) and 0<ev.pos[0]<LWIDTH: return i
        return None

class MainPanel:
    def __init__(self):
        self.rows=[]; self.scroll=Scrollbar(SW-Scrollbar.W-2,MAIN_Y,MAIN_H); self.edit=EditOverlay()
    def set_rows(self,rows):
        self.rows=rows; total=sum(r["h"] for r in rows)
        self.scroll.set_content(total,MAIN_H-(self.edit.H if self.edit.active else 0)); self.scroll.scroll=0
    def _row_rects(self):
        rects=[]; y=MAIN_Y-int(self.scroll.scroll)
        for r in self.rows: rects.append(pygame.Rect(MAIN_X,y,MAIN_W-Scrollbar.W,r["h"])); y+=r["h"]
        return rects
    def draw(self,surf):
        clip=pygame.Rect(MAIN_X,MAIN_Y,MAIN_W-Scrollbar.W,MAIN_H-(self.edit.H if self.edit.active else 0))
        surf.set_clip(clip); f12=gf(12); f11=gf(11); f10=gf(10); f13=gf(13)
        mx,my=pygame.mouse.get_pos(); rects=self._row_rects()
        for i,(row,rect) in enumerate(zip(self.rows,rects)):
            if rect.bottom<MAIN_Y or rect.top>MAIN_Y+MAIN_H: continue
            rt=row["type"]
            if rt=="hdr1":
                draw_rect(surf,rect,(16,28,44)); draw_rect(surf,pygame.Rect(MAIN_X,rect.y,3,rect.h),ACCENT)
                draw_text(surf,row["txt"],rect.x+10,rect.y+8,f13,BRIGHT,clip)
            elif rt=="hdr2":
                draw_rect(surf,rect,(13,22,36)); draw_rect(surf,pygame.Rect(rect.x,rect.bottom-1,rect.w,1),BORDER)
                draw_text(surf,row["txt"],rect.x+10,rect.y+6,f12,CYAN,clip)
            elif rt=="species_hdr":
                draw_rect(surf,rect,(14,24,38))
                crown="[crown]" if row["status"] in ("dominant","majority") else "[sp]"
                draw_text(surf,f"{row['name']}  ({row['status'].title()})",rect.x+10,rect.y+6,f12,GOLD,clip)
            elif rt=="territory_planet":
                draw_rect(surf,rect,(13,22,36)); draw_rect(surf,pygame.Rect(rect.x,rect.bottom-1,rect.w,1),BORDER2)
                draw_text(surf,f"> {row['name']}",rect.x+10,rect.y+6,f12,TEAL,clip)
            elif rt=="row":
                is_edit=bool(row.get("meta"))
                bg=HOVER if (is_edit and rect.collidepoint(mx,my)) else ((10,18,28) if i%2==0 else BG)
                draw_rect(surf,rect,bg); draw_text(surf,row["label"],rect.x+8,rect.y+3,f11,DIM,clip)
                vc=EDITBDR if (is_edit and rect.collidepoint(mx,my)) else row.get("vcol",TEXT)
                draw_text(surf,row["val"],rect.x+190,rect.y+3,f11,vc,clip)
            elif rt=="bar":
                draw_rect(surf,rect,(10,18,28) if i%2==0 else BG)
                draw_text(surf,row["label"],rect.x+8,rect.y+3,f11,DIM,clip)
                bx=rect.x+168; by=rect.y+5; bw=100; bh=10
                draw_rect(surf,pygame.Rect(bx,by,bw,bh),(18,32,50),radius=2)
                fw=int(row["pct"]*bw)
                if fw>0: draw_rect(surf,pygame.Rect(bx,by,fw,bh),row.get("vcol",CYAN),radius=2)
                draw_text(surf,row["txt"],bx+bw+6,rect.y+3,f11,TEXT,clip)
            elif rt=="btn":
                is_hov=rect.collidepoint(mx,my); base_col=row.get("col") or (28,54,82)
                bg=tuple(min(255,c+25) for c in base_col) if is_hov else base_col
                draw_rect(surf,rect,bg,radius=3); draw_rect(surf,rect,BORDER2,border=1,radius=3)
                s=f11.render(row["label"],True,BRIGHT); surf.blit(s,s.get_rect(midleft=(rect.x+8,rect.centery)))
            elif rt=="event_row":
                draw_rect(surf,rect,(10,18,28) if i%2==0 else BG)
                draw_text(surf,row["txt"],rect.x+8,rect.y+3,f10,tuple(row["col"]),clip)
        surf.set_clip(None); self.scroll.draw(surf)
    def on_click(self,ev):
        if ev.type!=pygame.MOUSEBUTTONDOWN or ev.button!=1: return None
        if not (MAIN_X<=ev.pos[0]<SW-Scrollbar.W and MAIN_Y<=ev.pos[1]<MAIN_Y+MAIN_H): return None
        for row,rect in zip(self.rows,self._row_rects()):
            if rect.collidepoint(ev.pos):
                if row["type"]=="btn": return row
                if row.get("meta"): return row
        return None
    def on_event(self,ev):
        mx,my=pygame.mouse.get_pos(); self.scroll.on_event(ev,MAIN_X<=mx<SW and MAIN_Y<=my<MAIN_Y+MAIN_H)

_status_msg=""; _status_col=DIM; _status_time=0.0
def set_status(msg,col=DIM):
    global _status_msg,_status_col,_status_time; _status_msg=msg; _status_col=col; _status_time=time.time()

def draw_top_bar(surf,name,turn,year,quarter,dirty):
    draw_rect(surf,pygame.Rect(LWIDTH,0,SW-LWIDTH,TBAR_H),(10,16,26))
    draw_rect(surf,pygame.Rect(LWIDTH,TBAR_H-1,SW-LWIDTH,1),BORDER)
    draw_text(surf,name,LWIDTH+12,10,gf(13,False),BRIGHT)
    if dirty: draw_text(surf,"UNSAVED",SW-80,12,gf(11),GOLD)

def draw_tab_bar(surf,tab_idx):
    draw_rect(surf,pygame.Rect(LWIDTH,TBAR_H,SW-LWIDTH,TABBAR_H),(10,16,26))
    draw_rect(surf,pygame.Rect(LWIDTH,TBAR_H+TABBAR_H-1,SW-LWIDTH,1),BORDER)
    f10=gf(10); w=(SW-LWIDTH)//len(TABS)
    for i,tab in enumerate(TABS):
        tx=LWIDTH+i*w; tr=pygame.Rect(tx,TBAR_H,w,TABBAR_H)
        if i==tab_idx:
            draw_rect(surf,tr,(18,36,58)); draw_rect(surf,pygame.Rect(tx,TBAR_H+TABBAR_H-2,w,2),CYAN)
            s=f10.render(tab,True,BRIGHT)
        else:
            if tr.collidepoint(pygame.mouse.get_pos()): draw_rect(surf,tr,HOVER)
            s=f10.render(tab,True,DIM)
        surf.blit(s,s.get_rect(center=tr.center))

def draw_status_bar(surf):
    draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,SBAR_H),(8,14,22)); draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,1),BORDER)
    age=time.time()-_status_time; col=_status_col if age<3.0 else DIM
    draw_text(surf,_status_msg if age<5.0 else "Ready",10,SH-SBAR_H+4,gf(10),col)
    draw_text(surf,"S=save  D=discord  Up/Down=nation  Tab/1-6=tab",SW-360,SH-SBAR_H+4,gf(10),DIM2)

def main():
    filepath=sys.argv[1] if len(sys.argv)>1 else DEFAULT_STATE
    sm=StateManager(filepath)
    if not sm.load(): sys.exit(f"[FATAL] Cannot load: {filepath}")
    pygame.init(); pygame.display.set_caption("Carmine NRP Engine - vAlpha0.4.0")
    surf=pygame.display.set_mode((SW,SH)); clock=pygame.time.Clock()
    left=LeftPanel(); main_=MainPanel()
    names=sm.nation_names(); sel_idx=0; tab_idx=0
    left.set_nations(names,sel_idx)
    def load_nation(idx):
        nonlocal sel_idx; sel_idx=max(0,min(idx,len(names)-1)); left.selected=sel_idx
        n=sm.get_nation(names[sel_idx])
        if n: main_.set_rows(build_rows(n,sm.state,TABS[tab_idx]))
    def do_discord():
        n=sm.get_nation(names[sel_idx])
        if n: path=_discord_export(n,sm.state); set_status(f"Discord -> {path}",CYAN)
    load_nation(0); set_status(f"Loaded: {filepath}  |  discord_exports/ subfolder ready",CYAN)
    running=True
    while running:
        dt=clock.tick(FPS)/1000.0
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False
            if main_.edit.active:
                result=main_.edit.on_event(ev)
                if result is not None:
                    n=sm.get_nation(names[sel_idx])
                    if n and apply_edit(n,main_.edit.meta,result):
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Saved.",GREEN)
                elif ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: main_.edit.close()
                continue
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_s: sm.save(); set_status("Saved with backup rotation.",GREEN)
                elif ev.key==pygame.K_d: do_discord()
                elif ev.key in (pygame.K_UP,pygame.K_LEFT): load_nation(sel_idx-1)
                elif ev.key in (pygame.K_DOWN,pygame.K_RIGHT): load_nation(sel_idx+1)
                elif ev.key==pygame.K_TAB:
                    tab_idx=(tab_idx+1)%len(TABS); load_nation(sel_idx)
                elif pygame.K_1<=ev.key<=pygame.K_6:
                    tab_idx=ev.key-pygame.K_1; load_nation(sel_idx)
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if LWIDTH<=ev.pos[0]<SW and TBAR_H<=ev.pos[1]<TBAR_H+TABBAR_H:
                    w=(SW-LWIDTH)//len(TABS); ti=(ev.pos[0]-LWIDTH)//w
                    if 0<=ti<len(TABS): tab_idx=ti; load_nation(sel_idx)
            clicked=left.on_event(ev)
            if clicked is not None: load_nation(clicked)
            if left.btn_minus.on_event(ev): left.adv_n=max(1,left.adv_n-1)
            if left.btn_plus.on_event(ev): left.adv_n=min(20,left.adv_n+1)
            if left.btn_adv.on_event(ev):
                evs=advance_turns(sm,left.adv_n); names=sm.nation_names(); left.set_nations(names,sel_idx); load_nation(sel_idx)
                t=sm.state.get("turn",1); y=sm.state.get("year",2200); q=sm.state.get("quarter",1)
                set_status(f"Advanced {left.adv_n}t -> T{t} {y}Q{q}  |  {len(evs)} events fired",GOLD)
            if left.btn_save.on_event(ev): sm.save(); set_status("Saved.",GREEN)
            if left.btn_disc.on_event(ev): do_discord()
            main_.on_event(ev)
            row=main_.on_click(ev)
            if row:
                if row["type"]=="btn":
                    action=row["action"]; data=row.get("data",{}); n=sm.get_nation(names[sel_idx])
                    if action=="add_system" and n:
                        add_system(n); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("New system added.",GREEN)
                    elif action=="add_planet" and n:
                        sl=n.get("star_systems",[]); si=data.get("si",0)
                        if si<len(sl): add_planet(sl[si],n.get("population",0)); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Planet added + randomized.",GREEN)
                    elif action=="randomize_planet" and n:
                        si=data.get("si",0); pi=data.get("pi",0); sl=n.get("star_systems",[])
                        if si<len(sl):
                            pl=sl[si].get("planets",[])
                            if pi<len(pl): randomize_planet(pl[pi],n.get("population",0)); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Planet randomized.",PURPLE)
                    elif action=="roll_events":
                        n2=sm.get_nation(data.get("nation",""))
                        if n2:
                            evs=roll_civic_events(n2,sm.state)+roll_planetside_events(n2,sm.state)+roll_resource_events(n2,sm.state)
                            sm.state.setdefault("events_log",[]).extend(evs); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status(f"Rolled {len(evs)} events for {data.get('nation','?')}.",GOLD)
                elif row.get("meta"): main_.edit.open(row["label"],row["val"],row["meta"])
        surf.fill(BG)
        turn=sm.state.get("turn",1); year=sm.state.get("year",2200); quarter=sm.state.get("quarter",1)
        draw_top_bar(surf,names[sel_idx] if names else "N/A",turn,year,quarter,sm.dirty)
        draw_tab_bar(surf,tab_idx); left.draw(surf,turn,year,quarter); main_.draw(surf)
        main_.edit.draw(surf,dt); draw_status_bar(surf); pygame.display.flip()
    pygame.quit()

if __name__=="__main__":
    main()