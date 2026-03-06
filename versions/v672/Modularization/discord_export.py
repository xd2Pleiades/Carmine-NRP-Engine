"""carmine.discord_export — Discord-formatted nation and market reports"""
from constants import *
from economy import (compute_resources, compute_trade, compute_planet_local_market,
                     compute_resource_export_credits, compute_debt, compute_gtc_debt,
                     compute_church_tithe, compute_tithe_income, spending_effects,
                     compute_military_consumption, compute_manpower, compute_galactic_stockpiles,
                     compute_vessel_resources, get_colony_progress, compute_subsidies,
                     econ_model_ipeu_modifier, price_shock_delta, _price_explain,
                     is_colony, years_elapsed, fmt_cr, fmt_pop,
                     fmt_res, fmt_pct, bar_str, nation_tag, RES_BASE_PRICE)
from constants import _avg_loyalty, _RESOURCES
from events import _MARKET_SHOCK
from corporateAlpha0671 import discord_corp_profile

# ── discord export ────────────────────────────────────────────────────────────
def _discord_export(nation,state):
    DISCORD_DIR.mkdir(exist_ok=True)
    SEP="  " + "─"*57
    ye=years_elapsed(state); ipeu=nation.get("base_ipeu",0.0)
    pop=nation.get("population",0.0)*(1.0+nation.get("pop_growth",0.0))**ye
    exp=nation.get("expenditure",{}) if isinstance(nation.get("expenditure"),dict) else {}
    routes=state.get("trade_routes",[]); trade=compute_trade(nation,routes)
    export_cr=compute_resource_export_credits(nation,state)
    rb=nation.get("research_budget",0.0); sfund=nation.get("strategic_fund",0.0)
    species=nation.get("species_populations",[]) or []; star_sys=nation.get("star_systems",[]) or []
    afd=nation.get("active_forces_detail",[]) or []
    ugroups={ug["ugid"]:ug for ug in (nation.get("unit_groups") or [])}
    active_r=nation.get("active_research_projects",[]) or []; done_r=nation.get("completed_techs",[]) or []
    eproj=nation.get("economic_projects") or []
    qtr=state.get("quarter",1); year=state.get("year",2200); turn=state.get("turn",1)
    tag=nation_tag(nation["name"]); homeworld="N/A"
    for sys in star_sys:
        for pl in sys.get("planets",[]): homeworld=pl.get("name","N/A"); break
        break
    L=[]; A=L.append

    # ── HEADER ────────────────────────────────────────────────────────────────
    A(f"-# [{tag}] {nation['name'].upper()}")
    A(f"# NATIONAL PROFILE - Q{qtr} [{year}]"); A("```")
    for s in species:
        A(f"  Species          : {s['name']} ({s.get('population_share',0)*100:.1f}%)")
    if not species: A("  Species          : N/A")
    A(f"  Population       : {fmt_pop(pop)}")
    A(f"  Pop Growth       : {fmt_pct(nation.get('pop_growth',0))} / yr")
    A(f"  Homeworld        : {homeworld}")
    A(f"  Civilisation     : {nation.get('civ_level','N/A')}")
    A(f"  Tier             : {nation.get('civ_tier','N/A')}")
    A(f"  Economic Model   : {nation.get('economic_model','MIXED')}")
    A(f"  Status           : {nation.get('eco_status','Stable')}"); A("```")

    # ── COLONY PATH ───────────────────────────────────────────────────────────
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
        # ── ECONOMY ───────────────────────────────────────────────────────────
        res=compute_resources(nation,ipeu); debt=compute_debt(nation,ipeu)
        _,tax_inc=compute_planet_local_market(nation,state,ipeu)
        eff=spending_effects(nation,ipeu)
        total_exp=sum(exp.values())*ipeu+rb
        tithe=compute_church_tithe(nation,state)
        tithe_in=compute_tithe_income(nation,state)
        net_bal=ipeu+trade["net"]+tax_inc+tithe_in-total_exp-debt["q_interest"]-tithe
        gtc_e=compute_gtc_debt(nation,state)
        gtc_qi=gtc_e.get("balance",0.0)*gtc_e.get("interest_rate",0.04)/4.0 if gtc_e else 0.0
        per_cap=int(ipeu/pop) if pop else 0
        mil_cons=compute_military_consumption(nation)
        econ=nation.get("economic_model","MIXED")
        A("# ECONOMY"); A("```")
        A(f"  IPEU (base)      : {fmt_cr(ipeu)}")
        A(f"  IPEU Growth      : {fmt_pct(nation.get('ipeu_growth',0))} / yr")
        A(f"  IPEU per Capita  : {per_cap:,} cr")
        A(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
        A(f"   - Exports       : {fmt_cr(trade['exports'])}")
        A(f"   - Imports       : {fmt_cr(trade['imports'])}")
        A(f"   - Transit       : {fmt_cr(trade['transit_income'])}")
        A(f"  Local Mrket Tax  : {fmt_cr(tax_inc)}")
        if tithe_in>0: A(f"  Tithe Income     : +{fmt_cr(tithe_in)}")
        if tithe>0:    A(f"  Church Tithe     : -{fmt_cr(tithe)}")
        if debt["q_interest"]>0: A(f"  Qrtly Intr Pymt  : -{fmt_cr(debt['q_interest'])}")
        if gtc_qi>0:   A(f"  GTC Interest     : -{fmt_cr(gtc_qi)}")
        A(f"  Total Expenditure: {fmt_cr(total_exp)}")
        A(f"  Research Budget  : {fmt_cr(rb)} / turn")
        A(f"  Net Balance      : {fmt_cr(net_bal)}"); A("```")

        # ── EXPENDITURE ───────────────────────────────────────────────────────
        A("## EXPENDITURE & BREAKDOWN"); A("```")
        mx=max(exp.values(),default=0.01)
        for cat,pct in exp.items():
            A(f"  {cat:<24} {pct*100:5.1f}%  {bar_str(pct/mx,20)}  {fmt_cr(pct*ipeu)}")
        A(SEP)
        A(f"  {'TOTAL':<24} {sum(exp.values())*100:5.1f}%{'':>22}  ({fmt_cr(total_exp)})")
        A("```")
        A("### SPENDING EFFECTS"); A("```")
        A(f"  Infra Trade Bonus      : +{eff['infra_trade_bonus']:.1f}% attractiveness")
        A(f"  PopDev Growth          : +{eff['popdev_growth_bonus']:.3f}% / yr")
        A(f"  Military Morale        : +{eff['mil_morale_bonus']:.1f}%")
        A(f"  Combat Power           : {eff['mil_combat_power']:.3f} Tcr  (10B cr = 1 CP)")
        A("```")
        if econ in ("PLANNED","MIXED"):
            loy=_avg_loyalty(nation)
            A("# PLANNED DISTRIBUTION & EFFICIENCY"); A("```")
            A(f"  Avg Loyalty            : {loy:.1f} / 100")
            A(f"  Resource Eff           : {100*(1.0+max(0,loy-50)/200):.1f}%")
            A(f"  Construction Eff       : N/A")
            A(f"  Research Eff           : N/A"); A("```")
        if econ in ("MARKET","MIXED"):
            planet_markets,_=compute_planet_local_market(nation,state,ipeu)
            A("# MARKET LOCAL PLANET OUTPUT"); A("```")
            for pm in planet_markets[:8]:
                A(f"  {pm.get('planet','?'):<28}: Attr: {pm.get('attractiveness',0):.2f}  Tax: {fmt_cr(pm.get('tax',0))}")
            eco_mod=econ_model_ipeu_modifier(nation)
            subs,invest=compute_subsidies(nation,ipeu)
            A(f"  Subsidy Cost           : {fmt_cr(subs)}")
            A(f"  Investment             : {fmt_cr(invest)}")
            A(f"  Investment Bonus       : x{eco_mod:.3f}"); A("```")

        # ── ECONOMIC PROJECTS ─────────────────────────────────────────────────
        if eproj:
            A("## ECONOMIC PROJECTS"); A("```")
            for ep in eproj:
                nm=ep.get("name","?"); rem=ep.get("turns_remaining",0)
                ben=ep.get("benefit",""); A(f"  {nm}  ({rem}t remaining)  {ben}")
            A(SEP); A("```")

        # ── FISCAL REPORT ─────────────────────────────────────────────────────
        A("## FISCAL REPORT"); A("```")
        dc_lbl="Debtor" if debt["is_debtor"] else "Creditor (GALACTIC TRADE CONFEDERATION)" if not debt["is_debtor"] else "Creditor"
        A(f"  Debtor / Creditor    : {dc_lbl}")
        A(f"  Debt Balance         : {fmt_cr(debt['balance'])}")
        load_bar=bar_str(min(1.0,debt['load_pct']/100),20)
        A(f"  Debt Load            : {debt['load_pct']:.1f}% of IPEU  {load_bar}")
        A(f"  Interest Rate        : {debt['rate']*100:.2f}%")
        A(f"  Quarterly Int.       : {fmt_cr(debt['q_interest'])}")
        A(f"  Debt Repayment       : {fmt_cr(debt['repayment'])}")
        if gtc_e:
            A("")
            A(f"  GTC Debt Balance     : {fmt_cr(gtc_e.get('balance',0.0))}")
            A(f"  GTC Rate             : {gtc_e.get('interest_rate',0.04)*100:.2f}% p.a.")
            A(f"  GTC Quarterly Int.   : {fmt_cr(gtc_qi)}")
            A(f"  GTC Since            : Turn {gtc_e.get('since_turn',1)}")
        A(SEP)
        sf_delta=-debt["q_interest"]-gtc_qi
        A(f"  Strategic Fund       : {fmt_cr(sfund)}")
        A(f"  Fund increase / turn : {('+' if sf_delta>=0 else '')}{fmt_cr(sf_delta)}"); A("```")

        # ── RESOURCES & STOCKPILES ────────────────────────────────────────────
        A("## RESOURCES & STOCKPILES")
        for rname in _RESOURCES:
            rd=res[rname]; ns=f"+{fmt_res(rd['net'])}" if rd["net"]>=0 else fmt_res(rd["net"])
            exc=export_cr.get(rname,0.0); A("```")
            A(f"  {rname} Stockpile            : {fmt_res(rd['stockpile'])}")
            A(f"  {rname} Production per turn  : {fmt_res(rd['production'])}")
            A(f"  {rname} Consumption per turn : {fmt_res(rd['consumption'])}")
            A(f"  {rname} Net per turn         : {ns}")
            A(f"  {rname} Trend                : {rd['trend']}")
            A(f"  {rname} Export               : {fmt_cr(exc)}"); A("```")

    # ── TERRITORIES ───────────────────────────────────────────────────────────
    A("# TERRITORIES"); A("```")
    for sys in star_sys:
        A(f"  Home System: {sys.get('name','?')}")
        A(f"  Planets:")
        for pl in sys.get("planets",[]):
            A(f"      - {pl.get('name','?')} Planet")
            A(f"        Type          : {pl.get('planet_type','?')}")
            A(f"        Size          : {pl.get('size','?')}")
            A(f"        Habitability  : {pl.get('habitability','?')}")
            A(f"        Devastation   : {pl.get('devastation',0):.1f}%")
            A(f"        Crime Rate    : {pl.get('crime_rate',0):.1f}%")
            A(f"        Unrest        : {pl.get('unrest',0):.1f}%")
            A(f"        Population    : {fmt_pop(pl.get('population',0))}")
            for sett in pl.get("settlements",[]):
                A(f"    {sett.get('name','?')}:")
                A(f"      Population    : {fmt_pop(sett.get('population',0))}")
                A(f"      Settlements   : {len(sett.get('districts',[]))} districts")
                dist_types={}
                for d in sett.get("districts",[]):
                    dt=d.get("type","?") if isinstance(d,dict) else str(d)
                    dist_types[dt]=dist_types.get(dt,0)+1
                for dt,cnt in dist_types.items():
                    A(f"        - {dt} x{cnt}")
    A("```")

    # ── NATIONAL DEMOGRAPHICS ─────────────────────────────────────────────────
    A("# NATIONAL DEMOGRAPHICS"); A("```")
    A(f"  Total Population     : {fmt_pop(pop)}")
    loy_mod=nation.get("loyalty_modifier",0.0)
    A(f"  Loyalty Modifier     : {loy_mod:+.2f}")
    A("```")
    for s in species:
        share=s.get("population_share",0.0)
        if share>=0.5:   share_lbl="Dominant"
        elif share>=0.3: share_lbl="Majority"
        elif share>=0.1: share_lbl="Significant"
        else:            share_lbl="Minority"
        crown=" 👑" if share==max((sp.get("population_share",0) for sp in species),default=0) else ""
        A("```")
        A(f"  {s['name']}{crown}")
        A(f"    Population       : {fmt_pop(pop*share)}")
        A(f"    Share            : {share*100:.1f}% — {share_lbl}")
        A(f"    Growth Rate      : {fmt_pct(s.get('growth_rate',nation.get('pop_growth',0)))}")
        A(f"    Culture          : {s.get('culture','N/A')}")
        A(f"    Language         : {s.get('language','N/A')}")
        A(f"    Religion         : {s.get('religion','N/A')}")
        A(f"    Loyalty          : {s.get('loyalty',0):.1f} / 100")
        A(f"    Happiness        : {s.get('happiness',0):.1f} / 100")
        A("```")

    # ── MILITARY ──────────────────────────────────────────────────────────────
    A("# MILITARY")
    for hdr,cats in [("## SPACEFLEET",["Spacefleet","Navy"]),
                     ("## AEROSPACE FORCES",["Air Force","Aerospace"]),
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
                    vet=u.get("veterancy","Green"); cnt=u.get("count",1)
                    notes=u.get("notes","").strip()
                    line=f"    - {nm} | x{cnt} | {vet}"
                    if notes: line+=f" | {notes}"
                    A(line)
        else: A("  None on record")
        A("```")
    A("# ARSENAL"); A("```")
    arsenal=nation.get("arsenal",[]) or []
    if arsenal:
        for item in arsenal:
            A(f"  {item.get('name','?')}")
            A(f"  {item.get('type','?')} | {item.get('size','?')} | Crew:{item.get('crew','?')} | Mnt:{fmt_cr(item.get('maintenance',0))} | {item.get('production_time','?')} turns")
    else: A("  None on record")
    A("```")
    A("## MANPOWER"); A("```")
    A(f"  Pool       : {fmt_pop(compute_manpower(nation))}")
    A(f"  Stored Pool: {fmt_pop(nation.get('manpower_pool',0))}"); A("```")

    # ── RESEARCH ──────────────────────────────────────────────────────────────
    A("# RESEARCH"); A("```")
    rp_pt=rb; rp_cost=1.0
    A(f"  RP per turn            : {fmt_cr(rp_pt)}")
    A(f"  .000001 RP Cost        : {fmt_cr(rp_cost)}")
    A(SEP)
    A("  Active Projects:")
    if active_r:
        for p in active_r:
            if isinstance(p, str):
                A(f"    {p}")
            else:
                A(f"    {p.get('name','?')}")
                A(f"      Field    : {p.get('field','?')}")
                A(f"      Progress : {p.get('progress',0):.1f}%  {bar_str(p.get('progress',0)/100,20)}")
                A(f"      Benefits : {p.get('benefit','N/A')}")
    else: A("    None active")
    A("  Completed Projects:")
    if done_r:
        for p in done_r:
            if isinstance(p, str):
                A(f"    {p}")
            else:
                A(f"    {p.get('name','?')}")
                A(f"      Field    : {p.get('field','?')}")
                A(f"      Benefits : {p.get('benefit','N/A')}")
    else: A("    None completed")
    A("```")

    if nation.get("is_megacorp") or "corporate_data" in nation:
        L.append(""); L.append(discord_corp_profile(nation,state))

    text="\n".join(L)
    fname=DISCORD_DIR/f"discord_{nation['name'].replace(' ','_')}_T{turn}.txt"
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
    return str(fname)


def _discord_market_export(state):
    """Generate a galactic market report in Discord-ready format."""
    DISCORD_DIR.mkdir(exist_ok=True)
    SEP="  " + "─"*57
    market=state.get("market",{}); mods=market.get("market_modifier",{})
    base_p=market.get("price_base",{}); ph=market.get("price_history",{})
    gal_stock,gal_prod,gal_cons=compute_galactic_stockpiles(state)
    turn=state.get("turn",1); qtr=state.get("quarter",1); year=state.get("year",2200)
    L=[]; A=L.append

    A(f"-# [GTC] GALACTIC MARKET REPORT")
    A(f"# GALACTIC MARKET — Q{qtr} [{year}]")
    A(f"*Issued by the Galactic Trade Confederation — Turn {turn}*")

    # ── COMMODITY OVERVIEW ────────────────────────────────────────────────────
    A("## COMMODITY OVERVIEW")
    for rname in _RESOURCES:
        base=base_p.get(rname,RES_BASE_PRICE[rname]); curr=mods.get(rname,base)
        mult=curr/base if base else 1.0
        hist=ph.get(rname,[])
        trend="▲" if (len(hist)>1 and hist[-1]>hist[-2]) else ("▼" if (len(hist)>1 and hist[-1]<hist[-2]) else "─")
        pbal=gal_prod[rname]-gal_cons[rname]
        sd_d=price_shock_delta(rname,gal_prod[rname],gal_cons[rname],curr,base)
        pressure="↑ Rising" if sd_d>0.01 else ("↓ Falling" if sd_d<-0.01 else "─ Stable")
        ratio=gal_prod[rname]/gal_cons[rname] if gal_cons[rname]>0 else 99.0
        mevs=[e for e in state.get("events_log",[]) if e.get("type")=="Market" and e.get("resource")==rname]
        last_label=mevs[-1].get("label","") if mevs else ""
        delta_approx=(curr-hist[-2])/hist[-2] if len(hist)>=2 and hist[-2] else 0.0
        explain=_price_explain(rname,ratio,last_label,delta_approx,curr,base)
        spark=""
        if len(hist)>=2:
            mn=min(hist); mxh=max(hist,default=mn+0.001)
            spark="".join("▁▂▃▄▅▆▇█"[min(7,int((v-mn)/(mxh-mn+0.001)*8))] for v in hist[-16:])
        A(f"### {rname}  {trend}"); A("```")
        A(f"  Current Price    : {curr:.4f} cr   (base: {base:.2f} cr  x{mult:.3f})")
        A(f"  Galaxy Stock     : {fmt_res(gal_stock[rname])}")
        A(f"  Production/turn  : {fmt_res(gal_prod[rname])}")
        A(f"  Demand/turn      : {fmt_res(gal_cons[rname])}")
        A(f"  Supply Bal/turn  : {fmt_res(pbal)}")
        A(f"  Pressure         : {pressure}")
        if spark: A(f"  Price History    : {spark}")
        if len(hist)>=2: A(f"  Range            : lo {min(hist):.3f}  hi {max(hist):.3f}  now {curr:.3f}")
        A(SEP)
        A(f"  Report           : {explain}"); A("```")

    # ── TOP EXPORTERS ─────────────────────────────────────────────────────────
    A("## TOP EXPORTERS BY RESOURCE"); A("```")
    for rname in _RESOURCES:
        ne=[(n["name"],compute_resource_export_credits(n,state).get(rname,0)) for n in state.get("nations",[])]
        ne.sort(key=lambda x:-x[1]); top=[(nm,c) for nm,c in ne if c>0][:3]
        if top:
            top_str="  |  ".join(f"{nation_tag(nm)} {fmt_cr(c)}" for nm,c in top)
            A(f"  {rname:<16}: {top_str}")
    A("```")

    # ── PIRACY SUMMARY ────────────────────────────────────────────────────────
    A("## PIRACY SUMMARY"); A("```")
    tot_p=sum(r.get("total_pirated",0) for r in state.get("trade_routes",[]))
    tot_i=sum(r.get("pirate_incidents",0) for r in state.get("trade_routes",[]))
    A(f"  Total Incidents  : {tot_i}")
    A(f"  Total Pirated    : {fmt_cr(tot_p)}")
    hot=[r for r in state.get("trade_routes",[]) if r.get("pirate_incidents",0)>0]
    if hot:
        A("")
        for r in sorted(hot,key=lambda x:-x.get("pirate_incidents",0))[:5]:
            A(f"  {r.get('name','?'):<28}: x{r.get('pirate_incidents',0)}  {fmt_cr(r.get('total_pirated',0))} stolen")
    A("```")

    # ── GTC DEBT LEDGER ───────────────────────────────────────────────────────
    A("## GTC DEBT LEDGER"); A("```")
    gtc_ldg=market.get("gtc",{}).get("debt_ledger",{})
    if gtc_ldg:
        total_owed=sum(e.get("balance",0.0) for e in gtc_ldg.values())
        A(f"  Total Owed to GTC: {fmt_cr(total_owed)}")
        A("")
        for nname,entry in sorted(gtc_ldg.items(),key=lambda x:-x[1].get("balance",0)):
            bal=entry.get("balance",0.0); rate=entry.get("interest_rate",0.04)
            qi=bal*rate/4.0; since=entry.get("since_turn",1)
            A(f"  {nname:<28}: {fmt_cr(bal)}  @ {rate*100:.2f}%  Qtr: {fmt_cr(qi)}  Since T{since}")
    else: A("  No active GTC debts on record.")
    A("```")

    text="\n".join(L)
    fname=DISCORD_DIR/f"discord_market_T{turn}.txt"
    with open(fname,"w",encoding="utf-8") as f: f.write(text)
    return str(fname)

