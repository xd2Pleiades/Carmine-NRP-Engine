#!/usr/bin/env python3
"""
Carmine NRP Engine - vAlpha0.6.71
Entry point. All logic is in the carmine sub-modules.
"""
import sys, pygame, time
from constants import *
from economy import (compute_resources, compute_trade, compute_planet_local_market,
                     is_colony, fmt_cr, fmt_pop, nation_tag, ECON_MODELS,
                     queue_construction, DISTRICT_BUILD_TURNS)
from constants import _RESOURCES, _CAT_NORM, _UNIT_CATS
from state_manager import StateManager, advance_turns
from gm_console import run_gm_command
from discord_export import _discord_export, _discord_market_export
from build_rows import build_rows
from ui_primitives import (gf, tw, draw_text, draw_rect, Scrollbar, Button,
                            EditOverlay, GMConsoleOverlay, apply_edit,
                            _row, _hdr1, _hdr2, _sep, _bar, _btn,
                            ROW_H, HDR1_H, HDR2_H, SEP_H, BTN_H, COL_H)
from overlays import (ConfirmOverlay, TradeBuilderOverlay, GraphOverlay,
                      UnitBuilderOverlay, EcoProjectOverlay, CasualtiesOverlay,
                      EventBuilderOverlay, LeftPanel, MainPanel)
from corporateAlpha0671 import (init_corp_module, compute_corp_income,
                                 compute_corp_market_cap, roll_corp_events,
                                 ContractBuilderOverlay, LocationBuilderOverlay,
                                 LocationSearcherOverlay, ShareholderBuilderOverlay,
                                 CorpEventBuilderOverlay, CorpGraphOverlay,
                                 TIER_MULT as _TIER_MULT)

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

def draw_galactic_subtab_bar(surf,sub_idx):
    """Mini subtab bar drawn at the top of the MAIN panel area when GALACTIC is active."""
    bar_rect=pygame.Rect(MAIN_X,MAIN_Y,MAIN_W,GSUB_H)
    draw_rect(surf,bar_rect,(10,18,30))
    draw_rect(surf,pygame.Rect(MAIN_X,MAIN_Y+GSUB_H-1,MAIN_W,1),BORDER2)
    f9=gf(9); w=120
    for i,lbl in enumerate(GALACTIC_SUBS):
        tx=MAIN_X+4+i*w; tr=pygame.Rect(tx,MAIN_Y+2,w-4,GSUB_H-4)
        if i==sub_idx:
            draw_rect(surf,tr,(22,48,72),radius=3)
            draw_rect(surf,tr,TEAL,border=1,radius=3)
            s=f9.render(lbl,True,BRIGHT)
        else:
            if tr.collidepoint(pygame.mouse.get_pos()): draw_rect(surf,tr,(16,32,52),radius=3)
            s=f9.render(lbl,True,DIM)
        surf.blit(s,s.get_rect(center=tr.center))

def draw_status_bar(surf):
    draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,SBAR_H),(8,14,22))
    draw_rect(surf,pygame.Rect(0,SH-SBAR_H,SW,1),BORDER)
    age=time.time()-_status_time; col=_status_col if age<3.0 else DIM
    draw_text(surf,_status_msg if age<5.0 else "Ready",10,SH-SBAR_H+4,gf(10),col)
    draw_text(surf,"S=save  D=discord  Arrows=nation  Tab/1-7=tab  ~=GM console",SW-460,SH-SBAR_H+4,gf(10),DIM2)

# ── main ──────────────────────────────────────────────────────────────────────
def main(filepath=None):
    if filepath is None:
        filepath=sys.argv[1] if len(sys.argv)>1 else DEFAULT_STATE
    sm=StateManager(filepath)
    if not sm.load(): sys.exit(f"[FATAL] Cannot load: {filepath}")
    pygame.init(); pygame.display.set_caption("Carmine NRP Engine - vAlpha0.6.71")
    init_corp_module({"gf":gf,"draw_text":draw_text,"draw_rect":draw_rect,"fmt_cr":fmt_cr,"fmt_res":fmt_res,"_row":_row,"_btn":_btn,"_hdr1":_hdr1,"_hdr2":_hdr2,"_sep":_sep,"_bar":_bar,"TEXT":TEXT,"BG":BG,"SEL":SEL,"EDITBDR":EDITBDR,"BRIGHT":BRIGHT,"DIM":DIM,"CYAN":CYAN,"TEAL":TEAL,"GOLD":GOLD,"RED_C":RED_C,"GREEN":GREEN,"PURPLE":PURPLE,"SW":SW,"SH":SH,"MAIN_X":MAIN_X,"MAIN_Y":MAIN_Y,"SBAR_H":SBAR_H})
    surf=pygame.display.set_mode((SW,SH)); clock=pygame.time.Clock()
    left=LeftPanel(); main_=MainPanel(); gm_console=GMConsoleOverlay()
    confirm_=ConfirmOverlay(); trade_builder_=TradeBuilderOverlay(); graph_overlay_=GraphOverlay()
    unit_builder_=UnitBuilderOverlay(); eco_proj_=EcoProjectOverlay(); casualties_=CasualtiesOverlay()
    contract_builder_=ContractBuilderOverlay(); location_builder_=LocationBuilderOverlay()
    location_searcher_=LocationSearcherOverlay()
    shareholder_builder_=ShareholderBuilderOverlay(); corp_event_builder_=CorpEventBuilderOverlay()
    corp_graph_=CorpGraphOverlay(); event_builder_=EventBuilderOverlay()
    names=sm.nation_names(); sel_idx=0; tab_idx=0; galactic_sub_idx=0

    def cur_nation(): return sm.get_nation(names[sel_idx]) if names else None
    def cur_tabs():
        n=cur_nation(); return get_tabs(n) if n else TABS

    def load_nation(idx):
        nonlocal sel_idx; sel_idx=max(0,min(idx,len(names)-1)); left.selected=sel_idx
        n=cur_nation()
        if n:
            tabs=get_tabs(n)
            ti=min(tab_idx,len(tabs)-1)
            main_.set_rows(build_rows(n,sm.state,tabs[ti],main_.collapsed_keys,galactic_sub_idx))

    def do_discord():
        n=cur_nation()
        if n: path=_discord_export(n,sm.state); set_status(f"Discord -> {path}",CYAN)

    left.set_nations(names,sel_idx,sm.state)
    load_nation(0)
    if getattr(sm,"_migration_warnings",[]):
        set_status(f"MIGRATION: flat offices/stores zeroed for: {", ".join(sm._migration_warnings)} — add locations manually.",GOLD)
    else:
        set_status(f"Carmine v0.6.71  ~=GM console  loaded: {filepath}",CYAN)
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

            # unit builder overlay
            if unit_builder_.active:
                ub_r=unit_builder_.on_event(ev)
                if ub_r=="save":
                    n_u=cur_nation()
                    if n_u:
                        ud=unit_builder_.get_unit_data()
                        afd2=n_u.setdefault("active_forces_detail",[])
                        if unit_builder_.mode=="new":
                            ud["ugid"]=None; afd2.append(ud)
                            set_status(f"Unit {ud.get('unit','?')} added.",GREEN)
                        else:
                            idx2=unit_builder_.unit_idx
                            if 0<=idx2<len(afd2):
                                ud["ugid"]=afd2[idx2].get("ugid"); afd2[idx2]=ud
                                set_status(f"Unit updated.",CYAN)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # eco project overlay
            if eco_proj_.active:
                ep_r=eco_proj_.on_event(ev)
                if ep_r=="save":
                    n_e=cur_nation()
                    if n_e:
                        n_e.setdefault("economic_projects",[]).append(eco_proj_.get_data())
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                        set_status("Economic project added.",GOLD)
                continue

            # casualties overlay
            if casualties_.active:
                cas_r=casualties_.on_event(ev)
                if cas_r=="save":
                    n_ca=cur_nation()
                    if n_ca:
                        n_ca.setdefault("military_deaths",[]).append(casualties_.get_data())
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                        set_status("Casualties logged.",RED_C)
                continue

            # contract builder
            if contract_builder_.active:
                _cbr=contract_builder_.on_event(ev)
                if _cbr=="save":
                    _nc=cur_nation()
                    if _nc:
                        _cd=_nc.setdefault("corporate_data",{}); _contracts=_cd.setdefault("contracts",[])
                        _d=contract_builder_.get_data()
                        if contract_builder_.mode=="new": _contracts.append(_d); set_status(f"Contract added: {_d.get('client','?')}.",GREEN)
                        else:
                            _idx=contract_builder_.contract_idx
                            if 0<=_idx<len(_contracts): _contracts[_idx]=_d; set_status("Contract updated.",CYAN)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # location searcher (planet picker)
            if location_searcher_.active:
                _lsr=location_searcher_.on_event(ev)
                if _lsr is not None:
                    location_builder_.set_location(_lsr[0],_lsr[1])
                    location_builder_.active=True
                continue

            # location builder
            if location_builder_.active:
                if location_builder_._open_searcher:
                    location_builder_._open_searcher=False
                    location_builder_.active=False
                    location_searcher_.open(sm.state)
                    continue
                _lbr=location_builder_.on_event(ev)
                if _lbr=="save":
                    _nc=cur_nation()
                    if _nc:
                        _cd=_nc.setdefault("corporate_data",{}); _locs=_cd.setdefault("locations",[])
                        _d=location_builder_.get_data()
                        if location_builder_.mode=="new": _locs.append(_d); set_status(f"Location added: {_d.get('name','?')}.",GREEN)
                        else:
                            _idx=location_builder_.loc_idx
                            if 0<=_idx<len(_locs): _locs[_idx]=_d; set_status("Location updated.",CYAN)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # shareholder builder
            if shareholder_builder_.active:
                _sbr=shareholder_builder_.on_event(ev)
                if _sbr=="save":
                    _nc=cur_nation()
                    if _nc:
                        _cd=_nc.setdefault("corporate_data",{}); _shs=_cd.setdefault("shareholders",[])
                        _d=shareholder_builder_.get_data()
                        if shareholder_builder_.mode=="new": _shs.append(_d); set_status(f"Shareholder added: {_d.get('name','?')}.",GREEN)
                        else:
                            _idx=shareholder_builder_.sh_idx
                            if 0<=_idx<len(_shs): _shs[_idx]=_d; set_status("Shareholder updated.",CYAN)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # corp event builder
            if corp_event_builder_.active:
                _cebr=corp_event_builder_.on_event(ev)
                if _cebr=="save":
                    _nc=cur_nation()
                    if _nc:
                        _cd=_nc.setdefault("corporate_data",{}); _d=corp_event_builder_.get_data(sm.state)
                        _cd["trust"]=max(0.0,min(1.0,_cd.get("trust",0.5)+_d.get("trust_delta",0.0)))
                        _cd.setdefault("corp_events",[]).append(_d); set_status(f"Corp event logged: {_d.get('label','?')}.",PURPLE)
                        sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                continue

            # corp graph overlay
            if corp_graph_.active:
                _cgr=corp_graph_.on_event(ev)
                if _cgr=="export":
                    _nc=cur_nation()
                    if _nc: _fp=corp_graph_.export_png(surf,_nc); set_status(f"Graph exported: {_fp}",GREEN)
                continue

            # event builder
            if event_builder_.active:
                _ebr=event_builder_.on_event(ev)
                if _ebr=="save":
                    _d=event_builder_.get_data(sm.state)
                    if event_builder_.mode=="new":
                        sm.state.setdefault("events_log",[]).append(_d); set_status("Event added.",CYAN)
                    else:
                        _ei=event_builder_.ev_idx; _elog=sm.state.get("events_log",[])
                        if 0<=_ei<len(_elog): _elog[_ei].update(_d); set_status("Event updated.",CYAN)
                    sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
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
                if ev.key==pygame.K_c:
                    _nc2=cur_nation()
                    if _nc2 and (_nc2.get("is_megacorp") or "corporate_data" in _nc2):
                        _tabs_c2=get_tabs(_nc2)
                        if "CORP" in _tabs_c2:
                            tab_idx=_tabs_c2.index("CORP"); load_nation(sel_idx); set_status("CORP tab (C).",GOLD)
                elif ev.key==pygame.K_s: sm.save(); set_status("Saved with backup rotation.",GREEN)
                elif ev.key==pygame.K_d: do_discord()
                elif ev.key in (pygame.K_UP,pygame.K_LEFT): load_nation(sel_idx-1)
                elif ev.key in (pygame.K_DOWN,pygame.K_RIGHT): load_nation(sel_idx+1)
                elif ev.key==pygame.K_TAB:
                    tabs=cur_tabs(); tab_idx2=(tab_idx+1)%len(tabs)
                    # we need nonlocal tab_idx
                    pass
                elif pygame.K_1<=ev.key<=pygame.K_8:
                    pass  # handled in second key block below

            # handle tab_idx changes cleanly
            if ev.type==pygame.KEYDOWN:
                tabs=cur_tabs()
                if ev.key==pygame.K_TAB:
                    tab_idx=(tab_idx+1)%len(tabs); load_nation(sel_idx)
                elif pygame.K_1<=ev.key<=pygame.K_8:
                    ti=ev.key-pygame.K_1
                    if 0<=ti<len(tabs): tab_idx=ti; load_nation(sel_idx)

            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                tabs=cur_tabs()
                if LWIDTH<=ev.pos[0]<SW and TBAR_H<=ev.pos[1]<TBAR_H+TABBAR_H:
                    w=(SW-LWIDTH)//len(tabs); ti=(ev.pos[0]-LWIDTH)//w
                    if 0<=ti<len(tabs): tab_idx=ti; load_nation(sel_idx)
                # galactic subtab bar click
                if tabs[tab_idx]=="GALACTIC" and MAIN_X<=ev.pos[0]<MAIN_X+MAIN_W and MAIN_Y<=ev.pos[1]<MAIN_Y+GSUB_H:
                    sw=120; si=(ev.pos[0]-MAIN_X-4)//sw
                    if 0<=si<len(GALACTIC_SUBS):
                        galactic_sub_idx=si; load_nation(sel_idx)

            clicked=left.on_event(ev)
            if clicked is not None: load_nation(clicked)
            if left.btn_minus.on_event(ev): left.adv_n=max(1,left.adv_n-1)
            if left.btn_plus.on_event(ev): left.adv_n=min(20,left.adv_n+1)
            if left.btn_adv.on_event(ev):
                evs=advance_turns(sm,left.adv_n); names2=sm.nation_names()
                names.clear(); names.extend(names2)
                left.set_nations(names,sel_idx,sm.state); load_nation(sel_idx)
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
                    elif action=="open_unit_builder" and n:
                        ugroups2=n.get("unit_groups") or []
                        unit_builder_.open_new(sm.nation_names(),ugroups2)
                    elif action=="edit_unit" and n:
                        idx2=data.get("unit_idx",0); afd2=n.get("active_forces_detail",[]) or []
                        if 0<=idx2<len(afd2):
                            unit_builder_.open_edit(afd2[idx2],idx2,sm.nation_names(),n.get("unit_groups") or [])
                    elif action=="open_eco_project":
                        eco_proj_.open()
                    elif action=="remove_eco_project" and n:
                        epi2=data.get("epi",0); ep2=n.get("economic_projects") or []
                        if 0<=epi2<len(ep2):
                            ep2.pop(epi2); n["economic_projects"]=ep2
                            sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status("Project removed.",RED_C)
                    elif action=="open_casualties" and n:
                        sp_names=[s["name"] for s in (n.get("species_populations") or [])]
                        casualties_.open(sp_names)
                    elif action=="end_corp_contract" and n:
                        ci2=data.get("ci",0); contracts2=n.get("corporate_data",{}).get("contracts") or []
                        if 0<=ci2<len(contracts2):
                            contracts2[ci2]["status"]="ended"
                            sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status("Contract ended.",RED_C)
                    elif action=="open_corp_contract":
                        contract_builder_.open_new()
                    elif action=="edit_corp_contract" and n:
                        _ci2=data.get("ci",0); _contracts2=n.get("corporate_data",{}).get("contracts") or []
                        if 0<=_ci2<len(_contracts2): contract_builder_.open_edit(_contracts2[_ci2],_ci2)
                    elif action=="open_new_location" and n:
                        location_builder_.open_new(n.get("base_ipeu",0.0))
                    elif action=="edit_location" and n:
                        _li2=data.get("li",0); _locs2=n.get("corporate_data",{}).get("locations") or []
                        if 0<=_li2<len(_locs2): location_builder_.open_edit(_locs2[_li2],_li2)
                    elif action=="remove_location" and n:
                        _li2=data.get("li",0); _locs2=n.get("corporate_data",{}).get("locations") or []
                        if 0<=_li2<len(_locs2): _locs2.pop(_li2); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Location removed.",RED_C)
                    elif action=="open_add_shareholder":
                        shareholder_builder_.open_new()
                    elif action=="remove_shareholder" and n:
                        _si2=data.get("si",0); _shs2=n.get("corporate_data",{}).get("shareholders") or []
                        if 0<=_si2<len(_shs2): _shs2.pop(_si2); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Shareholder removed.",RED_C)
                    elif action=="open_corp_event_log":
                        corp_event_builder_.open()
                    elif action=="remove_corp_event" and n:
                        _ri=data.get("cevi",0); _cevs=n.get("corporate_data",{}).get("corp_events") or []
                        if 0<=_ri<len(_cevs): _cevs.pop(_ri); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Corp event removed.",RED_C)
                    elif action=="open_corp_graph":
                        corp_graph_.open()
                    elif action=="approve_event":
                        _ei2=data.get("ei",0); _elog2=sm.state.get("events_log",[])
                        if 0<=_ei2<len(_elog2):
                            _elog2[_ei2]["approved"]=not _elog2[_ei2].get("approved",False)
                            sm.mark_dirty(); sm.autosave(); load_nation(sel_idx)
                            set_status("Event approval toggled.",GOLD)
                    elif action=="edit_event":
                        _ei2=data.get("ei",0); _elog2=sm.state.get("events_log",[])
                        if 0<=_ei2<len(_elog2): event_builder_.open_edit(_elog2[_ei2],_ei2)
                    elif action=="remove_event":
                        _ei2=data.get("ei",0); _elog2=sm.state.get("events_log",[])
                        if 0<=_ei2<len(_elog2): _elog2.pop(_ei2); sm.mark_dirty(); sm.autosave(); load_nation(sel_idx); set_status("Event removed.",RED_C)
                    elif action=="open_add_event":
                        event_builder_.open_new(data.get("nation",""))
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
        if tabs[tab_idx]=="GALACTIC": draw_galactic_subtab_bar(surf,galactic_sub_idx)
        main_.edit.draw(surf,dt)
        unit_builder_.draw(surf,dt)
        eco_proj_.draw(surf,dt)
        casualties_.draw(surf,dt)
        graph_overlay_.draw(surf,sm.state)
        trade_builder_.draw(surf,dt)
        confirm_.draw(surf,dt)
        contract_builder_.draw(surf,dt)
        location_builder_.draw(surf,dt)
        location_searcher_.draw(surf)
        shareholder_builder_.draw(surf,dt)
        corp_event_builder_.draw(surf,dt)
        corp_graph_.draw(surf,cur_nation())
        event_builder_.draw(surf,dt)
        gm_console.draw(surf,dt)
        draw_status_bar(surf); pygame.display.flip()
    pygame.quit()

if __name__=="__main__":
    main()