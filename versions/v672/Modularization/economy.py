"""carmine.economy — all compute_* economic, resource, trade, debt, market functions"""
import math, random
from constants import *
from corporateAlpha0671 import compute_corp_income, compute_corp_market_cap

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

def compute_gtc_debt(nation,state):
    """Return this nation's GTC debt entry, or empty dict if none."""
    ledger=state.get("market",{}).get("gtc",{}).get("debt_ledger",{})
    return ledger.get(nation["name"],{})

def apply_gtc_debt_service(state):
    """Accrue quarterly GTC interest & deduct from debtor, credit to Trade Confederation. Returns event list."""
    evs=[]; turn=state.get("turn",1); year=state.get("year",2200); q=state.get("quarter",1)
    ledger=state.setdefault("market",{}).setdefault("gtc",{}).setdefault("debt_ledger",{})
    nation_map={n["name"]:n for n in state.get("nations",[])}
    gtc_nation=nation_map.get("Trade Confederation")
    total_collected=0.0
    for nname,entry in list(ledger.items()):
        bal=entry.get("balance",0.0)
        if bal<=0: continue
        rate=entry.get("interest_rate",0.04); rep=entry.get("repayment",0.0)
        qi=bal*rate/4.0; new_bal=max(0.0,bal+qi-rep)
        entry["balance"]=new_bal
        n=nation_map.get(nname)
        if n: n["strategic_fund"]=n.get("strategic_fund",0.0)-qi
        total_collected+=qi
        evs.append({"turn":turn,"year":year,"quarter":q,"type":"GTC",
                    "description":f"{nname} GTC interest: {fmt_cr(qi)} (bal {fmt_cr(new_bal)})",
                    "col_rgb":[198,150,22]})
    if gtc_nation and total_collected>0:
        gtc_nation["strategic_fund"]=gtc_nation.get("strategic_fund",0.0)+total_collected
    return evs

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

_SUPPLY_LABELS=[(1.2,"heavy surplus"),(1.05,"mild surplus"),(0.95,"balanced"),(0.8,"mild shortage"),(0.0,"severe shortage")]
def _price_explain(rname,ratio,label,delta,curr,base):
    """Return a plain-English market commentary string."""
    sup=next(l for t,l in _SUPPLY_LABELS if ratio>=t)
    direction="risen" if delta>0.01 else ("fallen" if delta<-0.01 else "held steady")
    shock_note=f" — {label.lower()} shock this quarter" if label not in ("Stable","") else ""
    return f"{rname} supply/demand {sup} (S/D {ratio:.2f}). Price has {direction}{shock_note}."

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

