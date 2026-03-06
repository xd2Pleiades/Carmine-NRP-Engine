"""carmine.overlays — all overlay widgets, LeftPanel, MainPanel"""
import pygame, time, math, random
from constants import *
from economy import (compute_manpower, fmt_cr, fmt_pop, fmt_res,
                     nation_tag, is_colony, ECON_MODELS, queue_construction, DISTRICT_BUILD_TURNS)
from constants import _UNIT_CATS, _UNIT_TYPES_BY_CAT, _UNIT_VETERANCY, _CAT_NORM
from corporateAlpha0671 import compute_corp_income
from ui_primitives import (gf, tw, draw_text, draw_rect, Scrollbar, Button, EditOverlay,
                            GMConsoleOverlay, apply_edit, _row, _hdr1, _hdr2, _sep, _bar, _btn,
                            ROW_H, HDR1_H, HDR2_H, SEP_H, BTN_H, COL_H)
from build_rows import build_rows
from corporateAlpha0671 import (ContractBuilderOverlay, LocationBuilderOverlay,
                                 LocationSearcherOverlay, ShareholderBuilderOverlay,
                                 CorpEventBuilderOverlay, CorpGraphOverlay)

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


class UnitBuilderOverlay:
    """Overlay to create or edit a unit in active_forces_detail."""
    def __init__(self):
        self.active=False; self.mode="new"; self.unit_idx=-1
        self.fields=[]; self._blink=0.0; self.field_idx=0; self._nation_names=[]
    def _make_fields(self,u,nation_names):
        self._nation_names=list(nation_names)
        raw_cat=_CAT_NORM.get(u.get("category","Spacefleet"),"Spacefleet")
        cat_idx=_UNIT_CATS.index(raw_cat) if raw_cat in _UNIT_CATS else 0
        ut_list=_UNIT_TYPES_BY_CAT[_UNIT_CATS[cat_idx]]
        ut_idx=ut_list.index(u.get("unit",ut_list[0])) if u.get("unit") in ut_list else 0
        vet_idx=_UNIT_VETERANCY.index(u.get("veterancy","Regular")) if u.get("veterancy") in _UNIT_VETERANCY else 1
        self.fields=[
            {"key":"category",    "label":"Category",       "type":"choice","val":cat_idx,  "opts":_UNIT_CATS},
            {"key":"unit",        "label":"Unit Type",       "type":"choice","val":ut_idx,   "opts":ut_list},
            {"key":"count",       "label":"Count",           "type":"int",   "val":str(u.get("count",1))},
            {"key":"veterancy",   "label":"Veterancy",       "type":"choice","val":vet_idx,  "opts":_UNIT_VETERANCY},
            {"key":"custom_name", "label":"Custom Name",     "type":"text",  "val":u.get("custom_name","")},
            {"key":"training_turns","label":"Training Turns","type":"int",   "val":str(u.get("training_turns",0))},
            {"key":"maintenance", "label":"Maintenance/t",  "type":"float", "val":str(u.get("maintenance",0.0))},
        ]
    def open_new(self,nation_names,unit_groups):
        self.active=True; self.mode="new"; self.unit_idx=-1; self.field_idx=0
        self._make_fields({},nation_names)
    def open_edit(self,u,idx,nation_names,unit_groups):
        self.active=True; self.mode="edit"; self.unit_idx=idx; self.field_idx=0
        self._make_fields(u,nation_names)
    def close(self): self.active=False
    def _sync_cat(self):
        cat=_UNIT_CATS[self.fields[0]["val"]]
        ut_list=_UNIT_TYPES_BY_CAT[cat]
        self.fields[1]["opts"]=ut_list; self.fields[1]["val"]=min(self.fields[1]["val"],len(ut_list)-1)
    def get_unit_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="int":
                try: d[f["key"]]=int(f["val"])
                except: d[f["key"]]=0
            elif f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            else: d[f["key"]]=f["val"]
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx=MAIN_X; ry=MAIN_Y; rw=SW-MAIN_X; rh=SH-MAIN_Y-SBAR_H
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(5,10,22))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),BORDER2,border=2)
        f10=gf(10); f11=gf(11); f13=gf(13)
        lbl="NEW UNIT" if self.mode=="new" else f"EDIT UNIT  [#{self.unit_idx}]"
        draw_text(surf,lbl,rx+12,ry+7,f13,BRIGHT)
        draw_text(surf,"Up/Down=field  Left/Right=cycle choice  Type=edit text  Enter=save  Esc=cancel",rx+12,ry+24,f10,DIM)
        y=ry+42
        for i,f in enumerate(self.fields):
            sel=(i==self.field_idx)
            rr=pygame.Rect(rx+4,y,rw-8,22)
            draw_rect(surf,rr,SEL if sel else ((10,18,28) if i%2==0 else BG),radius=2)
            if sel: draw_rect(surf,rr,EDITBDR,border=1,radius=2)
            draw_text(surf,f["label"],rx+14,y+4,f11,BRIGHT if sel else DIM)
            if f["type"]=="choice":
                draw_text(surf,f"\u25c4 {f['opts'][f['val']]} \u25ba",rx+230,y+4,f11,CYAN if sel else TEXT)
            else:
                cur="\u258e" if (sel and self._blink<0.5) else ""
                draw_text(surf,f["val"]+cur,rx+230,y+4,f11,EDITBDR if sel else TEXT)
            y+=24
        # consumption preview
        ud=self.get_unit_data(); cat=ud.get("category",""); cnt=ud.get("count",1)
        uname=ud.get("unit","")
        if cat in ("Ground Forces",):
            food_p=cnt*GROUND_DIVISION_SIZE*GROUND_FOOD_PER_SOLDIER
            alloy_p=cnt*GROUND_ALLOY_PER_DIVISION
        else:
            food_p=UNIT_CREW.get(uname,0)*cnt; alloy_p=UNIT_ALLOY_CON.get(uname,0)*cnt
        draw_text(surf,f"Consumption preview:  Food {fmt_res(food_p)}/t   Alloys {fmt_res(alloy_p)}/t",rx+14,y+6,f10,TEAL)
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
                if f["key"]=="category": self._sync_cat()
            elif f["type"] in ("text","int","float"):
                if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
                elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode
        return None


class EcoProjectOverlay:
    """Simple overlay to define a new economic project."""
    def __init__(self):
        self.active=False; self._blink=0.0; self.field_idx=0
        self.fields=[]
    _PROJ_TYPES=["Investment","Subsidy","Infrastructure","R&D Grant","Market Intervention"]
    _EFFECT_FIELDS=["ipeu_growth","pop_growth","bureaucratic_efficiency","subsidy_rate","investment_rate","none"]
    def open(self):
        self.active=True; self.field_idx=0
        self.fields=[
            {"key":"name",          "label":"Project Name",  "type":"text",  "val":"New Project"},
            {"key":"type",          "label":"Project Type",  "type":"choice","val":0,"opts":self._PROJ_TYPES},
            {"key":"cost_per_turn", "label":"Cost / Turn",   "type":"float", "val":"0"},
            {"key":"total_turns",   "label":"Duration (turns)","type":"int", "val":"4"},
            {"key":"effect_field",  "label":"Effect Field",  "type":"choice","val":0,"opts":self._EFFECT_FIELDS},
            {"key":"effect_value",  "label":"Effect Value",  "type":"float", "val":"0.01"},
        ]
    def close(self): self.active=False
    def get_data(self):
        d={"status":"active"}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="int":
                try: d[f["key"]]=int(f["val"])
                except: d[f["key"]]=1
            elif f["type"]=="float":
                try: d[f["key"]]=float(f["val"])
                except: d[f["key"]]=0.0
            else: d[f["key"]]=f["val"]
        d["turns_remaining"]=d.get("total_turns",4)
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx=MAIN_X+60; ry=MAIN_Y+40; rw=SW-MAIN_X-120; rh=260
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(5,12,22))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),GOLD,border=2)
        f10=gf(10); f11=gf(11); f13=gf(13)
        draw_text(surf,"NEW ECONOMIC PROJECT",rx+10,ry+6,f13,BRIGHT)
        draw_text(surf,"Up/Down=field  Left/Right=cycle  Type=edit  Enter=save  Esc=cancel",rx+10,ry+22,f10,DIM)
        y=ry+40
        for i,f in enumerate(self.fields):
            sel=(i==self.field_idx)
            rr=pygame.Rect(rx+4,y,rw-8,22)
            draw_rect(surf,rr,SEL if sel else ((10,18,28) if i%2==0 else BG),radius=2)
            if sel: draw_rect(surf,rr,GOLD,border=1,radius=2)
            draw_text(surf,f["label"],rx+14,y+4,f11,BRIGHT if sel else DIM)
            if f["type"]=="choice":
                draw_text(surf,f"\u25c4 {f['opts'][f['val']]} \u25ba",rx+220,y+4,f11,GOLD if sel else TEXT)
            else:
                cur="\u258e" if (sel and self._blink<0.5) else ""
                draw_text(surf,f["val"]+cur,rx+220,y+4,f11,GOLD if sel else TEXT)
            y+=24
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            if ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            f=self.fields[self.field_idx]
            if f["type"]=="choice":
                if ev.key==pygame.K_LEFT: f["val"]=(f["val"]-1)%len(f["opts"])
                elif ev.key==pygame.K_RIGHT: f["val"]=(f["val"]+1)%len(f["opts"])
            elif f["type"] in ("text","int","float"):
                if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
                elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode
        return None


class CasualtiesOverlay:
    """Log military deaths for a species."""
    def __init__(self):
        self.active=False; self._blink=0.0; self.field_idx=0; self.fields=[]
    _LIFE_STAGES=["Teen","Young Adult","Adult","Middle Aged","Senior"]
    def open(self,species_names):
        self.active=True; self.field_idx=0
        opts=list(species_names) if species_names else ["Unknown"]
        self.fields=[
            {"key":"species",    "label":"Species",    "type":"choice","val":0,"opts":opts},
            {"key":"count",      "label":"Deaths",     "type":"int",   "val":"0"},
            {"key":"life_stage", "label":"Life Stage", "type":"choice","val":2,"opts":self._LIFE_STAGES},
        ]
    def close(self): self.active=False
    def get_data(self):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            elif f["type"]=="int":
                try: d[f["key"]]=int(f["val"])
                except: d[f["key"]]=0
            else: d[f["key"]]=f["val"]
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx=MAIN_X+80; ry=MAIN_Y+80; rw=SW-MAIN_X-160; rh=140
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(18,5,5))
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),RED_C,border=2)
        f10=gf(10); f11=gf(11); f13=gf(13)
        draw_text(surf,"LOG CASUALTIES",rx+10,ry+6,f13,BRIGHT)
        draw_text(surf,"Up/Down=field  Left/Right=cycle  Type=count  Enter=log  Esc=cancel",rx+10,ry+22,f10,DIM)
        y=ry+42
        for i,f in enumerate(self.fields):
            sel=(i==self.field_idx)
            rr=pygame.Rect(rx+4,y,rw-8,22)
            draw_rect(surf,rr,SEL if sel else BG,radius=2)
            if sel: draw_rect(surf,rr,RED_C,border=1,radius=2)
            draw_text(surf,f["label"],rx+14,y+4,f11,BRIGHT if sel else DIM)
            if f["type"]=="choice":
                draw_text(surf,f"\u25c4 {f['opts'][f['val']]} \u25ba",rx+180,y+4,f11,RED_C if sel else TEXT)
            else:
                cur="\u258e" if (sel and self._blink<0.5) else ""
                draw_text(surf,f["val"]+cur,rx+180,y+4,f11,RED_C if sel else TEXT)
            y+=24
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            if ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            f=self.fields[self.field_idx]
            if f["type"]=="choice":
                if ev.key==pygame.K_LEFT: f["val"]=(f["val"]-1)%len(f["opts"])
                elif ev.key==pygame.K_RIGHT: f["val"]=(f["val"]+1)%len(f["opts"])
            elif f["type"] in ("int","text"):
                if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
                elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode
        return None


# ── panels ────────────────────────────────────────────────────────────────────

# ContractBuilderOverlay...CorpGraphOverlay moved to corporateAlpha0671.py

class EventBuilderOverlay:
    """Add or edit a global events_log entry."""
    _TYPE_OPTS=["Market","Civic","Piracy","Resource","Planetside","Colony","Corp","Custom"]
    def __init__(self):
        self.active=False; self.mode="new"; self.ev_idx=-1
        self.fields=[]; self.field_idx=0; self._blink=0.0
    def _init_fields(self,ev,nation_name=""):
        tid=self._TYPE_OPTS.index(ev.get("type","Custom")) if ev.get("type","Custom") in self._TYPE_OPTS else 7
        self.fields=[
            {"key":"type",       "label":"Event Type", "type":"choice","val":tid,"opts":self._TYPE_OPTS},
            {"key":"nation",     "label":"Nation",     "type":"text",  "val":ev.get("nation",nation_name)},
            {"key":"label",      "label":"Label",      "type":"text",  "val":ev.get("label","")},
            {"key":"description","label":"Description","type":"text",  "val":ev.get("description","")},
        ]
        self.field_idx=0
    def open_new(self,nation_name=""): self.active=True; self.mode="new"; self.ev_idx=-1; self._init_fields({},nation_name)
    def open_edit(self,ev,idx): self.active=True; self.mode="edit"; self.ev_idx=idx; self._init_fields(ev)
    def close(self): self.active=False
    def get_data(self,state):
        d={}
        for f in self.fields:
            if f["type"]=="choice": d[f["key"]]=f["opts"][f["val"]]
            else: d[f["key"]]=f["val"]
        d["turn"]=state.get("turn",1); d["year"]=state.get("year",2200); d["quarter"]=state.get("quarter",1)
        d["roll"]="GM"; d["col_rgb"]=list(CYAN)
        return d
    def draw(self,surf,dt):
        if not self.active: return
        self._blink=(self._blink+dt)%1.0
        rx=MAIN_X; ry=MAIN_Y; rw=SW-MAIN_X; rh=SH-MAIN_Y-SBAR_H
        draw_rect(surf,pygame.Rect(rx,ry,rw,rh),(5,10,20)); draw_rect(surf,pygame.Rect(rx,ry,rw,rh),CYAN,border=2)
        lbl="NEW EVENT" if self.mode=="new" else f"EDIT EVENT [{self.ev_idx}]"
        draw_text(surf,lbl,rx+12,ry+7,gf(13),BRIGHT)
        draw_text(surf,"Up/Down=field  Left/Right=cycle  Type=edit  Enter=save  Esc=cancel",rx+12,ry+24,gf(10),DIM)
        y=ry+48
        for i,f in enumerate(self.fields):
            sel=(i==self.field_idx); rr=pygame.Rect(rx+4,y,rw-8,22)
            draw_rect(surf,rr,SEL if sel else((10,18,28) if i%2==0 else BG),radius=2)
            if sel: draw_rect(surf,rr,CYAN,border=1,radius=2)
            draw_text(surf,f["label"],rx+14,y+4,gf(11),BRIGHT if sel else DIM)
            if f["type"]=="choice": draw_text(surf,f"◄ {f['opts'][f['val']]} ►",rx+220,y+4,gf(11),CYAN if sel else TEXT)
            else:
                cur="▎" if (sel and self._blink<0.5) else ""
                draw_text(surf,f["val"]+cur,rx+220,y+4,gf(11),EDITBDR if sel else TEXT)
            y+=24
    def on_event(self,ev):
        if not self.active: return None
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close(); return None
            if ev.key==pygame.K_RETURN: return "save"
            if ev.key==pygame.K_UP: self.field_idx=max(0,self.field_idx-1)
            elif ev.key==pygame.K_DOWN: self.field_idx=min(len(self.fields)-1,self.field_idx+1)
            else:
                f=self.fields[self.field_idx]
                if f["type"]=="choice":
                    if ev.key==pygame.K_LEFT: f["val"]=(f["val"]-1)%len(f["opts"])
                    elif ev.key==pygame.K_RIGHT: f["val"]=(f["val"]+1)%len(f["opts"])
                elif f["type"]=="text":
                    if ev.key==pygame.K_BACKSPACE: f["val"]=f["val"][:-1]
                    elif ev.unicode and ev.unicode.isprintable(): f["val"]+=ev.unicode
        return None

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
    def set_nations(self,names,sel=0,state=None):
        self.nations=names; self.selected=sel; self._state=state or {}
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
        nmap={n["name"]:n for n in self._state.get("nations",[])}
        for i,name in enumerate(self.nations):
            yr=pygame.Rect(self.PAD,y0+i*22,LWIDTH-Scrollbar.W-self.PAD*2,20)
            if yr.collidepoint(mx,my): self._hover=i
            if i==self.selected: draw_rect(surf,yr,SEL,radius=2); draw_rect(surf,yr,BORDER2,border=1,radius=2)
            elif self._hover==i: draw_rect(surf,yr,HOVER,radius=2)
            is_npc=nmap.get(name,{}).get("is_npc",False)
            tag_col=DIM if is_npc else ACCENT
            draw_text(surf,f"[{nation_tag(name)}]",yr.x+2,yr.y+3,f10,tag_col)
            name_col=(DIM if is_npc else BRIGHT) if i==self.selected else (DIM if is_npc else TEXT)
            draw_text(surf,name[:22],yr.x+36,yr.y+3,f10,name_col)
            if is_npc: draw_text(surf,"NPC",yr.x+LWIDTH-Scrollbar.W-self.PAD*2-26,yr.y+3,f10,(50,72,92))
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
