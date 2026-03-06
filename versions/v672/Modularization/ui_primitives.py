"""carmine.ui_primitives — pygame drawing helpers, overlays, row builder helpers"""
import pygame, time, math
from constants import *
from economy import fmt_cr, fmt_res, fmt_pct, fmt_pop, bar_str, nation_tag
from constants import _RESOURCES
from corporateAlpha0671 import compute_corp_income

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
