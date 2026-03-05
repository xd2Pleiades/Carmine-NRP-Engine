#!/usr/bin/env python3
"""
Carmine NRP Engine - vAlpha0.6.3
New in 0.6.3: monetary loop fix (trade net credited to strategic_fund each turn),
              route_modifier applied, export_by_resource fix, discord tithe_in,
              compute_resource_export_credits uses net-of-piracy value
"""
import sys, os, json, shutil, math, time, random
import pygame
from pathlib import Path

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
TABS         = ["OVERVIEW","ECONOMY","MILITARY","TERRITORY","MARKET","GALACTIC","EVENTS"]
TABS_COLONY  = ["OVERVIEW","COLONY","MILITARY","TERRITORY","MARKET","GALACTIC","EVENTS"]

BG=(8,12,20);PANEL=(12,18,28);BORDER=(28,52,80);BORDER2=(44,86,128);ACCENT=(190,38,25)
CYAN=(0,190,214);TEAL=(0,138,158);TEXT=(198,226,246);DIM=(84,114,136);DIM2=(50,72,92)
BRIGHT=(238,248,255);GREEN=(22,184,82);RED_C=(216,54,40);GOLD=(198,150,22)
SEL=(18,40,65);HOVER=(14,30,50);EDITBG=(5,14,28);EDITBDR=(0,172,194)
BTNBG=(18,36,56);BTNHOV=(28,54,82);BTNACC=(140,24,16);BTNACC2=(190,38,25)
PURPLE=(130,60,200);ORANGE=(200,100,30);LIME=(120,220,60)

# ── formatting ────────────────────────────────────────────────────────────────
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

_RESOURCES=["Food","Minerals","Energy","Alloys","Consumer Goods"]
RES_BASE_PRICE={"Food":1.0,"Minerals":2.0,"Energy":4.0,"Alloys":5.0,"Consumer Goods":2.0}
ECON_MODELS=["PLANNED","MARKET","MIXED","COLONY_START"]

# ── district & platform production tables ─────────────────────────────────────
DISTRICT_PROD={
    "Farming":            {"Food":50e6},
    "Agricultural":       {"Food":40e6},
    "Mining":             {"Minerals":20e6},
    "Industrial Civilian":{"Alloys":8e6,"Consumer Goods":12e6},
    "Industrial Military":{"Alloys":18e6},
    "Energy Plant":       {"Energy":25e6},
    "Power":              {"Energy":20e6},
    "Urban":{}, "Residential":{}, "Military":{}, "Research Lab":{},
}
DISTRICT_CONS={
    "Farming":            {"Energy":2e6},
    "Agricultural":       {"Energy":1e6},
    "Mining":             {"Energy":4e6},
    "Industrial Civilian":{"Minerals":10e6,"Energy":8e6},
    "Industrial Military":{"Minerals":20e6,"Energy":12e6},
    "Energy Plant":       {"Minerals":3e6},
    "Power":              {"Minerals":2e6},
}
DISTRICT_MINERAL_COST={"Farming":20,"Agricultural":15,"Mining":30,"Industrial Civilian":40,
    "Industrial Military":60,"Energy Plant":35,"Power":25,"Urban":10,"Residential":8,
    "Military":50,"Research Lab":45}
DISTRICT_BUILD_TURNS={"Farming":2,"Agricultural":2,"Mining":3,"Industrial Civilian":4,
    "Industrial Military":5,"Energy Plant":3,"Power":2,"Urban":2,"Residential":1,
    "Military":4,"Research Lab":5}
PLATFORM_PROD={"Mining":{"Minerals":30e6},"Hydroponics":{"Food":60e6},"Research":{},"Dockyards":{}}

# ── military consumption tables ───────────────────────────────────────────────
# Food = crew headcount, Alloys = per unit (not per count)
UNIT_CREW = {
    "Siegebreaker":85000,"World Cracker":85000,"Dreadnaughts":50000,"Dreadnaught":50000,
    "Battleship":50000,"Battlecruiser":45000,"Heavy Cruiser":40000,"Cruiser":35000,
    "Light Cruiser":10000,"Destroyer":500,"Frigate":150,"Corvette":50,
    "Space patrol Vessels":10,"Space Patrol Vessel":10,"Shipyard Tender":50000,
    "Transport Vessel":10,"Dockyard":100000,
    "Fighter Aircraft":1,"Fighter Aircrafts":1,"Tactical Bomber":4,"Strategic Bomber":4,
    "Strategic Bombers":4,"Attack Aircraft":2,"Reconnaissance & Surveillance Aircraft":2,
    "Unmanned Aerial Vehicle":0,"Tanker Aircraft":2,"Gunship":5,"Transport Aircraft":10,
}
UNIT_ALLOY_CON = {
    "Siegebreaker":100000,"World Cracker":100000,"Dreadnaughts":50000,"Dreadnaught":50000,
    "Battleship":50000,"Battlecruiser":45000,"Heavy Cruiser":30000,"Cruiser":20000,
    "Light Cruiser":10000,"Destroyer":5000,"Frigate":2500,"Corvette":1000,
    "Space patrol Vessels":500,"Space Patrol Vessel":500,"Shipyard Tender":50000,
    "Transport Vessel":50000,"Dockyard":50000,
    "Fighter Aircraft":100,"Fighter Aircrafts":100,"Tactical Bomber":250,"Strategic Bomber":500,
    "Strategic Bombers":500,"Attack Aircraft":300,"Reconnaissance & Surveillance Aircraft":80,
    "Unmanned Aerial Vehicle":50,"Tanker Aircraft":300,"Gunship":250,"Transport Aircraft":250,
}
GROUND_DIVISION_SIZE = 10000  # soldiers per division
GROUND_FOOD_PER_SOLDIER = 1   # food units per soldier per turn
GROUND_ALLOY_PER_DIVISION = 2000  # alloys per division per turn

# ── colony event table ────────────────────────────────────────────────────────
_COLONY_EVENTS=[
    (1,1,"Catastrophic Failure",{"colonization_pct":(-15,-10),"pop_change":(-0.20,-0.10)},RED_C),
    (2,3,"Supply Shortage",{"colonization_pct":(-5,-2)},  (200,80,40)),
    (4,5,"Harsh Conditions",{"colonization_pct":(-3,-1)}, GOLD),
    (6,10,"Steady Progress",{"colonization_pct":(1,3)},   DIM),
    (11,15,"Good Survey",{"colonization_pct":(2,5)},      GREEN),
    (16,18,"Resource Discovery",{"colonization_pct":(3,6),"mineral_bonus":(10,30)}, CYAN),
    (19,19,"Population Surge",{"colonization_pct":(2,4),"pop_change":(0.05,0.15)}, GREEN),
    (20,20,"Golden Founding",{"colonization_pct":(5,10),"pop_change":(0.10,0.20),"mineral_bonus":(20,50)}, GOLD),
]

# ── helpers ───────────────────────────────────────────────────────────────────
def years_elapsed(state): return (state.get("turn",1)-1)*0.25

def _avg_loyalty(nation):
    sp=nation.get("species_populations") or []
    if not sp: return 50.0
    total=sum(s.get("population",0) for s in sp) or 1
    return sum(s.get("loyalty",50)*s.get("population",0) for s in sp)/total

def is_colony(nation): return bool(nation.get("is_colony_start"))

def get_tabs(nation): return TABS_COLONY if is_colony(nation) else TABS

# ── military consumption ──────────────────────────────────────────────────────
def compute_military_consumption(nation):
    """Returns {"Food": X, "Alloys": Y} consumed per turn by all units."""
    food=0.0; alloys=0.0
    for u in (nation.get("active_forces_detail") or []):
        unit_name=u.get("unit",""); count=u.get("count",1)
        cat=u.get("category","")
        if cat in ("Ground Forces","Ground","Army"):
            soldiers=count*GROUND_DIVISION_SIZE
            food+=soldiers*GROUND_FOOD_PER_SOLDIER
            alloys+=count*GROUND_ALLOY_PER_DIVISION
        else:
            crew=UNIT_CREW.get(unit_name,0)
            alloy=UNIT_ALLOY_CON.get(unit_name,0)
            food+=crew*count
            alloys+=alloy*count
    return {"Food":food,"Alloys":alloys}

# ── manpower ──────────────────────────────────────────────────────────────────
def compute_manpower(nation):
    """Returns total manpower pool from all species based on conscription/volunteer rates."""
    pop=nation.get("population",0.0)
    total=0.0
    for s in (nation.get("species_populations") or []):
        sp_pop=s.get("population",0)
        loy=s.get("loyalty",50)
        conscript_rate=s.get("conscription_rate", nation.get("conscription_rate",0.05))
        vol_rate=max(0, (loy-40)/200.0)  # loyalty>40 starts generating volunteers
        gm_adj=s.get("gm_manpower_adj",0.0)
        total+=sp_pop*(conscript_rate+vol_rate)+gm_adj
    override=nation.get("manpower_cap_override",0.0)
    return override if override>0 else total

# ── church tithe ─────────────────────────────────────────────────────────────
CHRISTIAN_KEYWORDS=["christian","catholic","protestant","orthodox","evangelical","church"]
TITHE_RATE=0.10

def compute_church_tithe(nation, state):
    """Returns tithe amount this nation owes to Regnum Dei (0 if not applicable)."""
    rd=next((n for n in state.get("nations",[]) if n["name"]=="Regnum Dei"),None)
    if not rd or nation["name"]=="Regnum Dei": return 0.0
    ipeu=nation.get("base_ipeu",0.0)
    pop=nation.get("population",1.0)
    christian_pop=0.0
    for s in (nation.get("species_populations") or []):
        rel=(s.get("religion") or "").lower()
        if any(k in rel for k in CHRISTIAN_KEYWORDS):
            christian_pop+=s.get("population",0)
    if christian_pop<=0: return 0.0
    christian_share=christian_pop/pop if pop else 0
    return ipeu*christian_share*TITHE_RATE

def apply_tithes(state):
    """Called each turn advance — transfers tithe from all nations to Regnum Dei."""
    rd=next((n for n in state.get("nations",[]) if n["name"]=="Regnum Dei"),None)
    if not rd: return []
    events=[]; turn=state.get("turn",1); year=state.get("year",2200); q=state.get("quarter",1)
    total_tithe=0.0
    for nation in state.get("nations",[]):
        if nation["name"]=="Regnum Dei": continue
        tithe=compute_church_tithe(nation,state)
        if tithe>0:
            nation["strategic_fund"]=nation.get("strategic_fund",0.0)-tithe
            total_tithe+=tithe
            events.append({"turn":turn,"year":year,"quarter":q,"type":"Tithe",
                "nation":nation["name"],"roll":"—","label":"Church Tithe",
                "description":f"{nation['name']} paid {fmt_cr(tithe)} tithe to Regnum Dei",
                "col_rgb":list(GOLD)})
    if total_tithe>0:
        rd["strategic_fund"]=rd.get("strategic_fund",0.0)+total_tithe
    return events
def compute_tithe_income(nation, state):
    """Returns total tithe credits this nation RECEIVES (non-zero only for Regnum Dei)."""
    if nation["name"] != "Regnum Dei": return 0.0
    return sum(compute_church_tithe(n, state) for n in state.get("nations",[]) if n["name"] != "Regnum Dei")


# ── district resources ────────────────────────────────────────────────────────
def compute_district_resources(nation):
    prod={r:0.0 for r in _RESOURCES}; cons={r:0.0 for r in _RESOURCES}
    econ=(nation.get("economic_model") or "MIXED").upper()
    loy=_avg_loyalty(nation)
    res_eff=1.0+(max(0,loy-50)/200.0) if econ=="PLANNED" else 1.0
    for sys in (nation.get("star_systems") or []):
        for planet in (sys.get("planets") or []):
            for sett in (planet.get("settlements") or []):
                for d in (sett.get("districts") or []):
                    if d.get("status","").lower() not in ("operational","active",""): continue
                    dt=d.get("type","")
                    for r,amt in DISTRICT_PROD.get(dt,{}).items(): prod[r]+=amt*res_eff
                    for r,amt in DISTRICT_CONS.get(dt,{}).items(): cons[r]+=amt
            for plat in (planet.get("platforms") or []):
                for r,amt in PLATFORM_PROD.get(plat.get("type",""),{}).items(): prod[r]+=amt
    return prod,cons

def _pop_cons(rname,pop):
    return pop*{"Food":0.001,"Consumer Goods":0.0005,"Energy":0.0002}.get(rname,0.0)

def compute_resources(nation,ipeu):
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    pop=nation.get("population",1.0)
    d_prod,d_cons=compute_district_resources(nation)
    mil_cons=compute_military_consumption(nation)
    out={}
    for rname in _RESOURCES:
        sd=(nation.get("resource_stockpiles") or {}).get(rname,{})
        if not isinstance(sd,dict): sd={}
        stock=sd.get("stockpile",0.0)
        if sd.get("production_mode")=="flat":
            prod=sd.get("flat_production",0.0); cons=sd.get("flat_consumption",0.0)
        elif d_prod.get(rname,0)>0 or d_cons.get(rname,0)>0:
            prod=d_prod[rname]; cons=d_cons[rname]+_pop_cons(rname,pop)
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
        # add military consumption on top
        cons+=mil_cons.get(rname,0.0)
        net=prod-cons
        out[rname]={"stockpile":stock,"production":prod,"consumption":cons,"net":net,
                    "trend":"▲" if net>0 else ("▼" if net<0 else "─"),
                    "mil_consumption":mil_cons.get(rname,0.0)}
    return out

# ── colony resource handling ──────────────────────────────────────────────────
def compute_vessel_resources(nation):
    vs=nation.get("vessel_stats",{}); vsp=nation.get("vessel_stockpiles",{})
    out={}
    for rname in ["Food","Minerals","Alloys","Energy"]:
        prod_key={"Food":"food_production","Minerals":"mineral_extraction",
                  "Alloys":"alloy_production","Energy":"energy_production"}.get(rname,"")
        cons_key={"Food":"food_consumption","Energy":"energy_consumption"}.get(rname,"")
        prod=vs.get(prod_key,0.0); cons=vs.get(cons_key,0.0) if cons_key else 0.0
        stock=vsp.get(rname,0.0); net=prod-cons
        out[rname]={"stockpile":stock,"production":prod,"consumption":cons,"net":net,
                    "trend":"▲" if net>0 else ("▼" if net<0 else "─")}
    return out

def get_colony_progress(nation):
    """Returns list of (planet_name, colonization_pct) across all planets."""
    result=[]
    for sys in (nation.get("star_systems") or []):
        for p in (sys.get("planets") or []):
            result.append({"planet":p.get("name","?"),"colonization_pct":p.get("colonization_pct",0.0),
                           "explored_pct":p.get("explored_pct",0.0),
                           "pop":p.get("pop_assigned",0),"system":sys.get("name","?")})
    return result

# ── loyalty / happiness formulas ──────────────────────────────────────────────
def compute_species_loyalty_happiness(nation,res):
    sp=nation.get("species_populations") or []
    if not sp: return
    exp=nation.get("expenditure") or {}
    pop_dev=exp.get("Population Development",0.0); infra=exp.get("Infrastructure",0.0)
    pop_dev_bonus=pop_dev*30; infra_hap=infra*20
    cg_stock=(res.get("Consumer Goods") or {}).get("stockpile",0.0)
    pop=nation.get("population",1.0); cg_per_cap=cg_stock/pop if pop else 0
    cg_factor=min(1.5,0.5+cg_per_cap*1e-4)
    total_unrest=total_crime=planet_count=0
    for sys in (nation.get("star_systems") or []):
        for p in (sys.get("planets") or []):
            total_unrest+=p.get("unrest",0.0); total_crime+=p.get("crime_rate",0.0); planet_count+=1
    avg_unrest=total_unrest/planet_count if planet_count else 0
    avg_crime=total_crime/planet_count if planet_count else 0
    econ=(nation.get("economic_model") or "MIXED").upper()
    dist_bonus=5.0 if econ=="PLANNED" else 0.0
    for s in sp:
        base_loy=s.get("_base_loyalty",s.get("loyalty",50)); s["_base_loyalty"]=base_loy
        s["loyalty"]=round(max(0,min(100,base_loy*cg_factor/(1+avg_unrest/100)+pop_dev_bonus+dist_bonus)),1)
        base_hap=s.get("_base_happiness",50.0)
        if isinstance(s.get("happiness"),(int,float)): base_hap=s["happiness"]; s["_base_happiness"]=base_hap
        s["happiness"]=round(max(0,min(100,base_hap*cg_factor/(1+avg_crime/100+avg_unrest/100)+infra_hap+dist_bonus)),1)

def compute_resource_export_credits(nation,state):
    name=nation["name"]; ec={r:0.0 for r in _RESOURCES}
    for route in state.get("trade_routes",[]):
        if route.get("status")!="active" or route.get("exporter")!=name: continue
        r=route.get("resource","")
        # use net-of-piracy, net-of-transit-tax value (mirrors compute_trade exporter earnings)
        if r not in ec: continue
        cr=route.get("credits_per_turn",0.0)*(1.0+route.get("route_modifier",0.0))
        loss=route.get("_piracy_loss_this_turn",0.0); net_cr=cr-loss
        ts=route.get("transit_nations",[])
        tax=sum(cr*t.get("tax_rate",0.0) for t in ts if t.get("status")=="active")
        ec[r]+=net_cr-tax
    return ec

def compute_planet_local_market(nation,state,ipeu):
    econ=(nation.get("economic_model") or "MIXED").upper()
    if econ in ("PLANNED","COLONY_START"): return [],0.0
    exp=nation.get("expenditure") or {}
    infra_bonus=exp.get("Infrastructure",0.0)*1.5
    tax_rate=0.15 if econ=="MARKET" else 0.10
    results=[]; total_tax=0.0
    for sys in (nation.get("star_systems") or []):
        for planet in (sys.get("planets") or []):
            attract=max(0,planet.get("habitability",50)-planet.get("devastation",0)
                        -planet.get("unrest",0)*0.5-planet.get("crime_rate",0)*0.3)
            local=planet.get("pop_assigned",0)*50.0*(attract/100.0)*(1+infra_bonus)
            tax=local*tax_rate; total_tax+=tax
            results.append({"planet":planet.get("name","?"),"attractiveness":round(attract,1),
                            "local_output":local,"tax_income":tax})
    return results,total_tax

def compute_subsidies(nation,ipeu):
    econ=(nation.get("economic_model") or "MIXED").upper()
    if econ in ("PLANNED","COLONY_START"): return 0.0,0.0
    return nation.get("subsidy_rate",0.0)*ipeu, nation.get("investment_rate",0.0)*20.0

def spending_effects(nation,ipeu):
    exp=nation.get("expenditure") or {}
    infra=exp.get("Infrastructure",0.0); popdev=exp.get("Population Development",0.0); mil=exp.get("Military",0.0)
    return {"infra_trade_bonus":round(infra*200,1),"infra_distrib_speed":round(infra*3,2),
            "popdev_growth_bonus":round(popdev*0.5,3),"mil_morale_bonus":round(mil*150,1),
            "mil_combat_power":round(mil*ipeu/1e12,3)}

def econ_model_ipeu_modifier(nation):
    econ=(nation.get("economic_model") or "MIXED").upper()
    loy=_avg_loyalty(nation)
    if econ=="PLANNED":   return nation.get("bureaucratic_efficiency",1.0)+(loy-50)/200.0
    elif econ=="MARKET":  return 1.05
    elif econ=="COLONY_START": return 0.80
    return 1.02  # MIXED

def compute_debt(nation,ipeu):
    bal=nation.get("debt_balance",0.0); rate=nation.get("interest_rate",0.0); rep=nation.get("debt_repayment",0.0)
    qi=bal*rate/4.0 if bal>0 else 0.0
    return {"balance":bal,"rate":rate,"repayment":rep,"q_interest":qi,
            "load_pct":(bal/ipeu*100) if ipeu else 0.0,"is_debtor":bal>0}

def compute_trade(nation,routes):
    name=nation["name"]; exports=imports=transit=0.0; ed={r:0.0 for r in _RESOURCES}
    for r in routes:
        if r.get("status")!="active": continue
        cr=r.get("credits_per_turn",0.0)*(1.0+r.get("route_modifier",0.0))  # apply route modifier
        loss=r.get("_piracy_loss_this_turn",0.0); net_cr=cr-loss
        ts=r.get("transit_nations",[])
        if r["exporter"]==name:
            tax=sum(cr*t.get("tax_rate",0.0) for t in ts if t.get("status")=="active")
            earns=net_cr-tax; exports+=earns; res=r.get("resource","")
            if res in ed: ed[res]+=earns  # track actual post-tax, post-piracy earnings
        if r["importer"]==name: imports+=net_cr
        for t in ts:
            if t.get("nation")==name and t.get("status")=="active": transit+=cr*t.get("tax_rate",0.0)
    return {"exports":exports,"imports":imports,"transit_income":transit,"net":exports-imports+transit,"export_by_resource":ed}

def compute_galactic_stockpiles(state):
    totals={r:0.0 for r in _RESOURCES}; prod={r:0.0 for r in _RESOURCES}; cons={r:0.0 for r in _RESOURCES}
    for nation in state.get("nations",[]):
        res=compute_resources(nation,nation.get("base_ipeu",0.0))
        for r in _RESOURCES:
            totals[r]+=res[r]["stockpile"]; prod[r]+=res[r]["production"]; cons[r]+=res[r]["consumption"]
    return totals,prod,cons

def price_shock_delta(rname,gprod,gcons,curr,base):
    if gcons<=0: return 0.0
    ratio=gprod/gcons
    if ratio>1.2:  return -0.05
    elif ratio>1.05: return -0.02
    elif ratio>0.95: return 0.0
    elif ratio>0.8:  return 0.03
    return 0.08

# ── construction queue ────────────────────────────────────────────────────────
def advance_construction(nation,state):
    """Tick all in-progress construction items. Returns list of completion events."""
    events=[]; turn=state.get("turn",1); year=state.get("year",2200); q=state.get("quarter",1)
    queue=nation.get("construction_queue") or []
    still_building=[]
    for item in queue:
        item["turns_remaining"]=item.get("turns_remaining",1)-1
        if item["turns_remaining"]<=0:
            # place the district
            si=item.get("si",0); pi=item.get("pi",0); sett_i=item.get("sett_i",0)
            try:
                planet=nation["star_systems"][si]["planets"][pi]
                sett=planet["settlements"][sett_i]
                sett.setdefault("districts",[]).append({"type":item["district_type"],"status":"Operational","notes":"","built_turn":turn,"workforce":0})
                events.append({"turn":turn,"year":year,"quarter":q,"type":"Construction","nation":nation["name"],
                    "roll":"—","label":"Build Complete",
                    "description":f"{item['district_type']} completed on {planet.get('name','?')} ({item.get('settlement_name','?')})",
                    "col_rgb":list(LIME)})
            except (IndexError,KeyError): pass
        else:
            still_building.append(item)
    nation["construction_queue"]=still_building
    return events

def queue_construction(nation,si,pi,sett_i,district_type,state):
    """Add a construction job. Returns (ok, message)."""
    mcost=DISTRICT_MINERAL_COST.get(district_type,20)
    sp=nation.get("resource_stockpiles",{})
    minerals=sp.get("Minerals",{}).get("stockpile",0.0) if isinstance(sp.get("Minerals"),dict) else 0.0
    if minerals<mcost: return False,f"Need {mcost} Minerals, have {fmt_res(minerals)}"
    # deduct minerals
    if isinstance(sp.get("Minerals"),dict): sp["Minerals"]["stockpile"]-=mcost
    turns=DISTRICT_BUILD_TURNS.get(district_type,3)
    try: sname=nation["star_systems"][si]["planets"][pi]["settlements"][sett_i].get("name","?")
    except: sname="?"
    nation.setdefault("construction_queue",[]).append({
        "district_type":district_type,"si":si,"pi":pi,"sett_i":sett_i,
        "turns_remaining":turns,"settlement_name":sname,"mineral_cost":mcost})
    return True,f"Queued {district_type} ({turns} turns, {mcost} Minerals)"

# ── piracy ────────────────────────────────────────────────────────────────────
_PIRACY_DIST={"near":0.05,"kind of far":0.12,"too far":0.22}
def roll_piracy_events(state):
    evs=[]; turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    for route in state.get("trade_routes",[]):
        if route.get("status")!="active": continue
        chance=max(0,_PIRACY_DIST.get(route.get("pirate_distance","near").lower(),0.05)
                   -int(route.get("pirate_escort","0") or 0)*0.01)
        if random.random()<chance:
            cpt=route.get("credits_per_turn",0.0); pct=random.uniform(0.10,0.40); stolen=cpt*pct
            route["pirate_incidents"]=route.get("pirate_incidents",0)+1
            route["total_pirated"]=route.get("total_pirated",0.0)+stolen
            route["_piracy_loss_this_turn"]=stolen
            evs.append({"turn":turn,"year":year,"quarter":q,"type":"Piracy",
                        "nation":route.get("exporter","?"),"roll":round(chance*100,1),
                        "label":f"Piracy on {route.get('name','?')}",
                        "description":f"{route.get('name','?')}: {pct:.0%} stolen = {fmt_cr(stolen)}",
                        "col_rgb":list(RED_C)})
        else: route["_piracy_loss_this_turn"]=0.0
    return evs

# ── standard event tables ─────────────────────────────────────────────────────
_MARKET_SHOCK=[(1,2,"MARKET CRASH",(-0.50,-0.30),RED_C),(3,5,"Price Drop",(-0.20,-0.10),(200,80,40)),
               (6,15,"Stable",(0.0,0.0),DIM),(16,18,"Price Surge",(0.10,0.20),GREEN),(19,20,"MARKET BOOM",(0.30,0.50),GOLD)]
_PLANETSIDE=[(1,1,"Natural Disaster",{"devastation":(5,15),"unrest":(10,20)},RED_C),
             (2,3,"Infrastructure Fail",{"crime_rate":(5,10)},(200,80,40)),
             (4,6,"Minor Unrest",{"unrest":(5,15)},GOLD),(7,14,"Stable",{},DIM),
             (15,16,"Pop Boom",{},GREEN),(17,18,"Crime Crackdown",{"crime_rate":(-10,-5)},CYAN),
             (19,19,"Infrastructure Boom",{"unrest":(-10,-5)},CYAN),
             (20,20,"Golden Age",{"unrest":(-15,-10),"crime_rate":(-10,-5)},GOLD)]
_RESOURCE_EV=[(1,2,"Resource Depletion","flat_production",(-0.30,-0.15),RED_C),
              (3,5,"Extraction Issues","flat_production",(-0.15,-0.05),(200,80,40)),
              (6,15,"Normal Output",None,(0.0,0.0),DIM),(16,18,"Rich Vein","flat_production",(0.10,0.25),GREEN),
              (19,20,"Motherlode","flat_production",(0.25,0.50),GOLD)]
_CIVIC=[(1,2,"Mass Exodus","loyalty",(-20,-10),RED_C),(3,5,"Civic Unrest","loyalty",(-12,-5),(200,80,40)),
        (6,8,"Protests","loyalty",(-5,-2),GOLD),(9,14,"Civic Stability",None,(0,0),DIM),
        (15,17,"Community Programs","loyalty",(3,6),GREEN),(18,19,"Cultural Festival","loyalty",(5,10),CYAN),
        (20,20,"Loyalty Surge","loyalty",(10,20),GOLD)]

def _d20(): return random.randint(1,20)
def _lookup(table,roll):
    for row in table:
        if row[0]<=roll<=row[1]: return row
    return table[len(table)//2]

def roll_market_events(state):
    market=state.get("market",{}); mods=market.get("market_modifier",{})
    evs=[]; turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    gal_s,gal_p,gal_c=compute_galactic_stockpiles(state)
    for rname in _RESOURCES:
        roll=_d20(); row=_lookup(_MARKET_SHOCK,roll); _,_,label,(lo,hi),col=row
        rand_d=0.0 if lo==hi==0.0 else random.uniform(lo,hi)
        base=RES_BASE_PRICE[rname]; old=mods.get(rname,base)
        sd_d=price_shock_delta(rname,gal_p[rname],gal_c[rname],old,base)
        delta=rand_d*0.7+sd_d*0.3; new=round(max(base*0.3,old*(1.0+delta)),4); mods[rname]=new
        evs.append({"turn":turn,"year":year,"quarter":q,"type":"Market","resource":rname,"roll":roll,"label":label,
                    "description":f"{rname}: {label} ({1+delta:+.0%}) -> {new:.3f} cr","col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]})
    market["market_modifier"]=mods
    ph=market.get("price_history",{})
    for rname in _RESOURCES: ph.setdefault(rname,[]).append(round(mods.get(rname,RES_BASE_PRICE[rname]),3))
    market["price_history"]=ph
    return evs

def roll_colony_events(nation,state):
    turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    evs=[]
    for sys in (nation.get("star_systems") or []):
        for planet in (sys.get("planets") or []):
            roll=_d20(); row=_lookup(_COLONY_EVENTS,roll)
            _,_,label,effects,col=row
            desc=f"{nation['name']} / {planet.get('name','?')}: {label}"
            for ef,rng in effects.items():
                if ef=="colonization_pct":
                    delta=random.uniform(*rng)
                    planet["colonization_pct"]=round(max(0,min(100,planet.get("colonization_pct",0)+delta)),2)
                    desc+=f"  col{delta:+.1f}%"
                elif ef=="pop_change":
                    pct=random.uniform(*rng)
                    planet["pop_assigned"]=max(0,planet.get("pop_assigned",0)*(1+pct))
                    desc+=f"  pop{pct:+.0%}"
                elif ef=="mineral_bonus":
                    amt=random.uniform(*rng)
                    vs=nation.get("vessel_stockpiles",{}); vs["Minerals"]=vs.get("Minerals",0)+amt
                    nation["vessel_stockpiles"]=vs; desc+=f"  +{amt:.0f} Minerals"
            evs.append({"turn":turn,"year":year,"quarter":q,"type":"Colony","nation":nation["name"],
                "roll":roll,"label":label,"description":desc,"col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]})
    return evs

def roll_civic_events(nation,state):
    turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    sp=nation.get("species_populations",[]) or []; roll=_d20(); row=_lookup(_CIVIC,roll)
    _,_,label,field,(lo,hi),col=row; desc=f"{nation['name']}: {label}"
    if field=="loyalty" and sp:
        delta=random.randint(int(lo),int(hi))
        for s in sp: s["_base_loyalty"]=max(0,min(100,s.get("_base_loyalty",s.get("loyalty",50))+delta))
        desc+=f"  (loyalty {delta:+d})"
    return [{"turn":turn,"year":year,"quarter":q,"type":"Civic","nation":nation["name"],"roll":roll,"label":label,
             "description":desc,"col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]

def roll_planetside_events(nation,state):
    turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    for sys in (nation.get("star_systems",[]) or []):
        for planet in sys.get("planets",[]):
            roll=_d20(); row=_lookup(_PLANETSIDE,roll); _,_,label,effects,col=row
            desc=f"{nation['name']} / {planet.get('name','?')}: {label}"
            for ef,(lo,hi) in effects.items():
                delta=random.uniform(lo,hi); planet[ef]=round(max(0,planet.get(ef,0)+delta),2); desc+=f"  {ef}{delta:+.1f}"
            return [{"turn":turn,"year":year,"quarter":q,"type":"Planetside","nation":nation["name"],"roll":roll,"label":label,
                     "description":desc,"col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]
    return []

def roll_resource_events(nation,state):
    turn,year,q=state.get("turn",1),state.get("year",2200),state.get("quarter",1)
    rname=random.choice(_RESOURCES); roll=_d20(); row=_lookup(_RESOURCE_EV,roll)
    _,_,label,field,(lo,hi),col=row; desc=f"{nation['name']}: {rname} - {label}"
    if field:
        delta=random.uniform(lo,hi); sp=nation.get("resource_stockpiles") or {}
        if not isinstance(sp,dict): sp={}
        rd=sp.get(rname,{})
        if not isinstance(rd,dict): rd={}
        if rd.get("production_mode")=="flat":
            rd["flat_production"]=max(0,rd.get("flat_production",0)*(1.0+delta)); sp[rname]=rd; nation["resource_stockpiles"]=sp
        desc+=f"  ({delta:+.0%})"
    return [{"turn":turn,"year":year,"quarter":q,"type":"Resource","nation":nation["name"],"roll":roll,"label":label,
             "description":desc,"col_rgb":list(col) if isinstance(col,tuple) else [84,114,136]}]

# ── turn advancement ──────────────────────────────────────────────────────────
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
                nation["strategic_fund"]=nation.get("strategic_fund",0.0)+tax+trade_flow["net"]
                all_evs.extend(advance_construction(nation,sm.state))
                all_evs.extend(roll_civic_events(nation,sm.state))
                all_evs.extend(roll_planetside_events(nation,sm.state))
                all_evs.extend(roll_resource_events(nation,sm.state))
            # update manpower pool
            nation["manpower_pool"]=compute_manpower(nation)
    sm.state.setdefault("events_log",[]).extend(all_evs)
    sm.mark_dirty(); sm.save()
    t2=sm.state.get("turn",1); y2=sm.state.get("year",2200); q2=sm.state.get("quarter",1)
    sm.save_history(t2,y2,q2,sm.state)
    return all_evs

# ── territory tools ───────────────────────────────────────────────────────────
_PLANET_TYPES=["Terrestrial","Continental","Arid","Desert","Ocean","Arctic","Toxic","Jungle","Barren","Gas Giant"]
_PLANET_SIZES=["Tiny","Small","Medium","Large","Huge"]
_CLIMATES=["Temperate","Arid","Oceanic","Arctic","Toxic","Jungle","Desert"]
_DISTRICT_TYPES=["Residential","Urban","Industrial Civilian","Industrial Military","Farming","Agricultural",
                  "Mining","Energy Plant","Power","Military","Research Lab"]
_PLATFORM_TYPES=["Mining","Hydroponics","Research","Dockyards"]

def _rng_name(prefix,idx):
    suf=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Prime","Secundus","Tertius","IV","V","VI"]
    return f"{prefix} {suf[idx%len(suf)]}"

def randomize_planet(planet,total_pop):
    planet["type"]=random.choice(_PLANET_TYPES); planet["size"]=random.choice(_PLANET_SIZES)
    planet["climate"]=random.choice(_CLIMATES); planet["habitability"]=round(random.uniform(10,95),1)
    planet["devastation"]=round(random.uniform(0,15),1); planet["crime_rate"]=round(random.uniform(0,25),1)
    planet["unrest"]=round(random.uniform(0,20),1)
    sz={"Tiny":0.05,"Small":0.10,"Medium":0.20,"Large":0.35,"Huge":0.50}
    pp=total_pop*sz.get(planet.get("size","Medium"),0.2)*(planet.get("habitability",50)/100.0)
    planet["pop_assigned"]=round(pp); n_s=random.randint(1,3); setts=[]; rem=pp
    for i in range(n_s):
        s_pop=rem/(n_s-i); n_d=random.randint(2,6)
        districts=[{"type":random.choice(_DISTRICT_TYPES),"status":"Operational","notes":"","built_turn":0,"workforce":0} for _ in range(n_d)]
        setts.append({"name":_rng_name(planet.get("name","S"),i),"population":round(s_pop),"loyalty":round(random.uniform(40,85),1),"amenities":round(random.uniform(30,80),1),"districts":districts})
        rem-=s_pop
    planet["settlements"]=setts; planet.setdefault("platforms",[])

def add_system(nation,name=""):
    si=len(nation.get("star_systems",[]))
    if not name: name=_rng_name("System",si)
    nation.setdefault("star_systems",[]).append({"name":name,"notes":"","coordinates":"","planets":[]})

def add_planet(system,nation_pop,name=""):
    pi=len(system.get("planets",[]))
    if not name: name=_rng_name(system["name"],pi)
    p={"name":name,"type":"Terrestrial","size":"Medium","climate":"Temperate","habitability":50.0,
       "devastation":0.0,"crime_rate":5.0,"unrest":5.0,"pop_assigned":0,"settlements":[],"platforms":[]}
    randomize_planet(p,nation_pop); system.setdefault("planets",[]).append(p)

def add_platform(planet,ptype="Mining"):
    planet.setdefault("platforms",[]).append({"type":ptype,"status":"Operational","name":f"{ptype} Platform"})

# ── state manager ─────────────────────────────────────────────────────────────
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
                'list nations')

    if verb=="list" and len(parts)>1 and parts[1]=="nations":
        return "\n".join(sm.nation_names())

    if verb=="tithe":
        evs=apply_tithes(sm.state); sm.mark_dirty(); sm.autosave()
        return f"Tithe applied. {len(evs)} transactions."

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

# ── discord export ────────────────────────────────────────────────────────────
def _discord_export(nation,state):
    DISCORD_DIR.mkdir(exist_ok=True)
    ye=years_elapsed(state); ipeu=nation.get("base_ipeu",0.0)
    pop=nation.get("population",0.0)*(1.0+nation.get("pop_growth",0.0))**ye
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    routes=state.get("trade_routes",[]); trade=compute_trade(nation,routes)
    export_cr=compute_resource_export_credits(nation,state)
    rb=nation.get("research_budget",0.0); sfund=nation.get("strategic_fund",0.0)
    species=nation.get("species_populations",[]) or []; star_sys=nation.get("star_systems",[]) or []
    projects=nation.get("projects",[]) or []; afd=nation.get("active_forces_detail",[]) or []
    ugroups={ug["ugid"]:ug for ug in (nation.get("unit_groups") or [])}
    active_r=nation.get("active_research_projects",[]) or []; done_r=nation.get("completed_techs",[]) or []
    qtr=state.get("quarter",1); year=state.get("year",2200); turn=state.get("turn",1)
    tag=nation_tag(nation["name"]); homeworld="N/A"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl.get("name","N/A"); break
        break
    sp_str=", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species) or "N/A"
    L=[]; A=L.append
    A(f"-# [{tag}] {nation['name'].upper()}")
    A(f"# NATIONAL PROFILE - Q{qtr} [{year}]"); A("```")
    A(f"  Species          : {sp_str}")
    A(f"  Population       : {fmt_pop(pop)}")
    A(f"  Pop Growth       : {fmt_pct(nation.get('pop_growth',0))} / yr")
    A(f"  Homeworld        : {homeworld}")
    A(f"  Economic Model   : {nation.get('economic_model','MIXED')}")
    A(f"  Status           : {nation.get('eco_status','Stable')}"); A("```")

    if is_colony(nation):
        vres=compute_vessel_resources(nation); vs=nation.get("vessel_stats",{})
        A("# COLONY VESSEL"); A("```")
        A(f"  Pop Capacity     : {fmt_pop(vs.get('pop_capacity',0))}")
        A(f"  Population       : {fmt_pop(pop)}"); A("```")
        A("## VESSEL STOCKPILES")
        for rname in ["Food","Minerals","Alloys","Energy"]:
            rd=vres[rname]; A("```")
            A(f"  {rname} Stockpile  : {fmt_res(rd['stockpile'])}")
            A(f"  {rname} Net/turn   : {fmt_res(rd['net'])}  {rd['trend']}"); A("```")
        A("## COLONY PROGRESS")
        for cp in get_colony_progress(nation):
            A("```")
            A(f"  {cp['planet']} ({cp['system']})")
            A(f"    Colonized : {cp['colonization_pct']:.1f}%  {bar_str(cp['colonization_pct']/100)}")
            A(f"    Explored  : {cp['explored_pct']:.1f}%"); A("```")
    else:
        res=compute_resources(nation,ipeu); debt=compute_debt(nation,ipeu)
        _,tax_inc=compute_planet_local_market(nation,state,ipeu)
        eff=spending_effects(nation,ipeu)
        total_exp=sum(exp.values())*ipeu+rb
        tithe=compute_church_tithe(nation,state)
        tithe_in=compute_tithe_income(nation,state)
        net_bal=ipeu+trade["net"]+tax_inc+tithe_in-total_exp-debt["q_interest"]-tithe
        per_cap=int(ipeu/pop) if pop else 0
        mil_cons=compute_military_consumption(nation)
        A("# ECONOMY"); A("```")
        A(f"  IPEU (base)      : {fmt_cr(ipeu)}")
        A(f"  IPEU Growth      : {fmt_pct(nation.get('ipeu_growth',0))} / yr")
        A(f"  IPEU per Capita  : {per_cap:,} cr")
        A(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
        A(f"   - Exports       : {fmt_cr(trade['exports'])}")
        A(f"   - Imports       : {fmt_cr(trade['imports'])}")
        A(f"  Local Mkt Tax    : {fmt_cr(tax_inc)}")
        if tithe_in>0: A(f"  Tithe Income     : +{fmt_cr(tithe_in)}")
        if tithe>0: A(f"  Church Tithe     : -{fmt_cr(tithe)}")
        A(f"  Total Expenditure: {fmt_cr(total_exp)}")
        A(f"  Net Balance      : {fmt_cr(net_bal)}"); A("```")
        A("## EXPENDITURE"); A("```")
        mx=max(exp.values(),default=0.01)
        for cat,pct in exp.items(): A(f"  {cat:<22} {pct*100:5.1f}%  {bar_str(pct/mx,20)}  {fmt_cr(pct*ipeu)}")
        A("```"); A("## RESOURCES & STOCKPILES")
        for rname in _RESOURCES:
            rd=res[rname]; ns=f"+{fmt_res(rd['net'])}" if rd["net"]>=0 else fmt_res(rd["net"])
            exc=export_cr.get(rname,0.0); A("```")
            A(f"  {rname} Stockpile   : {fmt_res(rd['stockpile'])}")
            A(f"  {rname} Production  : {fmt_res(rd['production'])}")
            A(f"  {rname} Consumption : {fmt_res(rd['consumption'])}")
            if rd.get("mil_consumption",0)>0:
                A(f"    (Military)    : {fmt_res(rd['mil_consumption'])}")
            A(f"  {rname} Net/turn    : {ns}  {rd['trend']}")
            A(f"  {rname} Export Rev  : {fmt_cr(exc)}"); A("```")
        if tithe>0:
            A("## CHURCH TITHE"); A("```")
            A(f"  Tithe to Regnum Dei : {fmt_cr(tithe)} / turn"); A("```")
        A("## MILITARY CONSUMPTION"); A("```")
        A(f"  Food   : {fmt_res(mil_cons['Food'])} / turn")
        A(f"  Alloys : {fmt_res(mil_cons['Alloys'])} / turn"); A("```")
        cq=nation.get("construction_queue") or []
        if cq:
            A("## CONSTRUCTION QUEUE"); A("```")
            for item in cq: A(f"  {item['district_type']} @ {item['settlement_name']}  {item['turns_remaining']}t left")
            A("```")
    A("# MILITARY")
    for hdr,cats in [("## SPACEFLEET",["Spacefleet","Navy"]),("## AEROSPACE FORCES",["Air Force","Aerospace"]),
                      ("## GROUND FORCES",["Ground Forces","Ground","Army"])]:
        units=[u for u in afd if u.get("category") in cats]; A(hdr); A("```")
        if units:
            gd={}
            for u in units:
                ugid=u.get("ugid"); grp=ugroups[ugid]["name"] if ugid and ugid in ugroups else "N/A"
                gd.setdefault(grp,[]).append(u)
            for grp,us in gd.items():
                if grp!="N/A": A(f"  {grp}")
                for u in us:
                    nm=u.get("custom_name") or u.get("unit","?")
                    A(f"    - {nm} | x{u.get('count',1)} | {u.get('veterancy','?')}")
        else: A("  None on record")
        A("```")
    A("## MANPOWER"); A("```")
    A(f"  Pool       : {fmt_pop(compute_manpower(nation))}")
    A(f"  Stored Pool: {fmt_pop(nation.get('manpower_pool',0))}"); A("```")
    elog=state.get("events_log",[]) or []
    recent=[e for e in elog if e.get("turn")==turn and
            (e.get("nation")==nation["name"] or e.get("type") in ("Market","Piracy","Tithe"))]
    if recent:
        A(f"# EVENTS - T{turn} Q{qtr} [{year}]"); A("```")
        for e in recent: A(f"  [{e['type']:<12}] {str(e.get('roll','?')):>5}  {e.get('label','?'):<20}  {e.get('description','')}")
        A("```")
    text="\n".join(L)
    fname=DISCORD_DIR/f"discord_{nation['name'].replace(' ','_')}_T{turn}.txt"
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
    return str(fname)

# ── pygame drawing primitives ─────────────────────────────────────────────────
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
        self.content_h=max(ch,vh); self.view_h=vh; self.scroll=max(0,min(self.scroll,self.content_h-self.view_h))
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
        self.rect=pygame.Rect(rect); self.label=label; self.accent=accent; self.small=small; self.color=color; self._hover=False
    def draw(self,surf):
        if self.color: bg=tuple(min(255,c+30) for c in self.color) if self._hover else self.color; bdr=BORDER2
        else: bg=(BTNACC2 if self._hover else BTNACC) if self.accent else (BTNHOV if self._hover else BTNBG); bdr=ACCENT if self.accent else BORDER2
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
        self.active=True; self.label=label; self.text=str(raw) if raw is not None else ""; self.meta=meta; pygame.key.set_repeat(400,40)
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

class GMConsoleOverlay:
    H=110
    def __init__(self): self.active=False; self.text=""; self.output=""; self._blink=0.0
    def open(self): self.active=True; self.text=""; self.output="Type 'help' for commands"; pygame.key.set_repeat(400,40)
    def close(self): self.active=False; self.text=""; pygame.key.set_repeat(0,0)
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        y=SH-self.H-SBAR_H; r=pygame.Rect(0,y,SW,self.H)
        draw_rect(surf,r,(4,10,20)); draw_rect(surf,r,(0,200,100),border=1)
        draw_text(surf,"GM CONSOLE  (~=close  Enter=run)",14,y+5,gf(11),(0,220,120))
        # output (multiline, last 3 lines)
        lines=self.output.split("\n")[-3:]
        for i,ln in enumerate(lines): draw_text(surf,ln,14,y+20+i*14,gf(10),DIM)
        bx=pygame.Rect(14,y+self.H-28,SW-28,22); draw_rect(surf,bx,(6,16,26)); draw_rect(surf,bx,(0,180,90),border=1)
        draw_text(surf,"> "+self.text,bx.x+4,bx.y+4,gf(11),BRIGHT)
        if self._blink<0.5:
            cx=bx.x+4+tw("> "+self.text,gf(11)); pygame.draw.line(surf,(0,220,120),(cx,bx.y+3),(cx,bx.y+17),1)
    def on_event(self,ev,sm,reload_cb):
        if not self.active: return
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_BACKQUOTE: self.close(); return
            if ev.key==pygame.K_ESCAPE: self.close(); return
            if ev.key==pygame.K_RETURN:
                self.output=run_gm_command(self.text,sm); self.text=""; reload_cb(); return
            if ev.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif ev.unicode and ev.unicode.isprintable() and ev.unicode!="`": self.text+=ev.unicode

def apply_edit(nation,meta,raw):
    path=meta.get("path",[]); dtype=meta.get("type","float")
    try:
        if dtype=="float": val=float(raw.replace(",",""))
        elif dtype=="pct": val=float(raw.replace("%","").replace(",",""))/100.0
        elif dtype=="int": val=int(raw.replace(",",""))
        else: val=raw
    except: return False
    obj=nation
    for key in path[:-1]: obj=obj[key] if isinstance(key,int) else obj.setdefault(key,{})
    last=path[-1]
    if isinstance(obj,dict): obj[last]=val
    elif isinstance(obj,list): obj[last]=val
    return True

# ── row builders ──────────────────────────────────────────────────────────────
ROW_H=20; HDR1_H=32; HDR2_H=26; SEP_H=8; BTN_H=28; COL_H=28

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
    return {"type":"event_row","txt":f"  [{ev['type']:<12}] {str(ev.get('roll','?')):>5}  {ev.get('label','?'):<20}  {ev.get('description','')}","col":cr,"h":ROW_H}
def _collapse(label,key,expanded,col=TEAL):
    arrow="▼" if expanded else "▶"
    return {"type":"collapse","label":f"{arrow} {label}","key":key,"expanded":expanded,"col":col,"h":COL_H}

# ── build_rows ────────────────────────────────────────────────────────────────
def build_rows(nation,state,tab,collapsed_keys=None):
    if collapsed_keys is None: collapsed_keys=set()
    tabs=get_tabs(nation)
    # map tab name to handler
    ye=years_elapsed(state); ipeu=nation.get("base_ipeu",0.0)
    pop=nation.get("population",0.0)*(1.0+nation.get("pop_growth",0.0))**ye
    species=nation.get("species_populations",[]) or []; star_sys=nation.get("star_systems",[]) or []
    afd=nation.get("active_forces_detail",[]) or []
    ugroups={ug["ugid"]:ug for ug in (nation.get("unit_groups") or [])}
    active_r=nation.get("active_research_projects",[]) or []; done_r=nation.get("completed_techs",[]) or []
    R=[]
    homeworld="N/A"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl.get("name","N/A"); break
        break
    econ=(nation.get("economic_model") or "MIXED").upper()

    # ── OVERVIEW ──────────────────────────────────────────────────────────────
    if tab=="OVERVIEW":
        sp_str=", ".join(s["name"] for s in species) if species else "N/A"
        R+=[_hdr1(f"  {nation['name']}"),
            _row("Species",sp_str),
            _row("Population",fmt_pop(pop)),
            _row("Pop Growth",fmt_pct(nation.get("pop_growth",0)),["pop_growth"],"pct",CYAN),
            _row("Homeworld",homeworld),
            _row("Civ Level",nation.get("civ_level","N/A"),["civ_level"],"str"),
            _row("Civ Tier",nation.get("civ_tier","N/A"),["civ_tier"],"int"),
            _sep(),_hdr2("ECONOMIC MODEL")]
        # clickable model selector buttons
        for em in ECON_MODELS:
            col=(22,60,36) if econ==em else (18,36,56)
            R.append(_btn(f"  {'►' if econ==em else ' '} {em}","set_econ_model",{"model":em},col))
        R+=[_row("Eco Status",nation.get("eco_status","Stable"),["eco_status"],"str"),
            _sep(),_hdr2("DEMOGRAPHICS"),
            _row("Total Pop",fmt_pop(pop)),
            _row("Avg Loyalty",f"{_avg_loyalty(nation):.1f}/100",vcol=CYAN),
            _row("Manpower Pool",fmt_pop(compute_manpower(nation)),vcol=GOLD)]
        for si,s in enumerate(species):
            sp_p=s.get("population",0); shr=sp_p/pop*100 if pop else 0
            loy=s.get("loyalty",0); lc=GREEN if loy>=70 else (GOLD if loy>=40 else RED_C)
            hap=s.get("happiness",0)
            tithe_lbl=""
            rel=(s.get("religion") or "").lower()
            if any(k in rel for k in CHRISTIAN_KEYWORDS): tithe_lbl=" ✝"
            R+=[_sep(),{"type":"species_hdr","name":s["name"]+tithe_lbl,"status":s.get("status",""),"h":HDR2_H},
                _row("  Population",fmt_pop(sp_p),["species_populations",si,"population"],"float",CYAN),
                _row("  Share",f"{shr:.1f}% - {s.get('status','?').title()}"),
                _row("  Loyalty",f"{loy}/100  {bar_str(loy/100,12)}",["species_populations",si,"_base_loyalty"],"float",lc),
                _row("  Happiness",f"{hap}/100" if isinstance(hap,(int,float)) else str(hap),vcol=CYAN),
                _row("  Conscript Rate",fmt_pct(s.get("conscription_rate",nation.get("conscription_rate",0.05))),
                     ["species_populations",si,"conscription_rate"],"pct",DIM),
                _row("  Culture",s.get("culture","N/A"),["species_populations",si,"culture"],"str"),
                _row("  Language",s.get("language","N/A"),["species_populations",si,"language"],"str"),
                _row("  Religion",s.get("religion","N/A"),["species_populations",si,"religion"],"str")]
        R+=[_sep(),_hdr2("RESEARCH"),_row("RP Budget/turn",fmt_cr(nation.get("research_budget",0)),["research_budget"],"float",CYAN)]
        for p in active_r: R.append(_bar(f"  {p.get('name','?')}",p.get("progress",0)/100,f"{p.get('progress',0):.1f}%",CYAN))
        if not active_r: R.append(_row("  Active","None",vcol=DIM))
        if done_r: R.append(_row("  Completed",f"{len(done_r)} techs",vcol=GREEN))

    # ── ECONOMY ───────────────────────────────────────────────────────────────
    elif tab=="ECONOMY":
        exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
        res=compute_resources(nation,ipeu)
        debt=compute_debt(nation,ipeu); rb=nation.get("research_budget",0.0); sf=nation.get("strategic_fund",0.0)
        export_cr=compute_resource_export_credits(nation,state)
        planet_markets,tax_inc=compute_planet_local_market(nation,state,ipeu)
        eff=spending_effects(nation,ipeu)
        tithe=compute_church_tithe(nation,state)
        tithe_in=compute_tithe_income(nation,state)
        total_exp=sum(exp.values())*ipeu+rb
        trade_data=compute_trade(nation,state.get("trade_routes",[]))
        trade_net=trade_data["net"]
        net_bal=ipeu+trade_net+tax_inc+tithe_in-total_exp-debt["q_interest"]-tithe
        eco_mod=econ_model_ipeu_modifier(nation); nc=GREEN if net_bal>=0 else RED_C
        mil_cons=compute_military_consumption(nation)
        R+=[_hdr1("ECONOMY"),
            _row("Economic Model",econ,vcol=GOLD),
            _row("IPEU (base)",fmt_cr(ipeu),["base_ipeu"],"float",GOLD),
            _row("Eco Multiplier",f"x{eco_mod:.3f}",vcol=CYAN),
            _row("IPEU Growth",fmt_pct(nation.get("ipeu_growth",0)),["ipeu_growth"],"pct",CYAN),
            _row("IPEU/Capita",f"{int(ipeu/pop):,} cr" if pop else "N/A"),
            _row("Trade Revenue",fmt_cr(trade_net)),
            _row("  Exports",fmt_cr(trade_data["exports"]),vcol=GREEN),
            _row("  Imports",fmt_cr(trade_data["imports"]),vcol=RED_C),
            _row("  Transit",fmt_cr(trade_data["transit_income"]),vcol=TEAL),
            _row("Local Mkt Tax",fmt_cr(tax_inc),vcol=CYAN)]
        if tithe_in>0:
            R.append(_row("Tithe Income",f"+{fmt_cr(tithe_in)}",vcol=GOLD))
        if tithe>0:
            R.append(_row("Church Tithe",f"-{fmt_cr(tithe)}",vcol=GOLD))
        R+=[_row("Research Bgt",fmt_cr(rb),["research_budget"],"float",CYAN),
            _row("Total Expend.",fmt_cr(total_exp)),
            _row("Net Balance",fmt_cr(net_bal),vcol=nc),
            _sep(),_hdr2("EXPENDITURE")]
        mx=max(exp.values(),default=0.01)
        for cat,pct in exp.items(): R.append(_bar(f"  {cat}",pct/mx,f"{pct*100:.1f}%  {fmt_cr(pct*ipeu)}"))
        R+=[_sep(),_hdr2("SPENDING EFFECTS"),
            _row("  Infra Trade Bonus",f"+{eff['infra_trade_bonus']:.1f}% attract.",vcol=TEAL),
            _row("  PopDev Growth",f"+{eff['popdev_growth_bonus']:.3f}%/yr",vcol=GREEN),
            _row("  Military Morale",f"+{eff['mil_morale_bonus']:.1f}%",vcol=CYAN),
            _row("  Combat Power",f"{eff['mil_combat_power']:.3f} Tcr",vcol=CYAN)]
        if econ in ("PLANNED","MIXED"):
            loy=_avg_loyalty(nation); lc=GREEN if loy>=70 else (GOLD if loy>=40 else RED_C)
            R+=[_sep(),_hdr2("PLANNED: DISTRIBUTION & EFFICIENCY"),
                _row("  Avg Loyalty",f"{loy:.1f}/100",vcol=lc),
                _row("  Resource Eff.",f"{100*(1.0+max(0,loy-50)/200):.1f}%",vcol=CYAN),
                _row("  Dist. Bonus","Active — loyalty+5",vcol=GREEN)]
        if econ in ("MARKET","MIXED"):
            R+=[_sep(),_hdr2("MARKET: LOCAL PLANET OUTPUT")]
            for pm in planet_markets[:8]:
                col=GREEN if pm["attractiveness"]>60 else (GOLD if pm["attractiveness"]>30 else RED_C)
                R.append(_row(f"  {pm['planet'][:22]}",f"Attr:{pm['attractiveness']:.0f}  Tax:{fmt_cr(pm['tax_income'])}",vcol=col))
            sub_cost,inv_bonus=compute_subsidies(nation,ipeu)
            R+=[_row("  Subsidy Cost",fmt_cr(sub_cost),["subsidy_rate"],"pct",RED_C),
                _row("  Invest Bonus",f"+{inv_bonus:.1f} attr.",["investment_rate"],"pct",GREEN)]
        R+=[_sep(),_hdr2("MILITARY CONSUMPTION"),
            _row("  Food",fmt_res(mil_cons["Food"])+" / turn",vcol=RED_C if mil_cons["Food"]>0 else DIM),
            _row("  Alloys",fmt_res(mil_cons["Alloys"])+" / turn",vcol=RED_C if mil_cons["Alloys"]>0 else DIM),
            _sep(),_hdr2("FISCAL REPORT")]
        dc=RED_C if debt["is_debtor"] else GREEN
        R+=[_row("Status","Debtor" if debt["is_debtor"] else "Creditor",vcol=dc),
            _row("Debt Balance",fmt_cr(debt["balance"]),["debt_balance"],"float"),
            _row("Debt Load",f"{debt['load_pct']:.1f}%"),
            _row("Interest Rate",f"{debt['rate']*100:.2f}%",["interest_rate"],"pct",CYAN),
            _row("Quarterly Int.",fmt_cr(debt["q_interest"])),
            _row("Debt Repayment",fmt_cr(debt["repayment"]),["debt_repayment"],"float")]
        sf_c=GREEN if sf>=0 else RED_C; fd=-debt["q_interest"]
        R+=[_row("Strategic Fund",fmt_cr(sf),["strategic_fund"],"float",sf_c),
            _row("Fund dt/turn",(f"+{fmt_cr(fd)}" if fd>=0 else fmt_cr(fd)),vcol=sf_c),
            _sep(),_hdr2("RESOURCES & STOCKPILES")]
        for rname in _RESOURCES:
            rd=res[rname]; tc=GREEN if rd["net"]>0 else (RED_C if rd["net"]<0 else DIM); exc=export_cr.get(rname,0.0)
            mc=rd.get("mil_consumption",0.0)
            R+=[_row(f"  {rname}",""),
                _row("    Stockpile",fmt_res(rd["stockpile"])),
                _row("    Production",fmt_res(rd["production"])),
                _row("    Consumption",fmt_res(rd["consumption"]))]
            if mc>0: R.append(_row("    (Military)",fmt_res(mc),vcol=RED_C))
            R+=[_row("    Net/turn",fmt_res(rd["net"]),vcol=tc),
                _row("    Export Rev",fmt_cr(exc),vcol=GREEN if exc>0 else DIM),
                _row("    Trend",rd["trend"],vcol=tc),_sep()]
        # construction queue
        cq=nation.get("construction_queue") or []
        R.append(_hdr2(f"CONSTRUCTION QUEUE  ({len(cq)} items)"))
        if cq:
            for item in cq:
                R.append(_row(f"  {item['district_type']}",
                    f"@ {item['settlement_name']}  {item['turns_remaining']}t left",vcol=LIME))
        else: R.append(_row("  Empty","",vcol=DIM))

    # ── COLONY ────────────────────────────────────────────────────────────────
    elif tab=="COLONY":
        vs=nation.get("vessel_stats",{}); vsp=nation.get("vessel_stockpiles",{})
        vres=compute_vessel_resources(nation)
        R+=[_hdr1("COLONY VESSEL"),
            _row("Pop Capacity",fmt_pop(vs.get("pop_capacity",0)),["vessel_stats","pop_capacity"],"float",CYAN),
            _row("Population",fmt_pop(pop)),
            _sep(),_hdr2("VESSEL STATS — EDIT")]
        for field,label in [("food_production","Food Prod"),("food_consumption","Food Cons"),
                              ("mineral_extraction","Mineral Ext"),("alloy_production","Alloy Prod"),
                              ("energy_production","Energy Prod"),("energy_consumption","Energy Cons")]:
            R.append(_row(f"  {label}",fmt_res(vs.get(field,0)),["vessel_stats",field],"float",TEAL))
        R+=[_sep(),_hdr2("VESSEL STOCKPILES")]
        for rname in ["Food","Minerals","Alloys","Energy"]:
            rd=vres[rname]; tc=GREEN if rd["net"]>0 else (RED_C if rd["net"]<0 else DIM)
            stock_val=vsp.get(rname,0.0)
            R+=[_row(f"  {rname} Stockpile",fmt_res(stock_val),["vessel_stockpiles",rname],"float"),
                _row(f"  {rname} Net/turn",fmt_res(rd["net"]),vcol=tc),
                _row(f"  {rname} Trend",rd["trend"],vcol=tc),_sep()]
        R+=[_hdr2("COLONY PROGRESS")]
        for cp in get_colony_progress(nation):
            col_pct=cp["colonization_pct"]; exp_pct=cp["explored_pct"]
            cc=GREEN if col_pct>50 else (GOLD if col_pct>20 else RED_C)
            R+=[_row(f"  {cp['planet']} ({cp['system']})","",vcol=TEAL),
                _bar(f"    Colonized",col_pct/100,f"{col_pct:.1f}%",cc),
                _bar(f"    Explored",exp_pct/100,f"{exp_pct:.1f}%",CYAN),
                _row(f"    Population",fmt_pop(cp["pop"]))]
        R+=[_sep(),_hdr2("COLONY EVENTS (last 20)")]
        elog=state.get("events_log",[]) or []
        cevs=[e for e in reversed(elog) if e.get("nation")==nation["name"] and e.get("type")=="Colony"][:20]
        if not cevs: R.append(_row("  No events yet","",vcol=DIM))
        for e in cevs: R.append(_ev_row(e))

    # ── MILITARY ──────────────────────────────────────────────────────────────
    elif tab=="MILITARY":
        exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
        eff=spending_effects(nation,ipeu)
        mil_pct=exp.get("Military",0.0)
        mil_cons=compute_military_consumption(nation)
        manpower=compute_manpower(nation)
        mc=GREEN if eff["mil_morale_bonus"]>15 else (GOLD if eff["mil_morale_bonus"]>5 else DIM)
        R+=[_hdr1("MILITARY"),
            _row("Military Spending",f"{mil_pct*100:.1f}% of IPEU",vcol=CYAN),
            _row("Morale Bonus",f"+{eff['mil_morale_bonus']:.1f}%",vcol=mc),
            _row("Combat Power",f"{eff['mil_combat_power']:.3f} Tcr",vcol=GOLD),
            _sep(),_hdr2("MANPOWER"),
            _row("  Total Pool",fmt_pop(manpower),vcol=GOLD),
            _row("  Stored Pool",fmt_pop(nation.get("manpower_pool",0)),vcol=DIM)]
        for si,s in enumerate(species):
            sp_pop=s.get("population",0)
            cr=s.get("conscription_rate",nation.get("conscription_rate",0.05))
            loy=s.get("loyalty",50); vol=max(0,(loy-40)/200.0)
            contrib=sp_pop*(cr+vol)+s.get("gm_manpower_adj",0.0)
            R.append(_row(f"  {s['name'][:20]}",
                f"Conscript:{cr*100:.1f}%  Vol:{vol*100:.1f}%  Pool:{fmt_pop(contrib)}",vcol=TEAL))
        R+=[_sep(),_hdr2("CONSUMPTION THIS TURN"),
            _row("  Food",fmt_res(mil_cons["Food"])+" / turn",vcol=RED_C if mil_cons["Food"]>0 else DIM),
            _row("  Alloys",fmt_res(mil_cons["Alloys"])+" / turn",vcol=RED_C if mil_cons["Alloys"]>0 else DIM),
            _sep()]
        for hdr,cats in [("SPACEFLEET",["Spacefleet","Navy"]),("AEROSPACE FORCES",["Air Force","Aerospace"]),
                          ("GROUND FORCES",["Ground Forces","Ground","Army"])]:
            units=[u for u in afd if u.get("category") in cats]; R.append(_hdr2(hdr))
            if units:
                gd={}
                for u in units:
                    ugid=u.get("ugid"); grp=ugroups[ugid]["name"] if ugid and ugid in ugroups else "Unassigned"
                    gd.setdefault(grp,[]).append(u)
                for grp,us in gd.items():
                    R.append(_row(f"  [{grp}]","",vcol=GOLD))
                    for u in us:
                        nm=u.get("custom_name") or u.get("unit","?")
                        cnt=u.get("count",1)
                        uname=u.get("unit","")
                        cat2=u.get("category","")
                        if cat2 in ("Ground Forces","Ground","Army"):
                            food_c=cnt*GROUND_DIVISION_SIZE*GROUND_FOOD_PER_SOLDIER
                            alloy_c=cnt*GROUND_ALLOY_PER_DIVISION
                        else:
                            food_c=UNIT_CREW.get(uname,0)*cnt
                            alloy_c=UNIT_ALLOY_CON.get(uname,0)*cnt
                        cons_str=f"F:{fmt_res(food_c)} A:{fmt_res(alloy_c)}"
                        R.append(_row(f"    {nm}",f"x{cnt} | {u.get('veterancy','?')} | {cons_str}",vcol=TEXT))
            else: R.append(_row("  None","",vcol=DIM))
            R.append(_sep())
        R.append(_hdr2("ARSENAL"))
        for a in (nation.get("arsenal",[]) or []):
            R.append(_row(f"  {a.get('name','?')}",f"{a.get('type','?')} | {a.get('size','?')} | Crew {a.get('crew','?')}"))
        if not (nation.get("arsenal") or []): R.append(_row("  None","",vcol=DIM))

    # ── TERRITORY ─────────────────────────────────────────────────────────────
    elif tab=="TERRITORY":
        R+=[_hdr1("TERRITORIES"),_btn("+ Add System","add_system",{},(22,60,36)),_sep()]
        if not star_sys: R.append(_row("No territorial data","",vcol=DIM))
        else:
            for si,sys in enumerate(star_sys):
                sk=f"sys_{si}"; sx=sk not in collapsed_keys
                R.append(_collapse(f"System: {sys['name']}  ({len(sys.get('planets',[]))} planets)",sk,sx,CYAN))
                if sx:
                    R+=[_row("  Name",sys["name"],["star_systems",si,"name"],"str"),
                        _row("  Notes",sys.get("notes",""),["star_systems",si,"notes"],"str"),
                        _row("  Coords",sys.get("coordinates",""),["star_systems",si,"coordinates"],"str"),
                        _btn("  + Add Planet","add_planet",{"si":si},(22,50,70))]
                    for pi,planet in enumerate(sys.get("planets",[])):
                        pk=f"planet_{si}_{pi}"; px=pk not in collapsed_keys
                        hab=planet.get("habitability",50); dev=planet.get("devastation",0)
                        R.append(_collapse(f"  > {planet.get('name','?')}  [{planet.get('type','?')}]  Hab:{hab:.0f} Dev:{dev:.0f}",pk,px,TEAL))
                        if px:
                            R+=[_row("    Name",planet["name"],["star_systems",si,"planets",pi,"name"],"str"),
                                _row("    Type",planet.get("type",""),["star_systems",si,"planets",pi,"type"],"str"),
                                _row("    Size",planet.get("size",""),["star_systems",si,"planets",pi,"size"],"str"),
                                _row("    Climate",planet.get("climate",""),["star_systems",si,"planets",pi,"climate"],"str"),
                                _row("    Habitability",planet.get("habitability",""),["star_systems",si,"planets",pi,"habitability"],"float"),
                                _row("    Devastation",planet.get("devastation",0),["star_systems",si,"planets",pi,"devastation"],"float",RED_C),
                                _row("    Crime Rate",planet.get("crime_rate",0),["star_systems",si,"planets",pi,"crime_rate"],"float"),
                                _row("    Unrest",planet.get("unrest",0),["star_systems",si,"planets",pi,"unrest"],"float"),
                                _row("    Population",fmt_pop(planet.get("pop_assigned",0))),
                                _row("    Settlements",f"{len(planet.get('settlements',[]) or [])}",vcol=CYAN)]
                            for sett_i,s in enumerate(planet.get("settlements",[]) or []):
                                R.append(_row(f"      o {s['name']}",f"Pop {fmt_pop(s.get('population',0))}  Loy {s.get('loyalty',0):.0f}%"))
                                dc={}
                                for d in s.get("districts",[]): dt=d.get("type","?"); dc[dt]=dc.get(dt,0)+1
                                if dc: R.append(_row("        Districts","  ".join(f"{t}x{c}" for t,c in dc.items()),vcol=DIM))
                                # construction submenu
                                bk=f"build_{si}_{pi}_{sett_i}"; bx2=bk not in collapsed_keys
                                R.append(_collapse(f"        + Build District",bk,bx2,LIME))
                                if bx2:
                                    for dt in _DISTRICT_TYPES:
                                        mc=DISTRICT_MINERAL_COST.get(dt,20); bt=DISTRICT_BUILD_TURNS.get(dt,3)
                                        R.append(_btn(f"          {dt}  [{mc}Min/{bt}t]","build_district",
                                            {"si":si,"pi":pi,"sett_i":sett_i,"district_type":dt},(30,50,30)))
                                # manage/remove districts
                                mk=f"mandistrict_{si}_{pi}_{sett_i}"; mx2=mk not in collapsed_keys
                                nd=len(s.get("districts",[]))
                                R.append(_collapse(f"        ✕ Manage Districts ({nd})",mk,mx2,RED_C))
                                if mx2:
                                    for di,dd in enumerate(s.get("districts",[])):
                                        R.append(_btn(f"          [{dd.get('type','?')}] ({dd.get('status','Operational')})  Remove",
                                            "confirm_remove_district",{"si":si,"pi":pi,"sett_i":sett_i,"di":di},(70,18,18)))
                            platforms=planet.get("platforms",[]) or []
                            if platforms:
                                R.append(_row("    Platforms",f"{len(platforms)} installed",vcol=PURPLE))
                                for pi2,plat in enumerate(platforms):
                                    R.append(_row(f"      [{plat.get('type','?')}]",plat.get("name","?"),
                                                  ["star_systems",si,"planets",pi,"platforms",pi2,"name"],"str",PURPLE))
                            R+=[_btn("    + Mining Platform","add_platform",{"si":si,"pi":pi,"ptype":"Mining"},(40,20,60)),
                                _btn("    + Hydroponics","add_platform",{"si":si,"pi":pi,"ptype":"Hydroponics"},(20,50,40)),
                                _btn("    + Research Platform","add_platform",{"si":si,"pi":pi,"ptype":"Research"},(20,40,60)),
                                _btn("    + Dockyards","add_platform",{"si":si,"pi":pi,"ptype":"Dockyards"},(40,30,20)),
                                _btn(f"    Randomize Planet","randomize_planet",{"si":si,"pi":pi},(60,30,80)),
                                _btn(f"    ✕ Remove Planet","confirm_remove_planet",{"si":si,"pi":pi},(70,18,18)),_sep()]
                R.append(_sep())

    # ── MARKET ────────────────────────────────────────────────────────────────
    elif tab=="MARKET":
        market=state.get("market",{}); mods=market.get("market_modifier",{})
        base_p=market.get("price_base",{}); ph=market.get("price_history",{})
        routes=state.get("trade_routes",[]) or []
        export_cr=compute_resource_export_credits(nation,state)
        R+=[_hdr1("NATION MARKET VIEW"),_hdr2("RESOURCE PRICES")]
        for rname in _RESOURCES:
            base=base_p.get(rname,RES_BASE_PRICE[rname]); curr=mods.get(rname,base); mult=curr/base if base else 1.0
            col=GREEN if mult>1.05 else (RED_C if mult<0.95 else DIM)
            hist=ph.get(rname,[])
            trend="▲" if (len(hist)>1 and hist[-1]>hist[-2]) else ("▼" if (len(hist)>1 and hist[-1]<hist[-2]) else "─")
            exc=export_cr.get(rname,0.0)
            R.append(_row(f"  {rname}",f"{curr:.3f} cr  base:{base:.2f}  x{mult:.2f}  {trend}  ExRev:{fmt_cr(exc)}",vcol=col))
            if hist:
                mn=min(hist[-8:]); mxh=max(hist[-8:],default=mn+0.001)
                bh="".join("_..,-+|#"[min(7,int((v-mn)/(mxh-mn+0.001)*8))] for v in hist[-8:])
                R.append(_row("    History (8t)",f"{bh}  lo:{mn:.3f} hi:{mxh:.3f}",vcol=DIM))
        R+=[_sep(),_hdr2(f"TRADE ROUTES ({len(routes)} total)"),
            _btn("  + New Trade Route","open_trade_builder",{},(20,55,30))]
        for r in routes:
            st=r.get("status","?"); sc=GREEN if st=="active" else RED_C
            pl=r.get("_piracy_loss_this_turn",0.0); pc=RED_C if pl>0 else DIM
            R+=[_row(f"  [{r.get('id','?')}] {r.get('name','')}",f"{r.get('resource','?')}  {fmt_cr(r.get('credits_per_turn',0))}/t  [{st}]",vcol=sc),
                _row(f"    {r.get('exporter','?')} → {r.get('importer','?')}","",vcol=DIM),
                _row("    Piracy",f"Dist:{r.get('pirate_distance','?')}  Inc:{r.get('pirate_incidents',0)}  Total:{fmt_cr(r.get('total_pirated',0))}",vcol=pc),
                _btn(f"    ✏ Edit Route","edit_trade_route",{"route_id":r.get("id")},(20,35,55))]
            if r.get("transit_nations"):
                tns=", ".join(f"{t.get('nation','?')}({t.get('tax_rate',0)*100:.0f}%)" for t in r["transit_nations"])
                R.append(_row("    Transit",tns,vcol=DIM))
        if not routes: R.append(_row("  No trade routes","",vcol=DIM))

    # ── GALACTIC ──────────────────────────────────────────────────────────────
    elif tab=="GALACTIC":
        market=state.get("market",{}); mods=market.get("market_modifier",{})
        base_p=market.get("price_base",{}); ph=market.get("price_history",{})
        gal_stock,gal_prod,gal_cons=compute_galactic_stockpiles(state)
        R+=[_hdr1("GALACTIC MARKET"),
            _btn("  Open Graphs","open_graphs",{},(30,20,65)),
            _hdr2("COMMODITY OVERVIEW")]
        for rname in _RESOURCES:
            base=base_p.get(rname,RES_BASE_PRICE[rname]); curr=mods.get(rname,base); mult=curr/base if base else 1.0
            col=GREEN if mult>1.1 else (RED_C if mult<0.9 else (GOLD if mult>1.0 else DIM))
            pbal=gal_prod[rname]-gal_cons[rname]; bal_col=GREEN if pbal>0 else RED_C
            hist=ph.get(rname,[])
            trend="▲" if (len(hist)>1 and hist[-1]>hist[-2]) else ("▼" if (len(hist)>1 and hist[-1]<hist[-2]) else "─")
            sd_d=price_shock_delta(rname,gal_prod[rname],gal_cons[rname],curr,base)
            pressure="↑" if sd_d>0.01 else ("↓" if sd_d<-0.01 else "─")
            R+=[_hdr2(f"  {rname}  {curr:.3f} cr  {trend}  Pressure:{pressure}"),
                _row("    Galaxy Stockpile",fmt_res(gal_stock[rname])),
                _row("    Galaxy Production",fmt_res(gal_prod[rname]),vcol=GREEN),
                _row("    Galaxy Demand",fmt_res(gal_cons[rname]),vcol=RED_C),
                _row("    Supply/Demand Bal",f"{fmt_res(pbal)}/turn",vcol=bal_col),
                _row("    Price Multiplier",f"x{mult:.3f}  base {base:.2f}",vcol=col)]
            if len(hist)>=2:
                mn=min(hist); mxh=max(hist,default=mn+0.001)
                spark="".join("▁▂▃▄▅▆▇█"[min(7,int((v-mn)/(mxh-mn+0.001)*8))] for v in hist[-16:])
                R.append(_row("    Price History",spark,vcol=CYAN))
                R.append(_row("    Range",f"lo:{mn:.3f}  hi:{mxh:.3f}  now:{curr:.3f}",vcol=DIM))
            R.append(_sep())
        R+=[_hdr2("TOP EXPORTERS BY RESOURCE")]
        for rname in _RESOURCES:
            ne=[(n["name"],compute_resource_export_credits(n,state).get(rname,0)) for n in state.get("nations",[])]
            ne.sort(key=lambda x:-x[1]); top=[(nm,c) for nm,c in ne if c>0][:3]
            if top: R.append(_row(f"  {rname}","  |  ".join(f"{nation_tag(nm)} {fmt_cr(c)}" for nm,c in top),vcol=TEAL))
        R+=[_sep(),_hdr2("PIRACY SUMMARY")]
        tot_p=sum(r.get("total_pirated",0) for r in state.get("trade_routes",[]))
        tot_i=sum(r.get("pirate_incidents",0) for r in state.get("trade_routes",[]))
        R+=[_row("  Total Incidents",str(tot_i),vcol=RED_C),_row("  Total Pirated",fmt_cr(tot_p),vcol=RED_C)]
        for r in state.get("trade_routes",[]):
            if r.get("pirate_incidents",0)>0:
                R.append(_row(f"  {r.get('name','?')}",f"x{r.get('pirate_incidents',0)}  {fmt_cr(r.get('total_pirated',0))} stolen",vcol=ORANGE))
        R+=[_sep(),_hdr2("CHURCH TITHES")]
        for n in state.get("nations",[]):
            t=compute_church_tithe(n,state)
            if t>0: R.append(_row(f"  {n['name'][:26]}",fmt_cr(t),vcol=GOLD))
        R+=[_sep(),_hdr2("PSST NATIONS")]
        psst=market.get("psst_nations",[])
        for n in psst: R.append(_row(f"  {n}","",vcol=GOLD))
        if not psst: R.append(_row("  None listed","",vcol=DIM))

    # ── EVENTS ────────────────────────────────────────────────────────────────
    elif tab=="EVENTS":
        elog=state.get("events_log",[]) or []; nname=nation["name"]
        R+=[_hdr1("EVENTS LOG"),_btn("Roll Events for This Nation","roll_events",{"nation":nname},(60,30,90)),_sep()]
        relevant=[e for e in reversed(elog) if e.get("nation")==nname or e.get("type") in ("Market","Piracy","Tithe")]
        if not relevant: R.append(_row("No events recorded","",vcol=DIM))
        else:
            cur_t=None
            for e in relevant[:100]:
                t=e.get("turn","?")
                if t!=cur_t: cur_t=t; R.append(_hdr2(f"Turn {t}  .  {e.get('year','?')} Q{e.get('quarter','?')}"))
                R.append(_ev_row(e))
    return R

_TR_DIST_OPTIONS=["near","kind of far","too far"]
_TR_STATUS_OPTIONS=["active","suspended"]

class ConfirmOverlay:
    H=72
    def __init__(self):
        self.active=False; self.message=""; self.pending_action=None; self.pending_data={}
        mid=SW//2; y_btn=SH-self.H-SBAR_H+20
        self.btn_yes=Button((mid-96,y_btn,90,28),"YES (Enter)",accent=True)
        self.btn_no=Button((mid+6,y_btn,90,28),"NO (Esc)")
    def open(self,message,action,data):
        self.active=True; self.message=message; self.pending_action=action; self.pending_data=data
    def close(self): self.active=False; self.pending_action=None; self.pending_data={}
    def draw(self,surf,dt):
        if not self.active: return
        y=SH-self.H-SBAR_H; r=pygame.Rect(0,y,SW,self.H)
        draw_rect(surf,r,(35,10,10)); draw_rect(surf,r,RED_C,border=1)
        draw_text(surf,f"CONFIRM: {self.message}",14,y+8,gf(12),BRIGHT)
        self.btn_yes.draw(surf); self.btn_no.draw(surf)
    def on_event(self,ev):
        if not self.active: return None
        if self.btn_yes.on_event(ev):
            act,d=self.pending_action,self.pending_data; self.close(); return (act,d)
        if self.btn_no.on_event(ev): self.close(); return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_RETURN:
                act,d=self.pending_action,self.pending_data; self.close(); return (act,d)
            if ev.key==pygame.K_ESCAPE: self.close(); return None
        return None


class TradeBuilderOverlay:
    """Overlay for creating/editing trade routes in the MARKET tab panel area."""
    def __init__(self):
        self.active=False; self.mode="new"; self.route_id=None
        self.fields=[]; self.transit_list=[]; self._nation_names=[]
        self._transit_nation_idx=0; self._transit_tax_buf="0.05"
        self.field_idx=0; self._blink=0.0
    def _init_fields(self,route,nation_names):
        self._nation_names=list(nation_names)
        def cidx(lst,v,fb=0): return lst.index(v) if v in lst else fb
        self.fields=[
            {"key":"name",            "label":"Route Name",        "type":"text",   "val":route.get("name","New Route")},
            {"key":"exporter",        "label":"Exporter",          "type":"choice", "val":cidx(nation_names,route.get("exporter",""),0),"opts":list(nation_names)},
            {"key":"importer",        "label":"Importer",          "type":"choice", "val":cidx(nation_names,route.get("importer",""),0),"opts":list(nation_names)},
            {"key":"resource",        "label":"Resource",          "type":"choice", "val":cidx(_RESOURCES,route.get("resource","Food"),0),"opts":list(_RESOURCES)},
            {"key":"credits_per_turn","label":"Credits / Turn",    "type":"float",  "val":str(route.get("credits_per_turn",0.0))},
            {"key":"pirate_distance", "label":"Pirate Distance",   "type":"choice", "val":cidx(_TR_DIST_OPTIONS,route.get("pirate_distance","near"),0),"opts":_TR_DIST_OPTIONS},
            {"key":"pirate_escort",   "label":"Escort Ships",      "type":"int",    "val":str(route.get("pirate_escort",0))},
            {"key":"route_modifier",  "label":"Route Modifier %",  "type":"float",  "val":str(round(route.get("route_modifier",0.0)*100,2))},
            {"key":"status",          "label":"Status",            "type":"choice", "val":cidx(_TR_STATUS_OPTIONS,route.get("status","active"),0),"opts":_TR_STATUS_OPTIONS},
        ]
        self.transit_list=list(route.get("transit_nations",[]))
        self._transit_nation_idx=0; self._transit_tax_buf="5.0"; self.field_idx=0
    def open_new(self,nation_names): self.active=True; self.mode="new"; self.route_id=None; self._init_fields({},nation_names)
    def open_edit(self,route,nation_names): self.active=True; self.mode="edit"; self.route_id=route.get("id"); self._init_fields(route,nation_names)
    def close(self): self.active=False
    def get_route_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="float":
                try: v=float(f["val"])
                except: v=0.0
                d[f["key"]]=(v/100.0 if f["key"]=="route_modifier" else v)
            elif f["type"]=="int":
                try: d[f["key"]]=int(f["val"])
                except: d[f["key"]]=0
            else: d[f["key"]]=f["val"]
        d["transit_nations"]=[dict(t) for t in self.transit_list]
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx=MAIN_X; ry=MAIN_Y; rw=SW-MAIN_X; rh=SH-MAIN_Y-SBAR_H
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(5,10,20))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),EDITBDR,border=2)
        f11=gf(11); f10=gf(10); f13=gf(13)
        lbl="NEW TRADE ROUTE" if self.mode=="new" else f"EDIT ROUTE  [{self.route_id}]"
        draw_text(surf,lbl,rx+12,ry+7,f13,BRIGHT)
        draw_text(surf,"Up/Down=field  Left/Right=cycle  Type=edit text  Enter=save  Esc=cancel",rx+12,ry+24,f10,DIM)
        draw_text(surf,"T=add transit  R=remove last transit  [/]=cycle transit nation",rx+12,ry+36,f10,DIM)
        y=ry+52
        for i,f in enumerate(self.fields):
            sel=(i==self.field_idx)
            row_r=pygame.Rect(rx+4,y,rw-8,22)
            draw_rect(surf,row_r,SEL if sel else ((10,18,28) if i%2==0 else BG),radius=2)
            if sel: draw_rect(surf,row_r,EDITBDR,border=1,radius=2)
            lc=BRIGHT if sel else DIM
            draw_text(surf,f["label"],rx+14,y+4,f11,lc)
            if f["type"]=="choice":
                vc=CYAN if sel else TEXT
                draw_text(surf,f"\u25c4 {f['opts'][f['val']]} \u25ba",rx+230,y+4,f11,vc)
            else:
                cursor="\u258e" if (sel and self._blink<0.5) else ""
                draw_text(surf,f["val"]+cursor,rx+230,y+4,f11,EDITBDR if sel else TEXT)
            y+=24
        # transit section
        y+=6; draw_text(surf,"TRANSIT NATIONS:",rx+14,y,f11,GOLD); y+=18
        if not self.transit_list: draw_text(surf,"  (none)",rx+14,y,f10,DIM); y+=16
        for t in self.transit_list:
            draw_text(surf,f"  {t.get('nation','?')}  tax:{t.get('tax_rate',0)*100:.1f}%  [{t.get('status','active')}]",rx+14,y,f10,TEAL); y+=16
        y+=4
        if self._nation_names:
            tn=self._nation_names[self._transit_nation_idx%len(self._nation_names)]
            draw_text(surf,f"  [T] Add: {tn}  tax:{self._transit_tax_buf}%   [/] to cycle nation",rx+14,y,f10,(80,130,80))
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1); return None
            if ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1); return None
            f=self.fields[self.field_idx]
            if f["type"]=="choice":
                if ev.key==pygame.K_LEFT: f["val"]=(f["val"]-1)%len(f["opts"])
                elif ev.key==pygame.K_RIGHT: f["val"]=(f["val"]+1)%len(f["opts"])
            elif f["type"] in ("text","float","int"):
                if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
                elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode
            # Transit controls (only when not editing a text field)
            if ev.key==pygame.K_t and f["type"]!="text":
                if self._nation_names:
                    tn=self._nation_names[self._transit_nation_idx%len(self._nation_names)]
                    try: tr=float(self._transit_tax_buf)/100.0
                    except: tr=0.05
                    self.transit_list.append({"nation":tn,"tax_rate":round(tr,4),"status":"active"})
            elif ev.key==pygame.K_r and f["type"]!="text":
                if self.transit_list: self.transit_list.pop()
            elif ev.key==pygame.K_LEFTBRACKET:
                self._transit_nation_idx=(self._transit_nation_idx-1)%max(1,len(self._nation_names))
            elif ev.key==pygame.K_RIGHTBRACKET:
                self._transit_nation_idx=(self._transit_nation_idx+1)%max(1,len(self._nation_names))
        return None


_GRAPH_VIEWS=["PRICES","NATIONS IPEU","GALACTIC FLOWS"]
_GRAPH_RES_COLORS=[GREEN,CYAN,GOLD,ORANGE,PURPLE]

class GraphOverlay:
    """Full-panel graph overlay with three views."""
    def __init__(self): self.active=False; self.view_idx=0
    def open(self): self.active=True
    def close(self): self.active=False
    def _line_chart(self,surf,series,rx,ry,rw,rh,title,colors):
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(7,13,23))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),BORDER2,border=1)
        f10=gf(10); f11=gf(11)
        draw_text(surf,title,rx+6,ry+4,f11,BRIGHT)
        all_v=[v for _,vs in series for v in vs]
        if not all_v: draw_text(surf,"No data yet — advance turns.",rx+20,ry+40,f10,DIM); return
        mn=min(all_v); mx2=max(all_v)
        if mx2==mn: mx2=mn+1
        pl=62; pr=10; pt=22; pb=22
        cw=rw-pl-pr; ch=rh-pt-pb; cx0=rx+pl; cy0=ry+pt+ch
        for i in range(5):
            yv=mn+(mx2-mn)*i/4; yp=cy0-int(ch*i/4)
            pygame.draw.line(surf,BORDER,(cx0,yp),(cx0+cw,yp),1)
            draw_text(surf,f"{yv:.2f}",rx+2,yp-6,f10,DIM)
        n_pts=max((len(vs) for _,vs in series),default=1)
        for (lbl,vs),col in zip(series,colors):
            if len(vs)<2: continue
            pts=[]
            for j,v in enumerate(vs):
                xp=cx0+int(cw*j/max(1,n_pts-1)); yp=cy0-int(ch*(v-mn)/(mx2-mn))
                pts.append((xp,yp))
            for j in range(len(pts)-1):
                pygame.draw.line(surf,col,pts[j],pts[j+1],2)
            if pts: draw_text(surf,lbl[:7],pts[-1][0]+2,pts[-1][1]-6,f10,col)
    def _bar_chart(self,surf,data,rx,ry,rw,rh,title,col=CYAN):
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(7,13,23))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),BORDER2,border=1)
        f10=gf(10); f11=gf(11)
        draw_text(surf,title,rx+6,ry+4,f11,BRIGHT)
        if not data: return
        mx2=max(v for _,v in data) or 1
        bh2=min(20,max(10,(rh-30)//max(1,len(data))-3))
        y=ry+24
        for lbl,val in data:
            bw2=int((rw-160)*val/mx2)
            draw_rect(surf,pygame.Rect(rx+140,y,max(2,bw2),bh2),col,radius=2)
            draw_text(surf,lbl[:20],rx+4,y+2,f10,DIM)
            draw_text(surf,fmt_cr(val),rx+144+bw2+2,y+2,f10,TEXT)
            y+=bh2+4
    def draw(self,surf,state):
        if not self.active: return
        rx=MAIN_X; ry=MAIN_Y; rw=SW-MAIN_X; rh=SH-MAIN_Y-SBAR_H
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(5,9,17))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),BORDER2,border=2)
        f10=gf(10); f11=gf(11); f13=gf(13)
        draw_text(surf,"GRAPHS",rx+12,ry+6,f13,BRIGHT)
        draw_text(surf,"Left/Right = switch view   Esc = close",rx+12,ry+22,f10,DIM)
        view=_GRAPH_VIEWS[self.view_idx]
        for i,v in enumerate(_GRAPH_VIEWS):
            sel=(i==self.view_idx)
            tx=rx+rw-260+i*88
            tr=pygame.Rect(tx,ry+4,86,22)
            draw_rect(surf,tr,SEL if sel else (12,22,36),radius=3)
            if sel: draw_rect(surf,tr,EDITBDR,border=1,radius=3)
            draw_text(surf,v,tr.x+4,tr.y+4,f10,BRIGHT if sel else DIM)
        market=state.get("market",{}); ph=market.get("price_history",{})
        if view=="PRICES":
            series=[(rn[:6],[v for v in ph.get(rn,[])[-24:]]) for rn in _RESOURCES if ph.get(rn)]
            self._line_chart(surf,series,rx+6,ry+38,rw-12,rh-44,"Resource Price History (last 24 turns)",_GRAPH_RES_COLORS)
        elif view=="NATIONS IPEU":
            nations=state.get("nations",[])
            data=sorted([(n["name"],n.get("base_ipeu",0)) for n in nations],key=lambda x:-x[1])
            self._bar_chart(surf,data,rx+6,ry+38,rw-12,rh-44,"Nation IPEU Comparison",CYAN)
        elif view=="GALACTIC FLOWS":
            gal_stock,gal_prod,gal_cons=compute_galactic_stockpiles(state)
            draw_rect(surf,pygame.Rect(rx+6,ry+38,rw-12,rh-44),(7,13,23))
            draw_rect(surf,pygame.Rect(rx+6,ry+38,rw-12,rh-44),BORDER2,border=1)
            draw_text(surf,"Galactic Resource Net Flow / Turn",rx+14,ry+44,f11,BRIGHT)
            y=ry+64; mx2=max((abs(gal_prod[r]-gal_cons[r]) for r in _RESOURCES),default=1) or 1
            bw_max=rw-200
            for rn,col in zip(_RESOURCES,_GRAPH_RES_COLORS):
                net=gal_prod[rn]-gal_cons[rn]; bw2=int(bw_max*abs(net)/mx2)
                draw_rect(surf,pygame.Rect(rx+130,y,max(2,bw2),18),GREEN if net>=0 else RED_C,radius=2)
                draw_text(surf,rn[:16],rx+14,y+2,f10,DIM)
                sign="+" if net>=0 else ""
                draw_text(surf,f"{sign}{fmt_res(net)}/t",rx+134+bw2+4,y+2,f10,GREEN if net>=0 else RED_C)
                y+=26
            y+=8; draw_text(surf,"Recent Price Shocks:",rx+14,y,f11,GOLD); y+=18
            elog=state.get("events_log",[]) or []
            shocks=[e for e in reversed(elog) if e.get("type")=="Market" and
                    any(k in e.get("label","") for k in ("CRASH","BOOM","Surge","Drop"))][:6]
            if not shocks: draw_text(surf,"  None on record",rx+14,y,f10,DIM)
            for e in shocks:
                draw_text(surf,f"  T{e.get('turn','?')} {e.get('label','?')}: {e.get('description','')[:65]}",rx+14,y,f10,tuple(e.get("col_rgb",[84,114,136]))); y+=14
    def on_event(self,ev):
        if not self.active: return
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close()
            elif ev.key==pygame.K_LEFT: self.view_idx=(self.view_idx-1)%len(_GRAPH_VIEWS)
            elif ev.key==pygame.K_RIGHT: self.view_idx=(self.view_idx+1)%len(_GRAPH_VIEWS)


# ── panels ────────────────────────────────────────────────────────────────────
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
        draw_text(surf,f"{len(self.nations)} nations  ~=console",self.PAD,TBAR_H+20,f10,DIM)
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
        self.rows=[]; self.scroll=Scrollbar(SW-Scrollbar.W-2,MAIN_Y,MAIN_H)
        self.edit=EditOverlay(); self.collapsed_keys=set()
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
            elif rt=="collapse":
                is_hov=rect.collidepoint(mx,my)
                draw_rect(surf,rect,(18,32,48) if is_hov else (14,24,38))
                draw_rect(surf,pygame.Rect(rect.x,rect.bottom-1,rect.w,1),BORDER2)
                draw_rect(surf,pygame.Rect(rect.x,rect.y,3,rect.h),row.get("col",TEAL))
                draw_text(surf,row["label"],rect.x+10,rect.y+7,f12,row.get("col",TEAL),clip)
            elif rt=="species_hdr":
                draw_rect(surf,rect,(14,24,38))
                draw_text(surf,f"{row['name']}  ({row['status'].title()})",rect.x+10,rect.y+6,f12,GOLD,clip)
            elif rt=="row":
                is_edit=bool(row.get("meta"))
                bg=HOVER if (is_edit and rect.collidepoint(mx,my)) else ((10,18,28) if i%2==0 else BG)
                draw_rect(surf,rect,bg); draw_text(surf,row["label"],rect.x+8,rect.y+3,f11,DIM,clip)
                vc=EDITBDR if (is_edit and rect.collidepoint(mx,my)) else row.get("vcol",TEXT)
                draw_text(surf,row["val"],rect.x+190,rect.y+3,f11,vc,clip)
            elif rt=="bar":
                draw_rect(surf,rect,(10,18,28) if i%2==0 else BG)
                draw_text(surf,row["label"],rect.x+8,rect.y+3,f11,DIM,clip)
                bx=rect.x+168; by=rect.y+5; bw2=100; bh=10
                draw_rect(surf,pygame.Rect(bx,by,bw2,bh),(18,32,50),radius=2)
                fw=int(row["pct"]*bw2)
                if fw>0: draw_rect(surf,pygame.Rect(bx,by,fw,bh),row.get("vcol",CYAN),radius=2)
                draw_text(surf,row["txt"],bx+bw2+6,rect.y+3,f11,TEXT,clip)
            elif rt=="btn":
                is_hov=rect.collidepoint(mx,my); bc=row.get("col") or (28,54,82)
                bg=tuple(min(255,c+25) for c in bc) if is_hov else bc
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
                if row["type"]=="collapse": return row
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

def draw_tab_bar(surf,tab_idx,tabs):
    draw_rect(surf,pygame.Rect(LWIDTH,TBAR_H,SW-LWIDTH,TABBAR_H),(10,16,26))
    draw_rect(surf,pygame.Rect(LWIDTH,TBAR_H+TABBAR_H-1,SW-LWIDTH,1),BORDER)
    f10=gf(10); w=(SW-LWIDTH)//len(tabs)
    for i,tab in enumerate(tabs):
        tx=LWIDTH+i*w; tr=pygame.Rect(tx,TBAR_H,w,TABBAR_H)
        if i==tab_idx:
            draw_rect(surf,tr,(18,36,58)); draw_rect(surf,pygame.Rect(tx,TBAR_H+TABBAR_H-2,w,2),CYAN)
            s=f10.render(tab,True,BRIGHT)
        else:
            if tr.collidepoint(pygame.mouse.get_pos()): draw_rect(surf,tr,HOVER)
            s=f10.render(tab,True,DIM)
        surf.blit(s,s.get_rect(center=tr.center))

def draw_status_bar(surf):
    draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,SBAR_H),(8,14,22))
    draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,1),BORDER)
    age=time.time()-_status_time; col=_status_col if age<3.0 else DIM
    draw_text(surf,_status_msg if age<5.0 else "Ready",10,SH-SBAR_H+4,gf(10),col)
    draw_text(surf,"S=save  D=discord  Arrows=nation  Tab/1-7=tab  ~=GM console",SW-460,SH-SBAR_H+4,gf(10),DIM2)

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    filepath=sys.argv[1] if len(sys.argv)>1 else DEFAULT_STATE
    sm=StateManager(filepath)
    if not sm.load(): sys.exit(f"[FATAL] Cannot load: {filepath}")
    pygame.init(); pygame.display.set_caption("Carmine NRP Engine - vAlpha0.6.3")
    surf=pygame.display.set_mode((SW,SH)); clock=pygame.time.Clock()
    left=LeftPanel(); main_=MainPanel(); gm_console=GMConsoleOverlay()
    confirm_=ConfirmOverlay(); trade_builder_=TradeBuilderOverlay(); graph_overlay_=GraphOverlay()
    names=sm.nation_names(); sel_idx=0; tab_idx=0

    def cur_nation(): return sm.get_nation(names[sel_idx]) if names else None
    def cur_tabs():
        n=cur_nation(); return get_tabs(n) if n else TABS

    def load_nation(idx):
        nonlocal sel_idx; sel_idx=max(0,min(idx,len(names)-1)); left.selected=sel_idx
        n=cur_nation()
        if n:
            tabs=get_tabs(n)
            ti=min(tab_idx,len(tabs)-1)
            main_.set_rows(build_rows(n,sm.state,tabs[ti],main_.collapsed_keys))

    def do_discord():
        n=cur_nation()
        if n: path=_discord_export(n,sm.state); set_status(f"Discord -> {path}",CYAN)

    left.set_nations(names,sel_idx)
    load_nation(0); set_status(f"Carmine v0.6.3  ~=GM console  loaded: {filepath}",CYAN)
    running=True
    while running:
        dt=clock.tick(FPS)/1000.0
        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: running=False

            # GM console swallows all input when active
            if gm_console.active:
                gm_console.on_event(ev,sm,lambda: load_nation(sel_idx))
                continue

            # trade builder overlay swallows input when active
            if trade_builder_.active:
                tb_result=trade_builder_.on_event(ev)
                if tb_result=="save":
                    rd=trade_builder_.get_route_data()
                    if trade_builder_.mode=="new":
                        existing_ids=[r.get("id","") for r in sm.state.get("trade_routes",[])]
                        new_id=f"TR{len(existing_ids)+1:04d}"
                        while new_id in existing_ids: new_id=f"TR{random.randint(1000,9999)}"
                        rd["id"]=new_id; rd.setdefault("pirate_incidents",0)
                        rd.setdefault("total_pirated",0.0); rd.setdefault("_piracy_loss_this_turn",0.0)
                        sm.state.setdefault("trade_routes",[]).append(rd)
                        set_status(f"Trade route {new_id} created.",GREEN)
                    else:
                        routes2=sm.state.get("trade_routes",[])
                        for ii,rr in enumerate(routes2):
                            if rr.get("id")==trade_builder_.route_id:
                                rd["id"]=trade_builder_.route_id
                                rd["pirate_incidents"]=rr.get("pirate_incidents",0)
                                rd["total_pirated"]=rr.get("total_pirated",0.0)
                                rd["_piracy_loss_this_turn"]=rr.get("_piracy_loss_this_turn",0.0)
                                routes2[ii]=rd; break
                        set_status(f"Route {trade_builder_.route_id} updated.",CYAN)
                    sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # confirm overlay
            if confirm_.active:
                cr=confirm_.on_event(ev)
                if cr:
                    cact,cdata=cr; n_c=cur_nation()
                    if cact=="do_remove_planet" and n_c:
                        si2,pi2=cdata["si"],cdata["pi"]
                        sl2=n_c.get("star_systems",[])
                        if si2<len(sl2) and pi2<len(sl2[si2].get("planets",[])):
                            sl2[si2]["planets"].pop(pi2)
                            sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status("Planet removed.",RED_C)
                    elif cact=="do_remove_district" and n_c:
                        si2,pi2,sett2,di2=cdata["si"],cdata["pi"],cdata["sett_i"],cdata["di"]
                        try:
                            n_c["star_systems"][si2]["planets"][pi2]["settlements"][sett2]["districts"].pop(di2)
                            sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status("District removed.",RED_C)
                        except: pass
                continue

            # graph overlay
            if graph_overlay_.active:
                graph_overlay_.on_event(ev)
                continue

            if main_.edit.active:
                result=main_.edit.on_event(ev)
                if result is not None:
                    n=cur_nation()
                    if n and apply_edit(n,main_.edit.meta,result):
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Saved.",GREEN)
                elif ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: main_.edit.close()
                continue

            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_BACKQUOTE: gm_console.open(); continue
                if ev.key==pygame.K_s: sm.save(); set_status("Saved with backup rotation.",GREEN)
                elif ev.key==pygame.K_d: do_discord()
                elif ev.key in (pygame.K_UP,pygame.K_LEFT): load_nation(sel_idx-1)
                elif ev.key in (pygame.K_DOWN,pygame.K_RIGHT): load_nation(sel_idx+1)
                elif ev.key==pygame.K_TAB:
                    tabs=cur_tabs(); tab_idx2=(tab_idx+1)%len(tabs)
                    # we need nonlocal tab_idx
                    pass
                elif pygame.K_1<=ev.key<=pygame.K_7:
                    tabs=cur_tabs(); ti=ev.key-pygame.K_1
                    if ti<len(tabs):
                        nonlocal_tab=ti
                        # handled below

            # handle tab_idx changes cleanly
            if ev.type==pygame.KEYDOWN:
                tabs=cur_tabs()
                if ev.key==pygame.K_TAB:
                    tab_idx=(tab_idx+1)%len(tabs); load_nation(sel_idx)
                elif pygame.K_1<=ev.key<=pygame.K_7:
                    ti=ev.key-pygame.K_1
                    if ti<len(tabs): tab_idx=ti; load_nation(sel_idx)

            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                tabs=cur_tabs()
                if LWIDTH<=ev.pos[0]<SW and TBAR_H<=ev.pos[1]<TBAR_H+TABBAR_H:
                    w=(SW-LWIDTH)//len(tabs); ti=(ev.pos[0]-LWIDTH)//w
                    if 0<=ti<len(tabs): tab_idx=ti; load_nation(sel_idx)

            clicked=left.on_event(ev)
            if clicked is not None: load_nation(clicked)
            if left.btn_minus.on_event(ev): left.adv_n=max(1,left.adv_n-1)
            if left.btn_plus.on_event(ev): left.adv_n=min(20,left.adv_n+1)
            if left.btn_adv.on_event(ev):
                evs=advance_turns(sm,left.adv_n); names2=sm.nation_names()
                names.clear(); names.extend(names2)
                left.set_nations(names,sel_idx); load_nation(sel_idx)
                t=sm.state.get("turn",1); y=sm.state.get("year",2200); q=sm.state.get("quarter",1)
                set_status(f"Advanced {left.adv_n}t -> T{t} {y}Q{q}  |  {len(evs)} events",GOLD)
            if left.btn_save.on_event(ev): sm.save(); set_status("Saved.",GREEN)
            if left.btn_disc.on_event(ev): do_discord()
            main_.on_event(ev)
            row=main_.on_click(ev)
            if row:
                if row["type"]=="collapse":
                    key=row["key"]
                    if key in main_.collapsed_keys: main_.collapsed_keys.discard(key)
                    else: main_.collapsed_keys.add(key)
                    load_nation(sel_idx)
                elif row["type"]=="btn":
                    action=row["action"]; data=row.get("data",{}); n=cur_nation()
                    if action=="set_econ_model" and n:
                        model=data.get("model","MIXED"); n["economic_model"]=model
                        n["is_colony_start"]=(model=="COLONY_START")
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                        set_status(f"Economic model set to {model}.",CYAN)
                    elif action=="add_system" and n:
                        add_system(n); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("New system added.",GREEN)
                    elif action=="add_planet" and n:
                        sl=n.get("star_systems",[]); si=data.get("si",0)
                        if si<len(sl): add_planet(sl[si],n.get("population",0)); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Planet added + randomized.",GREEN)
                    elif action=="add_platform" and n:
                        si=data.get("si",0); pi=data.get("pi",0); ptype=data.get("ptype","Mining")
                        sl=n.get("star_systems",[])
                        if si<len(sl):
                            pl=sl[si].get("planets",[])
                            if pi<len(pl): add_platform(pl[pi],ptype); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status(f"{ptype} platform added.",PURPLE)
                    elif action=="build_district" and n:
                        si=data.get("si",0); pi=data.get("pi",0); si2=data.get("sett_i",0); dt=data.get("district_type","Urban")
                        ok,msg=queue_construction(n,si,pi,si2,dt,sm.state)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                        set_status(msg, GREEN if ok else RED_C)
                    elif action=="randomize_planet" and n:
                        si=data.get("si",0); pi=data.get("pi",0); sl=n.get("star_systems",[])
                        if si<len(sl):
                            pl=sl[si].get("planets",[])
                            if pi<len(pl): randomize_planet(pl[pi],n.get("population",0)); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Planet randomized.",PURPLE)
                    elif action=="confirm_remove_planet" and n:
                        si2=data.get("si",0); pi2=data.get("pi",0)
                        try: pname=n["star_systems"][si2]["planets"][pi2].get("name","?")
                        except: pname="?"
                        confirm_.open(f"Remove planet {pname}?","do_remove_planet",data)
                    elif action=="confirm_remove_district" and n:
                        si2,pi2,sett2,di2=data.get("si",0),data.get("pi",0),data.get("sett_i",0),data.get("di",0)
                        try: dtype=n["star_systems"][si2]["planets"][pi2]["settlements"][sett2]["districts"][di2].get("type","?")
                        except: dtype="?"
                        confirm_.open(f"Remove {dtype} district?","do_remove_district",data)
                    elif action=="open_trade_builder":
                        trade_builder_.open_new(sm.nation_names())
                    elif action=="edit_trade_route":
                        rid=data.get("route_id")
                        route_obj=next((r for r in sm.state.get("trade_routes",[]) if r.get("id")==rid),None)
                        if route_obj: trade_builder_.open_edit(route_obj,sm.nation_names())
                    elif action=="open_graphs":
                        graph_overlay_.open()
                    elif action=="roll_events":
                        n2=sm.get_nation(data.get("nation",""))
                        if n2:
                            if is_colony(n2):
                                evs=roll_colony_events(n2,sm.state)+roll_civic_events(n2,sm.state)
                            else:
                                evs=roll_civic_events(n2,sm.state)+roll_planetside_events(n2,sm.state)+roll_resource_events(n2,sm.state)
                            sm.state.setdefault("events_log",[]).extend(evs); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status(f"Rolled {len(evs)} events for {data.get('nation','?')}.",GOLD)
                elif row.get("meta"): main_.edit.open(row["label"],row["val"],row["meta"])

        surf.fill(BG)
        turn=sm.state.get("turn",1); year=sm.state.get("year",2200); quarter=sm.state.get("quarter",1)
        tabs=cur_tabs()
        draw_top_bar(surf,names[sel_idx] if names else "N/A",turn,year,quarter,sm.dirty)
        draw_tab_bar(surf,tab_idx,tabs); left.draw(surf,turn,year,quarter); main_.draw(surf)
        main_.edit.draw(surf,dt)
        graph_overlay_.draw(surf,sm.state)
        trade_builder_.draw(surf,dt)
        confirm_.draw(surf,dt)
        gm_console.draw(surf,dt)
        draw_status_bar(surf); pygame.display.flip()
    pygame.quit()

if __name__=="__main__":
    main()