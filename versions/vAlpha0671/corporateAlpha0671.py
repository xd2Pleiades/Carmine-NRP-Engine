#!/usr/bin/env python3
"""
corporateAlpha0671.py
Corporate subsystem for Carmine NRP Engine vAlpha0.6.71
Contains: compute functions, overlays, Discord output, build_corp_rows.
Imported by vAlpha0.6.71.py — do not run directly.
Call init_corp_module(ctx) from main() before using anything here.
"""

import pygame, random, uuid
from pathlib import Path

# ── UI context injected by main via init_corp_module() ────────────────────────
_C = {}

def init_corp_module(ctx):
    global _C
    _C = ctx

def _gf(s):      return _C["gf"](s)
def _dt(su,t,x,y,f,c=None): _C["draw_text"](su,t,x,y,f,c if c is not None else _C["TEXT"])
def _dr(su,r,c,b=0,rad=0):  _C["draw_rect"](su,r,c,b,rad)
def _fcr(v):     return _C["fmt_cr"](v)

# ── Constants ─────────────────────────────────────────────────────────────────
TIER_MULT = {
    "tiny":   0.25,
    "small":  0.5,
    "medium": 1.0,
    "large":  2.0,
    "massive":4.0,
}
_TIER_OPTS   = ["tiny","small","medium","large","massive"]
_TYPE_OPTS   = ["office","store","factory"]
_LOC_STATUS  = ["active","under construction","closed"]
_CONTRACT_ST = ["active","pending","expired","ended"]
_CORP_EV_TABLE = [
    (1,3, "Scandal",       (-0.08,-0.04)),
    (4,6, "Bad Press",     (-0.04,-0.01)),
    (7,14,"Stable Quarter",(0.0,  0.0  )),
    (15,17,"Good PR",      (0.01, 0.03 )),
    (18,19,"Major Deal",   (0.03, 0.06 )),
    (20,20,"Trust Surge",  (0.06, 0.10 )),
]

def _d20():          return random.randint(1,20)
def _lookup(tbl,r):
    for row in tbl:
        if row[0]<=r<=row[1]: return row
    return tbl[len(tbl)//2]

def _bar_str(pct,w=20):
    pct=max(0.0,min(1.0,pct)); f=round(pct*w)
    return "\u2588"*f+"\u2591"*(w-f)

# ── Compute ───────────────────────────────────────────────────────────────────
def compute_corp_factory_output(nation):
    cd=nation.get("corporate_data",{}); total=0
    for loc in (cd.get("locations") or []):
        if loc.get("type")!="factory" or loc.get("status")!="active": continue
        ov=loc.get("units_produced_override")
        total+=ov if ov is not None else int(loc.get("employees",0)*TIER_MULT.get(loc.get("tier","medium"),1.0))
    return total

def compute_corp_store_sales(nation, units_available):
    cd=nation.get("corporate_data",{}); locs=cd.get("locations") or []
    trust=cd.get("trust",0.5)
    active_offices=sum(1 for l in locs if l.get("type")=="office" and l.get("status")=="active")
    boost=1.0+0.05*active_offices
    total_inc=0.0; total_sold=0; pool=units_available
    for loc in locs:
        if loc.get("type")!="store" or loc.get("status")!="active": continue
        tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
        cap=loc.get("sell_capacity_override") or int(loc.get("employees",0)*tm)
        sold=min(pool,cap); pool-=sold
        total_inc+=sold*loc.get("cr_per_unit",0.0)*trust*boost-loc.get("upkeep",0.0)
        total_sold+=sold
    return total_inc,total_sold

def compute_corp_income(nation):
    cd=nation.get("corporate_data",{}); trust=cd.get("trust",0.5); ipeu=nation.get("base_ipeu",0.0)
    base=ipeu*(cd.get("product_sale_pct",0.0)+cd.get("service_income_pct",0.0))*trust
    locs=cd.get("locations") or []; office_inc=0.0; factory_upkeep=0.0
    for loc in locs:
        if loc.get("status")!="active": continue
        typ=loc.get("type","office"); upkeep=loc.get("upkeep",0.0)
        if typ=="office":
            h=loc.get("host_ipeu",ipeu); tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
            fill=min(1.0,loc.get("employees",0)/max(1,loc.get("employee_cap",1)))
            office_inc+=h*tm*fill*trust-upkeep
        elif typ=="factory": factory_upkeep+=upkeep
    units=compute_corp_factory_output(nation)
    store_inc,_=compute_corp_store_sales(nation,units)
    contract_inc=sum(c.get("value_per_turn",0.0) for c in (cd.get("contracts") or []) if c.get("status")=="active")
    return base+office_inc+store_inc-factory_upkeep+contract_inc

def compute_corp_market_cap(nation):
    cd=nation.get("corporate_data",{}); trust=cd.get("trust",0.5); ipeu=nation.get("base_ipeu",0.0)
    loc_gross=0.0
    for loc in (cd.get("locations") or []):
        if loc.get("status")!="active": continue
        typ=loc.get("type","office")
        if typ=="office":
            h=loc.get("host_ipeu",ipeu); tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
            fill=min(1.0,loc.get("employees",0)/max(1,loc.get("employee_cap",1)))
            loc_gross+=h*tm*fill
        elif typ=="store":
            units=compute_corp_factory_output(nation); tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
            cap=loc.get("sell_capacity_override") or int(loc.get("employees",0)*tm)
            loc_gross+=min(units,cap)*loc.get("cr_per_unit",0.0)
    contracts_val=sum(c.get("value_per_turn",0.0) for c in (cd.get("contracts") or []) if c.get("status")=="active")
    return (contracts_val+loc_gross)*trust

def roll_corp_events(nation,state):
    cd=nation.get("corporate_data",{}); t=state.get("turn",1); y=state.get("year",2200); q=state.get("quarter",1)
    roll=_d20(); row=_lookup(_CORP_EV_TABLE,roll); _,_,label,(lo,hi)=row
    delta=0.0 if lo==hi==0.0 else round(random.uniform(lo,hi),4)
    desc=f"{nation['name']}: {label}  (trust {delta:+.1%})"
    return [{"turn":t,"year":y,"quarter":q,"label":label,"description":desc,
             "trust_delta":delta,"source":"auto","roll":roll,"col_rgb":[130,60,200]}]

# ── Discord corp profile ───────────────────────────────────────────────────────
def discord_corp_profile(nation,state):
    cd=nation.get("corporate_data",{}); trust=cd.get("trust",0.5)
    ipeu=nation.get("base_ipeu",0.0)
    prod_pct=cd.get("product_sale_pct",0.0); svc_pct=cd.get("service_income_pct",0.0)
    marketing_pct=cd.get("marketing_pct",0.0)
    locs=cd.get("locations") or []; contracts=cd.get("contracts") or []
    shareholders=cd.get("shareholders") or []; corp_events=cd.get("corp_events") or []
    base_product=ipeu*prod_pct*trust; base_service=ipeu*svc_pct*trust
    office_inc=0.0; factory_upkeep=0.0
    for loc in locs:
        if loc.get("status")!="active": continue
        typ=loc.get("type","office")
        if typ=="office":
            h=loc.get("host_ipeu",ipeu); tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
            fill=min(1.0,loc.get("employees",0)/max(1,loc.get("employee_cap",1)))
            office_inc+=h*tm*fill*trust-loc.get("upkeep",0.0)
        elif typ=="factory": factory_upkeep+=loc.get("upkeep",0.0)
    units_produced=compute_corp_factory_output(nation)
    store_inc,units_sold=compute_corp_store_sales(nation,units_produced)
    contract_inc=sum(c.get("value_per_turn",0.0) for c in contracts if c.get("status")=="active")
    loc_inc_total=office_inc+store_inc-factory_upkeep
    total_inc=base_product+base_service+loc_inc_total+contract_inc
    mktcap=compute_corp_market_cap(nation)

    def _fc(v):
        if v is None: return "\u2014"
        a=abs(v)
        if a>=1e15: return f"{v/1e15:.3f} Qcr"
        if a>=1e12: return f"{v/1e12:.3f} Tcr"
        if a>=1e9:  return f"{v/1e9:.3f} Bcr"
        if a>=1e6:  return f"{v/1e6:.3f} Mcr"
        if a>=1e3:  return f"{v/1e3:.2f} Kcr"
        return f"{v:.0f} cr"

    L=[]; A=L.append
    A("# CORPORATE")
    A(f"Trust: {_bar_str(trust)} {trust*100:.1f}%")
    A(f"Trust Value: {trust*100:.1f}%")
    A("")
    A("# CORPORATE ENTERPRISES")
    A("```")
    A(f"{'Base (IPEU * rate * trust)':<36}: {_fc(base_product+base_service)}")
    A(f"{'Location Income':<36}: {_fc(loc_inc_total)}")
    A(f"{'Active Contracts':<36}: {_fc(contract_inc)}")
    A(f"{'Product Sales Income':<36}: {_fc(base_product+store_inc)}")
    A(f"{'Service Income':<36}: {_fc(base_service)}")
    A("-"*54)
    A(f"{'TOTAL per turn':<36}: {_fc(total_inc)}")
    A(f"{'Market Capacity':<36}: {_fc(mktcap)}")
    A("```")
    A("")
    if locs:
        A("# LOCATIONS")
        for loc in locs:
            A(f"**{loc.get('name','?')}**")
            A("```")
            A(f"{'System':<28}: {loc.get('system','\u2014')}")
            A(f"{'Planet':<28}: {loc.get('planet','\u2014')}")
            A(f"{'Type':<28}: {loc.get('type','\u2014').title()}")
            A(f"{'Tier':<28}: {loc.get('tier','\u2014').title()}")
            A(f"{'Upkeep per turn':<28}: {_fc(loc.get('upkeep',0.0))}")
            A(f"{'Status':<28}: {loc.get('status','\u2014').title()}")
            typ=loc.get("type","")
            if typ in ("factory","store"):
                A("")
                A("PRODUCTION, SALES, MARKETING")
                if typ=="factory":
                    ov=loc.get("units_produced_override")
                    up=ov if ov is not None else int(loc.get("employees",0)*TIER_MULT.get(loc.get("tier","medium"),1.0))
                    A(f"{'- Product Produced':<28}: {up:,} units")
                    A(f"{'- Product Marketing':<28}: {marketing_pct*100:.1f}%")
                elif typ=="store":
                    tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
                    cap=loc.get("sell_capacity_override") or int(loc.get("employees",0)*tm)
                    sold_approx=min(units_produced,cap)
                    store_rev=sold_approx*loc.get("cr_per_unit",0.0)*trust
                    A(f"{'- Product Sold':<28}: {sold_approx:,} units & {_fc(store_rev)}")
                    A(f"{'- Product Marketing':<28}: {marketing_pct*100:.1f}%")
            A("```")
        A("")
    if shareholders:
        A("# SHAREHOLDERS & DIVIDENDS")
        for sh in shareholders:
            A(f"**{sh.get('name','?')}**")
            A("```")
            A(f"{'HELD':<28}: {sh.get('pct_held',0)*100:.1f}%")
            A(f"{'DIVIDEND RATE':<28}: {sh.get('dividend_rate',0)*100:.1f}%")
            A("```")
        div_total=sum(total_inc*sh.get("pct_held",0)*sh.get("dividend_rate",0) for sh in shareholders)
        A(f"Total Dividends per turn  : {_fc(div_total)}")
        A("")
    if contracts:
        A("# CLIENTS & CONTRACTS")
        for c in contracts:
            A(f"**{c.get('client','?')}**")
            A("```")
            A(f"{'Product / Service':<28}: {c.get('product','\u2014')}")
            A(f"{'Credits per turn':<28}: {_fc(c.get('value_per_turn',0.0))}")
            A(f"{'Status':<28}: {c.get('status','\u2014').title()}")
            A("```")
        A("")
    A("# CORPORATE EVENT LOG")
    if not corp_events:
        A("No events recorded.")
    else:
        A("```")
        for ev in reversed(corp_events[-10:]):
            src="[AUTO]" if ev.get("source")=="auto" else "[GM]  "
            A(f"T{ev.get('turn','?')} {src} {ev.get('label','?'):<20}  \u0394trust {ev.get('trust_delta',0):+.1%}")
            if ev.get("description"): A(f"      {ev.get('description','')}")
        A("```")
    return "\n".join(L)

# ── build_corp_rows ───────────────────────────────────────────────────────────
def build_corp_rows(nation,state,ipeu):
    _row=_C["_row"]; _btn=_C["_btn"]; _hdr1=_C["_hdr1"]; _hdr2=_C["_hdr2"]
    _sep=_C["_sep"]; _bar=_C["_bar"]
    G=_C["GREEN"]; R=_C["RED_C"]; GO=_C["GOLD"]; CY=_C["CYAN"]
    TE=_C["TEAL"]; BR=_C["BRIGHT"]; DI=_C["DIM"]; PU=_C["PURPLE"]

    cd=nation.get("corporate_data",{}); trust=cd.get("trust",0.5)
    tc=G if trust>0.7 else (GO if trust>0.4 else R)
    corp_inc=compute_corp_income(nation); mktcap=compute_corp_market_cap(nation)
    prod_pct=cd.get("product_sale_pct",0.0); svc_pct=cd.get("service_income_pct",0.0)
    marketing_pct=cd.get("marketing_pct",0.0)
    locs=cd.get("locations") or []; contracts=cd.get("contracts") or []
    shareholders=cd.get("shareholders") or []

    base_product=ipeu*prod_pct*trust; base_service=ipeu*svc_pct*trust
    office_inc=0.0; factory_upkeep=0.0
    for loc in locs:
        if loc.get("status")!="active": continue
        typ=loc.get("type","office")
        if typ=="office":
            h=loc.get("host_ipeu",ipeu); tm=TIER_MULT.get(loc.get("tier","medium"),1.0)
            fill=min(1.0,loc.get("employees",0)/max(1,loc.get("employee_cap",1)))
            office_inc+=h*tm*fill*trust-loc.get("upkeep",0.0)
        elif typ=="factory": factory_upkeep+=loc.get("upkeep",0.0)
    units_produced=compute_corp_factory_output(nation)
    store_inc,units_sold=compute_corp_store_sales(nation,units_produced)
    contract_inc=sum(c.get("value_per_turn",0.0) for c in contracts if c.get("status")=="active")

    rows=[]
    rows+=[_hdr1("CORPORATE PROFILE"),
           _row("Entity",nation.get("corp_entity_name",nation["name"]),["corp_entity_name"],"str",BR),
           _sep(),_bar("  TRUST",trust,f"{trust*100:.1f}%",tc),
           _row("  Trust Value",f"{trust*100:.1f}%",["corporate_data","trust"],"pct",tc),
           _sep(),_hdr2("CORPORATE ENTERPRISES"),
           _row("  Product Sale %",f"{prod_pct*100:.1f}%",["corporate_data","product_sale_pct"],"pct",CY),
           _row("  Service Income %",f"{svc_pct*100:.1f}%",["corporate_data","service_income_pct"],"pct",TE),
           _row("  Marketing %",f"{marketing_pct*100:.1f}%",["corporate_data","marketing_pct"],"pct",GO),
           _sep(),_hdr2("CORP INCOME SUMMARY"),
           _row("  Base Product",_fcr(base_product),vcol=G),
           _row("  Base Service",_fcr(base_service),vcol=TE),
           _row("  Office Income",_fcr(office_inc),vcol=CY),
           _row("  Store Income (unit sales)",_fcr(store_inc),vcol=CY),
           _row("  Factory Upkeep",_fcr(-factory_upkeep),vcol=R),
           _row("  Active Contracts",_fcr(contract_inc),vcol=TE),
           _row("  TOTAL / turn",_fcr(corp_inc),vcol=BR),
           _row("  Market Cap",_fcr(mktcap),vcol=GO),
           _sep(),_hdr2("PRODUCTION TOTALS"),
           _row("  Units Produced / turn",f"{units_produced:,}",vcol=G),
           _row("  Units Sold / turn",f"{units_sold:,}",vcol=CY),
           _sep(),_hdr2("LOCATIONS"),
           _btn("  + New Location","open_new_location",{},(20,55,30)),
           _btn("  Corp Graphs","open_corp_graph",{},(40,20,70))]

    if not locs: rows.append(_row("  No locations registered","",vcol=DI))
    for li,loc in enumerate(locs):
        cap=max(1,loc.get("employee_cap",1))
        fill2=min(1.0,loc.get("employees",0)/cap)
        typ=loc.get("type","office")
        sc=G if loc.get("status")=="active" else (GO if loc.get("status")=="under construction" else R)
        sys_pl=f"{loc.get('system','?')[:12]}/{loc.get('planet','?')[:12]}"
        rows+=[_row(f"  [{typ.upper()[:3]}] {loc.get('name','?')[:22]}  {sys_pl}",
                    f"{loc.get('tier','?')}  {fill2*100:.0f}%fill  [{loc.get('status','?')}]",vcol=sc),
               _row(f"    Emp: {loc.get('employees',0)}/{cap}  Upkeep: {_fcr(loc.get('upkeep',0.0))}/t","",vcol=DI)]
        if typ=="factory":
            up=loc.get("units_produced_override") or int(loc.get("employees",0)*TIER_MULT.get(loc.get("tier","medium"),1.0))
            rows.append(_row(f"    Produces: {up:,} units/t","",vcol=G))
        elif typ=="store":
            rows.append(_row(f"    cr/unit: {_fcr(loc.get('cr_per_unit',0.0))}","",vcol=CY))
        rows+=[_btn("    Edit","edit_location",{"li":li},(16,32,52)),
               _btn("    Remove","remove_location",{"li":li},(60,18,18))]

    rows+=[_sep(),_hdr2("SHAREHOLDERS & DIVIDENDS")]
    div_total=0.0
    if not shareholders: rows.append(_row("  No shareholders on record","",vcol=DI))
    for si,sh in enumerate(shareholders):
        div=corp_inc*sh.get("pct_held",0.0)*sh.get("dividend_rate",0.0); div_total+=div
        rows+=[_row(f"  {sh.get('name','?')[:28]}",f"{sh.get('pct_held',0)*100:.1f}% held  div {sh.get('dividend_rate',0)*100:.1f}%  -> {_fcr(div)}/t",vcol=CY),
               _btn("    Remove Shareholder","remove_shareholder",{"si":si},(60,18,18))]
    rows+=[_row("  Total Dividends / turn",_fcr(div_total),vcol=R),
           _btn("  + Add Shareholder","open_add_shareholder",{},(20,55,30)),
           _sep(),_hdr2("CLIENTS & CONTRACTS")]

    if not contracts: rows.append(_row("  No active contracts","",vcol=DI))
    for ci,c in enumerate(contracts):
        sc2=G if c.get("status")=="active" else (GO if c.get("status")=="pending" else R)
        rows+=[_row(f"  [{c.get('client','?')[:20]}]",f"{c.get('product','?')}  {_fcr(c.get('value_per_turn',0))}/t  [{c.get('status','?')}]",vcol=sc2),
               _btn("    Edit Contract","edit_corp_contract",{"ci":ci},(16,32,52)),
               _btn("    End Contract","end_corp_contract",{"ci":ci},(60,18,18))]
    rows+=[_btn("  + New Contract","open_corp_contract",{},(20,55,30)),
           _sep(),_hdr2("CORP EVENTS LOG"),
           _btn("  + Log Event","open_corp_event_log",{},(20,55,30))]

    corp_evs=cd.get("corp_events") or []
    if not corp_evs: rows.append(_row("  No corp events recorded","",vcol=DI))
    for cevi,cev in enumerate(reversed(corp_evs[-20:])):
        ri=len(corp_evs)-1-cevi
        col3=G if cev.get("trust_delta",0)>0 else (R if cev.get("trust_delta",0)<0 else DI)
        stag="[AUTO]" if cev.get("source")=="auto" else "[GM]"
        rows+=[_row(f"  T{cev.get('turn','?')} {stag} {cev.get('label','?')[:24]}",f"trust {cev.get('trust_delta',0):+.1%}  {cev.get('description','')[:30]}",vcol=col3),
               _btn("    Remove Corp Event","remove_corp_event",{"cevi":ri},(60,18,18))]

    rows+=[_sep(),_hdr2("CORPORATE REPUTATION")]
    for ev2 in (cd.get("reputation_log") or [])[-8:]:
        col4=G if ev2.get("delta",0)>0 else R
        rows.append(_row(f"  T{ev2.get('turn','?')} {ev2.get('label','?')[:30]}",f"{ev2.get('delta',0):+.1f}%",vcol=col4))
    if not (cd.get("reputation_log") or []): rows.append(_row("  No reputation events","",vcol=DI))
    return rows

# ── Overlays ──────────────────────────────────────────────────────────────────

def _overlay_bg(surf,border_col):
    BG=_C["BG"]; SW=_C["SW"]; SH=_C["SH"]; MX=_C["MAIN_X"]; MY=_C["MAIN_Y"]; SBH=_C["SBAR_H"]
    rx=MX; ry=MY; rw=SW-MX; rh=SH-MY-SBH
    _dr(surf,pygame.Rect(rx,ry,rw,rh),(5,10,20))
    _dr(surf,pygame.Rect(rx,ry,rw,rh),border_col,border=2)
    return rx,ry,rw,rh

def _field_rows(surf,fields,field_idx,blink,rx,ry,y0,border_col):
    BG=_C["BG"]; SEL=_C["SEL"]; BR=_C["BRIGHT"]; DI=_C["DIM"]; TX=_C["TEXT"]; CY=_C["CYAN"]
    y=y0
    for i,f in enumerate(fields):
        sel=(i==field_idx); rr=pygame.Rect(rx+4,y,_C["SW"]-_C["MAIN_X"]-8,22)
        _dr(surf,rr,SEL if sel else((10,18,28) if i%2==0 else BG),radius=2)
        if sel: _dr(surf,rr,border_col,border=1,radius=2)
        _dt(surf,f["label"],rx+14,y+4,_gf(11),BR if sel else DI)
        if f["type"]=="choice": _dt(surf,f"\u25c4 {f['opts'][f['val']]} \u25ba",rx+300,y+4,_gf(11),CY if sel else TX)
        else:
            cur="\u258e" if (sel and blink<0.5) else ""
            _dt(surf,f["val"]+cur,rx+300,y+4,_gf(11),border_col if sel else TX)
        y+=24
    return y

def _field_event(ev,fields,field_idx):
    f=fields[field_idx]
    if f["type"]=="choice":
        if ev.key==pygame.K_LEFT: f["val"]=(f["val"]-1)%len(f["opts"])
        elif ev.key==pygame.K_RIGHT: f["val"]=(f["val"]+1)%len(f["opts"])
    elif f["type"] in ("text","float","int"):
        if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
        elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode


class LocationSearcherOverlay:
    """Scans all nations' star_systems to pick system+planet for a location."""
    def __init__(self): self.active=False; self._entries=[]; self._scroll=0; self._sel=0; self._free=""; self._free_mode=False
    def open(self,state):
        self.active=True; self._entries=[]; self._scroll=0; self._sel=0; self._free=""; self._free_mode=False
        for n in state.get("nations",[]):
            for sys in (n.get("star_systems") or []):
                sn=sys.get("name","?")
                for pl in (sys.get("planets") or []):
                    self._entries.append({"nation":n["name"],"system":sn,"planet":pl.get("name","?")})
        self._entries.append({"_free":True})
    def close(self): self.active=False
    def _selected(self):
        if self._free_mode:
            parts=self._free.split("/",1)
            return (parts[0].strip(), parts[1].strip() if len(parts)>1 else "")
        if 0<=self._sel<len(self._entries)-1:
            e=self._entries[self._sel]; return (e["system"],e["planet"])
        return ("","")
    def draw(self,surf):
        if not self.active: return
        CY=_C["CYAN"]; BR=_C["BRIGHT"]; DI=_C["DIM"]; TX=_C["TEXT"]; GO=_C["GOLD"]; SEL=_C["SEL"]; BG=_C["BG"]
        SW=_C["SW"]; SH=_C["SH"]; MX=_C["MAIN_X"]; MY=_C["MAIN_Y"]; SBH=_C["SBAR_H"]
        rx=MX; ry=MY; rw=SW-MX; rh=SH-MY-SBH
        _dr(surf,pygame.Rect(rx,ry,rw,rh),(5,10,20)); _dr(surf,pygame.Rect(rx,ry,rw,rh),CY,border=2)
        _dt(surf,"LOCATION SEARCHER",rx+12,ry+7,_gf(13),BR)
        _dt(surf,"Up/Down=select  Enter=confirm  F=free text mode  Esc=cancel",rx+12,ry+24,_gf(10),DI)
        vis=18; y=ry+48
        for i in range(self._scroll,min(len(self._entries),self._scroll+vis)):
            e=self._entries[i]; sel=(i==self._sel)
            rr=pygame.Rect(rx+4,y,rw-8,18)
            _dr(surf,rr,SEL if sel else ((10,18,28) if i%2==0 else BG),radius=2)
            if sel: _dr(surf,rr,CY,border=1,radius=2)
            if e.get("_free"): _dt(surf,"  [ Manual entry — press F ]",rx+14,y+2,_gf(10),GO if sel else DI)
            else:
                txt=f"  {e['system']:<22} / {e['planet']:<22}  ({e['nation'][:18]})"
                _dt(surf,txt,rx+14,y+2,_gf(10),BR if sel else TX)
            y+=20
        if self._free_mode:
            _dr(surf,pygame.Rect(rx+4,ry+rh-30,rw-8,24),(5,14,28)); _dr(surf,pygame.Rect(rx+4,ry+rh-30,rw-8,24),GO,border=1)
            _dt(surf,f"  System / Planet : {self._free}\u258e",rx+14,ry+rh-26,_gf(11),GO)
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_f and not self._free_mode: self._free_mode=True; return None
            if self._free_mode:
                if ev.key==pygame.K_RETURN: r=self._selected(); self.close(); return r
                elif ev.key==pygame.K_BACKSPACE: self._free=self._free[:-1]
                elif ev.unicode and ev.unicode.isprintable(): self._free+=ev.unicode
            else:
                if ev.key==pygame.K_UP:
                    self._sel=max(0,self._sel-1); self._scroll=min(self._scroll,self._sel)
                elif ev.key==pygame.K_DOWN:
                    self._sel=min(len(self._entries)-1,self._sel+1)
                    if self._sel>=self._scroll+18: self._scroll+=1
                elif ev.key==pygame.K_RETURN:
                    if self._entries[self._sel].get("_free"): self._free_mode=True
                    else: r=self._selected(); self.close(); return r
        return None


class ContractBuilderOverlay:
    def __init__(self): self.active=False; self.mode="new"; self.contract_idx=-1; self.fields=[]; self.field_idx=0; self._blink=0.0
    def _init(self,c):
        sid=_CONTRACT_ST.index(c.get("status","active")) if c.get("status","active") in _CONTRACT_ST else 0
        self.fields=[{"key":"client","label":"Client","type":"text","val":c.get("client","")},
                     {"key":"product","label":"Product / Service","type":"text","val":c.get("product","")},
                     {"key":"value_per_turn","label":"Credits / Turn","type":"float","val":str(c.get("value_per_turn",0.0))},
                     {"key":"status","label":"Status","type":"choice","val":sid,"opts":_CONTRACT_ST}]; self.field_idx=0
    def open_new(self): self.active=True; self.mode="new"; self.contract_idx=-1; self._init({})
    def open_edit(self,c,idx): self.active=True; self.mode="edit"; self.contract_idx=idx; self._init(c)
    def close(self): self.active=False
    def get_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            else: d[f["key"]]=f["val"]
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx,ry,rw,rh=_overlay_bg(surf,_C["EDITBDR"])
        lbl="NEW CONTRACT" if self.mode=="new" else f"EDIT CONTRACT [{self.contract_idx}]"
        _dt(surf,lbl,rx+12,ry+7,_gf(13),_C["BRIGHT"])
        _dt(surf,"Up/Down=field  L/R=cycle  Type=edit  Enter=save  Esc=cancel",rx+12,ry+24,_gf(10),_C["DIM"])
        _field_rows(surf,self.fields,self.field_idx,self._blink,rx,ry,ry+48,_C["EDITBDR"])
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            elif ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            else: _field_event(ev,self.fields,self.field_idx)
        return None


class LocationBuilderOverlay:
    def __init__(self): self.active=False; self.mode="new"; self.loc_idx=-1; self.fields=[]; self.field_idx=0; self._blink=0.0; self._open_searcher=False
    def _init(self,loc):
        typ=loc.get("type","office"); tier=loc.get("tier","medium"); status=loc.get("status","active")
        tid=_TYPE_OPTS.index(typ) if typ in _TYPE_OPTS else 0
        tirid=_TIER_OPTS.index(tier) if tier in _TIER_OPTS else 2
        sid=_LOC_STATUS.index(status) if status in _LOC_STATUS else 0
        self.fields=[
            {"key":"system",       "label":"System",                   "type":"text",  "val":loc.get("system","")},
            {"key":"planet",       "label":"Planet",                   "type":"text",  "val":loc.get("planet","")},
            {"key":"name",         "label":"Facility Name",            "type":"text",  "val":loc.get("name","New Facility")},
            {"key":"type",         "label":"Type",                     "type":"choice","val":tid,   "opts":_TYPE_OPTS},
            {"key":"tier",         "label":"Tier",                     "type":"choice","val":tirid, "opts":_TIER_OPTS},
            {"key":"host_ipeu",    "label":"Host System IPEU",         "type":"float", "val":str(loc.get("host_ipeu",0.0))},
            {"key":"employees",    "label":"Employees",                "type":"int",   "val":str(loc.get("employees",0))},
            {"key":"employee_cap", "label":"Employee Cap",             "type":"int",   "val":str(loc.get("employee_cap",100))},
            {"key":"upkeep",       "label":"Upkeep / Turn (cr)",       "type":"float", "val":str(loc.get("upkeep",0.0))},
            {"key":"cr_per_unit",  "label":"cr / unit  (stores only)", "type":"float", "val":str(loc.get("cr_per_unit",0.0))},
            {"key":"status",       "label":"Status",                   "type":"choice","val":sid,   "opts":_LOC_STATUS},
        ]; self.field_idx=0; self._open_searcher=False
    def open_new(self,default_ipeu=0.0): self.active=True; self.mode="new"; self.loc_idx=-1; self._init({"host_ipeu":default_ipeu})
    def open_edit(self,loc,idx): self.active=True; self.mode="edit"; self.loc_idx=idx; self._init(loc)
    def close(self): self.active=False
    def set_location(self,system,planet):
        for f in self.fields:
            if f["key"]=="system": f["val"]=system
            elif f["key"]=="planet": f["val"]=planet
    def get_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            elif f["type"]=="int":
                try: d[f["key"]]=int(f["val"])
                except: d[f["key"]]=0
            else: d[f["key"]]=f["val"]
        d.setdefault("id",f"loc_{uuid.uuid4().hex[:6]}"); return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx,ry,rw,rh=_overlay_bg(surf,_C["EDITBDR"])
        lbl="NEW LOCATION" if self.mode=="new" else f"EDIT LOCATION [{self.loc_idx}]"
        _dt(surf,lbl,rx+12,ry+7,_gf(13),_C["BRIGHT"])
        _dt(surf,"Up/Down=field  L/R=cycle  Type=edit  S=search planet  Enter=save  Esc=cancel",rx+12,ry+22,_gf(10),_C["DIM"])
        tier_val=self.fields[4]["opts"][self.fields[4]["val"]] if len(self.fields)>4 else "medium"
        tm=TIER_MULT.get(tier_val,"?")
        _dt(surf,f"Office: IPEU x {tm} x fill x trust   |   Store: units_sold x cr/unit x trust x office_boost   |   Factory: employees x {tm} units/t",rx+12,ry+34,_gf(9),_C["GOLD"])
        _field_rows(surf,self.fields,self.field_idx,self._blink,rx,ry,ry+50,_C["EDITBDR"])
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_s:
                self._open_searcher=True; return None
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            elif ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            else: _field_event(ev,self.fields,self.field_idx)
        return None


class ShareholderBuilderOverlay:
    def __init__(self): self.active=False; self.mode="new"; self.sh_idx=-1; self.fields=[]; self.field_idx=0; self._blink=0.0
    def _init(self,sh):
        self.fields=[{"key":"name","label":"Shareholder Name","type":"text","val":sh.get("name","")},
                     {"key":"pct_held","label":"% Held (0.0-1.0)","type":"float","val":str(sh.get("pct_held",0.0))},
                     {"key":"dividend_rate","label":"Dividend Rate (0.0-1.0)","type":"float","val":str(sh.get("dividend_rate",0.05))}]
        self.field_idx=0
    def open_new(self): self.active=True; self.mode="new"; self.sh_idx=-1; self._init({})
    def open_edit(self,sh,idx): self.active=True; self.mode="edit"; self.sh_idx=idx; self._init(sh)
    def close(self): self.active=False
    def get_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            else: d[f["key"]]=f["val"]
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx,ry,rw,rh=_overlay_bg(surf,_C["GOLD"])
        _dt(surf,"ADD SHAREHOLDER" if self.mode=="new" else f"EDIT SHAREHOLDER [{self.sh_idx}]",rx+12,ry+7,_gf(13),_C["BRIGHT"])
        _dt(surf,"Up/Down=field  Type=edit  Enter=save  Esc=cancel",rx+12,ry+24,_gf(10),_C["DIM"])
        _field_rows(surf,self.fields,self.field_idx,self._blink,rx,ry,ry+48,_C["GOLD"])
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            elif ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            else: _field_event(ev,self.fields,self.field_idx)
        return None


class CorpEventBuilderOverlay:
    def __init__(self): self.active=False; self.fields=[]; self.field_idx=0; self._blink=0.0
    def open(self):
        self.active=True
        self.fields=[{"key":"label","label":"Event Label","type":"text","val":""},
                     {"key":"description","label":"Description","type":"text","val":""},
                     {"key":"trust_delta","label":"Trust Delta (e.g. -0.05)","type":"float","val":"0.0"}]
        self.field_idx=0
    def close(self): self.active=False
    def get_data(self,state):
        d={"source":"manual"}
        for f in self.fields:
            if f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            else: d[f["key"]]=f["val"]
        d["turn"]=state.get("turn",1); d["year"]=state.get("year",2200); d["quarter"]=state.get("quarter",1); d["roll"]="GM"
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx,ry,rw,rh=_overlay_bg(surf,_C["PURPLE"])
        _dt(surf,"LOG CORP EVENT",rx+12,ry+7,_gf(13),_C["BRIGHT"])
        _dt(surf,"Up/Down=field  Type=edit  Enter=save  Esc=cancel",rx+12,ry+24,_gf(10),_C["DIM"])
        _field_rows(surf,self.fields,self.field_idx,self._blink,rx,ry,ry+48,_C["PURPLE"])
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            elif ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            else: _field_event(ev,self.fields,self.field_idx)
        return None


class CorpGraphOverlay:
    _VIEWS=["TRUST","INCOME","MARKET CAP","CONTRACTS VALUE","EMPLOYEES","LOCATIONS"]
    _KEY_MAP={"TRUST":"trust","INCOME":"income","MARKET CAP":"market_cap","CONTRACTS VALUE":"contracts_value","EMPLOYEES":"employees","LOCATIONS":"location_count"}
    def __init__(self): self.active=False; self.view_idx=0
    def open(self): self.active=True; self.view_idx=0
    def close(self): self.active=False
    def draw(self,surf,nation):
        if not self.active or not nation: return
        BR=_C["BRIGHT"]; DI=_C["DIM"]; GO=_C["GOLD"]; BG=_C["BG"]; SEL=_C["SEL"]
        SW=_C["SW"]; SH=_C["SH"]; MX=_C["MAIN_X"]; MY=_C["MAIN_Y"]; SBH=_C["SBAR_H"]
        cd=nation.get("corporate_data",{}); hist=cd.get("corp_history",[])
        rx=MX; ry=MY; rw=SW-MX; rh=SH-MY-SBH
        _dr(surf,pygame.Rect(rx,ry,rw,rh),(4,8,16)); _dr(surf,pygame.Rect(rx,ry,rw,rh),GO,border=2)
        view=self._VIEWS[self.view_idx]
        _dt(surf,f"CORP GRAPH  \u2014  {nation['name']}  \u2014  {view}",rx+10,ry+6,_gf(13),BR)
        _dt(surf,"Left/Right=switch  E=export PNG  Esc=close",rx+10,ry+22,_gf(10),DI)
        tw2=rw//len(self._VIEWS)
        for i,v in enumerate(self._VIEWS):
            sel=(i==self.view_idx); _dr(surf,pygame.Rect(rx+i*tw2,ry+rh-22,tw2,20),SEL if sel else BG)
            _dt(surf,v,rx+i*tw2+3,ry+rh-20,_gf(10),BR if sel else DI)
        if not hist: _dt(surf,"No corp history yet \u2014 advance a turn to record.",rx+10,ry+50,_gf(11),DI); return
        key=self._KEY_MAP.get(view,"trust"); vals=[h.get(key,0.0) for h in hist]; turns=[h.get("turn",i+1) for i,h in enumerate(hist)]
        if len(vals)<2: _dt(surf,"Need >=2 turns of corp data.",rx+10,ry+50,_gf(11),DI); return
        mx=max(vals) or 1.0; mn=min(0,min(vals)); px0=rx+48; py0=ry+46; pw=rw-64; ph=rh-96
        _dr(surf,pygame.Rect(px0,py0,pw,ph),(6,12,22))
        for pct in [0.0,0.25,0.5,0.75,1.0]:
            yy=py0+ph-int(pct*ph); val=mn+(mx-mn)*pct
            pygame.draw.line(surf,(20,40,60),(px0,yy),(px0+pw,yy))
            lbl=f"{val*100:.0f}%" if view=="TRUST" else (str(int(val)) if view in ("EMPLOYEES","LOCATIONS") else _fcr(val))
            _dt(surf,lbl,rx+2,yy-5,_gf(10),DI)
        n2=len(vals); pts=[(px0+int(i/(n2-1)*pw),py0+ph-int((v-mn)/(mx-mn)*ph)) for i,v in enumerate(vals)]
        if len(pts)>1: pygame.draw.lines(surf,GO,False,pts,2)
        for x,y in pts: pygame.draw.circle(surf,BR,(x,y),3)
        step=max(1,n2//8)
        for i in range(0,n2,step):
            x=px0+int(i/(n2-1)*pw); _dt(surf,f"T{turns[i]}",x-8,py0+ph+2,_gf(10),DI)
        cur=vals[-1]; cv=f"{cur*100:.1f}%" if view=="TRUST" else (str(int(cur)) if view in ("EMPLOYEES","LOCATIONS") else _fcr(cur))
        _dt(surf,f"Latest: {cv}",rx+10,ry+rh-36,_gf(11),BR)
    def export_png(self,surf,nation):
        try:
            od=Path("discord_exports"); od.mkdir(exist_ok=True)
            name=nation.get("name","unknown").replace(" ","_"); view=self._VIEWS[self.view_idx].replace(" ","_")
            fname=od/f"corp_graph_{name}_{view}.png"
            SW=_C["SW"]; MX=_C["MAIN_X"]; MY=_C["MAIN_Y"]; SH=_C["SH"]; SBH=_C["SBAR_H"]
            sub=surf.subsurface(pygame.Rect(MX,MY,SW-MX,SH-MY-SBH))
            pygame.image.save(sub,str(fname)); return str(fname)
        except Exception as e: return f"[export error] {e}"
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close()
            elif ev.key==pygame.K_LEFT: self.view_idx=(self.view_idx-1)%len(self._VIEWS)
            elif ev.key==pygame.K_RIGHT: self.view_idx=(self.view_idx+1)%len(self._VIEWS)
            elif ev.key==pygame.K_e: return "export"
        return None
