"""carmine.events — piracy, market shocks, colony/civic/planetside/resource event rolls"""
import random
from constants import *
from economy import compute_galactic_stockpiles, price_shock_delta, apply_tithes

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

