"""
carmine_alpha023.py — Carmine NRP Engine v0.2.3
================================================
Standalone engine module.  Imported by the UI; can also be used
headlessly for scripting.

Sections
--------
  1. Constants & Event Tables
  2. Formatting Helpers
  3. StateManager          – JSON load / save / 5-slot backup rotation
  4. Economy Calculations  – IPEU, trade, resources, expenditure
  5. Population Engine     – loyalty, happiness, species split, migration
  6. Turn Advancer         – full quarterly tick + d20 planetary events
  7. Trade Route Engine    – builder, tax / pirate maths
  8. Market Engine         – prices, fluctuation, PSST
  9. Event Log             – structured events, Galactic News export
 10. Discord Formatters    – National Profile, Trade Route, Market Report, Galactic News
"""
from __future__ import annotations
import json, math, os, random, shutil, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION      = "v0.2.3"
BACKUP_COUNT = 5

RESOURCE_NAMES    = ["Food","Minerals","Energy","Alloys","Consumer Goods"]
EXPENDITURE_ORDER = ["Military","Infrastructure","Agriculture",
                     "Industry","Population Development","Others"]
ECONOMIC_MODELS   = ["Capitalist","Planned","Mixed"]
PLANET_TYPES      = ["Terrestrial","Gas Giant","Ice World","Barren","Oceanic"]
PLANET_SIZES      = ["Tiny","Small","Medium","Large","Massive"]
VETERANCY_LEVELS  = ["Green","Fresh","Rookies","Trained","Regulars",
                     "Battle-Hardened","Seasoned","Veteran"]
ORBITAL_BLDG_TYPES= ["Shipyard","Defense Platform","Trade Hub",
                     "Sensor Array","Mining Station"]
SEVERITY_EMOJI    = {"Info":"📊","Minor":"⚠️","Major":"🔴","Critical":"☢️"}

PIRATE_BASE_RISK  = {"near":0.05,"kind of far":0.15,"too far":0.35,"far":0.25}

# ── d20 tier mapping ─────────────────────────────────────────────
D20_TIER: Dict[int,Tuple[str,str]] = {
    1:("critical","bad"),2:("major","bad"),3:("major","bad"),
    4:("minor","bad"),5:("minor","bad"),6:("minor","bad"),7:("minor","bad"),
    8:("stable","none"),9:("stable","none"),10:("stable","none"),
    11:("stable","none"),12:("stable","none"),13:("stable","none"),
    14:("minor","good"),15:("minor","good"),16:("minor","good"),
    17:("major","good"),18:("major","good"),19:("major","good"),
    20:("critical","good"),
}

D20_EVENT_POOL: Dict[str,List[Dict]] = {
"critical_bad":[
 {"name":"Plague Outbreak","type":"Disaster","severity":"Critical",
  "deltas":{"population":-0.15,"unrest":22,"happiness":-20,"crime_rate":8},
  "body":"A virulent plague swept through {planet} ({nation}), decimating 15%% of the population and spiking unrest."},
 {"name":"Major Uprising","type":"Planetary","severity":"Critical",
  "deltas":{"crime_rate":30,"unrest":25,"loyalty":-20,"devastation":12},
  "body":"A full-scale uprising erupted on {planet} ({nation}). Security forces were overwhelmed as crime reached critical levels."},
 {"name":"Industrial Catastrophe","type":"Economic","severity":"Critical",
  "deltas":{"devastation":22,"alloys":-0.20,"cg":-0.20,"unrest":10},
  "body":"A catastrophic industrial accident on {planet} ({nation}) destroyed key facilities, cutting alloy and CG output by 20%%."},
 {"name":"Trade Network Collapse","type":"Economic","severity":"Critical",
  "deltas":{"strategic_fund":-0.12,"unrest":18},
  "body":"Critical trade infrastructure failures struck {nation}, suspending a major route and draining the strategic reserve."},
 {"name":"Pirate Surge","type":"Military","severity":"Critical",
  "deltas":{"strategic_fund":-0.08,"unrest":12},
  "body":"A coordinated pirate offensive struck trade lanes of {nation}, raiding multiple active routes and siphoning revenue."},
],
"major_bad":[
 {"name":"Worker Strike","type":"Economic","severity":"Major",
  "deltas":{"cg":-0.12,"minerals":-0.10,"unrest":12,"loyalty":-8},
  "body":"Widespread labour strikes paralysed industry on {planet} ({nation}), cutting output for the quarter."},
 {"name":"Criminal Surge","type":"Planetary","severity":"Major",
  "deltas":{"crime_rate":14,"happiness":-12,"loyalty":-6},
  "body":"Organised crime networks expanded rapidly on {planet} ({nation}), undermining public safety and eroding trust."},
 {"name":"Drought & Crop Failure","type":"Disaster","severity":"Major",
  "deltas":{"food":-0.14,"unrest":10,"happiness":-10},
  "body":"Severe drought on {planet} ({nation}) caused widespread crop failures, reducing food stockpiles significantly."},
 {"name":"Seismic Event","type":"Disaster","severity":"Major",
  "deltas":{"devastation":12,"population":-0.04,"unrest":8},
  "body":"A powerful seismic event struck {planet} ({nation}), damaging infrastructure and displacing thousands."},
 {"name":"Research Setback","type":"Research","severity":"Major",
  "deltas":{"strategic_fund":-0.05,"unrest":4},
  "body":"A major research failure at a {nation} facility set back active projects and consumed emergency funding."},
],
"minor_bad":[
 {"name":"Power Grid Instability","type":"Economic","severity":"Minor",
  "deltas":{"energy":-0.07,"cg":-0.05,"unrest":5},
  "body":"Rolling power outages across {planet} ({nation}) disrupted industry and consumer services for the quarter."},
 {"name":"Petty Crime Wave","type":"Planetary","severity":"Minor",
  "deltas":{"crime_rate":6,"happiness":-5},
  "body":"A rise in petty criminal activity on {planet} ({nation}) lowered public morale."},
 {"name":"Supply Chain Disruption","type":"Economic","severity":"Minor",
  "deltas":{"minerals":-0.06,"alloys":-0.05},
  "body":"Logistical bottlenecks disrupted supply chains in {nation}, causing minor shortfalls in minerals and alloys."},
 {"name":"Political Scandal","type":"Diplomatic","severity":"Minor",
  "deltas":{"loyalty":-5,"unrest":6},
  "body":"A minor political scandal within {nation} administration eroded public confidence on {planet}."},
 {"name":"Equipment Malfunction","type":"Economic","severity":"Minor",
  "deltas":{"alloys":-0.05,"strategic_fund":-0.02},
  "body":"Equipment failures at industrial sites on {planet} ({nation}) required emergency maintenance."},
],
"stable":[
 {"name":"Quarterly Review","type":"Economic","severity":"Info",
  "deltas":{},
  "body":"Standard quarterly review completed for {planet} ({nation}). All systems operating within normal parameters."},
 {"name":"Cultural Exchange","type":"Diplomatic","severity":"Info",
  "deltas":{},
  "body":"Cultural exchange programmes continued on {planet} ({nation}), fostering community cohesion."},
 {"name":"Routine Patrol","type":"Military","severity":"Info",
  "deltas":{},
  "body":"Security patrols on {planet} ({nation}) reported no significant incidents this quarter."},
 {"name":"Scientific Survey","type":"Research","severity":"Info",
  "deltas":{},
  "body":"Planetary survey teams completed routine assessments on {planet} ({nation})."},
 {"name":"Market Normalcy","type":"Economic","severity":"Info",
  "deltas":{},
  "body":"Economic activity on {planet} ({nation}) remained stable with no significant fluctuations recorded."},
],
"minor_good":[
 {"name":"Local Festival","type":"Planetary","severity":"Info",
  "deltas":{"happiness":6,"loyalty":4},
  "body":"A popular cultural festival on {planet} ({nation}) boosted public morale and community spirit."},
 {"name":"Minor Resource Find","type":"Economic","severity":"Minor",
  "deltas":{"minerals":0.07,"energy":0.05},
  "body":"Geological surveys on {planet} ({nation}) uncovered minor new deposits, boosting stockpiles."},
 {"name":"Safety Improvement","type":"Planetary","severity":"Info",
  "deltas":{"crime_rate":-5,"unrest":-4},
  "body":"Enhanced policing protocols on {planet} ({nation}) reduced petty crime and improved local stability."},
 {"name":"Agricultural Bonus","type":"Economic","severity":"Minor",
  "deltas":{"food":0.08},
  "body":"Favourable conditions produced bumper harvests on {planet} ({nation}), adding to food reserves."},
 {"name":"Trade Uptick","type":"Economic","severity":"Minor",
  "deltas":{"strategic_fund":0.03},
  "body":"A minor trade surge benefited {nation} merchants, contributing a small boost to the strategic fund."},
],
"major_good":[
 {"name":"Population Boom","type":"Planetary","severity":"Major",
  "deltas":{"population":0.06,"happiness":10,"loyalty":8},
  "body":"A notable population boom on {planet} ({nation}) expanded the labour force and lifted happiness significantly."},
 {"name":"Resource Discovery","type":"Economic","severity":"Major",
  "deltas":{"minerals":0.15,"energy":0.12,"alloys":0.10},
  "body":"Major resource surveys on {planet} ({nation}) revealed significant new deposits, substantially boosting stockpiles."},
 {"name":"Trade Boom","type":"Economic","severity":"Major",
  "deltas":{"strategic_fund":0.08},
  "body":"A trade boom centred on {nation} drove a significant surge in export revenues and strategic fund growth."},
 {"name":"Stability Dividend","type":"Planetary","severity":"Major",
  "deltas":{"unrest":-12,"crime_rate":-10,"happiness":12},
  "body":"Prolonged stability on {planet} ({nation}) paid dividends — crime fell, unrest eased, and public morale soared."},
 {"name":"Industrial Surge","type":"Economic","severity":"Major",
  "deltas":{"alloys":0.14,"cg":0.12,"ipeu":0.01},
  "body":"An industrial efficiency surge on {planet} ({nation}) permanently lifted IPEU by 1%% and boosted production."},
],
"critical_good":[
 {"name":"Golden Age Declaration","type":"Economic","severity":"Critical",
  "deltas":{"ipeu":0.025,"loyalty":18,"happiness":20,"unrest":-15},
  "body":"Exceptional conditions on {planet} ({nation}) ushered in a golden age — IPEU grew permanently and morale peaked."},
 {"name":"Miraculous Harvest","type":"Economic","severity":"Critical",
  "deltas":{"food":0.30,"happiness":15,"unrest":-10},
  "body":"Record harvests across {planet} ({nation}) filled food reserves to unprecedented levels."},
 {"name":"Major Discovery","type":"Research","severity":"Critical",
  "deltas":{"ipeu":0.02,"strategic_fund":0.10},
  "body":"A breakthrough discovery on {planet} ({nation}) opened new technological pathways and attracted investment."},
 {"name":"Mass Loyalty Rally","type":"Diplomatic","severity":"Critical",
  "deltas":{"loyalty":22,"happiness":18,"unrest":-18,"crime_rate":-12},
  "body":"A sweeping loyalty movement on {planet} ({nation}) dramatically improved every civic indicator."},
 {"name":"Resource Bonanza","type":"Economic","severity":"Critical",
  "deltas":{"minerals":0.25,"energy":0.20,"alloys":0.20,"strategic_fund":0.06},
  "body":"Extraordinary resource surveys on {planet} ({nation}) uncovered a bonanza, massively boosting multiple stockpiles."},
],
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. FORMATTING HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fmt_cr(v):
    """Format credits with magnitude suffix."""
    if v is None: return "—"
    a=abs(v)
    if a>=1e15: return f"{v/1e15:.3f} Qcr"
    if a>=1e12: return f"{v/1e12:.3f} Tcr"
    if a>=1e9:  return f"{v/1e9:.3f} Bcr"
    if a>=1e6:  return f"{v/1e6:.3f} Mcr"
    if a>=1e3:  return f"{v/1e3:.2f} Kcr"
    return f"{v:.0f} cr"

def fmt_pop(v):
    """Format population with B/M/K suffix."""
    if v is None: return "—"
    a=abs(v)
    if a>=1e9: return f"{v/1e9:.3f}B"
    if a>=1e6: return f"{v/1e6:.3f}M"
    if a>=1e3: return f"{v/1e3:.2f}K"
    return f"{v:.0f}"

def fmt_int(v):
    """Format as comma-separated integer."""
    return f"{int(v):,}"

def fmt_pct(v,plus=True):
    """Format 0-1 float as percentage string."""
    s=f"{v*100:.1f}%"
    if plus and v>0: s="+"+s
    return s

def fmt_res(v):
    """Format resource quantity with T/B/M/K suffix."""
    a=abs(v)
    if a>=1e12: return f"{v/1e12:.3f}T"
    if a>=1e9:  return f"{v/1e9:.3f}B"
    if a>=1e6:  return f"{v/1e6:.3f}M"
    if a>=1e3:  return f"{v/1e3:.2f}K"
    return f"{v:.2f}"

def loyalty_bar(score,width=20):
    """░/█ loyalty bar."""
    filled=round(max(0.0,min(1.0,score/100.0))*width)
    return "█"*filled+"░"*(width-filled)

def debt_bar(pct,width=20):
    """▓/░ debt load bar."""
    filled=round(min(1.0,max(0.0,pct))*width)
    return "▓"*filled+"░"*(width-filled)

def nation_tag(name):
    """Generate 2-4 char nation abbreviation."""
    stop={"of","the","and","or","for","in","to","a","an","des","du","de","von","van"}
    words=[w for w in name.split() if w.lower() not in stop and w.isalpha()]
    tag="".join(w[0].upper() for w in words[:4])
    return tag if tag else name[:3].upper()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. STATE MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StateManager:
    """Manages JSON state with 5-slot rotating backup system."""

    def __init__(self,filepath):
        self.filepath=Path(filepath)
        self.state={}
        self._dirty=False

    def load(self):
        """Load JSON state file. Returns False if not found."""
        if not self.filepath.exists():
            print(f"  [ERROR] Not found: {self.filepath}"); return False
        with open(self.filepath,"r",encoding="utf-8") as fh:
            self.state=json.load(fh)
        self._migrate()
        self._dirty=False
        t=self.state.get("turn","?"); y=self.state.get("year","?"); q=self.state.get("quarter","?")
        print(f"  [OK] Loaded {self.filepath.name}  T{t} Y{y}Q{q}")
        return True

    def save(self,filepath=None):
        """Save with backup rotation. Backup slots: .backup1 (newest) → .backup5 (oldest)."""
        target=Path(filepath) if filepath else self.filepath
        self._rotate(target)
        with open(target,"w",encoding="utf-8") as fh:
            json.dump(self.state,fh,indent=2,ensure_ascii=False)
        self._dirty=False
        print(f"  [OK] Saved → {target.name}")
        return True

    def autosave(self): return self.save()
    def mark_dirty(self): self._dirty=True

    def _rotate(self,target):
        """Shift backup slots and promote current file to backup1."""
        p=target.parent; s=target.stem; e=target.suffix
        bp=lambda n: p/f"{s}.backup{n}{e}"
        for i in range(BACKUP_COUNT,0,-1):
            src=bp(i); dst=bp(i+1)
            if i==BACKUP_COUNT:
                if src.exists(): src.unlink()
            else:
                if src.exists(): shutil.copy2(src,dst)
        if target.exists(): shutil.copy2(target,bp(1))

    def _migrate(self):
        """
        Upgrade older state files to v0.2.3 schema.
        Adds missing fields with sensible defaults so engine can
        assume they always exist.
        """
        self.state.setdefault("events",[])
        self.state.setdefault("event_counter",0)
        for n in self.state.get("nations",[]):
            n.setdefault("economic_model","Mixed")
            n.setdefault("investments",0.0)
            n.setdefault("subsidies",0.0)
            n.setdefault("local_market_output",0.0)
            n.setdefault("export_surplus",0.0)
            n.setdefault("domestic_production",0.0)
            n.setdefault("construction_efficiency",0.80)
            n.setdefault("research_efficiency",0.80)
            n.setdefault("bureaucracy_efficiency",0.80)
            n.setdefault("distribution",0.0)
            n.setdefault("civ_level","Interplanetary Industrial")
            n.setdefault("civ_tier",2)
            n.setdefault("eco_status","Stable")
            for sys in n.get("star_systems",[]):
                for pl in sys.get("planets",[]):
                    pl.setdefault("type","Terrestrial")
                    pl.setdefault("size","Medium")
                    pl.setdefault("habitability",75.0)
                    pl.setdefault("devastation",0.0)
                    pl.setdefault("crime_rate",10.0)
                    pl.setdefault("unrest",5.0)
                    pl.setdefault("orbital_buildings",[])
                    for s in pl.get("settlements",[]):
                        s.setdefault("populations",[])
                        if not s["populations"] and n.get("species_populations"):
                            total_sp=sum(sp.get("population",0) for sp in n["species_populations"])
                            s_pop=s.get("population",0)
                            for sp in n["species_populations"]:
                                share=(sp.get("population",0)/total_sp if total_sp>0
                                       else 1.0/len(n["species_populations"]))
                                s["populations"].append({
                                    "species":sp["name"],
                                    "size":round(s_pop*share),
                                    "growth":sp.get("growth_rate",0.025),
                                    "loyalty":sp.get("loyalty",75),
                                    "happiness":70,
                                })

    def get_nation(self,name):
        """Find nation by case-insensitive name match."""
        for n in self.state.get("nations",[]):
            if n["name"].lower()==name.lower(): return n
        return None

    def nation_names(self):
        """Return ordered list of all nation names."""
        return [n["name"] for n in self.state.get("nations",[])]

    def next_event_id(self):
        """Increment and return next EVT#### string."""
        self.state["event_counter"]=self.state.get("event_counter",0)+1
        return f"EVT{self.state['event_counter']:04d}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. ECONOMY CALCULATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def current_population(nation):
    """Sum species populations if present, else use nation.population."""
    sps=nation.get("species_populations",[])
    if sps: return sum(s.get("population",0) for s in sps)
    return nation.get("population",0.0)

def compute_trade(nation,routes):
    """
    Compute per-nation trade revenue from active routes.

    Returns dict: exports, imports, transit_income, net,
                  export_routes, import_routes
    """
    name=nation["name"]
    exports=0.0; imports=0.0; transit_income=0.0
    export_routes=[]; import_routes=[]
    for r in routes:
        if r.get("status")!="active": continue
        credits=r.get("credits_per_turn",0.0)
        transits=r.get("transit_nations",[])
        if r["exporter"]==name:
            tax_out=sum(credits*t.get("tax_rate",0.0)
                        for t in transits if t.get("status")=="active")
            net_exp=credits-tax_out
            exports+=net_exp
            export_routes.append({"id":r["id"],"name":r.get("name",""),
                "importer":r["importer"],"resource":r["resource"],"credits":net_exp})
        if r["importer"]==name:
            imports+=credits
            import_routes.append({"id":r["id"],"name":r.get("name",""),
                "exporter":r["exporter"],"resource":r["resource"],"credits":credits})
        for t in transits:
            if t.get("nation")==name and t.get("status")=="active":
                transit_income+=credits*t.get("tax_rate",0.0)
    return {"exports":exports,"imports":imports,"transit_income":transit_income,
            "net":exports-imports+transit_income,
            "export_routes":export_routes,"import_routes":import_routes}

def resource_export_credits(nation_name,resource,routes):
    """Sum net export credits for one resource across all active routes."""
    total=0.0
    for r in routes:
        if r.get("status")!="active" or r.get("resource")!=resource: continue
        if r["exporter"]==nation_name:
            credits=r.get("credits_per_turn",0.0)
            tax_out=sum(credits*t.get("tax_rate",0.0)
                        for t in r.get("transit_nations",[])
                        if t.get("status")=="active")
            total+=credits-tax_out
    return total

def compute_resource_flows(nation):
    """
    Return per-resource production/consumption/net/trend dict.
    Uses flat values if mode=flat, otherwise derives from IPEU slices.
    """
    ipeu=nation.get("base_ipeu",0.0)
    exp=nation.get("expenditure",{})
    out={}
    for rname in RESOURCE_NAMES:
        sd=nation.get("resource_stockpiles",{}).get(rname,{})
        mode=sd.get("production_mode","derived")
        stk=sd.get("stockpile",0.0)
        if mode=="flat":
            prod=sd.get("flat_production",0.0); cons=sd.get("flat_consumption",0.0); est=False
        else:
            agri=exp.get("Agriculture",0.0)*ipeu; ind=exp.get("Industry",0.0)*ipeu
            fe=nation.get("food_efficiency",1.0); fc=nation.get("food_consumption_rate",0.1)
            ce=nation.get("cg_efficiency",1.0); cc=nation.get("cg_consumption_rate",0.1)
            mp=nation.get("mineral_workforce_pct",0.3); mf=nation.get("mineral_ipeu_factor",0.05)
            ar=nation.get("mineral_to_alloy_ratio",0.5); pop=nation.get("population",1.0)
            if rname=="Food":          prod=agri*fe/1e6; cons=pop*fc
            elif rname=="Minerals":    prod=ind*mp*mf/1e3; cons=prod*0.4
            elif rname=="Energy":      prod=ind*0.002/1e3; cons=prod*0.6
            elif rname=="Alloys":      prod=ind*ar*0.001/1e3; cons=prod*0.3
            else:                      prod=ind*ce*0.0005/1e3; cons=pop*cc
            est=True
        net=prod-cons; eps=max(abs(prod)*0.05,1.0)
        trend=("Stable" if abs(net)<eps else ("Surplus" if net>0 else "Deficit"))
        out[rname]={"stockpile":stk,"production":prod,"consumption":cons,
                    "net":net,"trend":trend,"estimated":est}
    return out

def compute_debt(nation):
    """Return debt summary dict for display and tick use."""
    ipeu=nation.get("base_ipeu",1.0); balance=nation.get("debt_balance",0.0)
    rate=nation.get("interest_rate",0.0); repay=nation.get("debt_repayment",0.0)
    q_int=balance*rate/4.0 if balance>0 else 0.0
    load_pct=(balance/ipeu*100) if ipeu>0 else 0.0
    return {"balance":balance,"rate":rate,"repayment":repay,"q_interest":q_int,
            "load_pct":load_pct,"is_debtor":balance>0}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. POPULATION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def recalc_loyalty_happiness(nation):
    """
    Recalculate loyalty and happiness for all species in all settlements.

    Formulae
    --------
      cg_ratio = cg_stockpile / max(1, pop * cg_consumption_rate)
      cg_mod   = clamp(cg_ratio, 0, 1.2)
      loyalty  = clamp(base_loyalty - unrest*0.3 + cg_mod*15 - crime*0.1, 0, 100)
      happiness= clamp(100 - crime*0.4 - unrest*0.3 - devastation*0.2 + cg_mod*20, 0, 100)
    """
    cg_stk=nation.get("resource_stockpiles",{}).get("Consumer Goods",{}).get("stockpile",0.0)
    pop=max(1.0,current_population(nation)); cc=nation.get("cg_consumption_rate",0.1)
    cg_mod=min(1.2,cg_stk/max(1.0,pop*cc))
    for sys in nation.get("star_systems",[]):
        for pl in sys.get("planets",[]):
            unrest=pl.get("unrest",5.0); crime=pl.get("crime_rate",10.0); dev=pl.get("devastation",0.0)
            for s in pl.get("settlements",[]):
                for sp in s.get("populations",[]):
                    base_loy=sp.get("loyalty",75)
                    sp["loyalty"]=round(max(0.0,min(100.0,base_loy-unrest*0.3+cg_mod*15-crime*0.1)),1)
                    sp["happiness"]=round(max(0.0,min(100.0,100.0-crime*0.4-unrest*0.3-dev*0.2+cg_mod*20)),1)
    for sp in nation.get("species_populations",[]):
        loy=sp.get("loyalty",75)
        sp["loyalty"]=round(max(0.0,min(100.0,loy-5.0*0.3+cg_mod*15-10.0*0.1)),1)

def tick_migration(nation):
    """Shift small fraction of population toward high-attractiveness settlements."""
    for sys in nation.get("star_systems",[]):
        for pl in sys.get("planets",[]):
            setts=pl.get("settlements",[])
            if len(setts)<2: continue
            avg_att=sum(s.get("attractiveness",50.0) for s in setts)/len(setts)
            for s in setts:
                rate=0.005*(s.get("attractiveness",50.0)-avg_att)/100.0
                s["population"]=max(0.0,s.get("population",0.0)*(1.0+rate))
                for sp in s.get("populations",[]):
                    sp["size"]=max(0.0,sp.get("size",0.0)*(1.0+rate))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. TURN ADVANCER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def advance_turn(sm):
    """
    Advance all nations one quarter.  Returns list of Event dicts.

    Per-nation tick order
    ---------------------
      a. IPEU compound quarterly growth
      b. Species population compound growth
      c. Resource stockpile tick (flat-mode only)
      d. Trade route credit payouts → strategic fund
      e. Debt interest deducted; repayment processed
      f. Research RP generation; project progress
      g. Project completion check
      h. d20 planetary event roll (1 per planet)
      i. Loyalty / Happiness recalculation
      j. Settlement attractiveness migration

    Global (post-nations)
    ---------------------
      k. Market modifier drift
      l. Autosave + backup rotation
    """
    state=sm.state; events=[]
    state["turn"]=state.get("turn",1)+1
    q=state.get("quarter",1)+1; y=state.get("year",2200)
    if q>4: q=1; y+=1
    state["quarter"]=q; state["year"]=y
    routes=state.get("trade_routes",[]); market=state.get("market",{})
    for nation in state.get("nations",[]):
        events.extend(_tick_nation(nation,routes,market,state["turn"],y,q,sm))
    _tick_market(market)
    state.setdefault("events",[]).extend(events)
    sm.mark_dirty(); sm.autosave()
    return events

def _tick_nation(nation,routes,market,turn,year,quarter,sm):
    """Run all per-nation tick steps. Returns list of events."""
    events=[]
    # a IPEU
    g=nation.get("ipeu_growth",0.0)
    nation["base_ipeu"]=nation.get("base_ipeu",0.0)*(1.0+g/4.0)
    # b Population
    sps=nation.get("species_populations",[])
    if sps:
        for sp in sps:
            sg=sp.get("growth_rate",0.0); sp["population"]=sp.get("population",0.0)*(1.0+sg/4.0)
        nation["population"]=sum(s["population"] for s in sps)
    else:
        pg=nation.get("pop_growth",0.0); nation["population"]=nation.get("population",0.0)*(1.0+pg/4.0)
    # c Resources (flat only)
    for rname in RESOURCE_NAMES:
        sd=nation.setdefault("resource_stockpiles",{}).setdefault(rname,{})
        if sd.get("production_mode","derived")=="flat":
            prod=sd.get("flat_production",0.0); cons=sd.get("flat_consumption",0.0)
            sd["stockpile"]=max(0.0,sd.get("stockpile",0.0)+prod-cons)
            sd["shortage"]=sd["stockpile"]==0.0
    # d Trade payouts
    trade=compute_trade(nation,routes)
    nation["strategic_fund"]=nation.get("strategic_fund",0.0)+trade["exports"]+trade["transit_income"]-trade["imports"]
    # e Debt
    debt=nation.get("debt_balance",0.0); rate=nation.get("interest_rate",0.0)
    q_int=debt*rate/4.0 if debt>0 else 0.0
    nation["strategic_fund"]=nation.get("strategic_fund",0.0)-q_int
    repay=nation.get("debt_repayment",0.0)
    if repay>0 and debt>0:
        actual=min(repay,debt); nation["debt_balance"]=max(0.0,debt-actual)
        nation["strategic_fund"]-=actual
    # f Research
    rp_per_turn=nation.get("research_budget",0.0)*0.000001
    re=nation.get("research_efficiency",0.8); rp=rp_per_turn*re
    for proj in nation.get("active_research_projects",[]):
        cost=max(1.0,proj.get("rp_cost",1000.0))
        proj["progress"]=min(100.0,proj.get("progress",0.0)+rp/cost*100.0)
    # g Project completion
    for proj in nation.get("projects",[]):
        if proj.get("status") in ("active","in_progress"):
            proj["turns_elapsed"]=proj.get("turns_elapsed",0)+1
            if proj["turns_elapsed"]>=proj.get("duration_turns",999):
                proj["status"]="complete"
                events.append(_make_event(sm,turn,year,quarter,"Economic","Nation",
                    nation["name"],None,f"Project Complete: {proj['name']}",
                    f"The project '{proj['name']}' ({proj.get('category','?')}) completed in {nation['name']}.",
                    {},"Minor",0))
    # h d20 events
    for sys in nation.get("star_systems",[]):
        for pl in sys.get("planets",[]):
            ev=_roll_planet_d20(sm,nation,pl,turn,year,quarter)
            if ev:
                events.append(ev)
                _apply_deltas(nation,pl,ev["stat_deltas"])
    # i Loyalty / Happiness
    recalc_loyalty_happiness(nation)
    # j Migration
    tick_migration(nation)
    return events

def _roll_planet_d20(sm,nation,planet,turn,year,quarter):
    """Roll d20 for a planet. Stable events suppressed 60% of the time."""
    roll=random.randint(1,20)
    tier,sign=D20_TIER[roll]
    pool_key=f"{tier}_{sign}" if sign!="none" else "stable"
    pool=D20_EVENT_POOL.get(pool_key,[])
    if not pool: return None
    template=random.choice(pool)
    if tier=="stable" and random.random()<0.60: return None
    body=(template["body"]
          .replace("{nation}",nation["name"])
          .replace("{planet}",planet["name"]))
    return _make_event(sm,turn,year,quarter,template["type"],"Planet",
        nation["name"],planet["name"],
        f"{template['name']} on {planet['name']}",
        body,dict(template["deltas"]),template["severity"],roll)

def _make_event(sm,turn,year,quarter,etype,scope,nation,planet,title,body,deltas,severity,roll):
    """Construct a structured Event dict."""
    return {"event_id":sm.next_event_id(),"turn":turn,"year":year,"quarter":quarter,
            "type":etype,"scope":scope,"nation":nation,"planet":planet,
            "title":title,"body":body,"stat_deltas":deltas,
            "severity":severity,"d20_roll":roll,"gm_approved":False,"gm_edited":False}

def _apply_deltas(nation,planet,deltas):
    """Apply event stat_deltas to nation/planet. Fractional keys are multiplicative."""
    if not deltas: return
    clamp=lambda v,lo,hi: max(lo,min(hi,v))
    if "unrest"     in deltas: planet["unrest"]    =clamp(planet.get("unrest",5.0)+deltas["unrest"],0,100)
    if "crime_rate" in deltas: planet["crime_rate"]=clamp(planet.get("crime_rate",10.0)+deltas["crime_rate"],0,100)
    if "devastation"in deltas: planet["devastation"]=clamp(planet.get("devastation",0.0)+deltas["devastation"],0,100)
    if "happiness"  in deltas:
        for s in planet.get("settlements",[]):
            for sp in s.get("populations",[]):
                sp["happiness"]=clamp(sp.get("happiness",70)+deltas["happiness"],0,100)
    if "loyalty"    in deltas:
        for s in planet.get("settlements",[]):
            for sp in s.get("populations",[]):
                sp["loyalty"]=clamp(sp.get("loyalty",75)+deltas["loyalty"],0,100)
    if "population" in deltas:
        mult=1.0+deltas["population"]
        for s in planet.get("settlements",[]):
            s["population"]=max(0.0,s.get("population",0.0)*mult)
            for sp in s.get("populations",[]):
                sp["size"]=max(0.0,sp.get("size",0.0)*mult)
    if "ipeu" in deltas:
        nation["base_ipeu"]=nation.get("base_ipeu",0.0)*(1.0+deltas["ipeu"])
    if "strategic_fund" in deltas:
        nation["strategic_fund"]=nation.get("strategic_fund",0.0)*(1.0+deltas["strategic_fund"])
    res_map={"food":"Food","minerals":"Minerals","energy":"Energy","alloys":"Alloys","cg":"Consumer Goods"}
    for key,rname in res_map.items():
        if key in deltas:
            sd=nation.setdefault("resource_stockpiles",{}).setdefault(rname,{})
            sd["stockpile"]=max(0.0,sd.get("stockpile",0.0)*(1.0+deltas[key]))

def _tick_market(market):
    """Random ±3% drift on all resource market modifiers per turn."""
    mods=market.get("market_modifier",{})
    hist=market.setdefault("price_history",{})
    pb  =market.get("price_base",{})
    for rname in RESOURCE_NAMES:
        if rname not in mods: continue
        drift=random.uniform(-0.03,0.03)
        mods[rname]=round(max(0.5,min(8.0,mods[rname]+drift)),3)
        eff=pb.get(rname,1.0)*mods[rname]
        hist.setdefault(rname,[]).append(round(eff,4))
        if len(hist[rname])>20: hist[rname]=hist[rname][-20:]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. TRADE ROUTE ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TradeRouteEngine:
    """
    Builds and calculates trade routes.

    Quantity auto-calc
    ------------------
      Capitalist/Mixed : stockpile + 4-turn net surplus buffer * export_pct
      Planned          : direct stockpile * export_pct (no surplus buffer)
    """

    def __init__(self,state):
        self.state=state
        self.market=state.get("market",{})

    def effective_price(self,resource):
        """Return base × modifier effective price for a resource."""
        pb =self.market.get("price_base",{}).get(resource,1.0)
        mod=self.market.get("market_modifier",{}).get(resource,1.0)
        return pb*mod

    def available_export(self,nation,resource):
        """Compute units available to export per turn."""
        sd  =nation.get("resource_stockpiles",{}).get(resource,{})
        stk =sd.get("stockpile",0.0)
        mode=sd.get("production_mode","derived")
        if mode=="flat":
            net=sd.get("flat_production",0.0)-sd.get("flat_consumption",0.0)
        else:
            flows=compute_resource_flows(nation); net=flows.get(resource,{}).get("net",0.0)
        eco=nation.get("economic_model","Mixed")
        if eco=="Planned": return max(0.0,stk)
        return max(0.0,stk+max(0.0,net)*4.0)

    def calculate(self,exporter_name,importer_name,resource,quantity_per_turn,
                  transit_nations,pirate_distance="near",escort_pct=0.0,route_modifier=1.0):
        """
        Compute gross, taxes, net, and pirate risk for a proposed route.

        Parameters
        ----------
        transit_nations : list of {"nation": str, "tax_rate": float}

        Returns
        -------
        dict with gross, transit_taxes, net_income, pirate_risk_pct, etc.
        """
        price=self.effective_price(resource)
        gross=quantity_per_turn*price*route_modifier
        taxes=[]; total_tax=0.0
        for t in transit_nations:
            amt=gross*t.get("tax_rate",0.0)
            taxes.append({"nation":t["nation"],"rate":t.get("tax_rate",0.0),"amount":amt})
            total_tax+=amt
        net_income=gross-total_tax
        base=PIRATE_BASE_RISK.get(pirate_distance,0.15)
        risk=base*max(0.0,1.0-escort_pct/100.0*0.8)
        risk=round(min(0.95,max(0.0,risk)),4)
        exp_loss=risk*0.25*gross
        return {"exporter":exporter_name,"importer":importer_name,"resource":resource,
                "quantity_per_turn":quantity_per_turn,"effective_price":price,
                "gross":gross,"transit_taxes":taxes,"total_tax":total_tax,
                "net_income":net_income,"pirate_distance":pirate_distance,
                "escort_pct":escort_pct,"pirate_risk":risk,
                "pirate_risk_pct":round(risk*100,1),
                "expected_pirate_loss":exp_loss,"route_modifier":route_modifier}

    def build(self,preview,pirate_distance="near",pirate_escort=""):
        """Construct a ready-to-append route dict from a calculate() preview."""
        existing=self.state.get("trade_routes",[]); new_id=f"TR{len(existing)+1:04d}"
        return {"id":new_id,
                "name":f"{preview['exporter']} → {preview['importer']} {preview['resource']}",
                "exporter":preview["exporter"],"importer":preview["importer"],
                "resource":preview["resource"],
                "quantity_per_turn":preview["quantity_per_turn"],
                "credits_per_turn":preview["gross"],
                "duration_turns":-1,"status":"active",
                "transit_nations":[{"nation":t["nation"],"tax_rate":t["rate"],"status":"active"}
                                   for t in preview["transit_taxes"]],
                "created_turn":self.state.get("turn",1),
                "pirate_distance":pirate_distance,"pirate_escort":pirate_escort,
                "pirate_incidents":0,"total_pirated":0.0,
                "route_modifier":preview["route_modifier"]}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. MARKET ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketEngine:
    """Manages galactic market prices and fluctuations."""

    def __init__(self,market): self.market=market

    def get_prices(self):
        """Return list of price dicts for all resources."""
        pb=self.market.get("price_base",{}); mods=self.market.get("market_modifier",{})
        hist=self.market.get("price_history",{}); out=[]
        for rname in RESOURCE_NAMES:
            base=pb.get(rname,1.0); mod=mods.get(rname,1.0); eff=base*mod
            h=hist.get(rname,[eff])
            trend=("▲" if len(h)>=2 and h[-1]>h[-2]
                   else("▼" if len(h)>=2 and h[-1]<h[-2] else "─"))
            out.append({"resource":rname,"base":base,"modifier":mod,
                         "effective":eff,"trend":trend,"history":h[-10:]})
        return out

    def set_modifier(self,resource,value):
        """Directly set the market modifier for a resource."""
        self.market.setdefault("market_modifier",{})[resource]=round(max(0.1,min(20.0,value)),3)

    def set_base(self,resource,value):
        """Override base price for a resource."""
        self.market.setdefault("price_base",{})[resource]=max(0.01,value)

    def fluctuate_all(self,intensity=0.08):
        """Randomly shift all modifiers ±intensity. Returns list of change dicts."""
        mods=self.market.setdefault("market_modifier",{}); changes=[]
        for rname in RESOURCE_NAMES:
            old=mods.get(rname,1.0)
            new=round(max(0.5,min(8.0,old+random.uniform(-intensity,intensity))),3)
            mods[rname]=new; changes.append({"resource":rname,"old":old,"new":new})
        return changes

    def add_custom(self,name,base_price,modifier=1.0):
        """Register a custom (non-standard) resource in the market."""
        self.market.setdefault("custom_resources",{})[name]={"base_price":base_price,"modifier":modifier}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. EVENT LOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventLog:
    """Wrapper around state['events'] with filtering and bulk operations."""

    def __init__(self,state): self.state=state

    @property
    def events(self): return self.state.setdefault("events",[])

    def filter(self,turn=None,nation=None,etype=None,severity=None,approved=None):
        """Return filtered events list, newest first."""
        out=[]
        for ev in reversed(self.events):
            if turn     is not None and ev.get("turn")!=turn:          continue
            if nation   is not None and ev.get("nation")!=nation:      continue
            if etype    is not None and ev.get("type")!=etype:         continue
            if severity is not None and ev.get("severity")!=severity:  continue
            if approved is not None and ev.get("gm_approved")!=approved: continue
            out.append(ev)
        return out

    def approve(self,event_id):
        """Toggle GM approval. Returns new boolean state."""
        for ev in self.events:
            if ev["event_id"]==event_id:
                ev["gm_approved"]=not ev["gm_approved"]; return ev["gm_approved"]
        return False

    def edit_body(self,event_id,new_body):
        """Edit the one-liner body of an event."""
        for ev in self.events:
            if ev["event_id"]==event_id:
                ev["body"]=new_body; ev["gm_edited"]=True; return

    def delete(self,event_id):
        """Remove an event by ID."""
        before=len(self.events)
        self.state["events"]=[e for e in self.events if e["event_id"]!=event_id]
        return len(self.events)<before

    def approved_for_turn(self,turn):
        """Return approved events for a turn sorted Critical→Info."""
        order=["Critical","Major","Minor","Info"]
        evs=self.filter(turn=turn,approved=True)
        return sorted(evs,key=lambda e:order.index(e.get("severity","Info"))
                         if e.get("severity","Info") in order else 99)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. DISCORD FORMATTERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def discord_profile(nation,state):
    """
    Generate full Discord-ready National Profile post.

    Format matches the v0.2.3 reference template exactly, including
    economic model branch (Capitalist/Planned/Mixed) sub-sections.
    """
    turn=state.get("turn",1); year=state.get("year",2200); quarter=state.get("quarter",1)
    routes=state.get("trade_routes",[])
    ipeu=nation.get("base_ipeu",0.0); pop=current_population(nation)
    exp_d=nation.get("expenditure",{}); trade=compute_trade(nation,routes)
    rflows=compute_resource_flows(nation); debt=compute_debt(nation)
    rbudget=nation.get("research_budget",0.0); sfund=nation.get("strategic_fund",0.0)
    star_sys=nation.get("star_systems",[]); species=nation.get("species_populations",[])
    tag=nation_tag(nation["name"]); eco_m=nation.get("economic_model","Mixed")
    total_exp_pct=sum(exp_d.values())
    total_exp_cr=total_exp_pct*ipeu+rbudget
    net_bal=ipeu+trade["net"]-total_exp_cr-debt["q_interest"]
    per_cap=int(ipeu/pop) if pop>0 else 0
    fund_delta=trade["net"]-debt["q_interest"]
    homeworld="—"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl["name"]; break
        break
    species_str=(", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species)
                 if species else "—")
    L=[]; ln=L.append
    ln(f"-# [{tag}] {nation['name'].upper()}")
    ln(f"# NATIONAL PROFILE - Q{quarter} {year}")
    ln("```")
    ln(f"  Species          : {species_str}")
    ln(f"  Population       : {fmt_pop(pop)}")
    ln(f"  Pop Growth       : {fmt_pct(nation.get('pop_growth',0))} / yr")
    ln(f"  Homeworld        : {homeworld}")
    ln(f"  Civilisation     : {nation.get('civ_level','Interplanetary Industrial')}")
    ln(f"  Tier             : {nation.get('civ_tier',2)}")
    ln(f"  Economic Model   : {eco_m}")
    ln(f"  Status           : {nation.get('eco_status','Stable')}")
    ln("```")
    ln("# ECONOMY")
    ln("```")
    ln(f"  IPEU (base)      : {fmt_cr(ipeu)}")
    ln(f"  IPEU Growth      : {fmt_pct(nation.get('ipeu_growth',0))} / yr")
    ln(f"  IPEU per Capita  : {per_cap:,} cr")
    ln(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
    ln(f"   - Exports       : {fmt_cr(trade['exports'])}")
    ln(f"   - Imports       : {fmt_cr(-trade['imports'])}")
    ln(f"  Total Expenditure: {fmt_cr(total_exp_cr)}  ({total_exp_pct*100:.1f}%%)")
    ln(f"  Research Budget  : {fmt_cr(rbudget)} / turn")
    ln(f"  Net Balance      : {fmt_cr(net_bal)}")
    ln("```")
    ln("## EXPENDITURE & BREAKDOWN")
    ln("```")
    max_pct=max(exp_d.values(),default=0.01)
    for cat in EXPENDITURE_ORDER:
        pct=exp_d.get(cat,0.0)
        if pct==0.0 and cat not in exp_d: continue
        bw=round(pct/max_pct*20) if max_pct>0 else 0
        bar="█"*bw+"░"*(20-bw)
        ln(f"  {cat:<22} {pct*100:5.1f}%%  {bar}  {fmt_cr(pct*ipeu)}")
    ln(f"  {'─'*61}")
    ln(f"  {'TOTAL':<22} {total_exp_pct*100:5.1f}%%  {'':20}  ({fmt_cr(total_exp_cr)})")
    ln("```")
    ln("## ECONOMIC PROJECTS")
    ln("```")
    projs=[p for p in nation.get("projects",[]) if p.get("status") in ("active","in_progress","complete")]
    if projs:
        for p in projs:
            done=p.get("status")=="complete"
            tl=p.get("duration_turns",0)-p.get("turns_elapsed",0)
            tag2="[COMPLETE]" if done else f"[{tl} turns remaining]"
            ln(f"  {p['name']} ({p.get('category','?')})  {tag2}")
            for eff in p.get("effects",[]): ln(f"    - {eff}")
    else: ln("  None")
    ln("```")
    if eco_m in ("Capitalist","Mixed"):
        ln("## ECONOMIC MODEL — MARKET DATA")
        ln("```")
        ln(f"  Trade            : {fmt_cr(trade['net'])} total  ({fmt_cr(trade['exports'])} exp, {fmt_cr(trade['imports'])} imp)")
        ln(f"  Trade Balance    : {fmt_cr(trade['exports']-trade['imports'])}")
        ln(f"  Investments      : {fmt_cr(nation.get('investments',0.0))}")
        ln(f"  Subsidies        : {fmt_cr(nation.get('subsidies',0.0))}")
        ln(f"  Local Mkt Output : {fmt_cr(nation.get('local_market_output',0.0))}")
        ln("```")
    if eco_m in ("Planned","Mixed"):
        ln("## ECONOMIC MODEL — PLANNED DATA")
        ln("```")
        ln(f"  Domestic Prod.   : {fmt_cr(nation.get('domestic_production',0.0))}")
        ln(f"  Export Surplus   : {fmt_cr(nation.get('export_surplus',0.0))}")
        ln(f"  Construction Eff.: {nation.get('construction_efficiency',0.8)*100:.0f}%%")
        ln(f"  Research Eff.    : {nation.get('research_efficiency',0.8)*100:.0f}%%")
        ln(f"  Bureaucracy Eff. : {nation.get('bureaucracy_efficiency',0.8)*100:.0f}%%")
        ln(f"  Distribution     : {fmt_cr(nation.get('distribution',0.0))}")
        ln("```")
    ln("## FISCAL REPORT")
    ln("```")
    ln(f"  Debt Balance     : {fmt_cr(debt['balance'])}  ({debt['load_pct']:.1f}%% of IPEU)")
    ln(f"  Debt Load        : {debt_bar(debt['load_pct']/100)}")
    ln(f"  Interest Rate    : {debt['rate']*100:.1f}%% / yr")
    ln(f"  Quarterly Int.   : {fmt_cr(debt['q_interest'])}")
    ln(f"  Debt Repayment   : {fmt_cr(debt['repayment'])} / qtr")
    ln(f"  {'─'*61}")
    sf_icon="🟢" if sfund>=0 else "🔴"
    ln(f"  Strategic Fund   : {sf_icon} {fmt_cr(sfund)}")
    fd_sign="+" if fund_delta>=0 else ""
    ln(f"  Fund Δ this turn : {fd_sign}{fmt_cr(fund_delta)}")
    ln("```")
    ln("## RESOURCES & STOCKPILES")
    ln("```")
    for rname in RESOURCE_NAMES:
        rd=rflows.get(rname,{}); stk=rd.get("stockpile",0.0)
        prod=rd.get("production",0.0); cons=rd.get("consumption",0.0)
        net=rd.get("net",0.0); trend=rd.get("trend","Stable")
        exp_c=resource_export_credits(nation["name"],rname,routes)
        ns=f"+{fmt_int(net)}" if net>=0 else fmt_int(int(net))
        ln(f"  {rname} Stockpile{'':<13}: {fmt_int(stk)}")
        ln(f"  {rname} Production per turn  : {fmt_int(prod)}")
        ln(f"  {rname} Consumption per turn : {fmt_int(cons)}")
        ln(f"  {rname} Net per turn         : {ns}")
        ln(f"  {rname} Trend                : {trend}")
        if exp_c>0: ln(f"  {rname} Export              : {fmt_cr(exp_c)}")
        ln("")
    ln("```")
    ln("# TERRITORIES")
    if star_sys:
        sys0=star_sys[0]; ln(f"Home System: {sys0['name']}"); ln("Planets:"); ln("```")
        for pl in sys0.get("planets",[]):
            p_pop=pl.get("pop_assigned",pop)
            ln(f"  Homeworld: {pl['name']}")
            ln(f"    Type          : {pl.get('type','Terrestrial')}")
            ln(f"    Size          : {pl.get('size','Medium')}")
            ln(f"    Habitability   : {pl.get('habitability',75):.0f}%%")
            ln(f"    Devastation     : {pl.get('devastation',0):.0f}%%")
            ln(f"    Crime Rate     : {pl.get('crime_rate',10):.0f}%%")
            ln(f"    Unrest         : {pl.get('unrest',5):.0f}%%")
            ln(f"    Population      : {fmt_pop(p_pop)}")
            pop_by_sp={}
            for s in pl.get("settlements",[]):
                for sp2 in s.get("populations",[]):
                    pop_by_sp[sp2["species"]]=pop_by_sp.get(sp2["species"],0.0)+sp2.get("size",0.0)
            for sp_name,sp_sz in pop_by_sp.items():
                sp_data=next((s for s in species if s["name"]==sp_name),{})
                loy=sp_data.get("loyalty",75); hap=70
                for s in pl.get("settlements",[]):
                    for sp2 in s.get("populations",[]):
                        if sp2["species"]==sp_name: hap=sp2.get("happiness",70)
                ln(f"     - {sp_name} | {fmt_pop(sp_sz)} | Loyalty {loy} | Happiness {hap}")
            setts=pl.get("settlements",[])
            if setts:
                ln(f"    Settlements   : {len(setts)}")
                for s in setts:
                    ln(f"      › {s['name']}  (pop: {fmt_pop(s.get('population',0))})")
                    dcounts={}
                    for d in s.get("districts",[]):
                        dt=d.get("type","?"); dcounts[dt]=dcounts.get(dt,0)+1
                    for dt,cnt in dcounts.items(): ln(f"          [{dt}] x{cnt}")
            else: ln("    Settlements   : None")
        ln("```")
    ln("# NATIONAL DEMOGRAPHICS")
    ln("```")
    ln(f"  Total Population     : {fmt_pop(pop)}")
    ln(f"  Loyalty Modifier     : {nation.get('loyalty_modifier_cg',1.0)*100:.0f}%%")
    ln("```")
    for sp in species:
        is_dom=sp.get("status","") in ("dominant","majority")
        crown="👑" if is_dom else "👥"
        sp_pop=sp.get("population",0); shr=sp_pop/pop*100 if pop>0 else 0
        loy=sp.get("loyalty",75); loy_icon="🟢" if loy>=70 else("🟡" if loy>=40 else "🔴")
        hap=70
        for sys in star_sys:
            for pl in sys.get("planets",[]):
                for s in pl.get("settlements",[]):
                    for sp2 in s.get("populations",[]):
                        if sp2["species"]==sp["name"]: hap=sp2.get("happiness",70)
        ln(f"**{sp['name']}**  {crown} {sp.get('status','?').title()}")
        ln("```")
        ln(f"  Population       : {fmt_pop(sp_pop)}")
        ln(f"  Share            : {shr:.1f}%% of total")
        ln(f"  Growth Rate      : {fmt_pct(sp.get('growth_rate',0))} / yr")
        ln(f"  Culture          : {sp.get('culture','—')}")
        ln(f"  Language         : {sp.get('language','—')}")
        ln(f"  Religion         : {sp.get('religion','—')}")
        ln(f"  Loyalty          : {loy_icon} {loy}/100  {loyalty_bar(loy)}")
        ln(f"  Happiness        : {hap}/100  {loyalty_bar(hap)}")
        ln("```")
    return "\n".join(L)

def discord_trade_route(preview,route_id="TR????"):
    """Format a trade route preview for Discord posting."""
    R=preview; L=[]; ln=L.append
    ln(f"-# [{route_id}] {R['exporter']} → {R['importer']}")
    ln(f"# TRADE ROUTE — {R['resource']}")
    ln("```")
    ln(f"  Route ID      : {route_id}")
    ln(f"  Exporter      : {R['exporter']}")
    ln(f"  Importer      : {R['importer']}")
    ln(f"  Resource      : {R['resource']}")
    ln(f"  Qty/turn      : {fmt_int(R['quantity_per_turn'])}")
    ln(f"  Unit Price    : {R['effective_price']:.4f} cr")
    ln(f"  Gross/turn    : {fmt_cr(R['gross'])}")
    for t in R.get("transit_taxes",[]):
        ln(f"  Transit {t['nation'][:20]:<20}: -{fmt_cr(t['amount'])}  ({t['rate']*100:.1f}%%)")
    ln(f"  NET/turn      : {fmt_cr(R['net_income'])}")
    ln(f"  {'─'*49}")
    ln(f"  Pirate dist.  : {R['pirate_distance']}")
    ln(f"  Escort        : {R['escort_pct']:.0f}%%")
    ln(f"  Pirate risk   : {R['pirate_risk_pct']:.1f}%% / turn")
    ln(f"  Exp. loss/t   : {fmt_cr(R['expected_pirate_loss'])}")
    ln("```")
    return "\n".join(L)

def discord_galactic_news(state,turn):
    """Format all GM-approved events for a turn as a Galactic News broadcast."""
    elog=EventLog(state); evs=elog.approved_for_turn(turn)
    year=state.get("year",2200); q=state.get("quarter",1)
    L=[]; ln=L.append
    ln(f"-# 📡 GALACTIC NEWS NETWORK — T{turn} | Y{year} Q{q}")
    ln("# 🌌 GALACTIC DISPATCH"); ln("")
    if not evs:
        ln("*No approved events for this turn.*")
    else:
        for ev in evs:
            icon=SEVERITY_EMOJI.get(ev.get("severity","Info"),"📊")
            scope=ev.get("nation","Galactic")
            if ev.get("planet"): scope+=f" | {ev['planet']}"
            ln(f"{icon} **{ev.get('severity','Info').upper()} — {scope}**")
            ln(ev["body"]); ln("")
    ln("─"*61)
    ln(f"*Transmitted by the Galactic News Network, Y{year} Q{q}*")
    return "\n".join(L)

def discord_market_report(state):
    """Format current galactic market prices for Discord."""
    me=MarketEngine(state.get("market",{})); rows=me.get_prices()
    turn=state.get("turn",1); year=state.get("year",2200); q=state.get("quarter",1)
    L=[]; ln=L.append
    ln(f"-# 📈 GALACTIC MARKET REPORT — T{turn} | Y{year} Q{q}")
    ln("# GALACTIC MARKET"); ln("```")
    ln(f"  {'Resource':<18} {'Base':>8}  {'Mod':>6}  {'Effective':>10}  {'Trend':>5}")
    ln(f"  {'─'*58}")
    for r in rows:
        ln(f"  {r['resource']:<18} {r['base']:>8.2f}  x{r['modifier']:>5.2f}  {r['effective']:>10.2f} cr  {r['trend']:>5}")
    psst=state.get("market",{}).get("psst_nations",[])
    if psst: ln(""); ln(f"  PSST Nations: {', '.join(psst)}")
    ln("```")
    return "\n".join(L)
