"""carmine.build_rows — build_rows() panel content builder for all tabs"""
from constants import *
from economy import (compute_resources, compute_trade, compute_planet_local_market,
                     compute_resource_export_credits, compute_debt, compute_gtc_debt,
                     compute_church_tithe, compute_tithe_income, spending_effects,
                     compute_military_consumption, compute_manpower, compute_galactic_stockpiles,
                     compute_vessel_resources, get_colony_progress, compute_subsidies,
                     econ_model_ipeu_modifier, price_shock_delta, _price_explain,
                     is_colony, years_elapsed, fmt_cr, fmt_pop,
                     fmt_res, fmt_pct, bar_str, nation_tag, RES_BASE_PRICE,
                     queue_construction, ECON_MODELS, DISTRICT_BUILD_TURNS)
from constants import (_avg_loyalty, _RESOURCES, _CAT_NORM, _UNIT_TYPES_BY_CAT,
                       _UNIT_VETERANCY, _UNIT_CATS)
from events import _MARKET_SHOCK
from ui_primitives import (_row, _hdr1, _hdr2, _sep, _bar, _btn, _ev_row, _collapse,
                            apply_edit, gf, ROW_H, HDR1_H, HDR2_H, SEP_H, BTN_H, COL_H)
from corporateAlpha0671 import build_corp_rows

def build_rows(nation,state,tab,collapsed_keys=None,galactic_sub=0):
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
        ipeu_current=ipeu*eco_mod
        mil_cons=compute_military_consumption(nation)
        R+=[_hdr1("ECONOMY"),
            _row("Economic Model",econ,vcol=GOLD),
            _row("IPEU (base)",fmt_cr(ipeu),["base_ipeu"],"float",GOLD),
            _row("IPEU (current)",fmt_cr(ipeu_current),vcol=BRIGHT),
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
            _row("  Alloys",fmt_res(mil_cons["Alloys"])+" / turn",vcol=RED_C if mil_cons["Alloys"]>0 else DIM)]
        eproj=nation.get("economic_projects") or []
        ep_key="eco_projects"; ep_open=ep_key not in collapsed_keys
        R+=[_sep(),_collapse(f"ECONOMIC PROJECTS  ({len(eproj)} active)",ep_key,ep_open,GOLD)]
        if ep_open:
            R.append(_btn("  + New Project","open_eco_project",{},(30,50,20)))
            for epi,ep in enumerate(eproj):
                pc=GREEN if ep.get("status")=="active" else DIM
                tr2=ep.get("turns_remaining",0); tt=ep.get("total_turns",1)
                R+=[_row(f"  [{ep.get('type','?')}] {ep.get('name','?')[:28]}",
                         f"Cost:{fmt_cr(ep.get('cost_per_turn',0))}/t  {tr2}/{tt}t left",vcol=pc),
                    _btn(f"    \u2715 Remove","remove_eco_project",{"epi":epi},(60,18,18))]
        R+=[_sep(),_hdr2("FISCAL REPORT")]
        dc=RED_C if debt["is_debtor"] else GREEN
        R+=[_row("Status","Debtor" if debt["is_debtor"] else "Creditor",vcol=dc),
            _row("Debt Balance",fmt_cr(debt["balance"]),["debt_balance"],"float"),
            _row("Debt Load",f"{debt['load_pct']:.1f}%"),
            _row("Interest Rate",f"{debt['rate']*100:.2f}%",["interest_rate"],"pct",CYAN),
            _row("Quarterly Int.",fmt_cr(debt["q_interest"])),
            _row("Debt Repayment",fmt_cr(debt["repayment"]),["debt_repayment"],"float")]
        gtc_e=compute_gtc_debt(nation,state)
        if gtc_e:
            gtc_bal=gtc_e.get("balance",0.0); gtc_rate=gtc_e.get("interest_rate",0.04)
            gtc_qi=gtc_bal*gtc_rate/4.0; gtc_rep=gtc_e.get("repayment",0.0)
            gtc_since=gtc_e.get("since_turn",1)
            R+=[_sep(),_hdr2("GTC DEBT — GALACTIC TRADE CONFEDERATION"),
                _row("  Creditor","Galactic Trade Confederation",vcol=GOLD),
                _row("  Principal",fmt_cr(gtc_e.get("balance",0.0)),vcol=RED_C),
                _row("  Interest Rate",f"{gtc_rate*100:.2f}% p.a.",vcol=CYAN),
                _row("  Quarterly Int.",fmt_cr(gtc_qi),vcol=RED_C),
                _row("  Repayment/Qtr",fmt_cr(gtc_rep) if gtc_rep else "None set",vcol=DIM),
                _row("  Debt Since",f"Turn {gtc_since}",vcol=DIM),
                _row("  Note",gtc_e.get("note",""),vcol=DIM)]
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
                        afd_idx=afd.index(u) if u in afd else -1  # safe index into full afd list
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
                        if afd_idx>=0: R.append(_btn(f"      ✏ Edit","edit_unit",{"unit_idx":afd_idx},(16,32,52)))
            else: R.append(_row("  None","",vcol=DIM))
            R.append(_sep())
        R.append(_hdr2("ARSENAL"))
        for a in (nation.get("arsenal",[]) or []):
            R.append(_row(f"  {a.get('name','?')}",f"{a.get('type','?')} | {a.get('size','?')} | Crew {a.get('crew','?')}"))
        if not (nation.get("arsenal") or []): R.append(_row("  None","",vcol=DIM))

        R+=[_sep(),_btn("+ Add / Edit Unit","open_unit_builder",{},(20,40,70))]
        # ── military deaths ──
        mil_deaths=nation.get("military_deaths") or []
        if mil_deaths:
            R+=[_sep(),_hdr2("MILITARY CASUALTIES")]
            _LIFE_STAGES=["Teen","Young Adult","Adult","Middle Aged","Senior"]
            by_sp={}
            for d in mil_deaths:
                sp_n=d.get("species","Unknown"); by_sp.setdefault(sp_n,[]).append(d)
            for sp_n,deaths in by_sp.items():
                total_d=sum(d.get("count",0) for d in deaths)
                R.append(_row(f"  {sp_n[:22]}",f"Total: {fmt_pop(total_d)} KIA",vcol=RED_C))
                stage_totals={ls:0 for ls in _LIFE_STAGES}
                for d in deaths:
                    ls=d.get("life_stage","Adult")
                    if ls in stage_totals: stage_totals[ls]+=d.get("count",0)
                for ls,cnt in stage_totals.items():
                    if cnt>0:
                        pct=cnt/total_d*100 if total_d else 0
                        R.append(_row(f"    {ls}",f"{fmt_pop(cnt)}  ({pct:.1f}%)",vcol=ORANGE))
        R+=[_sep(),_btn("+ Log Casualties","open_casualties",{},(60,20,20))]
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
        # spacer so rows start below the galactic subtab bar
        R.append({"type":"sep","h":GSUB_H+2})

        # ── OVERVIEW subtab ───────────────────────────────────────────────────
        if galactic_sub==0:
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
                ratio=gal_prod[rname]/gal_cons[rname] if gal_cons[rname]>0 else 99.0
                mevs=[e for e in state.get("events_log",[]) if e.get("type")=="Market" and e.get("resource")==rname]
                last_label=mevs[-1].get("label","") if mevs else ""
                delta_approx=(curr-hist[-2])/hist[-2] if len(hist)>=2 and hist[-2] else 0.0
                explain=_price_explain(rname,ratio,last_label,delta_approx,curr,base)
                R+=[_hdr2(f"  {rname}  {curr:.3f} cr  {trend}  Pressure:{pressure}"),
                    _row("    Galaxy Stockpile",fmt_res(gal_stock[rname])),
                    _row("    Galaxy Production",fmt_res(gal_prod[rname]),vcol=GREEN),
                    _row("    Galaxy Demand",fmt_res(gal_cons[rname]),vcol=RED_C),
                    _row("    Supply/Demand Bal",f"{fmt_res(pbal)}/turn",vcol=bal_col),
                    _row("    Price Multiplier",f"x{mult:.3f}  base {base:.2f}",vcol=col),
                    _row("    Report",explain,vcol=CYAN)]
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
            R+=[_sep(),_hdr2("GTC — GALACTIC TRADE CONFEDERATION DEBT LEDGER")]
            gtc_ldg=market.get("gtc",{}).get("debt_ledger",{})
            if gtc_ldg:
                total_owed=sum(e.get("balance",0.0) for e in gtc_ldg.values())
                R.append(_row("  Total Owed to GTC",fmt_cr(total_owed),vcol=GOLD))
                for nname,entry in sorted(gtc_ldg.items(),key=lambda x:-x[1].get("balance",0)):
                    bal=entry.get("balance",0.0); rate=entry.get("interest_rate",0.04)
                    qi=bal*rate/4.0; since=entry.get("since_turn",1)
                    R+=[_row(f"  {nname[:24]}",fmt_cr(bal),vcol=RED_C if bal>0 else GREEN),
                        _row(f"    Interest/Qtr",fmt_cr(qi),vcol=DIM),
                        _row(f"    Rate / Since",f"{rate*100:.2f}%  Turn {since}",vcol=DIM)]
            else:
                R.append(_row("  No GTC debt recorded","",vcol=DIM))
            R+=[_sep(),_hdr2("PSST NATIONS")]
            psst=market.get("psst_nations",[])
            for n in psst: R.append(_row(f"  {n}","",vcol=GOLD))
            if not psst: R.append(_row("  None listed","",vcol=DIM))

        # ── PRICE REPORT subtab ───────────────────────────────────────────────
        elif galactic_sub==1:
            turn=state.get("turn",1)
            R+=[_hdr1("GALACTIC PRICE REPORT"),
                _hdr2("SHOCK TABLE REFERENCE")]
            for lo,hi,label,(dlo,dhi),col in _MARKET_SHOCK:
                range_str=f"d20 [{lo}-{hi}]"
                delta_str=f"{dlo*100:+.0f}% to {dhi*100:+.0f}%" if (dlo,dhi)!=(0.0,0.0) else "No change"
                R.append(_row(f"  {label}",f"{range_str}   {delta_str}",vcol=col))
            R+=[_sep(),_hdr2("PER-COMMODITY PRICE ANALYSIS")]
            for rname in _RESOURCES:
                base=base_p.get(rname,RES_BASE_PRICE[rname]); curr=mods.get(rname,base)
                mult=curr/base if base else 1.0
                hist=ph.get(rname,[])
                sd_d=price_shock_delta(rname,gal_prod[rname],gal_cons[rname],curr,base)
                ratio=gal_prod[rname]/gal_cons[rname] if gal_cons[rname]>0 else 99.0
                col=GREEN if mult>1.1 else (RED_C if mult<0.9 else (GOLD if mult>1.0 else DIM))
                pressure_lbl="Rising ↑" if sd_d>0.01 else ("Falling ↓" if sd_d<-0.01 else "Stable ─")
                mevs=[e for e in state.get("events_log",[]) if e.get("type")=="Market" and e.get("resource")==rname]
                last_label=mevs[-1].get("label","") if mevs else "No data"
                delta_approx=(curr-hist[-2])/hist[-2] if len(hist)>=2 and hist[-2] else 0.0
                explain=_price_explain(rname,ratio,last_label,delta_approx,curr,base)
                # full sparkline
                spark=""
                if hist:
                    mn=min(hist); mxh=max(hist,default=mn+0.001)
                    spark="".join("▁▂▃▄▅▆▇█"[min(7,int((v-mn)/(mxh-mn+0.001)*8))] for v in hist)
                R+=[_hdr2(f"  {rname}"),
                    _row("    Current Price",f"{curr:.4f} cr  (base {base:.2f}  x{mult:.3f})",vcol=col),
                    _row("    S/D Ratio",f"{ratio:.3f}  ({gal_prod[rname]/1e6:.1f}M prod / {gal_cons[rname]/1e6:.1f}M cons)"),
                    _row("    Pressure",pressure_lbl,vcol=GREEN if sd_d>0.01 else (RED_C if sd_d<-0.01 else DIM)),
                    _row("    Last Shock",last_label,vcol=GOLD),
                    _row("    Analysis",explain,vcol=CYAN)]
                if hist:
                    R+=[_row("    Full History",spark,vcol=TEAL),
                        _row("    Range",f"lo:{min(hist):.4f}  hi:{max(hist):.4f}  now:{curr:.4f}  base:{base:.2f}",vcol=DIM)]
                # last 5 market events for this resource
                recent_evs=mevs[-5:] if mevs else []
                if recent_evs:
                    R.append(_row("    Recent Events","",vcol=DIM))
                    for e in reversed(recent_evs):
                        ecol=tuple(e["col_rgb"]) if e.get("col_rgb") else DIM
                        R.append(_row(f"      T{e.get('turn','?')} Q{e.get('quarter','?')}",
                                      f"{e.get('label','?'):<18} {e.get('description','')}",vcol=ecol))
                R.append(_sep())

    # ── CORP ── (rendered by corporateAlpha0671.build_corp_rows) ──────────────────
    elif tab=="CORP":
        R += build_corp_rows(nation,state,ipeu)

    # ── EVENTS ────────────────────────────────────────────────────────────────
    elif tab=="EVENTS":
        elog=state.get("events_log",[]) or []; nname=nation["name"]
        R+=[_hdr1("EVENTS LOG"),
            _btn("Roll Events for This Nation","roll_events",{"nation":nname},(60,30,90)),
            _btn("  + Add Custom Event","open_add_event",{"nation":nname},(20,55,30)),
            _sep()]
        indexed=[(i,e) for i,e in enumerate(elog) if e.get("nation")==nname or e.get("type") in ("Market","Piracy","Tithe")]
        indexed.reverse()
        if not indexed: R.append(_row("No events recorded","",vcol=DIM))
        else:
            cur_t=None
            for orig_i,e in indexed[:100]:
                t=e.get("turn","?")
                if t!=cur_t: cur_t=t; R.append(_hdr2(f"Turn {t}  .  {e.get('year','?')} Q{e.get('quarter','?')}"))
                approved=e.get("approved",False)
                R+=[_ev_row(e),
                    _btn(f"    {chr(10003)+' Approved' if approved else chr(9675)+' Approve'}","approve_event",{"ei":orig_i},
                         (20,50,20) if approved else (50,40,10)),
                    _btn(f"    ✏ Edit","edit_event",{"ei":orig_i},(16,32,52)),
                    _btn(f"    ✕ Remove","remove_event",{"ei":orig_i},(60,18,18))]
    return R

_TR_DIST_OPTIONS=["near","kind of far","too far"]
_TR_STATUS_OPTIONS=["active","suspended"]

