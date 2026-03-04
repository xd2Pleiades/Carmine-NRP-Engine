# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LeftPanel:
    """Nation list sidebar with action buttons."""
    ROW_H = 40; PAD = 8

    def __init__(self, lay: Layout):
        self.lay = lay; self.names = []; self.scroll = 0
        self.selected = 0; self._hov = -1

    def update_layout(self, lay: Layout): self.lay = lay
    def set_nations(self, names, sel=0): self.names = names; self.selected = sel

    def _buttons(self):
        lw = self.lay.lw; sh = self.lay.sh; p = self.PAD; bw = lw - p*2
        return {
            "save":  Button((p, sh-130, bw, 26), "[ SAVE  S ]",  accent=True),
            "disc":  Button((p, sh-100, bw, 26), "[ DISCORD  D ]"),
            "trade": Button((p, sh- 70, bw, 26), "[ TRADE ROUTE  R ]"),
            "adv":   Button((p, sh- 40, bw, 26), "[ ADVANCE TURN  T ]", accent=True),
        }

    def draw(self, surf, turn, year, quarter):
        lw = self.lay.lw; sh = self.lay.sh
        pygame.draw.rect(surf, PANEL, (0, 0, lw, sh))
        pygame.draw.rect(surf, BORDER, (0, 0, lw, sh), 1)
        corner_deco(surf, 0, 0, lw, sh, ACCENT, 10)
        pygame.draw.rect(surf, ACCENT2, (0, 0, lw, 3))
        bt = blit_text
        bt(surf, "CARMINE NRP", self.PAD, 8, gf(14, mono=False), ACCENT)
        bt(surf, f"T{turn}  ·  {year} Q{quarter}", self.PAD, 28, gf(11), TEAL)
        yd = 48; pygame.draw.line(surf, BORDER2, (4, yd), (lw-4, yd), 1)
        ly0 = yd+4; lh = sh - yd - 145
        surf.set_clip(pygame.Rect(0, ly0, lw, lh))
        fi = gf(12); ft = gf(10)
        for i, name in enumerate(self.names):
            iy = ly0 + i*self.ROW_H - self.scroll
            if iy + self.ROW_H < ly0 or iy > ly0+lh: continue
            rr = pygame.Rect(4, iy, lw-8, self.ROW_H-3)
            if i == self.selected:
                pygame.draw.rect(surf, SEL, rr, border_radius=3)
                pygame.draw.rect(surf, CYAN, rr, 1, border_radius=3)
                pygame.draw.rect(surf, CYAN, (0, iy, 3, self.ROW_H-3)); nc = BRIGHT
            elif i == self._hov:
                pygame.draw.rect(surf, HOV, rr, border_radius=3); nc = TEXT
            else: nc = DIM
            tag_str = f"[{nation_tag(name)}]"
            bt(surf, tag_str, self.PAD+2, iy+4, ft, TEAL if i==self.selected else DIM2)
            ns = name if len(name) <= 20 else name[:18]+".."
            bt(surf, ns, self.PAD+2, iy+18, fi, nc)
        surf.set_clip(None)
        for b in self._buttons().values(): b.draw(surf)

    def on_event(self, event):
        lw = self.lay.lw
        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            if pos[0] < lw:
                rel = pos[1] - 52 + self.scroll; i = rel // self.ROW_H
                self._hov = i if 0 <= i < len(self.names) else -1
            else: self._hov = -1
        if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] < lw:
            self.scroll = max(0, self.scroll - event.y * self.ROW_H)
        for key, btn in self._buttons().items():
            if btn.on_event(event): return None, key
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if pos[0] < lw:
                rel = pos[1] - 52 + self.scroll; i = rel // self.ROW_H
                if 0 <= i < len(self.names): self.selected = i; return i, None
        return None, None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE  –  build render-item list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_profile_items(nation: dict, state: dict) -> list:
    """Build flat render-item list for ProfilePanel."""
    items = []; y = 8
    routes = state.get("trade_routes", [])
    ipeu   = nation.get("base_ipeu", 0.0)
    pop    = current_population(nation)
    exp_d  = nation.get("expenditure", {})
    trade  = compute_trade(nation, routes)
    rflows = compute_resource_flows(nation)
    debt   = compute_debt(nation)
    rbudget= nation.get("research_budget", 0.0)
    sfund  = nation.get("strategic_fund",  0.0)
    total_exp_pct = sum(exp_d.values())
    total_exp_cr  = total_exp_pct*ipeu + rbudget
    net_bal        = ipeu + trade["net"] - total_exp_cr - debt["q_interest"]
    fund_delta     = trade["net"] - debt["q_interest"]
    per_cap        = int(ipeu/pop) if pop > 0 else 0
    star_sys  = nation.get("star_systems", [])
    species   = nation.get("species_populations", [])
    projs     = nation.get("projects", [])
    act_res   = nation.get("active_research_projects", [])
    comp_tech = nation.get("completed_techs", [])
    eco_m     = nation.get("economic_model", "Mixed")
    afd       = nation.get("active_forces_detail", [])
    if not isinstance(afd, list): afd = []
    homeworld = "—"
    for ss in star_sys:
        for pl in ss.get("planets", []): homeworld = pl["name"]; break
        break
    sstr = (", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species)
            if species else "—")

    def add(item): nonlocal y; item["y"] = y; items.append(item); y += item["h"]
    def hdr1(t): add({"type":"hdr1","h":36,"text":t})
    def hdr2(t): add({"type":"hdr2","h":30,"text":t})
    def spc(h=8): add({"type":"spc","h":h})
    def sep():    add({"type":"sep","h":10})
    def crow(lbl, val, key=None, et=None, lw=18, vc=TEXT, ib=True):
        meta = {"path":[key],"type":et,"raw":nation.get(key,val)} if key else None
        add({"type":"row","h":22,"in_block":ib,"label":lbl,"value":str(val),
             "label_w":lw,"editable":meta is not None,"edit_meta":meta,"val_color":vc})

    add({"type":"nhdr","h":62,"tag":nation_tag(nation["name"]),"name":nation["name"]})
    spc()
    for lbl,val,key,et in [
        ("Species",    sstr,                                          None, None),
        ("Population", fmt_pop(pop),                                  "population","pop"),
        ("Pop Growth", fmt_pct(nation.get("pop_growth",0))+" / yr",   "pop_growth","pct"),
        ("Homeworld",  homeworld,                                      None, None),
        ("Civilisation",nation.get("civ_level","Interplanetary Industrial"),"civ_level","str"),
        ("Tier",       str(nation.get("civ_tier",2)),                  "civ_tier","int"),
        ("Eco Model",  eco_m,                                          "economic_model","str"),
        ("Status",     nation.get("eco_status","Stable"),              "eco_status","str"),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,val)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":str(val),
             "label_w":16,"editable":meta is not None,"edit_meta":meta,
             "val_color":CYAN if key else TEXT})
    spc()

    hdr1("# ECONOMY")
    for lbl,val,key,et,vc in [
        ("IPEU (base)",       fmt_cr(ipeu),                              "base_ipeu","float",CYAN),
        ("IPEU Growth",       fmt_pct(nation.get("ipeu_growth",0))+" / yr","ipeu_growth","pct",TEXT),
        ("IPEU per Capita",   f"{per_cap:,} cr",                         None,None,TEXT),
        ("Trade Revenue",     fmt_cr(trade["net"]),                      None,None,TEXT),
        (" - Exports",        fmt_cr(trade["exports"]),                  None,None,GREEN),
        (" - Imports",        fmt_cr(-trade["imports"]),                 None,None,RED_C),
        ("Total Expenditure", fmt_cr(total_exp_cr)+f"  ({total_exp_pct*100:.1f}%)",None,None,TEXT),
        ("Research Budget",   fmt_cr(rbudget)+" / turn",                 "research_budget","float",CYAN),
        ("Net Balance",       fmt_cr(net_bal),                           None,None,GREEN if net_bal>=0 else RED_C),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,0)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
             "label_w":18,"editable":meta is not None,"edit_meta":meta,"val_color":vc})
    spc()

    hdr2("## EXPENDITURE & BREAKDOWN")
    max_pct = max(exp_d.values(), default=0.01)
    for cat in EXPENDITURE_ORDER:
        pct = exp_d.get(cat, 0.0)
        if pct == 0.0 and cat not in exp_d: continue
        add({"type":"bar","h":22,"in_block":True,"label":cat,"pct":pct,
             "amount":fmt_cr(pct*ipeu),"editable":True,
             "edit_meta":{"path":["expenditure",cat],"type":"pct","raw":pct}})
    sep()
    add({"type":"row","h":22,"in_block":True,"label":"TOTAL",
         "value":f"{total_exp_pct*100:.1f}%   ({fmt_cr(total_exp_cr)})",
         "label_w":18,"editable":False,"edit_meta":None,"val_color":GOLD})
    spc()

    if eco_m in ("Capitalist","Mixed"):
        hdr2("## MARKET DATA")
        for lbl,val,key,et in [
            ("Investments",     fmt_cr(nation.get("investments",0)),    "investments","float"),
            ("Subsidies",       fmt_cr(nation.get("subsidies",0)),      "subsidies","float"),
            ("Local Mkt Output",fmt_cr(nation.get("local_market_output",0)),"local_market_output","float"),
        ]:
            meta = {"path":[key],"type":et,"raw":nation.get(key,0)}
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":20,"editable":True,"edit_meta":meta,"val_color":TEXT})
        spc()
    if eco_m in ("Planned","Mixed"):
        hdr2("## PLANNED DATA")
        for lbl,val,key,et in [
            ("Domestic Prod.", fmt_cr(nation.get("domestic_production",0)),"domestic_production","float"),
            ("Export Surplus", fmt_cr(nation.get("export_surplus",0)),    "export_surplus","float"),
            ("Construction Eff.",f"{nation.get('construction_efficiency',0.8)*100:.0f}%","construction_efficiency","pct"),
            ("Research Eff.",  f"{nation.get('research_efficiency',0.8)*100:.0f}%","research_efficiency","pct"),
            ("Bureaucracy Eff.",f"{nation.get('bureaucracy_efficiency',0.8)*100:.0f}%","bureaucracy_efficiency","pct"),
            ("Distribution",   fmt_cr(nation.get("distribution",0)),      "distribution","float"),
        ]:
            meta = {"path":[key],"type":et,"raw":nation.get(key,0)}
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":20,"editable":True,"edit_meta":meta,"val_color":TEXT})
        spc()

    hdr2("## ECONOMIC PROJECTS")
    ap = [p for p in projs if p.get("status") in ("active","in_progress","complete")]
    if ap:
        for p in ap:
            done = p.get("status")=="complete"
            tl = p.get("duration_turns",0)-p.get("turns_elapsed",0)
            add({"type":"row","h":22,"in_block":True,
                 "label":f"{p['name']} ({p.get('category','?')})",
                 "value":"[COMPLETE]" if done else f"[{tl}t left]",
                 "label_w":36,"editable":False,"edit_meta":None,
                 "val_color":GREEN if done else GOLD})
    else:
        add({"type":"row","h":22,"in_block":True,"label":"None active","value":"",
             "label_w":36,"editable":False,"edit_meta":None,"val_color":DIM})
    spc()

    hdr2("## FISCAL REPORT")
    for lbl,val,key,et,vc in [
        ("Debt Balance", fmt_cr(debt["balance"])+f"  ({debt['load_pct']:.1f}% of IPEU)",
                         "debt_balance","float",RED_C if debt["balance"]>0 else TEXT),
        ("Interest Rate",f"{debt['rate']*100:.1f}% / yr","interest_rate","pct",TEXT),
        ("Quarterly Int.",fmt_cr(debt["q_interest"]),None,None,TEXT),
        ("Debt Repayment",fmt_cr(debt["repayment"])+" / qtr","debt_repayment","float",TEXT),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,0)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
             "label_w":18,"editable":meta is not None,"edit_meta":meta,"val_color":vc})
    add({"type":"debtbar","h":22,"in_block":True,"pct":debt["load_pct"]/100})
    sep()
    sf_col = GREEN if sfund >= 0 else RED_C
    fd_col = GREEN if fund_delta >= 0 else RED_C
    add({"type":"row","h":22,"in_block":True,"label":"Strategic Fund",
         "value":fmt_cr(sfund),"label_w":18,"editable":True,"val_color":sf_col,
         "edit_meta":{"path":["strategic_fund"],"type":"float","raw":sfund}})
    fds = ("+"+fmt_cr(fund_delta) if fund_delta>=0 else fmt_cr(fund_delta))
    add({"type":"row","h":22,"in_block":True,"label":"Fund Δ this turn",
         "value":fds,"label_w":18,"editable":False,"edit_meta":None,"val_color":fd_col})
    spc()

    hdr2("## RESOURCES & STOCKPILES")
    for rname in RESOURCE_NAMES:
        rd   = rflows.get(rname,{}); stk=rd.get("stockpile",0.0)
        prod = rd.get("production",0.0); cons=rd.get("consumption",0.0)
        net  = rd.get("net",0.0); trend=rd.get("trend","Stable")
        ncol = GREEN if net>=0 else RED_C
        tcol = GREEN if "Surplus" in trend else (RED_C if "Deficit" in trend else GOLD)
        ns   = ("+"+fmt_int(net)) if net>=0 else fmt_int(int(net))
        sd   = nation.get("resource_stockpiles",{}).get(rname,{})
        mode = sd.get("production_mode","derived")
        exp_c= next((r2.get("credits",0) for r2 in trade["export_routes"] if r2.get("resource")==rname), 0)
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Stockpile","value":fmt_int(stk),
             "label_w":28,"editable":True,"val_color":TEXT,
             "edit_meta":{"path":["resource_stockpiles",rname,"stockpile"],"type":"float","raw":stk}})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Prod/turn","value":fmt_int(prod),
             "label_w":28,"editable":mode=="flat","val_color":TEXT,
             "edit_meta":{"path":["resource_stockpiles",rname,"flat_production"],"type":"float","raw":prod}
                         if mode=="flat" else None})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Cons/turn","value":fmt_int(cons),
             "label_w":28,"editable":False,"edit_meta":None,"val_color":TEXT})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Net/turn","value":ns,
             "label_w":28,"editable":False,"edit_meta":None,"val_color":ncol})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Trend","value":trend,
             "label_w":28,"editable":False,"edit_meta":None,"val_color":tcol})
        if exp_c > 0:
            add({"type":"row","h":22,"in_block":True,"label":f"{rname} Export","value":fmt_cr(exp_c),
                 "label_w":28,"editable":False,"edit_meta":None,"val_color":CYAN})
        spc(4)
    spc()

    hdr1("# TERRITORIES")
    for ss in star_sys:
        add({"type":"row","h":22,"in_block":False,
             "label":f"System: {ss['name']}  [{ss.get('coordinates','—')}]",
             "value":ss.get("notes",""),"label_w":36,"editable":False,"edit_meta":None,"val_color":CYAN})
        for pl in ss.get("planets",[]):
            add({"type":"row","h":22,"in_block":True,
                 "label":f"  ▸ {pl['name']}",
                 "value":(f"{pl.get('type','?')} · {pl.get('size','?')} · "
                          f"Hab:{pl.get('habitability',0):.0f}% · "
                          f"Dev:{pl.get('devastation',0):.0f}% · "
                          f"Crime:{pl.get('crime_rate',0):.0f}% · "
                          f"Unrest:{pl.get('unrest',0):.0f}%"),
                 "label_w":22,"editable":False,"edit_meta":None,"val_color":TEXT})
            for s in pl.get("settlements",[]):
                sp_inf = " | ".join(f"{sp['species'][:8]} loy:{sp.get('loyalty',0):.0f}"
                                    for sp in s.get("populations",[]))
                add({"type":"row","h":22,"in_block":True,
                     "label":f"      › {s['name']}",
                     "value":f"pop:{fmt_pop(s.get('population',0))} {sp_inf}",
                     "label_w":26,"editable":False,"edit_meta":None,"val_color":DIM})
    spc()

    hdr2("## NATIONAL DEMOGRAPHICS")
    add({"type":"row","h":22,"in_block":True,"label":"Total Population","value":fmt_pop(pop),
         "label_w":22,"editable":False,"edit_meta":None,"val_color":TEXT})
    add({"type":"row","h":22,"in_block":True,"label":"Loyalty Modifier",
         "value":f"{nation.get('loyalty_modifier_cg',1.0)*100:.0f}%",
         "label_w":22,"editable":True,
         "edit_meta":{"path":["loyalty_modifier_cg"],"type":"float","raw":nation.get("loyalty_modifier_cg",1.0)},
         "val_color":TEXT})
    spc(6)
    for sp in species:
        is_dom = sp.get("status","") in ("dominant","majority")
        add({"type":"sphdr","h":28,"name":sp["name"],"status":sp.get("status","?").title(),"dominant":is_dom})
        sp_pop = sp.get("population",0); shr = sp_pop/pop*100 if pop>0 else 0
        loy = sp.get("loyalty",75); lc = GREEN if loy>=70 else (GOLD if loy>=40 else RED_C)
        hap = 70
        for ss2 in star_sys:
            for pl2 in ss2.get("planets",[]):
                for s2 in pl2.get("settlements",[]):
                    for sp2 in s2.get("populations",[]):
                        if sp2["species"]==sp["name"]: hap=sp2.get("happiness",70)
        for lbl,val,meta_key,et,vc in [
            ("Population",  fmt_pop(sp_pop),  None,None,TEXT),
            ("Share",       f"{shr:.1f}% of total",None,None,TEXT),
            ("Growth Rate", fmt_pct(sp.get("growth_rate",0))+" / yr",None,None,TEXT),
            ("Culture",     sp.get("culture","—"),None,None,TEXT),
            ("Language",    sp.get("language","—"),None,None,TEXT),
            ("Religion",    sp.get("religion","—"),None,None,TEXT),
            ("Loyalty",     f"{loy}/100  {loyalty_bar(loy)}","loyalty","int",lc),
            ("Happiness",   f"{hap}/100  {loyalty_bar(hap)}",None,None,GOLD),
        ]:
            m = {"path":["_species",sp["name"],meta_key],"type":et,"raw":sp.get(meta_key,loy)} if meta_key else None
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":16,"editable":m is not None,"edit_meta":m,"val_color":vc})
        spc(6)

    hdr1("# MILITARY")
    for sec, cats in [("## SPACEFLEET",["Spacefleet","Navy"]),
                      ("## AEROSPACE",["Air Force","Aerospace"]),
                      ("## GROUND FORCES",["Ground Forces","Ground","Army"])]:
        hdr2(sec)
        units = [u for u in afd if u.get("category") in cats]
        if units:
            for u in units:
                cname = u.get("custom_name") or u.get("unit","?")
                add({"type":"row","h":22,"in_block":True,
                     "label":f"  {cname}","value":f"×{u.get('count',1)}  {u.get('veterancy','?')}",
                     "label_w":30,"editable":False,"edit_meta":None,"val_color":DIM})
        else:
            add({"type":"row","h":22,"in_block":True,"label":"  None on record","value":"",
                 "label_w":30,"editable":False,"edit_meta":None,"val_color":DIM2})
    spc()

    hdr1("# RESEARCH")
    add({"type":"row","h":22,"in_block":True,"label":"Budget/turn","value":fmt_cr(rbudget),
         "label_w":18,"editable":True,"val_color":CYAN,
         "edit_meta":{"path":["research_budget"],"type":"float","raw":rbudget}})
    for proj in act_res:
        add({"type":"row","h":22,"in_block":True,
             "label":f"  [{proj.get('field','?')}] {proj.get('name','?')}",
             "value":f"{proj.get('progress',0.0):.1f}%",
             "label_w":38,"editable":False,"edit_meta":None,"val_color":GOLD})
    for t in (comp_tech[-6:] if comp_tech else []):
        tname = t if isinstance(t,str) else t.get("name",str(t))
        add({"type":"row","h":22,"in_block":True,"label":f"  ✓ {tname}","value":"",
             "label_w":40,"editable":False,"edit_meta":None,"val_color":GREEN})
    spc(20)
    return items

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE PANEL  (scroll + render)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProfilePanel:
    """Scrollable profile with click-to-edit."""
    LPAD = 18
    def __init__(self, lay: Layout):
        self.lay = lay; self.items = []; self.content_h = 0
        self.scrl = Scrollbar(0,0,10,100); self._hov = -1
    def update_layout(self, lay: Layout):
        self.lay = lay
        self.scrl.update_rect(lay.sw-lay.scrl_w, lay.my, lay.scrl_w, lay.mh)
    def set_items(self, items):
        self.items = items
        self.content_h = (items[-1]["y"]+items[-1]["h"]) if items else 0
        self.scrl.set_content(self.content_h, self.lay.mh)
        self.scrl.scroll = 0; self.scrl.clamp(); self._hov = -1
    def _sy(self, iy): return self.lay.my + iy - self.scrl.scroll
    def draw(self, surf):
        lay = self.lay; r = lay.main_rect
        pygame.draw.rect(surf, BG, r); surf.set_clip(r)
        fm=gf(13); fs=gf(11); f1=gf(16,mono=False); f2=gf(14,mono=False)
        fn=gf(19,mono=False); fsp=gf(13,mono=False)
        x0=r.x+self.LPAD; rw=r.w
        for i, item in enumerate(self.items):
            sy = self._sy(item["y"]); sh = item["h"]
            if sy+sh < r.y or sy > r.bottom: continue
            t = item["type"]
            if t == "nhdr":
                pygame.draw.rect(surf,PANEL2,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,ACCENT,(r.x,sy,4,sh))
                for gx in range(r.x, r.x+rw, 32):
                    pygame.draw.line(surf,(16,24,36),(gx,sy),(gx,sy+sh),1)
                tag_s = f"[{item['tag']}]"
                blit_text(surf,tag_s,x0,sy+14,f1,ACCENT)
                blit_text(surf,"  "+item["name"],x0+tw(tag_s,f1),sy+12,fn,BRIGHT)
                pygame.draw.line(surf,BORDER2,(r.x,sy+sh-1),(r.right,sy+sh-1),1)
            elif t == "hdr1":
                pygame.draw.rect(surf,PANEL2,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,ACCENT,(r.x,sy,3,sh))
                blit_text(surf,item["text"],x0,sy+10,f1,CYAN)
                pygame.draw.line(surf,BORDER,(r.x,sy+sh-1),(r.right,sy+sh-1),1)
            elif t == "hdr2":
                pygame.draw.rect(surf,PANEL3,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,TEAL2,(r.x,sy,2,sh))
                blit_text(surf,item["text"],x0,sy+8,f2,TEAL)
            elif t == "row":
                bg = BLK2 if (item.get("in_block") and i%2==0) else (BLOCK if item.get("in_block") else BG)
                pygame.draw.rect(surf,bg,(r.x,sy,rw,sh))
                if i == self._hov and item.get("editable"):
                    pygame.draw.rect(surf,HOV,(r.x,sy,rw,sh))
                lbl = item.get("label",""); val = str(item.get("value",""))
                lw_ = item.get("label_w",18); vc = item.get("val_color",TEXT)
                lbl_s = f"{lbl:<{lw_}}: "
                blit_text(surf,lbl_s,x0,sy+4,fm,DIM)
                blit_text(surf,val,x0+tw(lbl_s,fm),sy+4,fm,vc)
                if item.get("editable"):
                    pygame.draw.rect(surf,TEAL,(r.right-4,sy,2,sh))
            elif t == "bar":
                bg = BLK2 if i%2==0 else BLOCK
                pygame.draw.rect(surf,bg,(r.x,sy,rw,sh))
                if i == self._hov and item.get("editable"):
                    pygame.draw.rect(surf,HOV,(r.x,sy,rw,sh))
                lbl_s = f"{item['label']:<22} {item['pct']*100:5.1f}%"
                blit_text(surf,lbl_s,x0,sy+5,fs,DIM)
                bx = x0+tw(lbl_s,fs)+8
                draw_bar(surf,bx,sy+(sh-10)//2,160,10,item["pct"],fg=CYAN)
                blit_text(surf,item["amount"],bx+168,sy+5,fs,GOLD)
                if item.get("editable"):
                    pygame.draw.rect(surf,TEAL,(r.right-4,sy,2,sh))
            elif t == "debtbar":
                pygame.draw.rect(surf,BLOCK,(r.x,sy,rw,sh))
                lbl_s = f"{'Debt Load':<18}: "
                blit_text(surf,lbl_s,x0,sy+5,fm,DIM)
                bx = x0+tw(lbl_s,fm); pct=item["pct"]
                fc = RED_C if pct>0.5 else (GOLD if pct>0.2 else GREEN)
                draw_bar(surf,bx,sy+6,200,10,pct,fg=fc)
                blit_text(surf,f"  {pct*100:.1f}%",bx+208,sy+5,fm,DIM)
            elif t == "sep":
                my = sy+sh//2
                pygame.draw.line(surf,BORDER2,(r.x+6,my),(r.right-6,my),1)
            elif t == "sphdr":
                pygame.draw.rect(surf,PANEL3,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,GOLD2,(r.x,sy,3,sh))
                crown = "👑" if item.get("dominant") else "👥"
                lbl = f"{crown}  {item['name']}"
                blit_text(surf,lbl,x0,sy+6,fsp,GOLD)
                blit_text(surf,f"  {item['status']}",x0+tw(lbl,fsp),sy+7,gf(12,mono=False),TEAL)
        surf.set_clip(None)
        pygame.draw.rect(surf,BORDER,r,1)
        self.scrl.draw(surf)

    def on_event(self, event) -> Optional[dict]:
        lay = self.lay
        over = pygame.Rect(lay.mx,lay.my,lay.mw+lay.scrl_w,lay.mh)
        self.scrl.on_event(event, over.collidepoint(pygame.mouse.get_pos()))
        if event.type == pygame.MOUSEMOTION and lay.main_rect.collidepoint(event.pos):
            abs_y = event.pos[1]-lay.my+self.scrl.scroll; self._hov = -1
            for i,item in enumerate(self.items):
                if item["y"] <= abs_y < item["y"]+item["h"]:
                    self._hov = i if item.get("editable") else -1; break
        elif event.type == pygame.MOUSEMOTION: self._hov = -1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sr = pygame.Rect(lay.sw-lay.scrl_w,lay.my,lay.scrl_w,lay.mh)
            if lay.main_rect.collidepoint(event.pos) and not sr.collidepoint(event.pos):
                abs_y = event.pos[1]-lay.my+self.scrl.scroll
                for item in self.items:
                    if item["y"] <= abs_y < item["y"]+item["h"]:
                        if item.get("editable") and item.get("edit_meta"):
                            return {"label":item.get("label","Field"),
                                    "raw":item["edit_meta"].get("raw",""),
                                    "meta":item["edit_meta"]}
                        break
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM MAP PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SystemMapPanel:
    """2-D orbital diagram for the nation's home system."""
    PCOL = {"Terrestrial":(0,180,80),"Gas Giant":(200,120,20),
            "Ice World":(100,200,240),"Barren":(120,100,80),"Oceanic":(20,80,200)}
    def __init__(self, lay: Layout):
        self.lay = lay; self.nation = None; self.sel_planet = None
        self._prects = {}; self._btn_exp = None
    def update_layout(self, lay): self.lay = lay
    def set_nation(self, n): self.nation = n; self.sel_planet = None

    def draw(self, surf):
        lay = self.lay; r = lay.main_rect
        pygame.draw.rect(surf, BG, r)
        if not self.nation:
            blit_text(surf,"No nation selected",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        star_sys = self.nation.get("star_systems",[])
        if not star_sys:
            blit_text(surf,"No system data",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        sys0 = star_sys[0]; planets = sys0.get("planets",[])
        detail_w = 310 if self.sel_planet else 0
        map_w = r.w - detail_w; cx = r.x+map_w//2; cy = r.y+r.h//2
        # Star
        pygame.draw.circle(surf,(255,220,60),(cx,cy),22)
        pygame.draw.circle(surf,(255,255,140),(cx,cy),16)
        blit_text(surf,"★",cx-7,cy-9,gf(16,False),(255,240,100))
        max_r = min(map_w, r.h)*0.44; step = max_r/max(len(planets),1)
        self._prects = {}
        for idx, pl in enumerate(planets):
            orb_r = int(step*(idx+1))
            pygame.draw.circle(surf,(20,35,55),(cx,cy),orb_r,1)
            angle = math.pi*0.5 + idx*0.9
            px = int(cx+orb_r*math.cos(angle)); py = int(cy+orb_r*math.sin(angle))
            ptype = pl.get("type","Terrestrial"); pcol = self.PCOL.get(ptype,(80,80,120))
            dev = pl.get("devastation",0)/100.0
            if dev > 0.1:
                pcol = tuple(int(c*(1-dev)+RED_C[i]*dev) for i,c in enumerate(pcol))
            pr = 8+idx*2
            pygame.draw.circle(surf,pcol,(px,py),pr)
            pygame.draw.circle(surf,BRIGHT,(px,py),pr,1)
            if pl is self.sel_planet:
                pygame.draw.circle(surf,CYAN,(px,py),pr+5,2)
            fn = gf(11); pname = pl["name"]
            blit_text(surf,pname,px-tw(pname,fn)//2,py+pr+4,fn,TEXT)
            if pl.get("crime_rate",0)>30: pygame.draw.circle(surf,RED_C,(px+pr,py-pr),4)
            if pl.get("unrest",0)>20:     pygame.draw.circle(surf,GOLD,(px-pr,py-pr),4)
            self._prects[pl["name"]] = (pl, pygame.Rect(px-pr-2,py-pr-2,pr*2+4,pr*2+4))
        blit_text(surf,f"★  {sys0['name']}",r.x+14,r.y+12,gf(16,False),BRIGHT)
        blit_text(surf,f"{len(planets)} planet(s)",r.x+14,r.y+34,gf(11),TEAL)
        blit_text(surf,"● Crime>30%",r.x+map_w-140,r.y+14,gf(10),RED_C)
        blit_text(surf,"● Unrest>20%",r.x+map_w-140,r.y+28,gf(10),GOLD)
        # Detail drawer
        self._btn_exp = None
        if self.sel_planet:
            pl = self.sel_planet
            dr = pygame.Rect(r.right-detail_w,r.y,detail_w,r.h)
            pygame.draw.rect(surf,PANEL2,dr)
            pygame.draw.line(surf,BORDER2,(dr.x,dr.y),(dr.x,dr.bottom),1)
            corner_deco(surf,dr.x,dr.y,dr.w,dr.h,CYAN,8)
            x=dr.x+12; y=dr.y+10; f=gf(12); fs=gf(11)
            blit_text(surf,pl["name"],x,y,gf(15,False),BRIGHT); y+=22
            pygame.draw.line(surf,BORDER2,(dr.x+4,y),(dr.right-4,y),1); y+=8
            for lbl,val in [("Type",pl.get("type","?")),("Size",pl.get("size","?")),
                             ("Habitability",f"{pl.get('habitability',0):.0f}%"),
                             ("Devastation",f"{pl.get('devastation',0):.0f}%"),
                             ("Crime Rate",f"{pl.get('crime_rate',0):.0f}%"),
                             ("Unrest",f"{pl.get('unrest',0):.0f}%")]:
                blit_text(surf,f"{lbl:<16}: ",x,y,fs,DIM)
                blit_text(surf,val,x+tw(f"{lbl:<16}: ",fs),y,fs,TEXT); y+=18
            y+=4; blit_text(surf,"SETTLEMENTS",x,y,fs,TEAL); y+=16
            for s in pl.get("settlements",[]):
                blit_text(surf,f"  › {s['name']}  pop:{fmt_pop(s.get('population',0))}",x,y,fs,TEXT); y+=16
                for sp in s.get("populations",[]):
                    loy=sp.get("loyalty",0); lc=GREEN if loy>=70 else(GOLD if loy>=40 else RED_C)
                    blit_text(surf,f"    {sp['species'][:12]}  loy:{loy:.0f}  hap:{sp.get('happiness',0):.0f}",
                              x,y,gf(10),lc); y+=14
            y+=6; blit_text(surf,"ORBITAL BUILDINGS",x,y,fs,TEAL); y+=16
            obs = pl.get("orbital_buildings",[])
            if obs:
                for ob in obs: blit_text(surf,f"  ⊕ {ob.get('type','?')} [{ob.get('status','?')}]",x,y,fs,DIM); y+=16
            else: blit_text(surf,"  None",x,y,fs,DIM2)
            bx = dr.x+(dr.w-160)//2; by = dr.bottom-42
            self._btn_exp = Button((bx,by,160,28),"[EXPORT SYSTEM  D]",small=True)
            self._btn_exp.draw(surf)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, state) -> Optional[str]:
        if self._btn_exp and self._btn_exp.on_event(event) and self.nation:
            return self._export_discord(self.nation)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for pname,(pl,pr) in self._prects.items():
                if pr.collidepoint(event.pos):
                    self.sel_planet = pl; return None
        return None

    def _export_discord(self, nation) -> str:
        star_sys = nation.get("star_systems",[])
        if not star_sys: return ""
        ss = star_sys[0]; tag = nation_tag(nation["name"]); L=[]; ln=L.append
        ln(f"-# [{tag}] {nation['name'].upper()} — SYSTEM REPORT")
        ln(f"# STAR SYSTEM: {ss['name']}")
        for pl in ss.get("planets",[]):
            ln("```")
            ln(f"  {pl['name']}")
            for k,v in [("Type",pl.get("type","?")),("Size",pl.get("size","?")),
                         ("Habitability",f"{pl.get('habitability',0):.0f}%"),
                         ("Devastation",f"{pl.get('devastation',0):.0f}%"),
                         ("Crime Rate",f"{pl.get('crime_rate',0):.0f}%"),
                         ("Unrest",f"{pl.get('unrest',0):.0f}%")]:
                ln(f"    {k:<16}: {v}")
            for s in pl.get("settlements",[]): ln(f"      › {s['name']}  pop:{fmt_pop(s.get('population',0))}")
            for ob in pl.get("orbital_buildings",[]): ln(f"      ⊕ {ob.get('type','?')} [{ob.get('status','?')}]")
            ln("```")
        return "\n".join(L)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVENT LOG PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventLogPanel:
    """Filter / approve / edit / delete d20 events."""
    RH = 64
    SEV_COL = {"Critical":RED_C,"Major":GOLD,"Minor":CYAN,"Info":DIM}
    def __init__(self, lay: Layout):
        self.lay=lay; self.state=None; self.nation_filter=None
        self.scrl=Scrollbar(0,0,10,100); self._hov=-1; self._events=[]
    def update_layout(self, lay):
        self.lay=lay; self.scrl.update_rect(lay.sw-lay.scrl_w,lay.my,lay.scrl_w,lay.mh)
    def set_state(self, state, nation_filter=None):
        self.state=state; self.nation_filter=nation_filter; self._refresh()
    def _refresh(self):
        if not self.state: self._events=[]; return
        self._events=EventLog(self.state).filter(nation=self.nation_filter)
        self.scrl.set_content(len(self._events)*self.RH+60, self.lay.mh); self.scrl.clamp()

    def draw(self, surf):
        lay=self.lay; r=lay.main_rect
        pygame.draw.rect(surf,BG,r)
        if not self.state:
            blit_text(surf,"No state loaded.",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        # Toolbar
        TH=36; pygame.draw.rect(surf,PANEL2,(r.x,r.y,r.w,TH))
        pygame.draw.line(surf,BORDER2,(r.x,r.y+TH),(r.right,r.y+TH),1)
        turn=self.state.get("turn",1)
        approved=sum(1 for e in self._events if e.get("gm_approved"))
        blit_text(surf,f"T{turn}  Events: {len(self._events)}  Approved: {approved}  |  D = Export Galactic News",
                  r.x+14,r.y+11,gf(12),TEAL)
        if not self._events:
            blit_text(surf,"No events — advance the turn to generate d20 rolls.",r.x+20,r.y+TH+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); self.scrl.draw(surf); return
        surf.set_clip(pygame.Rect(r.x,r.y+TH,r.w,r.h-TH))
        f=gf(12); fs=gf(11); f10=gf(10)
        for i,ev in enumerate(self._events):
            iy=r.y+TH+i*self.RH-self.scrl.scroll
            if iy+self.RH<r.y or iy>r.bottom: continue
            sev=ev.get("severity","Info"); scol=self.SEV_COL.get(sev,DIM)
            bg=PANEL if i%2==0 else PANEL2
            pygame.draw.rect(surf,bg,(r.x,iy,r.w,self.RH))
            if i==self._hov: pygame.draw.rect(surf,HOV,(r.x,iy,r.w,self.RH))
            pygame.draw.rect(surf,scol,(r.x,iy,3,self.RH))
            icon=SEVERITY_EMOJI.get(sev,"📊")
            scope=ev.get("nation","?"); planet=ev.get("planet")
            if planet: scope+=f" | {planet}"
            blit_text(surf,f"{icon} {ev.get('title','?')}",r.x+12,iy+6,f,BRIGHT)
            blit_text(surf,scope,r.x+12,iy+24,fs,TEAL)
            roll_s=f"d20={ev.get('d20_roll','?')}"; roll=ev.get("d20_roll",10)
            rc=RED_C if roll<=3 else(GOLD if roll<=7 else(GREEN if roll>=17 else DIM))
            blit_text(surf,roll_s,r.x+12,iy+42,f10,rc)
            blit_text(surf,f"T{ev.get('turn','?')}  {sev}",r.x+80,iy+42,f10,DIM)
            # Body preview
            body=ev.get("body",""); bp=body[:100]+("…" if len(body)>100 else "")
            blit_text(surf,bp,r.x+200,iy+42,f10,DIM2)
            # Approve button area
            appr=ev.get("gm_approved",False)
            ax=r.right-160
            pygame.draw.rect(surf,GREEN2 if appr else BTNBG,(ax,iy+12,130,22),border_radius=2)
            pygame.draw.rect(surf,GREEN if appr else BORDER2,(ax,iy+12,130,22),1,border_radius=2)
            astr="✓  APPROVED" if appr else "  APPROVE"
            blit_text(surf,astr,ax+(130-tw(astr,f10))//2,iy+18,f10,BRIGHT)
            edited=ev.get("gm_edited",False)
            if edited: blit_text(surf,"[edited]",ax,iy+38,f10,TEAL)
        surf.set_clip(None); self.scrl.draw(surf)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, edit_overlay: EditOverlay) -> Optional[str]:
        lay=self.lay; r=lay.main_rect
        over=r.collidepoint(pygame.mouse.get_pos())
        self.scrl.on_event(event, over)
        TH=36
        if event.type==pygame.MOUSEMOTION and r.collidepoint(event.pos):
            abs_y=event.pos[1]-r.y-TH+self.scrl.scroll
            self._hov=max(0,abs_y//self.RH) if abs_y>=0 else -1
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and r.collidepoint(event.pos):
            abs_y=event.pos[1]-r.y-TH+self.scrl.scroll
            idx=abs_y//self.RH
            if 0<=idx<len(self._events):
                ev=self._events[idx]; ax=r.right-160
                if event.pos[0]>=ax:
                    EventLog(self.state).approve(ev["event_id"]); self._refresh()
                else:
                    edit_overlay.open(f"Event {ev['event_id']} body",ev.get("body",""),
                                      {"path":["_event",ev["event_id"]],"type":"str","raw":ev.get("body","")})
        return None

    def apply_body_edit(self, event_id, new_body):
        EventLog(self.state).edit_body(event_id, new_body); self._refresh()

    def export_news(self) -> str:
        if not self.state: return ""
        return discord_galactic_news(self.state, self.state.get("turn",1))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARKET PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketPanel:
    """Live price table + modifier editor."""
    RH = 30
    def __init__(self, lay: Layout):
        self.lay=lay; self.state=None; self._hov=-1
        self._price_rects=[]; self._btn_fluc=None; self._btn_exp=None
    def update_layout(self, lay): self.lay=lay
    def set_state(self, state): self.state=state

    def draw(self, surf):
        lay=self.lay; r=lay.main_rect
        pygame.draw.rect(surf,BG,r)
        if not self.state:
            blit_text(surf,"No state loaded.",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        me=MarketEngine(self.state.get("market",{})); prices=me.get_prices()
        x=r.x+20; y=r.y+14; f=gf(13); fh=gf(15,False); fs=gf(11); f10=gf(10)
        blit_text(surf,"# GALACTIC MARKET",x,y,fh,CYAN); y+=30
        HDR=f"  {'Resource':<20} {'Base':>10}  {'Modifier':>10}  {'Effective':>12}  Trend  (sparkline)"
        blit_text(surf,HDR,x,y,fs,DIM); y+=6
        pygame.draw.line(surf,BORDER2,(x,y),(r.right-20,y),1); y+=8
        TRCOL={"▲":GREEN,"▼":RED_C,"─":DIM}
        self._price_rects=[]
        for i,row in enumerate(prices):
            iy=y+i*self.RH; bg=BLOCK if i%2==0 else BLK2
            pygame.draw.rect(surf,bg,(r.x,iy,r.w,self.RH))
            if i==self._hov: pygame.draw.rect(surf,HOV,(r.x,iy,r.w,self.RH))
            pygame.draw.rect(surf,TEAL2,(r.x,iy,2,self.RH))
            ln_=f"  {row['resource']:<20} {row['base']:>10.2f} cr  x{row['modifier']:>8.3f}  {row['effective']:>10.2f} cr"
            blit_text(surf,ln_,x,iy+8,f,TEXT)
            tc=TRCOL.get(row["trend"],DIM)
            blit_text(surf,row["trend"],x+tw(ln_,f)+6,iy+8,f,tc)
            # Sparkline
            hist=row.get("history",[]); sx=r.right-200; sy=iy+3; sw_=150; sh_=24
            if len(hist)>=2:
                mn=min(hist); mx_=max(hist); rng=max(mx_-mn,0.001)
                pts=[(sx+int(j/(len(hist)-1)*sw_),
                      sy+int((1-(h-mn)/rng)*sh_)) for j,h in enumerate(hist)]
                pygame.draw.lines(surf,TEAL,False,pts,1)
            blit_text(surf,"[edit mod]",r.right-60,iy+10,f10,DIM)
            self._price_rects.append((row, pygame.Rect(r.x,iy,r.w,self.RH)))
        by=r.bottom-50; bx=x
        self._btn_fluc=Button((bx,by,140,30),"[ FLUCTUATE ]",accent=True)
        self._btn_exp =Button((bx+154,by,180,30),"[ EXPORT MARKET  D ]")
        self._btn_fluc.draw(surf); self._btn_exp.draw(surf)
        psst=self.state.get("market",{}).get("psst_nations",[])
        if psst: blit_text(surf,f"PSST: {', '.join(psst)}",x,by-22,fs,GOLD)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, edit_overlay: EditOverlay, sm) -> Optional[str]:
        r=self.lay.main_rect
        if event.type==pygame.MOUSEMOTION and r.collidepoint(event.pos):
            for i,(_,pr) in enumerate(self._price_rects):
                if pr.collidepoint(event.pos): self._hov=i; break
            else: self._hov=-1
        if self._btn_fluc and self._btn_fluc.on_event(event):
            MarketEngine(self.state.get("market",{})).fluctuate_all()
            sm.mark_dirty(); sm.autosave(); set_status("Market fluctuated.",GOLD); return None
        if self._btn_exp and self._btn_exp.on_event(event):
            return discord_market_report(self.state)
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for row,pr in self._price_rects:
                if pr.collidepoint(event.pos):
                    edit_overlay.open(f"{row['resource']} modifier",row["modifier"],
                                      {"path":["_market",row["resource"]],"type":"float","raw":row["modifier"]})
                    return None
        if self._btn_fluc: self._btn_fluc.on_event(event)
        if self._btn_exp:  self._btn_exp.on_event(event)
        return None

    def apply_market_edit(self, resource, new_val, sm):
        MarketEngine(self.state.get("market",{})).set_modifier(resource, new_val)
        sm.mark_dirty(); sm.autosave(); set_status(f"{resource} modifier → {new_val:.3f}",GREEN)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADE ROUTE MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TradeModal:
    """Full-screen modal for building a trade route."""
    DIST_OPTS = list(PIRATE_BASE_RISK.keys())
    def __init__(self):
        self.active=False; self.state=None; self._exporter=""; self._importer=""
        self._resource=RESOURCE_NAMES[0]; self._export_pct=0.25; self._escort=0.0
        self._modifier=1.0; self._dist_idx=0; self._transits=[]; self._preview=None
        self._err=""; self._drag_pct=False; self._drag_esc=False
        self._res_rects=[]; self._dist_rects=[]; self._pct_slider=None; self._esc_slider=None
        self._btn_confirm=None; self._btn_export=None; self._btn_cancel=None

    def open(self, state, sel_nation_name):
        self.active=True; self.state=state
        self._exporter=sel_nation_name or ""; self._importer=""
        self._preview=None; self._err=""; self._transits=[]; self._recalc()

    def close(self): self.active=False

    def _nation(self, name):
        for n in self.state.get("nations",[]): 
            if n["name"]==name: return n
        return None

    def _recalc(self):
        if not self.state or not self._exporter or not self._importer: return
        en=self._nation(self._exporter)
        if not en: return
        try:
            eng=TradeRouteEngine(self.state)
            avail=eng.available_export(en,self._resource)
            qty=avail*self._export_pct
            dist=self.DIST_OPTS[self._dist_idx]
            self._preview=eng.calculate(self._exporter,self._importer,self._resource,
                                        qty,self._transits,dist,self._escort,self._modifier)
            self._err=""
        except Exception as e: self._err=str(e); self._preview=None

    def draw(self, surf, lay: Layout):
        if not self.active: return
        ov=pygame.Surface((lay.sw,lay.sh),pygame.SRCALPHA); ov.fill((0,0,0,180)); surf.blit(ov,(0,0))
        mw=min(lay.sw-60,920); mh=min(lay.sh-60,660)
        mx=(lay.sw-mw)//2; my=(lay.sh-mh)//2; r=pygame.Rect(mx,my,mw,mh)
        pygame.draw.rect(surf,MODALBG,r); pygame.draw.rect(surf,MODALBDR,r,2)
        corner_deco(surf,mx,my,mw,mh,CYAN,12)
        fh=gf(16,False); f=gf(13); fs=gf(11); f10=gf(10)
        x=mx+20; y=my+14
        blit_text(surf,"TRADE ROUTE BUILDER",x,y,fh,CYAN); y+=28
        pygame.draw.line(surf,BORDER2,(mx+4,y),(mx+mw-4,y),1); y+=10
        col1w=(mw-60)//2; col2x=x+col1w+20; cy=y

        # --- LEFT COLUMN ---
        blit_text(surf,"Exporter:",x,cy,fs,DIM); cy+=16
        pygame.draw.rect(surf,BORDER2 if self._exporter else BORDER,(x,cy,col1w-10,22),1)
        blit_text(surf,self._exporter or "(select in sidebar)",x+4,cy+4,f,BRIGHT if self._exporter else DIM)
        cy+=26; blit_text(surf,"Importer:",x,cy,fs,DIM); cy+=16
        pygame.draw.rect(surf,BORDER,(x,cy,col1w-10,22),1)
        blit_text(surf,self._importer or "(type nation name)",x+4,cy+4,f,BRIGHT if self._importer else DIM)
        self._imp_rect=pygame.Rect(x,cy,col1w-10,22); cy+=26

        blit_text(surf,"Resource:",x,cy,fs,DIM); cy+=16
        slot_w=(col1w-10)//len(RESOURCE_NAMES)-2; self._res_rects=[]
        for i,rn in enumerate(RESOURCE_NAMES):
            sel=rn==self._resource; rx=x+i*(slot_w+2)
            bg=TABACT if sel else PANEL2
            pygame.draw.rect(surf,bg,(rx,cy,slot_w,20),border_radius=2)
            if sel: pygame.draw.rect(surf,CYAN,(rx,cy,slot_w,20),1,border_radius=2)
            blit_text(surf,rn[:7],rx+2,cy+4,f10,BRIGHT if sel else DIM)
            self._res_rects.append((rn,pygame.Rect(rx,cy,slot_w,20)))
        cy+=28
        blit_text(surf,f"Export %:  {self._export_pct*100:.0f}%",x,cy,fs,DIM); cy+=16
        sw_=col1w-10; draw_bar(surf,x,cy,sw_,12,self._export_pct,fg=CYAN)
        self._pct_slider=pygame.Rect(x,cy,sw_,12); cy+=20
        if self._exporter and self.state:
            en=self._nation(self._exporter)
            if en:
                eng=TradeRouteEngine(self.state)
                avail=eng.available_export(en,self._resource); qty=avail*self._export_pct
                blit_text(surf,f"Avail: {fmt_int(avail)}  Qty/turn: {fmt_int(qty)}",x,cy,fs,TEAL)
        cy+=20

        blit_text(surf,"Pirate distance:",x,cy,fs,DIM); cy+=16
        dslot=(col1w-10)//len(self.DIST_OPTS)-2; self._dist_rects=[]
        for i,d in enumerate(self.DIST_OPTS):
            sel=i==self._dist_idx; dx=x+i*(dslot+2)
            bg=TABACT if sel else PANEL2
            pygame.draw.rect(surf,bg,(dx,cy,dslot,20),border_radius=2)
            if sel: pygame.draw.rect(surf,GOLD,(dx,cy,dslot,20),1,border_radius=2)
            blit_text(surf,d[:9],dx+2,cy+4,f10,BRIGHT if sel else DIM)
            self._dist_rects.append((i,pygame.Rect(dx,cy,dslot,20)))
        cy+=28
        blit_text(surf,f"Escort: {self._escort:.0f}%",x,cy,fs,DIM); cy+=16
        draw_bar(surf,x,cy,sw_,12,self._escort/100,fg=GREEN2)
        self._esc_slider=pygame.Rect(x,cy,sw_,12); cy+=24
        blit_text(surf,f"Route modifier: x{self._modifier:.2f}",x,cy,fs,DIM); cy+=16

        # transit list
        blit_text(surf,"Transit nations:",x,cy,fs,DIM); cy+=16
        for t in self._transits:
            blit_text(surf,f"  {t['nation']}  {t['tax_rate']*100:.1f}%",x,cy,f10,TEXT); cy+=16

        # --- RIGHT COLUMN: live preview ---
        ry=y; blit_text(surf,"ROUTE PREVIEW",col2x,ry,gf(15,False),GOLD); ry+=28
        pygame.draw.line(surf,BORDER2,(col2x,ry),(mx+mw-20,ry),1); ry+=10
        if self._preview:
            P=self._preview
            for lbl,val,vc in [
                ("Gross/turn",       fmt_cr(P["gross"]),                     BRIGHT),
            ]:
                blit_text(surf,f"{lbl:<22}: ",col2x,ry,f,DIM); blit_text(surf,val,col2x+tw(f"{lbl:<22}: ",f),ry,f,vc); ry+=22
            for t in P.get("transit_taxes",[]):
                blit_text(surf,f"  Transit {t['nation'][:14]:<14}: -{fmt_cr(t['amount'])}",col2x,ry,f,RED_C); ry+=22
            for lbl,val,vc in [
                ("NET/turn",         fmt_cr(P["net_income"]),                 GREEN),
                ("",None,TEXT),
                ("Pirate dist.",     P["pirate_distance"],                    DIM),
                ("Escort",          f"{P['escort_pct']:.0f}%",              DIM),
                ("Pirate risk",     f"{P['pirate_risk_pct']:.1f}% / turn",   RED_C if P["pirate_risk_pct"]>15 else GOLD),
                ("Exp. loss/turn",   fmt_cr(P["expected_pirate_loss"]),      RED_C),
                ("Unit price",      f"{P['effective_price']:.4f} cr",       DIM),
                ("Qty/turn",         fmt_int(P["quantity_per_turn"]),        DIM),
            ]:
                if val is None: ry+=8; continue
                blit_text(surf,f"{lbl:<22}: ",col2x,ry,f,DIM); blit_text(surf,val,col2x+tw(f"{lbl:<22}: ",f),ry,f,vc); ry+=22
            ry+=6; blit_text(surf,"Pirate Risk",col2x,ry,fs,DIM); ry+=14
            prc=P["pirate_risk_pct"]/100; fc=RED_C if prc>0.2 else(GOLD if prc>0.1 else GREEN)
            draw_bar(surf,col2x,ry,min(200,mw-col1w-60),10,prc,fg=fc); ry+=18
        elif self._err:
            blit_text(surf,f"Error: {self._err}",col2x,ry,fs,RED_C)
        else:
            blit_text(surf,"Set exporter + importer to preview.",col2x,ry,fs,DIM)

        # Action buttons
        bw=130; bby=my+mh-44; bx_=mx+mw-bw*3-30
        self._btn_confirm=Button((bx_,bby,bw,30),"[ CONFIRM ROUTE ]",accent=True)
        self._btn_export =Button((bx_+bw+10,bby,bw,30),"[ DISCORD EXPORT ]")
        self._btn_cancel =Button((bx_+bw*2+20,bby,bw,30),"[ CANCEL ]")
        for b in (self._btn_confirm,self._btn_export,self._btn_cancel): b.draw(surf)
        if self._err: blit_text(surf,self._err,mx+20,bby+8,fs,RED_C)

    def on_event(self, event, lay: Layout, sm) -> Optional[str]:
        if not self.active: return None
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: self.close(); return None
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for rn,r in self._res_rects:
                if r.collidepoint(event.pos): self._resource=rn; self._recalc()
            for i,r in self._dist_rects:
                if r.collidepoint(event.pos): self._dist_idx=i; self._recalc()
            if self._btn_cancel and self._btn_cancel.on_event(event):
                self.close(); return None
            if self._btn_export and self._btn_export.on_event(event) and self._preview:
                rid=TradeRouteEngine.next_route_id(self.state) if hasattr(TradeRouteEngine,"next_route_id") else "TR????"
                return discord_trade_route(self._preview, rid)
            if self._btn_confirm and self._btn_confirm.on_event(event) and self._preview:
                eng=TradeRouteEngine(self.state); dist=self.DIST_OPTS[self._dist_idx]
                route=eng.build(self._preview,dist,"")
                self.state.setdefault("trade_routes",[]).append(route)
                sm.mark_dirty(); sm.autosave()
                set_status(f"Route {route['id']} created: {route['name']}",GREEN); self.close(); return "confirmed"
            if self._pct_slider and self._pct_slider.collidepoint(event.pos): self._drag_pct=True
            if self._esc_slider and self._esc_slider.collidepoint(event.pos): self._drag_esc=True
        if event.type==pygame.MOUSEBUTTONUP: self._drag_pct=False; self._drag_esc=False
        if event.type==pygame.MOUSEMOTION:
            if self._drag_pct and self._pct_slider:
                rel=(event.pos[0]-self._pct_slider.x)/max(1,self._pct_slider.w)
                self._export_pct=max(0.01,min(1.0,rel)); self._recalc()
            if self._drag_esc and self._esc_slider:
                rel=(event.pos[0]-self._esc_slider.x)/max(1,self._esc_slider.w)
                self._escort=max(0.0,min(100.0,rel*100)); self._recalc()
        for b in (self._btn_confirm,self._btn_export,self._btn_cancel):
            if b: b.on_event(event)
        return None

    def set_exporter(self, name): self._exporter=name; self._recalc()
    def set_importer(self, name): self._importer=name; self._recalc()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADVANCE TURN MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TurnModal:
    """Shows d20 roll results after advancing the turn."""
    def __init__(self):
        self.active=False; self.events=[]; self.turn=0
        self._scrl=Scrollbar(0,0,10,100); self._btn_close=None

    def open(self, events, turn):
        self.active=True; self.events=events; self.turn=turn
        self._scrl.set_content(max(300,len(events)*54+100),520); self._scrl.scroll=0

    def close(self): self.active=False

    def draw(self, surf, lay: Layout):
        if not self.active: return
        ov=pygame.Surface((lay.sw,lay.sh),pygame.SRCALPHA); ov.fill((0,0,0,190)); surf.blit(ov,(0,0))
        mw=min(lay.sw-100,780); mh=min(lay.sh-80,560)
        mx=(lay.sw-mw)//2; my=(lay.sh-mh)//2; r=pygame.Rect(mx,my,mw,mh)
        pygame.draw.rect(surf,MODALBG,r); pygame.draw.rect(surf,ACCENT,r,2)
        corner_deco(surf,mx,my,mw,mh,GOLD,12)
        fh=gf(15,False); f=gf(12); fs=gf(11); f10=gf(10)
        SEV_COL={"Critical":RED_C,"Major":GOLD,"Minor":CYAN,"Info":DIM}
        blit_text(surf,f"TURN {self.turn} COMPLETE — d20 PLANETARY EVENTS",mx+16,my+12,fh,GOLD)
        blit_text(surf,f"{len(self.events)} event(s) generated",mx+16,my+34,fs,DIM)
        pygame.draw.line(surf,BORDER2,(mx+4,my+50),(mx+mw-4,my+50),1)
        lh=mh-110; lr=pygame.Rect(mx+2,my+54,mw-14,lh)
        self._scrl.update_rect(mx+mw-12,my+54,10,lh); self._scrl.view_h=lh
        surf.set_clip(lr)
        for i,ev in enumerate(self.events):
            iy=my+56+i*54-self._scrl.scroll
            if iy+54<lr.y or iy>lr.bottom: continue
            sev=ev.get("severity","Info"); scol=SEV_COL.get(sev,DIM)
            bg=PANEL if i%2==0 else PANEL2
            pygame.draw.rect(surf,bg,(mx+4,iy,mw-18,52))
            pygame.draw.rect(surf,scol,(mx+4,iy,3,52))
            roll=ev.get("d20_roll",0); rc=RED_C if roll<=3 else(GOLD if roll<=7 else(GREEN if roll>=17 else DIM))
            blit_text(surf,f"d20={roll}",mx+14,iy+6,f,rc)
            blit_text(surf,f"{SEVERITY_EMOJI.get(sev,'📊')} {ev.get('title','?')}",mx+70,iy+6,f,BRIGHT)
            scope=ev.get("nation","?")
            if ev.get("planet"): scope+=f" | {ev['planet']}"
            blit_text(surf,scope,mx+14,iy+24,fs,TEAL)
            body=ev.get("body",""); bp=body[:120]+("…" if len(body)>120 else "")
            blit_text(surf,bp,mx+14,iy+40,f10,DIM2)
        surf.set_clip(None); self._scrl.draw(surf)
        bx=(lay.sw-140)//2; by=my+mh-40
        self._btn_close=Button((bx,by,140,30),"[ CLOSE ]",accent=True)
        self._btn_close.draw(surf)

    def on_event(self, event) -> bool:
        """Returns True when modal should close."""
        self._scrl.on_event(event, True)
        if self._btn_close and self._btn_close.on_event(event): return True
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE):
            return True
        if self._btn_close: self._btn_close.on_event(event)
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLIPBOARD HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    try:
        import subprocess, platform
        p=platform.system()
        if p=="Linux":
            for cmd in (["xclip","-selection","clipboard"],["xsel","--clipboard","--input"]):
                try:
                    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
                    proc.communicate(text.encode()); return True
                except FileNotFoundError: continue
        elif p=="Darwin":
            subprocess.Popen(["pbcopy"],stdin=subprocess.PIPE).communicate(text.encode()); return True
        elif p=="Windows":
            subprocess.Popen(["clip"],stdin=subprocess.PIPE,shell=True).communicate(text.encode()); return True
    except Exception: pass
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN APPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class App:
    """
    Carmine NRP GM Tool — main application loop.

    State machine
    -------------
      tab 0  PROFILE   – ProfilePanel + EditOverlay
      tab 1  SYSTEM MAP – SystemMapPanel
      tab 2  EVENT LOG  – EventLogPanel + EditOverlay
      tab 3  MARKET     – MarketPanel + EditOverlay
      modal  TRADE      – TradeModal (R key)
      modal  TURN       – TurnModal (T key)
    """
    def __init__(self, state_file: Optional[str] = None):
        pygame.init(); pygame.display.set_caption(f"Carmine NRP GM Tool {VERSION}")
        self.screen = pygame.display.set_mode((1280,720), pygame.RESIZABLE)
        self.clock  = pygame.time.Clock()
        self.lay    = Layout(1280, 720)

        # Engine
        self.sm     = StateManager(state_file or "carmine_state.json")
        loaded      = self.sm.load() if state_file else False
        if not loaded and state_file:
            set_status(f"Could not load {state_file}", RED_C)

        # Widgets
        self.tab_bar     = TabBar(self.lay, TAB_NAMES)
        self.left        = LeftPanel(self.lay)
        self.profile     = ProfilePanel(self.lay)
        self.sysmap      = SystemMapPanel(self.lay)
        self.evlog       = EventLogPanel(self.lay)
        self.market      = MarketPanel(self.lay)
        self.edit        = EditOverlay()
        self.trade_modal = TradeModal()
        self.turn_modal  = TurnModal()

        self._refresh_nation_list()
        self._load_nation(0)

    # ── Data helpers ──────────────────────────────

    def _refresh_nation_list(self):
        names = self.sm.nation_names()
        self.left.set_nations(names, self.left.selected)

    def _load_nation(self, idx: int):
        names = self.sm.nation_names()
        if not names: return
        idx = max(0, min(idx, len(names)-1))
        self.left.selected = idx
        nation = self.sm.state.get("nations",[])[idx]
        self.profile.set_items(build_profile_items(nation, self.sm.state))
        self.sysmap.set_nation(nation)
        self.evlog.set_state(self.sm.state, nation["name"])
        self.market.set_state(self.sm.state)

    def _current_nation(self) -> Optional[dict]:
        nations = self.sm.state.get("nations",[])
        if not nations: return None
        idx = self.left.selected
        return nations[min(idx, len(nations)-1)]

    def _do_discord_export(self):
        """Export currently-active panel to clipboard."""
        tab = self.tab_bar.active; nation = self._current_nation()
        if tab == 0 and nation:
            text = discord_profile(nation, self.sm.state)
        elif tab == 1 and nation:
            text = self.sysmap._export_discord(nation)
        elif tab == 2:
            text = self.evlog.export_news()
        elif tab == 3:
            text = discord_market_report(self.sm.state)
        else: return
        ok = copy_to_clipboard(text)
        set_status("Discord export copied to clipboard!" if ok else "Clipboard unavailable — see terminal.", GREEN if ok else GOLD)
        print("\n" + "="*60 + "\n" + text + "\n" + "="*60)

    def _do_advance_turn(self):
        if not self.sm.state.get("nations"): set_status("No nations loaded.",RED_C); return
        set_status("Advancing turn…", GOLD)
        pygame.display.flip()
        events = advance_turn(self.sm)
        turn   = self.sm.state.get("turn",1)
        self.turn_modal.open(events, turn)
        self._refresh_nation_list()
        self._load_nation(self.left.selected)
        set_status(f"Turn {turn} advanced. {len(events)} events generated.", GREEN)

    # ── Edit commit ───────────────────────────────

    def _commit_edit(self):
        raw = self.edit.text; meta = self.edit.meta
        if meta is None: self.edit.close(); return
        path = meta.get("path",[])
        # Event body edit
        if path and path[0]=="_event":
            self.evlog.apply_body_edit(path[1], raw)
            self.edit.close(); set_status("Event body updated.",GREEN); return
        # Market modifier edit
        if path and path[0]=="_market":
            try:
                val = float(raw.strip())
                self.market.apply_market_edit(path[1], val, self.sm)
            except ValueError: set_status("Invalid number.",RED_C)
            self.edit.close(); return
        # Nation field edit
        nation = self._current_nation()
        if nation and apply_edit(nation, meta, raw):
            recalc_loyalty_happiness(nation)
            self.sm.mark_dirty(); self.sm.autosave()
            self.profile.set_items(build_profile_items(nation, self.sm.state))
            set_status(f"Updated: {path}", GREEN)
        else:
            set_status("Invalid value — edit discarded.", RED_C)
        self.edit.close()

    # ── Main loop ─────────────────────────────────

    def run(self):
        running = True; dt = 0.0
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False; break
                if event.type == pygame.VIDEORESIZE:
                    sw, sh = event.w, event.h
                    self.screen = pygame.display.set_mode((sw,sh), pygame.RESIZABLE)
                    self.lay.update(sw,sh)
                    for obj in (self.tab_bar,self.left,self.profile,self.sysmap,
                                self.evlog,self.market):
                        obj.update_layout(self.lay)

                # Turn modal absorbs all events when open
                if self.turn_modal.active:
                    if self.turn_modal.on_event(event): self.turn_modal.close()
                    continue

                # Trade modal
                if self.trade_modal.active:
                    result = self.trade_modal.on_event(event, self.lay, self.sm)
                    if result and result != "confirmed":
                        ok = copy_to_clipboard(result)
                        set_status("Trade route export copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)
                    if result == "confirmed": self._load_nation(self.left.selected)
                    continue

                # Edit overlay
                if self.edit.active:
                    res = self.edit.on_event(event)
                    if res == "confirm": self._commit_edit()
                    elif res == "cancel": self.edit.close(); set_status("Edit cancelled.",DIM)
                    continue

                # Global keyboard shortcuts
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_s: self.sm.autosave(); set_status("Saved.",GREEN)
                    elif k == pygame.K_d: self._do_discord_export()
                    elif k == pygame.K_t: self._do_advance_turn()
                    elif k == pygame.K_r:
                        n = self._current_nation()
                        self.trade_modal.open(self.sm.state, n["name"] if n else "")
                    elif k == pygame.K_UP:
                        self._load_nation(self.left.selected - 1)
                    elif k == pygame.K_DOWN:
                        self._load_nation(self.left.selected + 1)
                    elif k == pygame.K_ESCAPE: running = False; break
                    elif k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                        delta = -self.profile.lay.mh if k==pygame.K_PAGEUP else self.profile.lay.mh
                        self.profile.scrl.scroll = max(0, self.profile.scrl.scroll + delta)
                        self.profile.scrl.clamp()

                # Tab bar
                new_tab = self.tab_bar.on_event(event)
                if new_tab is not None: self._load_nation(self.left.selected)

                # Left panel
                nation_idx, action = self.left.on_event(event)
                if nation_idx is not None: self._load_nation(nation_idx)
                if action == "save":  self.sm.autosave(); set_status("Saved.",GREEN)
                if action == "disc":  self._do_discord_export()
                if action == "adv":   self._do_advance_turn()
                if action == "trade":
                    n = self._current_nation()
                    self.trade_modal.open(self.sm.state, n["name"] if n else "")

                # Panel events
                tab = self.tab_bar.active
                if tab == 0:
                    hit = self.profile.on_event(event)
                    if hit: self.edit.open(hit["label"], hit["raw"], hit["meta"])
                elif tab == 1:
                    result = self.sysmap.on_event(event, self.sm.state)
                    if result:
                        ok = copy_to_clipboard(result)
                        set_status("System export copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)
                elif tab == 2:
                    self.evlog.on_event(event, self.edit)
                elif tab == 3:
                    result = self.market.on_event(event, self.edit, self.sm)
                    if result:
                        ok = copy_to_clipboard(result)
                        set_status("Market report copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)

            # ── DRAW ─────────────────────────────────────
            self.screen.fill(BG)
            tab = self.tab_bar.active
            n   = self._current_nation()
            nname = n["name"] if n else "—"
            state = self.sm.state
            draw_top_bar(self.screen, self.lay, nname,
                         state.get("turn",1), state.get("year",2200),
                         state.get("quarter",1), self.sm._dirty)
            self.tab_bar.draw(self.screen)
            self.left.draw(self.screen, state.get("turn",1),
                           state.get("year",2200), state.get("quarter",1))
            if tab == 0: self.profile.draw(self.screen)
            elif tab == 1: self.sysmap.draw(self.screen)
            elif tab == 2: self.evlog.draw(self.screen)
            elif tab == 3: self.market.draw(self.screen)
            draw_status_bar(self.screen, self.lay)
            self.edit.draw(self.screen, self.lay, dt)
            self.turn_modal.draw(self.screen, self.lay)
            self.trade_modal.draw(self.screen, self.lay)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LeftPanel:
    """Nation list sidebar with action buttons."""
    ROW_H = 40; PAD = 8

    def __init__(self, lay: Layout):
        self.lay = lay; self.names = []; self.scroll = 0
        self.selected = 0; self._hov = -1

    def update_layout(self, lay: Layout): self.lay = lay
    def set_nations(self, names, sel=0): self.names = names; self.selected = sel

    def _buttons(self):
        lw = self.lay.lw; sh = self.lay.sh; p = self.PAD; bw = lw - p*2
        return {
            "save":  Button((p, sh-130, bw, 26), "[ SAVE  S ]",  accent=True),
            "disc":  Button((p, sh-100, bw, 26), "[ DISCORD  D ]"),
            "trade": Button((p, sh- 70, bw, 26), "[ TRADE ROUTE  R ]"),
            "adv":   Button((p, sh- 40, bw, 26), "[ ADVANCE TURN  T ]", accent=True),
        }

    def draw(self, surf, turn, year, quarter):
        lw = self.lay.lw; sh = self.lay.sh
        pygame.draw.rect(surf, PANEL, (0, 0, lw, sh))
        pygame.draw.rect(surf, BORDER, (0, 0, lw, sh), 1)
        corner_deco(surf, 0, 0, lw, sh, ACCENT, 10)
        pygame.draw.rect(surf, ACCENT2, (0, 0, lw, 3))
        bt = blit_text
        bt(surf, "CARMINE NRP", self.PAD, 8, gf(14, mono=False), ACCENT)
        bt(surf, f"T{turn}  ·  {year} Q{quarter}", self.PAD, 28, gf(11), TEAL)
        yd = 48; pygame.draw.line(surf, BORDER2, (4, yd), (lw-4, yd), 1)
        ly0 = yd+4; lh = sh - yd - 145
        surf.set_clip(pygame.Rect(0, ly0, lw, lh))
        fi = gf(12); ft = gf(10)
        for i, name in enumerate(self.names):
            iy = ly0 + i*self.ROW_H - self.scroll
            if iy + self.ROW_H < ly0 or iy > ly0+lh: continue
            rr = pygame.Rect(4, iy, lw-8, self.ROW_H-3)
            if i == self.selected:
                pygame.draw.rect(surf, SEL, rr, border_radius=3)
                pygame.draw.rect(surf, CYAN, rr, 1, border_radius=3)
                pygame.draw.rect(surf, CYAN, (0, iy, 3, self.ROW_H-3)); nc = BRIGHT
            elif i == self._hov:
                pygame.draw.rect(surf, HOV, rr, border_radius=3); nc = TEXT
            else: nc = DIM
            tag_str = f"[{nation_tag(name)}]"
            bt(surf, tag_str, self.PAD+2, iy+4, ft, TEAL if i==self.selected else DIM2)
            ns = name if len(name) <= 20 else name[:18]+".."
            bt(surf, ns, self.PAD+2, iy+18, fi, nc)
        surf.set_clip(None)
        for b in self._buttons().values(): b.draw(surf)

    def on_event(self, event):
        lw = self.lay.lw
        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            if pos[0] < lw:
                rel = pos[1] - 52 + self.scroll; i = rel // self.ROW_H
                self._hov = i if 0 <= i < len(self.names) else -1
            else: self._hov = -1
        if event.type == pygame.MOUSEWHEEL and pygame.mouse.get_pos()[0] < lw:
            self.scroll = max(0, self.scroll - event.y * self.ROW_H)
        for key, btn in self._buttons().items():
            if btn.on_event(event): return None, key
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if pos[0] < lw:
                rel = pos[1] - 52 + self.scroll; i = rel // self.ROW_H
                if 0 <= i < len(self.names): self.selected = i; return i, None
        return None, None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE  –  build render-item list
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_profile_items(nation: dict, state: dict) -> list:
    """Build flat render-item list for ProfilePanel."""
    items = []; y = 8
    routes = state.get("trade_routes", [])
    ipeu   = nation.get("base_ipeu", 0.0)
    pop    = current_population(nation)
    exp_d  = nation.get("expenditure", {})
    trade  = compute_trade(nation, routes)
    rflows = compute_resource_flows(nation)
    debt   = compute_debt(nation)
    rbudget= nation.get("research_budget", 0.0)
    sfund  = nation.get("strategic_fund",  0.0)
    total_exp_pct = sum(exp_d.values())
    total_exp_cr  = total_exp_pct*ipeu + rbudget
    net_bal        = ipeu + trade["net"] - total_exp_cr - debt["q_interest"]
    fund_delta     = trade["net"] - debt["q_interest"]
    per_cap        = int(ipeu/pop) if pop > 0 else 0
    star_sys  = nation.get("star_systems", [])
    species   = nation.get("species_populations", [])
    projs     = nation.get("projects", [])
    act_res   = nation.get("active_research_projects", [])
    comp_tech = nation.get("completed_techs", [])
    eco_m     = nation.get("economic_model", "Mixed")
    afd       = nation.get("active_forces_detail", [])
    if not isinstance(afd, list): afd = []
    homeworld = "—"
    for ss in star_sys:
        for pl in ss.get("planets", []): homeworld = pl["name"]; break
        break
    sstr = (", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species)
            if species else "—")

    def add(item): nonlocal y; item["y"] = y; items.append(item); y += item["h"]
    def hdr1(t): add({"type":"hdr1","h":36,"text":t})
    def hdr2(t): add({"type":"hdr2","h":30,"text":t})
    def spc(h=8): add({"type":"spc","h":h})
    def sep():    add({"type":"sep","h":10})
    def crow(lbl, val, key=None, et=None, lw=18, vc=TEXT, ib=True):
        meta = {"path":[key],"type":et,"raw":nation.get(key,val)} if key else None
        add({"type":"row","h":22,"in_block":ib,"label":lbl,"value":str(val),
             "label_w":lw,"editable":meta is not None,"edit_meta":meta,"val_color":vc})

    add({"type":"nhdr","h":62,"tag":nation_tag(nation["name"]),"name":nation["name"]})
    spc()
    for lbl,val,key,et in [
        ("Species",    sstr,                                          None, None),
        ("Population", fmt_pop(pop),                                  "population","pop"),
        ("Pop Growth", fmt_pct(nation.get("pop_growth",0))+" / yr",   "pop_growth","pct"),
        ("Homeworld",  homeworld,                                      None, None),
        ("Civilisation",nation.get("civ_level","Interplanetary Industrial"),"civ_level","str"),
        ("Tier",       str(nation.get("civ_tier",2)),                  "civ_tier","int"),
        ("Eco Model",  eco_m,                                          "economic_model","str"),
        ("Status",     nation.get("eco_status","Stable"),              "eco_status","str"),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,val)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":str(val),
             "label_w":16,"editable":meta is not None,"edit_meta":meta,
             "val_color":CYAN if key else TEXT})
    spc()

    hdr1("# ECONOMY")
    for lbl,val,key,et,vc in [
        ("IPEU (base)",       fmt_cr(ipeu),                              "base_ipeu","float",CYAN),
        ("IPEU Growth",       fmt_pct(nation.get("ipeu_growth",0))+" / yr","ipeu_growth","pct",TEXT),
        ("IPEU per Capita",   f"{per_cap:,} cr",                         None,None,TEXT),
        ("Trade Revenue",     fmt_cr(trade["net"]),                      None,None,TEXT),
        (" - Exports",        fmt_cr(trade["exports"]),                  None,None,GREEN),
        (" - Imports",        fmt_cr(-trade["imports"]),                 None,None,RED_C),
        ("Total Expenditure", fmt_cr(total_exp_cr)+f"  ({total_exp_pct*100:.1f}%)",None,None,TEXT),
        ("Research Budget",   fmt_cr(rbudget)+" / turn",                 "research_budget","float",CYAN),
        ("Net Balance",       fmt_cr(net_bal),                           None,None,GREEN if net_bal>=0 else RED_C),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,0)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
             "label_w":18,"editable":meta is not None,"edit_meta":meta,"val_color":vc})
    spc()

    hdr2("## EXPENDITURE & BREAKDOWN")
    max_pct = max(exp_d.values(), default=0.01)
    for cat in EXPENDITURE_ORDER:
        pct = exp_d.get(cat, 0.0)
        if pct == 0.0 and cat not in exp_d: continue
        add({"type":"bar","h":22,"in_block":True,"label":cat,"pct":pct,
             "amount":fmt_cr(pct*ipeu),"editable":True,
             "edit_meta":{"path":["expenditure",cat],"type":"pct","raw":pct}})
    sep()
    add({"type":"row","h":22,"in_block":True,"label":"TOTAL",
         "value":f"{total_exp_pct*100:.1f}%   ({fmt_cr(total_exp_cr)})",
         "label_w":18,"editable":False,"edit_meta":None,"val_color":GOLD})
    spc()

    if eco_m in ("Capitalist","Mixed"):
        hdr2("## MARKET DATA")
        for lbl,val,key,et in [
            ("Investments",     fmt_cr(nation.get("investments",0)),    "investments","float"),
            ("Subsidies",       fmt_cr(nation.get("subsidies",0)),      "subsidies","float"),
            ("Local Mkt Output",fmt_cr(nation.get("local_market_output",0)),"local_market_output","float"),
        ]:
            meta = {"path":[key],"type":et,"raw":nation.get(key,0)}
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":20,"editable":True,"edit_meta":meta,"val_color":TEXT})
        spc()
    if eco_m in ("Planned","Mixed"):
        hdr2("## PLANNED DATA")
        for lbl,val,key,et in [
            ("Domestic Prod.", fmt_cr(nation.get("domestic_production",0)),"domestic_production","float"),
            ("Export Surplus", fmt_cr(nation.get("export_surplus",0)),    "export_surplus","float"),
            ("Construction Eff.",f"{nation.get('construction_efficiency',0.8)*100:.0f}%","construction_efficiency","pct"),
            ("Research Eff.",  f"{nation.get('research_efficiency',0.8)*100:.0f}%","research_efficiency","pct"),
            ("Bureaucracy Eff.",f"{nation.get('bureaucracy_efficiency',0.8)*100:.0f}%","bureaucracy_efficiency","pct"),
            ("Distribution",   fmt_cr(nation.get("distribution",0)),      "distribution","float"),
        ]:
            meta = {"path":[key],"type":et,"raw":nation.get(key,0)}
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":20,"editable":True,"edit_meta":meta,"val_color":TEXT})
        spc()

    hdr2("## ECONOMIC PROJECTS")
    ap = [p for p in projs if p.get("status") in ("active","in_progress","complete")]
    if ap:
        for p in ap:
            done = p.get("status")=="complete"
            tl = p.get("duration_turns",0)-p.get("turns_elapsed",0)
            add({"type":"row","h":22,"in_block":True,
                 "label":f"{p['name']} ({p.get('category','?')})",
                 "value":"[COMPLETE]" if done else f"[{tl}t left]",
                 "label_w":36,"editable":False,"edit_meta":None,
                 "val_color":GREEN if done else GOLD})
    else:
        add({"type":"row","h":22,"in_block":True,"label":"None active","value":"",
             "label_w":36,"editable":False,"edit_meta":None,"val_color":DIM})
    spc()

    hdr2("## FISCAL REPORT")
    for lbl,val,key,et,vc in [
        ("Debt Balance", fmt_cr(debt["balance"])+f"  ({debt['load_pct']:.1f}% of IPEU)",
                         "debt_balance","float",RED_C if debt["balance"]>0 else TEXT),
        ("Interest Rate",f"{debt['rate']*100:.1f}% / yr","interest_rate","pct",TEXT),
        ("Quarterly Int.",fmt_cr(debt["q_interest"]),None,None,TEXT),
        ("Debt Repayment",fmt_cr(debt["repayment"])+" / qtr","debt_repayment","float",TEXT),
    ]:
        meta = {"path":[key],"type":et,"raw":nation.get(key,0)} if key else None
        add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
             "label_w":18,"editable":meta is not None,"edit_meta":meta,"val_color":vc})
    add({"type":"debtbar","h":22,"in_block":True,"pct":debt["load_pct"]/100})
    sep()
    sf_col = GREEN if sfund >= 0 else RED_C
    fd_col = GREEN if fund_delta >= 0 else RED_C
    add({"type":"row","h":22,"in_block":True,"label":"Strategic Fund",
         "value":fmt_cr(sfund),"label_w":18,"editable":True,"val_color":sf_col,
         "edit_meta":{"path":["strategic_fund"],"type":"float","raw":sfund}})
    fds = ("+"+fmt_cr(fund_delta) if fund_delta>=0 else fmt_cr(fund_delta))
    add({"type":"row","h":22,"in_block":True,"label":"Fund Δ this turn",
         "value":fds,"label_w":18,"editable":False,"edit_meta":None,"val_color":fd_col})
    spc()

    hdr2("## RESOURCES & STOCKPILES")
    for rname in RESOURCE_NAMES:
        rd   = rflows.get(rname,{}); stk=rd.get("stockpile",0.0)
        prod = rd.get("production",0.0); cons=rd.get("consumption",0.0)
        net  = rd.get("net",0.0); trend=rd.get("trend","Stable")
        ncol = GREEN if net>=0 else RED_C
        tcol = GREEN if "Surplus" in trend else (RED_C if "Deficit" in trend else GOLD)
        ns   = ("+"+fmt_int(net)) if net>=0 else fmt_int(int(net))
        sd   = nation.get("resource_stockpiles",{}).get(rname,{})
        mode = sd.get("production_mode","derived")
        exp_c= next((r2.get("credits",0) for r2 in trade["export_routes"] if r2.get("resource")==rname), 0)
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Stockpile","value":fmt_int(stk),
             "label_w":28,"editable":True,"val_color":TEXT,
             "edit_meta":{"path":["resource_stockpiles",rname,"stockpile"],"type":"float","raw":stk}})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Prod/turn","value":fmt_int(prod),
             "label_w":28,"editable":mode=="flat","val_color":TEXT,
             "edit_meta":{"path":["resource_stockpiles",rname,"flat_production"],"type":"float","raw":prod}
                         if mode=="flat" else None})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Cons/turn","value":fmt_int(cons),
             "label_w":28,"editable":False,"edit_meta":None,"val_color":TEXT})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Net/turn","value":ns,
             "label_w":28,"editable":False,"edit_meta":None,"val_color":ncol})
        add({"type":"row","h":22,"in_block":True,"label":f"{rname} Trend","value":trend,
             "label_w":28,"editable":False,"edit_meta":None,"val_color":tcol})
        if exp_c > 0:
            add({"type":"row","h":22,"in_block":True,"label":f"{rname} Export","value":fmt_cr(exp_c),
                 "label_w":28,"editable":False,"edit_meta":None,"val_color":CYAN})
        spc(4)
    spc()

    hdr1("# TERRITORIES")
    for ss in star_sys:
        add({"type":"row","h":22,"in_block":False,
             "label":f"System: {ss['name']}  [{ss.get('coordinates','—')}]",
             "value":ss.get("notes",""),"label_w":36,"editable":False,"edit_meta":None,"val_color":CYAN})
        for pl in ss.get("planets",[]):
            add({"type":"row","h":22,"in_block":True,
                 "label":f"  ▸ {pl['name']}",
                 "value":(f"{pl.get('type','?')} · {pl.get('size','?')} · "
                          f"Hab:{pl.get('habitability',0):.0f}% · "
                          f"Dev:{pl.get('devastation',0):.0f}% · "
                          f"Crime:{pl.get('crime_rate',0):.0f}% · "
                          f"Unrest:{pl.get('unrest',0):.0f}%"),
                 "label_w":22,"editable":False,"edit_meta":None,"val_color":TEXT})
            for s in pl.get("settlements",[]):
                sp_inf = " | ".join(f"{sp['species'][:8]} loy:{sp.get('loyalty',0):.0f}"
                                    for sp in s.get("populations",[]))
                add({"type":"row","h":22,"in_block":True,
                     "label":f"      › {s['name']}",
                     "value":f"pop:{fmt_pop(s.get('population',0))} {sp_inf}",
                     "label_w":26,"editable":False,"edit_meta":None,"val_color":DIM})
    spc()

    hdr2("## NATIONAL DEMOGRAPHICS")
    add({"type":"row","h":22,"in_block":True,"label":"Total Population","value":fmt_pop(pop),
         "label_w":22,"editable":False,"edit_meta":None,"val_color":TEXT})
    add({"type":"row","h":22,"in_block":True,"label":"Loyalty Modifier",
         "value":f"{nation.get('loyalty_modifier_cg',1.0)*100:.0f}%",
         "label_w":22,"editable":True,
         "edit_meta":{"path":["loyalty_modifier_cg"],"type":"float","raw":nation.get("loyalty_modifier_cg",1.0)},
         "val_color":TEXT})
    spc(6)
    for sp in species:
        is_dom = sp.get("status","") in ("dominant","majority")
        add({"type":"sphdr","h":28,"name":sp["name"],"status":sp.get("status","?").title(),"dominant":is_dom})
        sp_pop = sp.get("population",0); shr = sp_pop/pop*100 if pop>0 else 0
        loy = sp.get("loyalty",75); lc = GREEN if loy>=70 else (GOLD if loy>=40 else RED_C)
        hap = 70
        for ss2 in star_sys:
            for pl2 in ss2.get("planets",[]):
                for s2 in pl2.get("settlements",[]):
                    for sp2 in s2.get("populations",[]):
                        if sp2["species"]==sp["name"]: hap=sp2.get("happiness",70)
        for lbl,val,meta_key,et,vc in [
            ("Population",  fmt_pop(sp_pop),  None,None,TEXT),
            ("Share",       f"{shr:.1f}% of total",None,None,TEXT),
            ("Growth Rate", fmt_pct(sp.get("growth_rate",0))+" / yr",None,None,TEXT),
            ("Culture",     sp.get("culture","—"),None,None,TEXT),
            ("Language",    sp.get("language","—"),None,None,TEXT),
            ("Religion",    sp.get("religion","—"),None,None,TEXT),
            ("Loyalty",     f"{loy}/100  {loyalty_bar(loy)}","loyalty","int",lc),
            ("Happiness",   f"{hap}/100  {loyalty_bar(hap)}",None,None,GOLD),
        ]:
            m = {"path":["_species",sp["name"],meta_key],"type":et,"raw":sp.get(meta_key,loy)} if meta_key else None
            add({"type":"row","h":22,"in_block":True,"label":lbl,"value":val,
                 "label_w":16,"editable":m is not None,"edit_meta":m,"val_color":vc})
        spc(6)

    hdr1("# MILITARY")
    for sec, cats in [("## SPACEFLEET",["Spacefleet","Navy"]),
                      ("## AEROSPACE",["Air Force","Aerospace"]),
                      ("## GROUND FORCES",["Ground Forces","Ground","Army"])]:
        hdr2(sec)
        units = [u for u in afd if u.get("category") in cats]
        if units:
            for u in units:
                cname = u.get("custom_name") or u.get("unit","?")
                add({"type":"row","h":22,"in_block":True,
                     "label":f"  {cname}","value":f"×{u.get('count',1)}  {u.get('veterancy','?')}",
                     "label_w":30,"editable":False,"edit_meta":None,"val_color":DIM})
        else:
            add({"type":"row","h":22,"in_block":True,"label":"  None on record","value":"",
                 "label_w":30,"editable":False,"edit_meta":None,"val_color":DIM2})
    spc()

    hdr1("# RESEARCH")
    add({"type":"row","h":22,"in_block":True,"label":"Budget/turn","value":fmt_cr(rbudget),
         "label_w":18,"editable":True,"val_color":CYAN,
         "edit_meta":{"path":["research_budget"],"type":"float","raw":rbudget}})
    for proj in act_res:
        add({"type":"row","h":22,"in_block":True,
             "label":f"  [{proj.get('field','?')}] {proj.get('name','?')}",
             "value":f"{proj.get('progress',0.0):.1f}%",
             "label_w":38,"editable":False,"edit_meta":None,"val_color":GOLD})
    for t in (comp_tech[-6:] if comp_tech else []):
        tname = t if isinstance(t,str) else t.get("name",str(t))
        add({"type":"row","h":22,"in_block":True,"label":f"  ✓ {tname}","value":"",
             "label_w":40,"editable":False,"edit_meta":None,"val_color":GREEN})
    spc(20)
    return items

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE PANEL  (scroll + render)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProfilePanel:
    """Scrollable profile with click-to-edit."""
    LPAD = 18
    def __init__(self, lay: Layout):
        self.lay = lay; self.items = []; self.content_h = 0
        self.scrl = Scrollbar(0,0,10,100); self._hov = -1
    def update_layout(self, lay: Layout):
        self.lay = lay
        self.scrl.update_rect(lay.sw-lay.scrl_w, lay.my, lay.scrl_w, lay.mh)
    def set_items(self, items):
        self.items = items
        self.content_h = (items[-1]["y"]+items[-1]["h"]) if items else 0
        self.scrl.set_content(self.content_h, self.lay.mh)
        self.scrl.scroll = 0; self.scrl.clamp(); self._hov = -1
    def _sy(self, iy): return self.lay.my + iy - self.scrl.scroll
    def draw(self, surf):
        lay = self.lay; r = lay.main_rect
        pygame.draw.rect(surf, BG, r); surf.set_clip(r)
        fm=gf(13); fs=gf(11); f1=gf(16,mono=False); f2=gf(14,mono=False)
        fn=gf(19,mono=False); fsp=gf(13,mono=False)
        x0=r.x+self.LPAD; rw=r.w
        for i, item in enumerate(self.items):
            sy = self._sy(item["y"]); sh = item["h"]
            if sy+sh < r.y or sy > r.bottom: continue
            t = item["type"]
            if t == "nhdr":
                pygame.draw.rect(surf,PANEL2,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,ACCENT,(r.x,sy,4,sh))
                for gx in range(r.x, r.x+rw, 32):
                    pygame.draw.line(surf,(16,24,36),(gx,sy),(gx,sy+sh),1)
                tag_s = f"[{item['tag']}]"
                blit_text(surf,tag_s,x0,sy+14,f1,ACCENT)
                blit_text(surf,"  "+item["name"],x0+tw(tag_s,f1),sy+12,fn,BRIGHT)
                pygame.draw.line(surf,BORDER2,(r.x,sy+sh-1),(r.right,sy+sh-1),1)
            elif t == "hdr1":
                pygame.draw.rect(surf,PANEL2,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,ACCENT,(r.x,sy,3,sh))
                blit_text(surf,item["text"],x0,sy+10,f1,CYAN)
                pygame.draw.line(surf,BORDER,(r.x,sy+sh-1),(r.right,sy+sh-1),1)
            elif t == "hdr2":
                pygame.draw.rect(surf,PANEL3,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,TEAL2,(r.x,sy,2,sh))
                blit_text(surf,item["text"],x0,sy+8,f2,TEAL)
            elif t == "row":
                bg = BLK2 if (item.get("in_block") and i%2==0) else (BLOCK if item.get("in_block") else BG)
                pygame.draw.rect(surf,bg,(r.x,sy,rw,sh))
                if i == self._hov and item.get("editable"):
                    pygame.draw.rect(surf,HOV,(r.x,sy,rw,sh))
                lbl = item.get("label",""); val = str(item.get("value",""))
                lw_ = item.get("label_w",18); vc = item.get("val_color",TEXT)
                lbl_s = f"{lbl:<{lw_}}: "
                blit_text(surf,lbl_s,x0,sy+4,fm,DIM)
                blit_text(surf,val,x0+tw(lbl_s,fm),sy+4,fm,vc)
                if item.get("editable"):
                    pygame.draw.rect(surf,TEAL,(r.right-4,sy,2,sh))
            elif t == "bar":
                bg = BLK2 if i%2==0 else BLOCK
                pygame.draw.rect(surf,bg,(r.x,sy,rw,sh))
                if i == self._hov and item.get("editable"):
                    pygame.draw.rect(surf,HOV,(r.x,sy,rw,sh))
                lbl_s = f"{item['label']:<22} {item['pct']*100:5.1f}%"
                blit_text(surf,lbl_s,x0,sy+5,fs,DIM)
                bx = x0+tw(lbl_s,fs)+8
                draw_bar(surf,bx,sy+(sh-10)//2,160,10,item["pct"],fg=CYAN)
                blit_text(surf,item["amount"],bx+168,sy+5,fs,GOLD)
                if item.get("editable"):
                    pygame.draw.rect(surf,TEAL,(r.right-4,sy,2,sh))
            elif t == "debtbar":
                pygame.draw.rect(surf,BLOCK,(r.x,sy,rw,sh))
                lbl_s = f"{'Debt Load':<18}: "
                blit_text(surf,lbl_s,x0,sy+5,fm,DIM)
                bx = x0+tw(lbl_s,fm); pct=item["pct"]
                fc = RED_C if pct>0.5 else (GOLD if pct>0.2 else GREEN)
                draw_bar(surf,bx,sy+6,200,10,pct,fg=fc)
                blit_text(surf,f"  {pct*100:.1f}%",bx+208,sy+5,fm,DIM)
            elif t == "sep":
                my = sy+sh//2
                pygame.draw.line(surf,BORDER2,(r.x+6,my),(r.right-6,my),1)
            elif t == "sphdr":
                pygame.draw.rect(surf,PANEL3,(r.x,sy,rw,sh))
                pygame.draw.rect(surf,GOLD2,(r.x,sy,3,sh))
                crown = "👑" if item.get("dominant") else "👥"
                lbl = f"{crown}  {item['name']}"
                blit_text(surf,lbl,x0,sy+6,fsp,GOLD)
                blit_text(surf,f"  {item['status']}",x0+tw(lbl,fsp),sy+7,gf(12,mono=False),TEAL)
        surf.set_clip(None)
        pygame.draw.rect(surf,BORDER,r,1)
        self.scrl.draw(surf)

    def on_event(self, event) -> Optional[dict]:
        lay = self.lay
        over = pygame.Rect(lay.mx,lay.my,lay.mw+lay.scrl_w,lay.mh)
        self.scrl.on_event(event, over.collidepoint(pygame.mouse.get_pos()))
        if event.type == pygame.MOUSEMOTION and lay.main_rect.collidepoint(event.pos):
            abs_y = event.pos[1]-lay.my+self.scrl.scroll; self._hov = -1
            for i,item in enumerate(self.items):
                if item["y"] <= abs_y < item["y"]+item["h"]:
                    self._hov = i if item.get("editable") else -1; break
        elif event.type == pygame.MOUSEMOTION: self._hov = -1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sr = pygame.Rect(lay.sw-lay.scrl_w,lay.my,lay.scrl_w,lay.mh)
            if lay.main_rect.collidepoint(event.pos) and not sr.collidepoint(event.pos):
                abs_y = event.pos[1]-lay.my+self.scrl.scroll
                for item in self.items:
                    if item["y"] <= abs_y < item["y"]+item["h"]:
                        if item.get("editable") and item.get("edit_meta"):
                            return {"label":item.get("label","Field"),
                                    "raw":item["edit_meta"].get("raw",""),
                                    "meta":item["edit_meta"]}
                        break
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM MAP PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SystemMapPanel:
    """2-D orbital diagram for the nation's home system."""
    PCOL = {"Terrestrial":(0,180,80),"Gas Giant":(200,120,20),
            "Ice World":(100,200,240),"Barren":(120,100,80),"Oceanic":(20,80,200)}
    def __init__(self, lay: Layout):
        self.lay = lay; self.nation = None; self.sel_planet = None
        self._prects = {}; self._btn_exp = None
    def update_layout(self, lay): self.lay = lay
    def set_nation(self, n): self.nation = n; self.sel_planet = None

    def draw(self, surf):
        lay = self.lay; r = lay.main_rect
        pygame.draw.rect(surf, BG, r)
        if not self.nation:
            blit_text(surf,"No nation selected",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        star_sys = self.nation.get("star_systems",[])
        if not star_sys:
            blit_text(surf,"No system data",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        sys0 = star_sys[0]; planets = sys0.get("planets",[])
        detail_w = 310 if self.sel_planet else 0
        map_w = r.w - detail_w; cx = r.x+map_w//2; cy = r.y+r.h//2
        # Star
        pygame.draw.circle(surf,(255,220,60),(cx,cy),22)
        pygame.draw.circle(surf,(255,255,140),(cx,cy),16)
        blit_text(surf,"★",cx-7,cy-9,gf(16,False),(255,240,100))
        max_r = min(map_w, r.h)*0.44; step = max_r/max(len(planets),1)
        self._prects = {}
        for idx, pl in enumerate(planets):
            orb_r = int(step*(idx+1))
            pygame.draw.circle(surf,(20,35,55),(cx,cy),orb_r,1)
            angle = math.pi*0.5 + idx*0.9
            px = int(cx+orb_r*math.cos(angle)); py = int(cy+orb_r*math.sin(angle))
            ptype = pl.get("type","Terrestrial"); pcol = self.PCOL.get(ptype,(80,80,120))
            dev = pl.get("devastation",0)/100.0
            if dev > 0.1:
                pcol = tuple(int(c*(1-dev)+RED_C[i]*dev) for i,c in enumerate(pcol))
            pr = 8+idx*2
            pygame.draw.circle(surf,pcol,(px,py),pr)
            pygame.draw.circle(surf,BRIGHT,(px,py),pr,1)
            if pl is self.sel_planet:
                pygame.draw.circle(surf,CYAN,(px,py),pr+5,2)
            fn = gf(11); pname = pl["name"]
            blit_text(surf,pname,px-tw(pname,fn)//2,py+pr+4,fn,TEXT)
            if pl.get("crime_rate",0)>30: pygame.draw.circle(surf,RED_C,(px+pr,py-pr),4)
            if pl.get("unrest",0)>20:     pygame.draw.circle(surf,GOLD,(px-pr,py-pr),4)
            self._prects[pl["name"]] = (pl, pygame.Rect(px-pr-2,py-pr-2,pr*2+4,pr*2+4))
        blit_text(surf,f"★  {sys0['name']}",r.x+14,r.y+12,gf(16,False),BRIGHT)
        blit_text(surf,f"{len(planets)} planet(s)",r.x+14,r.y+34,gf(11),TEAL)
        blit_text(surf,"● Crime>30%",r.x+map_w-140,r.y+14,gf(10),RED_C)
        blit_text(surf,"● Unrest>20%",r.x+map_w-140,r.y+28,gf(10),GOLD)
        # Detail drawer
        self._btn_exp = None
        if self.sel_planet:
            pl = self.sel_planet
            dr = pygame.Rect(r.right-detail_w,r.y,detail_w,r.h)
            pygame.draw.rect(surf,PANEL2,dr)
            pygame.draw.line(surf,BORDER2,(dr.x,dr.y),(dr.x,dr.bottom),1)
            corner_deco(surf,dr.x,dr.y,dr.w,dr.h,CYAN,8)
            x=dr.x+12; y=dr.y+10; f=gf(12); fs=gf(11)
            blit_text(surf,pl["name"],x,y,gf(15,False),BRIGHT); y+=22
            pygame.draw.line(surf,BORDER2,(dr.x+4,y),(dr.right-4,y),1); y+=8
            for lbl,val in [("Type",pl.get("type","?")),("Size",pl.get("size","?")),
                             ("Habitability",f"{pl.get('habitability',0):.0f}%"),
                             ("Devastation",f"{pl.get('devastation',0):.0f}%"),
                             ("Crime Rate",f"{pl.get('crime_rate',0):.0f}%"),
                             ("Unrest",f"{pl.get('unrest',0):.0f}%")]:
                blit_text(surf,f"{lbl:<16}: ",x,y,fs,DIM)
                blit_text(surf,val,x+tw(f"{lbl:<16}: ",fs),y,fs,TEXT); y+=18
            y+=4; blit_text(surf,"SETTLEMENTS",x,y,fs,TEAL); y+=16
            for s in pl.get("settlements",[]):
                blit_text(surf,f"  › {s['name']}  pop:{fmt_pop(s.get('population',0))}",x,y,fs,TEXT); y+=16
                for sp in s.get("populations",[]):
                    loy=sp.get("loyalty",0); lc=GREEN if loy>=70 else(GOLD if loy>=40 else RED_C)
                    blit_text(surf,f"    {sp['species'][:12]}  loy:{loy:.0f}  hap:{sp.get('happiness',0):.0f}",
                              x,y,gf(10),lc); y+=14
            y+=6; blit_text(surf,"ORBITAL BUILDINGS",x,y,fs,TEAL); y+=16
            obs = pl.get("orbital_buildings",[])
            if obs:
                for ob in obs: blit_text(surf,f"  ⊕ {ob.get('type','?')} [{ob.get('status','?')}]",x,y,fs,DIM); y+=16
            else: blit_text(surf,"  None",x,y,fs,DIM2)
            bx = dr.x+(dr.w-160)//2; by = dr.bottom-42
            self._btn_exp = Button((bx,by,160,28),"[EXPORT SYSTEM  D]",small=True)
            self._btn_exp.draw(surf)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, state) -> Optional[str]:
        if self._btn_exp and self._btn_exp.on_event(event) and self.nation:
            return self._export_discord(self.nation)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for pname,(pl,pr) in self._prects.items():
                if pr.collidepoint(event.pos):
                    self.sel_planet = pl; return None
        return None

    def _export_discord(self, nation) -> str:
        star_sys = nation.get("star_systems",[])
        if not star_sys: return ""
        ss = star_sys[0]; tag = nation_tag(nation["name"]); L=[]; ln=L.append
        ln(f"-# [{tag}] {nation['name'].upper()} — SYSTEM REPORT")
        ln(f"# STAR SYSTEM: {ss['name']}")
        for pl in ss.get("planets",[]):
            ln("```")
            ln(f"  {pl['name']}")
            for k,v in [("Type",pl.get("type","?")),("Size",pl.get("size","?")),
                         ("Habitability",f"{pl.get('habitability',0):.0f}%"),
                         ("Devastation",f"{pl.get('devastation',0):.0f}%"),
                         ("Crime Rate",f"{pl.get('crime_rate',0):.0f}%"),
                         ("Unrest",f"{pl.get('unrest',0):.0f}%")]:
                ln(f"    {k:<16}: {v}")
            for s in pl.get("settlements",[]): ln(f"      › {s['name']}  pop:{fmt_pop(s.get('population',0))}")
            for ob in pl.get("orbital_buildings",[]): ln(f"      ⊕ {ob.get('type','?')} [{ob.get('status','?')}]")
            ln("```")
        return "\n".join(L)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVENT LOG PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EventLogPanel:
    """Filter / approve / edit / delete d20 events."""
    RH = 64
    SEV_COL = {"Critical":RED_C,"Major":GOLD,"Minor":CYAN,"Info":DIM}
    def __init__(self, lay: Layout):
        self.lay=lay; self.state=None; self.nation_filter=None
        self.scrl=Scrollbar(0,0,10,100); self._hov=-1; self._events=[]
    def update_layout(self, lay):
        self.lay=lay; self.scrl.update_rect(lay.sw-lay.scrl_w,lay.my,lay.scrl_w,lay.mh)
    def set_state(self, state, nation_filter=None):
        self.state=state; self.nation_filter=nation_filter; self._refresh()
    def _refresh(self):
        if not self.state: self._events=[]; return
        self._events=EventLog(self.state).filter(nation=self.nation_filter)
        self.scrl.set_content(len(self._events)*self.RH+60, self.lay.mh); self.scrl.clamp()

    def draw(self, surf):
        lay=self.lay; r=lay.main_rect
        pygame.draw.rect(surf,BG,r)
        if not self.state:
            blit_text(surf,"No state loaded.",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        # Toolbar
        TH=36; pygame.draw.rect(surf,PANEL2,(r.x,r.y,r.w,TH))
        pygame.draw.line(surf,BORDER2,(r.x,r.y+TH),(r.right,r.y+TH),1)
        turn=self.state.get("turn",1)
        approved=sum(1 for e in self._events if e.get("gm_approved"))
        blit_text(surf,f"T{turn}  Events: {len(self._events)}  Approved: {approved}  |  D = Export Galactic News",
                  r.x+14,r.y+11,gf(12),TEAL)
        if not self._events:
            blit_text(surf,"No events — advance the turn to generate d20 rolls.",r.x+20,r.y+TH+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); self.scrl.draw(surf); return
        surf.set_clip(pygame.Rect(r.x,r.y+TH,r.w,r.h-TH))
        f=gf(12); fs=gf(11); f10=gf(10)
        for i,ev in enumerate(self._events):
            iy=r.y+TH+i*self.RH-self.scrl.scroll
            if iy+self.RH<r.y or iy>r.bottom: continue
            sev=ev.get("severity","Info"); scol=self.SEV_COL.get(sev,DIM)
            bg=PANEL if i%2==0 else PANEL2
            pygame.draw.rect(surf,bg,(r.x,iy,r.w,self.RH))
            if i==self._hov: pygame.draw.rect(surf,HOV,(r.x,iy,r.w,self.RH))
            pygame.draw.rect(surf,scol,(r.x,iy,3,self.RH))
            icon=SEVERITY_EMOJI.get(sev,"📊")
            scope=ev.get("nation","?"); planet=ev.get("planet")
            if planet: scope+=f" | {planet}"
            blit_text(surf,f"{icon} {ev.get('title','?')}",r.x+12,iy+6,f,BRIGHT)
            blit_text(surf,scope,r.x+12,iy+24,fs,TEAL)
            roll_s=f"d20={ev.get('d20_roll','?')}"; roll=ev.get("d20_roll",10)
            rc=RED_C if roll<=3 else(GOLD if roll<=7 else(GREEN if roll>=17 else DIM))
            blit_text(surf,roll_s,r.x+12,iy+42,f10,rc)
            blit_text(surf,f"T{ev.get('turn','?')}  {sev}",r.x+80,iy+42,f10,DIM)
            # Body preview
            body=ev.get("body",""); bp=body[:100]+("…" if len(body)>100 else "")
            blit_text(surf,bp,r.x+200,iy+42,f10,DIM2)
            # Approve button area
            appr=ev.get("gm_approved",False)
            ax=r.right-160
            pygame.draw.rect(surf,GREEN2 if appr else BTNBG,(ax,iy+12,130,22),border_radius=2)
            pygame.draw.rect(surf,GREEN if appr else BORDER2,(ax,iy+12,130,22),1,border_radius=2)
            astr="✓  APPROVED" if appr else "  APPROVE"
            blit_text(surf,astr,ax+(130-tw(astr,f10))//2,iy+18,f10,BRIGHT)
            edited=ev.get("gm_edited",False)
            if edited: blit_text(surf,"[edited]",ax,iy+38,f10,TEAL)
        surf.set_clip(None); self.scrl.draw(surf)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, edit_overlay: EditOverlay) -> Optional[str]:
        lay=self.lay; r=lay.main_rect
        over=r.collidepoint(pygame.mouse.get_pos())
        self.scrl.on_event(event, over)
        TH=36
        if event.type==pygame.MOUSEMOTION and r.collidepoint(event.pos):
            abs_y=event.pos[1]-r.y-TH+self.scrl.scroll
            self._hov=max(0,abs_y//self.RH) if abs_y>=0 else -1
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and r.collidepoint(event.pos):
            abs_y=event.pos[1]-r.y-TH+self.scrl.scroll
            idx=abs_y//self.RH
            if 0<=idx<len(self._events):
                ev=self._events[idx]; ax=r.right-160
                if event.pos[0]>=ax:
                    EventLog(self.state).approve(ev["event_id"]); self._refresh()
                else:
                    edit_overlay.open(f"Event {ev['event_id']} body",ev.get("body",""),
                                      {"path":["_event",ev["event_id"]],"type":"str","raw":ev.get("body","")})
        return None

    def apply_body_edit(self, event_id, new_body):
        EventLog(self.state).edit_body(event_id, new_body); self._refresh()

    def export_news(self) -> str:
        if not self.state: return ""
        return discord_galactic_news(self.state, self.state.get("turn",1))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARKET PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketPanel:
    """Live price table + modifier editor."""
    RH = 30
    def __init__(self, lay: Layout):
        self.lay=lay; self.state=None; self._hov=-1
        self._price_rects=[]; self._btn_fluc=None; self._btn_exp=None
    def update_layout(self, lay): self.lay=lay
    def set_state(self, state): self.state=state

    def draw(self, surf):
        lay=self.lay; r=lay.main_rect
        pygame.draw.rect(surf,BG,r)
        if not self.state:
            blit_text(surf,"No state loaded.",r.x+20,r.y+20,gf(13),DIM)
            pygame.draw.rect(surf,BORDER,r,1); return
        me=MarketEngine(self.state.get("market",{})); prices=me.get_prices()
        x=r.x+20; y=r.y+14; f=gf(13); fh=gf(15,False); fs=gf(11); f10=gf(10)
        blit_text(surf,"# GALACTIC MARKET",x,y,fh,CYAN); y+=30
        HDR=f"  {'Resource':<20} {'Base':>10}  {'Modifier':>10}  {'Effective':>12}  Trend  (sparkline)"
        blit_text(surf,HDR,x,y,fs,DIM); y+=6
        pygame.draw.line(surf,BORDER2,(x,y),(r.right-20,y),1); y+=8
        TRCOL={"▲":GREEN,"▼":RED_C,"─":DIM}
        self._price_rects=[]
        for i,row in enumerate(prices):
            iy=y+i*self.RH; bg=BLOCK if i%2==0 else BLK2
            pygame.draw.rect(surf,bg,(r.x,iy,r.w,self.RH))
            if i==self._hov: pygame.draw.rect(surf,HOV,(r.x,iy,r.w,self.RH))
            pygame.draw.rect(surf,TEAL2,(r.x,iy,2,self.RH))
            ln_=f"  {row['resource']:<20} {row['base']:>10.2f} cr  x{row['modifier']:>8.3f}  {row['effective']:>10.2f} cr"
            blit_text(surf,ln_,x,iy+8,f,TEXT)
            tc=TRCOL.get(row["trend"],DIM)
            blit_text(surf,row["trend"],x+tw(ln_,f)+6,iy+8,f,tc)
            # Sparkline
            hist=row.get("history",[]); sx=r.right-200; sy=iy+3; sw_=150; sh_=24
            if len(hist)>=2:
                mn=min(hist); mx_=max(hist); rng=max(mx_-mn,0.001)
                pts=[(sx+int(j/(len(hist)-1)*sw_),
                      sy+int((1-(h-mn)/rng)*sh_)) for j,h in enumerate(hist)]
                pygame.draw.lines(surf,TEAL,False,pts,1)
            blit_text(surf,"[edit mod]",r.right-60,iy+10,f10,DIM)
            self._price_rects.append((row, pygame.Rect(r.x,iy,r.w,self.RH)))
        by=r.bottom-50; bx=x
        self._btn_fluc=Button((bx,by,140,30),"[ FLUCTUATE ]",accent=True)
        self._btn_exp =Button((bx+154,by,180,30),"[ EXPORT MARKET  D ]")
        self._btn_fluc.draw(surf); self._btn_exp.draw(surf)
        psst=self.state.get("market",{}).get("psst_nations",[])
        if psst: blit_text(surf,f"PSST: {', '.join(psst)}",x,by-22,fs,GOLD)
        pygame.draw.rect(surf,BORDER,r,1)

    def on_event(self, event, edit_overlay: EditOverlay, sm) -> Optional[str]:
        r=self.lay.main_rect
        if event.type==pygame.MOUSEMOTION and r.collidepoint(event.pos):
            for i,(_,pr) in enumerate(self._price_rects):
                if pr.collidepoint(event.pos): self._hov=i; break
            else: self._hov=-1
        if self._btn_fluc and self._btn_fluc.on_event(event):
            MarketEngine(self.state.get("market",{})).fluctuate_all()
            sm.mark_dirty(); sm.autosave(); set_status("Market fluctuated.",GOLD); return None
        if self._btn_exp and self._btn_exp.on_event(event):
            return discord_market_report(self.state)
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for row,pr in self._price_rects:
                if pr.collidepoint(event.pos):
                    edit_overlay.open(f"{row['resource']} modifier",row["modifier"],
                                      {"path":["_market",row["resource"]],"type":"float","raw":row["modifier"]})
                    return None
        if self._btn_fluc: self._btn_fluc.on_event(event)
        if self._btn_exp:  self._btn_exp.on_event(event)
        return None

    def apply_market_edit(self, resource, new_val, sm):
        MarketEngine(self.state.get("market",{})).set_modifier(resource, new_val)
        sm.mark_dirty(); sm.autosave(); set_status(f"{resource} modifier → {new_val:.3f}",GREEN)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADE ROUTE MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TradeModal:
    """Full-screen modal for building a trade route."""
    DIST_OPTS = list(PIRATE_BASE_RISK.keys())
    def __init__(self):
        self.active=False; self.state=None; self._exporter=""; self._importer=""
        self._resource=RESOURCE_NAMES[0]; self._export_pct=0.25; self._escort=0.0
        self._modifier=1.0; self._dist_idx=0; self._transits=[]; self._preview=None
        self._err=""; self._drag_pct=False; self._drag_esc=False
        self._res_rects=[]; self._dist_rects=[]; self._pct_slider=None; self._esc_slider=None
        self._btn_confirm=None; self._btn_export=None; self._btn_cancel=None

    def open(self, state, sel_nation_name):
        self.active=True; self.state=state
        self._exporter=sel_nation_name or ""; self._importer=""
        self._preview=None; self._err=""; self._transits=[]; self._recalc()

    def close(self): self.active=False

    def _nation(self, name):
        for n in self.state.get("nations",[]): 
            if n["name"]==name: return n
        return None

    def _recalc(self):
        if not self.state or not self._exporter or not self._importer: return
        en=self._nation(self._exporter)
        if not en: return
        try:
            eng=TradeRouteEngine(self.state)
            avail=eng.available_export(en,self._resource)
            qty=avail*self._export_pct
            dist=self.DIST_OPTS[self._dist_idx]
            self._preview=eng.calculate(self._exporter,self._importer,self._resource,
                                        qty,self._transits,dist,self._escort,self._modifier)
            self._err=""
        except Exception as e: self._err=str(e); self._preview=None

    def draw(self, surf, lay: Layout):
        if not self.active: return
        ov=pygame.Surface((lay.sw,lay.sh),pygame.SRCALPHA); ov.fill((0,0,0,180)); surf.blit(ov,(0,0))
        mw=min(lay.sw-60,920); mh=min(lay.sh-60,660)
        mx=(lay.sw-mw)//2; my=(lay.sh-mh)//2; r=pygame.Rect(mx,my,mw,mh)
        pygame.draw.rect(surf,MODALBG,r); pygame.draw.rect(surf,MODALBDR,r,2)
        corner_deco(surf,mx,my,mw,mh,CYAN,12)
        fh=gf(16,False); f=gf(13); fs=gf(11); f10=gf(10)
        x=mx+20; y=my+14
        blit_text(surf,"TRADE ROUTE BUILDER",x,y,fh,CYAN); y+=28
        pygame.draw.line(surf,BORDER2,(mx+4,y),(mx+mw-4,y),1); y+=10
        col1w=(mw-60)//2; col2x=x+col1w+20; cy=y

        # --- LEFT COLUMN ---
        blit_text(surf,"Exporter:",x,cy,fs,DIM); cy+=16
        pygame.draw.rect(surf,BORDER2 if self._exporter else BORDER,(x,cy,col1w-10,22),1)
        blit_text(surf,self._exporter or "(select in sidebar)",x+4,cy+4,f,BRIGHT if self._exporter else DIM)
        cy+=26; blit_text(surf,"Importer:",x,cy,fs,DIM); cy+=16
        pygame.draw.rect(surf,BORDER,(x,cy,col1w-10,22),1)
        blit_text(surf,self._importer or "(type nation name)",x+4,cy+4,f,BRIGHT if self._importer else DIM)
        self._imp_rect=pygame.Rect(x,cy,col1w-10,22); cy+=26

        blit_text(surf,"Resource:",x,cy,fs,DIM); cy+=16
        slot_w=(col1w-10)//len(RESOURCE_NAMES)-2; self._res_rects=[]
        for i,rn in enumerate(RESOURCE_NAMES):
            sel=rn==self._resource; rx=x+i*(slot_w+2)
            bg=TABACT if sel else PANEL2
            pygame.draw.rect(surf,bg,(rx,cy,slot_w,20),border_radius=2)
            if sel: pygame.draw.rect(surf,CYAN,(rx,cy,slot_w,20),1,border_radius=2)
            blit_text(surf,rn[:7],rx+2,cy+4,f10,BRIGHT if sel else DIM)
            self._res_rects.append((rn,pygame.Rect(rx,cy,slot_w,20)))
        cy+=28
        blit_text(surf,f"Export %:  {self._export_pct*100:.0f}%",x,cy,fs,DIM); cy+=16
        sw_=col1w-10; draw_bar(surf,x,cy,sw_,12,self._export_pct,fg=CYAN)
        self._pct_slider=pygame.Rect(x,cy,sw_,12); cy+=20
        if self._exporter and self.state:
            en=self._nation(self._exporter)
            if en:
                eng=TradeRouteEngine(self.state)
                avail=eng.available_export(en,self._resource); qty=avail*self._export_pct
                blit_text(surf,f"Avail: {fmt_int(avail)}  Qty/turn: {fmt_int(qty)}",x,cy,fs,TEAL)
        cy+=20

        blit_text(surf,"Pirate distance:",x,cy,fs,DIM); cy+=16
        dslot=(col1w-10)//len(self.DIST_OPTS)-2; self._dist_rects=[]
        for i,d in enumerate(self.DIST_OPTS):
            sel=i==self._dist_idx; dx=x+i*(dslot+2)
            bg=TABACT if sel else PANEL2
            pygame.draw.rect(surf,bg,(dx,cy,dslot,20),border_radius=2)
            if sel: pygame.draw.rect(surf,GOLD,(dx,cy,dslot,20),1,border_radius=2)
            blit_text(surf,d[:9],dx+2,cy+4,f10,BRIGHT if sel else DIM)
            self._dist_rects.append((i,pygame.Rect(dx,cy,dslot,20)))
        cy+=28
        blit_text(surf,f"Escort: {self._escort:.0f}%",x,cy,fs,DIM); cy+=16
        draw_bar(surf,x,cy,sw_,12,self._escort/100,fg=GREEN2)
        self._esc_slider=pygame.Rect(x,cy,sw_,12); cy+=24
        blit_text(surf,f"Route modifier: x{self._modifier:.2f}",x,cy,fs,DIM); cy+=16

        # transit list
        blit_text(surf,"Transit nations:",x,cy,fs,DIM); cy+=16
        for t in self._transits:
            blit_text(surf,f"  {t['nation']}  {t['tax_rate']*100:.1f}%",x,cy,f10,TEXT); cy+=16

        # --- RIGHT COLUMN: live preview ---
        ry=y; blit_text(surf,"ROUTE PREVIEW",col2x,ry,gf(15,False),GOLD); ry+=28
        pygame.draw.line(surf,BORDER2,(col2x,ry),(mx+mw-20,ry),1); ry+=10
        if self._preview:
            P=self._preview
            for lbl,val,vc in [
                ("Gross/turn",       fmt_cr(P["gross"]),                     BRIGHT),
            ]:
                blit_text(surf,f"{lbl:<22}: ",col2x,ry,f,DIM); blit_text(surf,val,col2x+tw(f"{lbl:<22}: ",f),ry,f,vc); ry+=22
            for t in P.get("transit_taxes",[]):
                blit_text(surf,f"  Transit {t['nation'][:14]:<14}: -{fmt_cr(t['amount'])}",col2x,ry,f,RED_C); ry+=22
            for lbl,val,vc in [
                ("NET/turn",         fmt_cr(P["net_income"]),                 GREEN),
                ("",None,TEXT),
                ("Pirate dist.",     P["pirate_distance"],                    DIM),
                ("Escort",          f"{P['escort_pct']:.0f}%",              DIM),
                ("Pirate risk",     f"{P['pirate_risk_pct']:.1f}% / turn",   RED_C if P["pirate_risk_pct"]>15 else GOLD),
                ("Exp. loss/turn",   fmt_cr(P["expected_pirate_loss"]),      RED_C),
                ("Unit price",      f"{P['effective_price']:.4f} cr",       DIM),
                ("Qty/turn",         fmt_int(P["quantity_per_turn"]),        DIM),
            ]:
                if val is None: ry+=8; continue
                blit_text(surf,f"{lbl:<22}: ",col2x,ry,f,DIM); blit_text(surf,val,col2x+tw(f"{lbl:<22}: ",f),ry,f,vc); ry+=22
            ry+=6; blit_text(surf,"Pirate Risk",col2x,ry,fs,DIM); ry+=14
            prc=P["pirate_risk_pct"]/100; fc=RED_C if prc>0.2 else(GOLD if prc>0.1 else GREEN)
            draw_bar(surf,col2x,ry,min(200,mw-col1w-60),10,prc,fg=fc); ry+=18
        elif self._err:
            blit_text(surf,f"Error: {self._err}",col2x,ry,fs,RED_C)
        else:
            blit_text(surf,"Set exporter + importer to preview.",col2x,ry,fs,DIM)

        # Action buttons
        bw=130; bby=my+mh-44; bx_=mx+mw-bw*3-30
        self._btn_confirm=Button((bx_,bby,bw,30),"[ CONFIRM ROUTE ]",accent=True)
        self._btn_export =Button((bx_+bw+10,bby,bw,30),"[ DISCORD EXPORT ]")
        self._btn_cancel =Button((bx_+bw*2+20,bby,bw,30),"[ CANCEL ]")
        for b in (self._btn_confirm,self._btn_export,self._btn_cancel): b.draw(surf)
        if self._err: blit_text(surf,self._err,mx+20,bby+8,fs,RED_C)

    def on_event(self, event, lay: Layout, sm) -> Optional[str]:
        if not self.active: return None
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE: self.close(); return None
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            for rn,r in self._res_rects:
                if r.collidepoint(event.pos): self._resource=rn; self._recalc()
            for i,r in self._dist_rects:
                if r.collidepoint(event.pos): self._dist_idx=i; self._recalc()
            if self._btn_cancel and self._btn_cancel.on_event(event):
                self.close(); return None
            if self._btn_export and self._btn_export.on_event(event) and self._preview:
                rid=TradeRouteEngine.next_route_id(self.state) if hasattr(TradeRouteEngine,"next_route_id") else "TR????"
                return discord_trade_route(self._preview, rid)
            if self._btn_confirm and self._btn_confirm.on_event(event) and self._preview:
                eng=TradeRouteEngine(self.state); dist=self.DIST_OPTS[self._dist_idx]
                route=eng.build(self._preview,dist,"")
                self.state.setdefault("trade_routes",[]).append(route)
                sm.mark_dirty(); sm.autosave()
                set_status(f"Route {route['id']} created: {route['name']}",GREEN); self.close(); return "confirmed"
            if self._pct_slider and self._pct_slider.collidepoint(event.pos): self._drag_pct=True
            if self._esc_slider and self._esc_slider.collidepoint(event.pos): self._drag_esc=True
        if event.type==pygame.MOUSEBUTTONUP: self._drag_pct=False; self._drag_esc=False
        if event.type==pygame.MOUSEMOTION:
            if self._drag_pct and self._pct_slider:
                rel=(event.pos[0]-self._pct_slider.x)/max(1,self._pct_slider.w)
                self._export_pct=max(0.01,min(1.0,rel)); self._recalc()
            if self._drag_esc and self._esc_slider:
                rel=(event.pos[0]-self._esc_slider.x)/max(1,self._esc_slider.w)
                self._escort=max(0.0,min(100.0,rel*100)); self._recalc()
        for b in (self._btn_confirm,self._btn_export,self._btn_cancel):
            if b: b.on_event(event)
        return None

    def set_exporter(self, name): self._exporter=name; self._recalc()
    def set_importer(self, name): self._importer=name; self._recalc()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADVANCE TURN MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TurnModal:
    """Shows d20 roll results after advancing the turn."""
    def __init__(self):
        self.active=False; self.events=[]; self.turn=0
        self._scrl=Scrollbar(0,0,10,100); self._btn_close=None

    def open(self, events, turn):
        self.active=True; self.events=events; self.turn=turn
        self._scrl.set_content(max(300,len(events)*54+100),520); self._scrl.scroll=0

    def close(self): self.active=False

    def draw(self, surf, lay: Layout):
        if not self.active: return
        ov=pygame.Surface((lay.sw,lay.sh),pygame.SRCALPHA); ov.fill((0,0,0,190)); surf.blit(ov,(0,0))
        mw=min(lay.sw-100,780); mh=min(lay.sh-80,560)
        mx=(lay.sw-mw)//2; my=(lay.sh-mh)//2; r=pygame.Rect(mx,my,mw,mh)
        pygame.draw.rect(surf,MODALBG,r); pygame.draw.rect(surf,ACCENT,r,2)
        corner_deco(surf,mx,my,mw,mh,GOLD,12)
        fh=gf(15,False); f=gf(12); fs=gf(11); f10=gf(10)
        SEV_COL={"Critical":RED_C,"Major":GOLD,"Minor":CYAN,"Info":DIM}
        blit_text(surf,f"TURN {self.turn} COMPLETE — d20 PLANETARY EVENTS",mx+16,my+12,fh,GOLD)
        blit_text(surf,f"{len(self.events)} event(s) generated",mx+16,my+34,fs,DIM)
        pygame.draw.line(surf,BORDER2,(mx+4,my+50),(mx+mw-4,my+50),1)
        lh=mh-110; lr=pygame.Rect(mx+2,my+54,mw-14,lh)
        self._scrl.update_rect(mx+mw-12,my+54,10,lh); self._scrl.view_h=lh
        surf.set_clip(lr)
        for i,ev in enumerate(self.events):
            iy=my+56+i*54-self._scrl.scroll
            if iy+54<lr.y or iy>lr.bottom: continue
            sev=ev.get("severity","Info"); scol=SEV_COL.get(sev,DIM)
            bg=PANEL if i%2==0 else PANEL2
            pygame.draw.rect(surf,bg,(mx+4,iy,mw-18,52))
            pygame.draw.rect(surf,scol,(mx+4,iy,3,52))
            roll=ev.get("d20_roll",0); rc=RED_C if roll<=3 else(GOLD if roll<=7 else(GREEN if roll>=17 else DIM))
            blit_text(surf,f"d20={roll}",mx+14,iy+6,f,rc)
            blit_text(surf,f"{SEVERITY_EMOJI.get(sev,'📊')} {ev.get('title','?')}",mx+70,iy+6,f,BRIGHT)
            scope=ev.get("nation","?")
            if ev.get("planet"): scope+=f" | {ev['planet']}"
            blit_text(surf,scope,mx+14,iy+24,fs,TEAL)
            body=ev.get("body",""); bp=body[:120]+("…" if len(body)>120 else "")
            blit_text(surf,bp,mx+14,iy+40,f10,DIM2)
        surf.set_clip(None); self._scrl.draw(surf)
        bx=(lay.sw-140)//2; by=my+mh-40
        self._btn_close=Button((bx,by,140,30),"[ CLOSE ]",accent=True)
        self._btn_close.draw(surf)

    def on_event(self, event) -> bool:
        """Returns True when modal should close."""
        self._scrl.on_event(event, True)
        if self._btn_close and self._btn_close.on_event(event): return True
        if event.type==pygame.KEYDOWN and event.key in (pygame.K_ESCAPE,pygame.K_RETURN,pygame.K_SPACE):
            return True
        if self._btn_close: self._btn_close.on_event(event)
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLIPBOARD HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    try:
        import subprocess, platform
        p=platform.system()
        if p=="Linux":
            for cmd in (["xclip","-selection","clipboard"],["xsel","--clipboard","--input"]):
                try:
                    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
                    proc.communicate(text.encode()); return True
                except FileNotFoundError: continue
        elif p=="Darwin":
            subprocess.Popen(["pbcopy"],stdin=subprocess.PIPE).communicate(text.encode()); return True
        elif p=="Windows":
            subprocess.Popen(["clip"],stdin=subprocess.PIPE,shell=True).communicate(text.encode()); return True
    except Exception: pass
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN APPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class App:
    """
    Carmine NRP GM Tool — main application loop.

    State machine
    -------------
      tab 0  PROFILE   – ProfilePanel + EditOverlay
      tab 1  SYSTEM MAP – SystemMapPanel
      tab 2  EVENT LOG  – EventLogPanel + EditOverlay
      tab 3  MARKET     – MarketPanel + EditOverlay
      modal  TRADE      – TradeModal (R key)
      modal  TURN       – TurnModal (T key)
    """
    def __init__(self, state_file: Optional[str] = None):
        pygame.init(); pygame.display.set_caption(f"Carmine NRP GM Tool {VERSION}")
        self.screen = pygame.display.set_mode((1280,720), pygame.RESIZABLE)
        self.clock  = pygame.time.Clock()
        self.lay    = Layout(1280, 720)

        # Engine
        self.sm     = StateManager(state_file or "carmine_state.json")
        loaded      = self.sm.load() if state_file else False
        if not loaded and state_file:
            set_status(f"Could not load {state_file}", RED_C)

        # Widgets
        self.tab_bar     = TabBar(self.lay, TAB_NAMES)
        self.left        = LeftPanel(self.lay)
        self.profile     = ProfilePanel(self.lay)
        self.sysmap      = SystemMapPanel(self.lay)
        self.evlog       = EventLogPanel(self.lay)
        self.market      = MarketPanel(self.lay)
        self.edit        = EditOverlay()
        self.trade_modal = TradeModal()
        self.turn_modal  = TurnModal()

        self._refresh_nation_list()
        self._load_nation(0)

    # ── Data helpers ──────────────────────────────

    def _refresh_nation_list(self):
        names = self.sm.nation_names()
        self.left.set_nations(names, self.left.selected)

    def _load_nation(self, idx: int):
        names = self.sm.nation_names()
        if not names: return
        idx = max(0, min(idx, len(names)-1))
        self.left.selected = idx
        nation = self.sm.state.get("nations",[])[idx]
        self.profile.set_items(build_profile_items(nation, self.sm.state))
        self.sysmap.set_nation(nation)
        self.evlog.set_state(self.sm.state, nation["name"])
        self.market.set_state(self.sm.state)

    def _current_nation(self) -> Optional[dict]:
        nations = self.sm.state.get("nations",[])
        if not nations: return None
        idx = self.left.selected
        return nations[min(idx, len(nations)-1)]

    def _do_discord_export(self):
        """Export currently-active panel to clipboard."""
        tab = self.tab_bar.active; nation = self._current_nation()
        if tab == 0 and nation:
            text = discord_profile(nation, self.sm.state)
        elif tab == 1 and nation:
            text = self.sysmap._export_discord(nation)
        elif tab == 2:
            text = self.evlog.export_news()
        elif tab == 3:
            text = discord_market_report(self.sm.state)
        else: return
        ok = copy_to_clipboard(text)
        set_status("Discord export copied to clipboard!" if ok else "Clipboard unavailable — see terminal.", GREEN if ok else GOLD)
        print("\n" + "="*60 + "\n" + text + "\n" + "="*60)

    def _do_advance_turn(self):
        if not self.sm.state.get("nations"): set_status("No nations loaded.",RED_C); return
        set_status("Advancing turn…", GOLD)
        pygame.display.flip()
        events = advance_turn(self.sm)
        turn   = self.sm.state.get("turn",1)
        self.turn_modal.open(events, turn)
        self._refresh_nation_list()
        self._load_nation(self.left.selected)
        set_status(f"Turn {turn} advanced. {len(events)} events generated.", GREEN)

    # ── Edit commit ───────────────────────────────

    def _commit_edit(self):
        raw = self.edit.text; meta = self.edit.meta
        if meta is None: self.edit.close(); return
        path = meta.get("path",[])
        # Event body edit
        if path and path[0]=="_event":
            self.evlog.apply_body_edit(path[1], raw)
            self.edit.close(); set_status("Event body updated.",GREEN); return
        # Market modifier edit
        if path and path[0]=="_market":
            try:
                val = float(raw.strip())
                self.market.apply_market_edit(path[1], val, self.sm)
            except ValueError: set_status("Invalid number.",RED_C)
            self.edit.close(); return
        # Nation field edit
        nation = self._current_nation()
        if nation and apply_edit(nation, meta, raw):
            recalc_loyalty_happiness(nation)
            self.sm.mark_dirty(); self.sm.autosave()
            self.profile.set_items(build_profile_items(nation, self.sm.state))
            set_status(f"Updated: {path}", GREEN)
        else:
            set_status("Invalid value — edit discarded.", RED_C)
        self.edit.close()

    # ── Main loop ─────────────────────────────────

    def run(self):
        running = True; dt = 0.0
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False; break
                if event.type == pygame.VIDEORESIZE:
                    sw, sh = event.w, event.h
                    self.screen = pygame.display.set_mode((sw,sh), pygame.RESIZABLE)
                    self.lay.update(sw,sh)
                    for obj in (self.tab_bar,self.left,self.profile,self.sysmap,
                                self.evlog,self.market):
                        obj.update_layout(self.lay)

                # Turn modal absorbs all events when open
                if self.turn_modal.active:
                    if self.turn_modal.on_event(event): self.turn_modal.close()
                    continue

                # Trade modal
                if self.trade_modal.active:
                    result = self.trade_modal.on_event(event, self.lay, self.sm)
                    if result and result != "confirmed":
                        ok = copy_to_clipboard(result)
                        set_status("Trade route export copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)
                    if result == "confirmed": self._load_nation(self.left.selected)
                    continue

                # Edit overlay
                if self.edit.active:
                    res = self.edit.on_event(event)
                    if res == "confirm": self._commit_edit()
                    elif res == "cancel": self.edit.close(); set_status("Edit cancelled.",DIM)
                    continue

                # Global keyboard shortcuts
                if event.type == pygame.KEYDOWN:
                    k = event.key
                    if k == pygame.K_s: self.sm.autosave(); set_status("Saved.",GREEN)
                    elif k == pygame.K_d: self._do_discord_export()
                    elif k == pygame.K_t: self._do_advance_turn()
                    elif k == pygame.K_r:
                        n = self._current_nation()
                        self.trade_modal.open(self.sm.state, n["name"] if n else "")
                    elif k == pygame.K_UP:
                        self._load_nation(self.left.selected - 1)
                    elif k == pygame.K_DOWN:
                        self._load_nation(self.left.selected + 1)
                    elif k == pygame.K_ESCAPE: running = False; break
                    elif k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                        delta = -self.profile.lay.mh if k==pygame.K_PAGEUP else self.profile.lay.mh
                        self.profile.scrl.scroll = max(0, self.profile.scrl.scroll + delta)
                        self.profile.scrl.clamp()

                # Tab bar
                new_tab = self.tab_bar.on_event(event)
                if new_tab is not None: self._load_nation(self.left.selected)

                # Left panel
                nation_idx, action = self.left.on_event(event)
                if nation_idx is not None: self._load_nation(nation_idx)
                if action == "save":  self.sm.autosave(); set_status("Saved.",GREEN)
                if action == "disc":  self._do_discord_export()
                if action == "adv":   self._do_advance_turn()
                if action == "trade":
                    n = self._current_nation()
                    self.trade_modal.open(self.sm.state, n["name"] if n else "")

                # Panel events
                tab = self.tab_bar.active
                if tab == 0:
                    hit = self.profile.on_event(event)
                    if hit: self.edit.open(hit["label"], hit["raw"], hit["meta"])
                elif tab == 1:
                    result = self.sysmap.on_event(event, self.sm.state)
                    if result:
                        ok = copy_to_clipboard(result)
                        set_status("System export copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)
                elif tab == 2:
                    self.evlog.on_event(event, self.edit)
                elif tab == 3:
                    result = self.market.on_event(event, self.edit, self.sm)
                    if result:
                        ok = copy_to_clipboard(result)
                        set_status("Market report copied!" if ok else "See terminal.", GREEN if ok else GOLD)
                        print("\n"+result)

            # ── DRAW ─────────────────────────────────────
            self.screen.fill(BG)
            tab = self.tab_bar.active
            n   = self._current_nation()
            nname = n["name"] if n else "—"
            state = self.sm.state
            draw_top_bar(self.screen, self.lay, nname,
                         state.get("turn",1), state.get("year",2200),
                         state.get("quarter",1), self.sm._dirty)
            self.tab_bar.draw(self.screen)
            self.left.draw(self.screen, state.get("turn",1),
                           state.get("year",2200), state.get("quarter",1))
            if tab == 0: self.profile.draw(self.screen)
            elif tab == 1: self.sysmap.draw(self.screen)
            elif tab == 2: self.evlog.draw(self.screen)
            elif tab == 3: self.market.draw(self.screen)
            draw_status_bar(self.screen, self.lay)
            self.edit.draw(self.screen, self.lay, dt)
            self.turn_modal.draw(self.screen, self.lay)
            self.trade_modal.draw(self.screen, self.lay)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    sf = sys.argv[1] if len(sys.argv) > 1 else None
    App(sf).run()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    sf = sys.argv[1] if len(sys.argv) > 1 else None
    App(sf).run()z