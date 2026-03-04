#!/usr/bin/env python3
"""
Carmine NRP Engine — vAlpha0.3.0
Single-file GM tool: Pygame UI + engine + Discord export + 5-slot backup
Run: python3 carmine_nrp.py [state_file.json]
"""

import sys, os, json, shutil, math, time, textwrap
import pygame
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
DEFAULT_STATE  = str(Path(__file__).parent / "carmine_state_T5_Y2201Q1.json")
BACKUP_COUNT   = 5
SW, SH         = 1280, 720
LWIDTH         = 240
TBAR_H         = 40
TABBAR_H       = 30
SBAR_H         = 22
FPS            = 60

MAIN_X = LWIDTH
MAIN_Y = TBAR_H + TABBAR_H
MAIN_W = SW - LWIDTH
MAIN_H = SH - TBAR_H - TABBAR_H - SBAR_H

# ─────────────────────────────────────────────
#  PALETTE
# ─────────────────────────────────────────────
BG      = (  8, 12, 20)
PANEL   = ( 12, 18, 28)
PANEL2  = ( 16, 24, 38)
BORDER  = ( 28, 52, 80)
BORDER2 = ( 44, 86,128)
ACCENT  = (190, 38, 25)
CYAN    = (  0,190,214)
TEAL    = (  0,138,158)
TEXT    = (198,226,246)
DIM     = ( 84,114,136)
DIM2    = ( 50, 72, 92)
BRIGHT  = (238,248,255)
GREEN   = ( 22,184, 82)
RED_C   = (216, 54, 40)
GOLD    = (198,150, 22)
SEL     = ( 18, 40, 65)
HOVER   = ( 14, 30, 50)
EDITBG  = (  5, 14, 28)
EDITBDR = (  0,172,194)
BTNBG   = ( 18, 36, 56)
BTNHOV  = ( 28, 54, 82)
BTNACC  = (140, 24, 16)
BTNACC2 = (190, 38, 25)

# ─────────────────────────────────────────────
#  FORMATTING HELPERS
# ─────────────────────────────────────────────
def fmt_cr(v: float) -> str:
    if v is None: return "—"
    a = abs(v)
    if a >= 1e15: return f"{v/1e15:.3f} Qcr"
    if a >= 1e12: return f"{v/1e12:.3f} Tcr"
    if a >= 1e9:  return f"{v/1e9:.3f} Bcr"
    if a >= 1e6:  return f"{v/1e6:.3f} Mcr"
    if a >= 1e3:  return f"{v/1e3:.2f} Kcr"
    return f"{v:.0f} cr"

def fmt_pop(v: float) -> str:
    if v is None: return "—"
    a = abs(v)
    if a >= 1e9: return f"{v/1e9:.3f}B"
    if a >= 1e6: return f"{v/1e6:.3f}M"
    if a >= 1e3: return f"{v/1e3:.2f}K"
    return f"{v:.0f}"

def fmt_res(v: float) -> str:
    if v is None: return "—"
    a = abs(v)
    if a >= 1e9: return f"{v/1e9:.3f}B"
    if a >= 1e6: return f"{v/1e6:.3f}M"
    if a >= 1e3: return f"{v/1e3:.2f}K"
    return f"{v:.2f}"

def fmt_pct(v: float) -> str:
    s = f"{v*100:+.2f}%" if v != 0 else "0.00%"
    return s

def bar_str(pct: float, w: int = 18) -> str:
    pct = max(0.0, min(1.0, pct))
    f = round(pct * w)
    return "█" * f + "░" * (w - f)

def nation_tag(name: str) -> str:
    words = name.split()
    if len(words) >= 2:
        return "".join(w[0].upper() for w in words[:4])
    return name[:4].upper()

# ─────────────────────────────────────────────
#  ENGINE — COMPUTE
# ─────────────────────────────────────────────
def years_elapsed(state: dict) -> float:
    return (state.get("turn", 1) - 1) * 0.25

def current_ipeu(nation: dict, ye: float) -> float:
    return nation.get("base_ipeu", 0.0) * (1.0 + nation.get("ipeu_growth", 0.0)) ** ye

def current_population(nation: dict, ye: float) -> float:
    return nation.get("population", 0.0) * (1.0 + nation.get("pop_growth", 0.0)) ** ye

def compute_trade(nation: dict, routes: list) -> dict:
    name = nation["name"]
    exports = imports = transit_income = 0.0
    for r in routes:
        if r.get("status") != "active": continue
        cr = r.get("credits_per_turn", 0.0)
        ts = r.get("transit_nations", [])
        if r["exporter"] == name:
            tax = sum(cr * t.get("tax_rate", 0.0) for t in ts if t.get("status") == "active")
            exports += cr - tax
        if r["importer"] == name:
            imports += cr
        for t in ts:
            if t.get("nation") == name and t.get("status") == "active":
                transit_income += cr * t.get("tax_rate", 0.0)
    return {"exports": exports, "imports": imports, "transit_income": transit_income,
            "net": exports - imports + transit_income}

def compute_resources(nation: dict, ipeu: float) -> dict:
    exp = nation.get("expenditure", {})
    pop = nation.get("population", 1.0)
    out = {}
    for rname in ["Food", "Minerals", "Energy", "Alloys", "Consumer Goods"]:
        sd    = (nation.get("resource_stockpiles") or {}).get(rname, {})
        if not isinstance(sd, dict): sd = {}
        mode  = sd.get("production_mode", "derived")
        stock = sd.get("stockpile", 0.0)
        if mode == "flat":
            prod, cons, est = sd.get("flat_production", 0.0), sd.get("flat_consumption", 0.0), False
        else:
            agri = exp.get("Agriculture", 0.0) * ipeu
            ind  = exp.get("Industry",    0.0) * ipeu
            if rname == "Food":
                prod = agri * nation.get("food_efficiency", 1.0) / 1e6
                cons = pop  * nation.get("food_consumption_rate", 0.01)
            elif rname == "Minerals":
                prod = ind * nation.get("mineral_workforce_pct", 0.05) * nation.get("mineral_ipeu_factor", 0.5) / 1e3
                cons = prod * 0.4
            elif rname == "Energy":
                prod = ind * 0.002 / 1e3; cons = prod * 0.6
            elif rname == "Alloys":
                prod = ind * nation.get("mineral_to_alloy_ratio", 0.0) * 0.001 / 1e3; cons = prod * 0.3
            else:  # Consumer Goods
                prod = ind * nation.get("cg_efficiency", 0.8) * 0.0005 / 1e3
                cons = pop  * nation.get("cg_consumption_rate", 0.005)
            est = True
        net   = prod - cons
        trend = "▲" if net > 0 else ("▼" if net < 0 else "─")
        out[rname] = {"stockpile": stock, "production": prod, "consumption": cons,
                      "net": net, "trend": trend, "estimated": est}
    return out

def compute_debt(nation: dict, ipeu: float) -> dict:
    bal  = nation.get("debt_balance", 0.0)
    rate = nation.get("interest_rate", 0.0)
    rep  = nation.get("debt_repayment", 0.0)
    qi   = bal * rate / 4.0 if bal > 0 else 0.0
    return {"balance": bal, "rate": rate, "repayment": rep,
            "q_interest": qi, "load_pct": (bal / ipeu * 100) if ipeu else 0.0,
            "is_debtor": bal > 0}

# ─────────────────────────────────────────────
#  STATE MANAGER
# ─────────────────────────────────────────────
class StateManager:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.state: dict = {}
        self.dirty = False

    def load(self) -> bool:
        try:
            with open(self.filepath) as f:
                self.state = json.load(f)
            self.dirty = False
            return True
        except Exception as e:
            print(f"[LOAD ERROR] {e}")
            return False

    def save(self, path: Optional[Path] = None) -> bool:
        target = Path(path) if path else self.filepath
        self._rotate_backups(target)
        try:
            with open(target, "w") as f:
                json.dump(self.state, f, indent=2)
            self.dirty = False
            return True
        except Exception as e:
            print(f"[SAVE ERROR] {e}")
            return False

    def autosave(self):
        self.save()

    def mark_dirty(self):
        self.dirty = True

    def _rotate_backups(self, target: Path):
        def bp(n): return target.with_suffix(f".bak{n}.json")
        if bp(BACKUP_COUNT - 1).exists(): bp(BACKUP_COUNT - 1).unlink()
        for i in range(BACKUP_COUNT - 2, 0, -1):
            if bp(i).exists(): bp(i).rename(bp(i + 1))
        if target.exists():
            try: target.rename(bp(1))
            except: pass

    def nation_names(self) -> list:
        ns = self.state.get("nations", [])
        return [n["name"] for n in ns]

    def get_nation(self, name: str) -> Optional[dict]:
        for n in self.state.get("nations", []):
            if n["name"] == name: return n
        return None

# ─────────────────────────────────────────────
#  DISCORD FORMATTER  (matches NRP_Mechanics.md spec)
# ─────────────────────────────────────────────
def format_discord(nation: dict, state: dict) -> str:
    ye       = years_elapsed(state)
    ipeu     = nation.get("base_ipeu", 0.0)
    pop      = current_population(nation, ye)
    exp      = nation.get("expenditure", {}) if isinstance(nation.get("expenditure"), dict) else {}
    routes   = state.get("trade_routes", [])
    trade    = compute_trade(nation, routes)
    res      = compute_resources(nation, ipeu)
    debt     = compute_debt(nation, ipeu)
    rbudget  = nation.get("research_budget", 0.0)
    sfund    = nation.get("strategic_fund", 0.0)
    species  = nation.get("species_populations", [])
    star_sys = nation.get("star_systems", [])
    projects = nation.get("projects", [])
    afd      = nation.get("active_forces_detail", []) or []
    ugroups  = {ug["ugid"]: ug for ug in (nation.get("unit_groups") or [])}
    active_r = nation.get("active_research_projects", []) or []
    done_r   = nation.get("completed_techs", []) or []

    quarter  = state.get("quarter", 1)
    year     = state.get("year", 2200)
    tag      = nation_tag(nation["name"])
    civ_lvl  = nation.get("civ_level",  "Interplanetary Industrial")
    civ_tier = nation.get("civ_tier",   2)
    eco_mdl  = nation.get("economic_model", "MIXED")
    eco_st   = nation.get("eco_status",  "Stable")

    homeworld = "—"
    for sys in star_sys:
        for pl in sys.get("planets", []):
            homeworld = pl["name"]; break
        break

    sp_str    = ", ".join(f"{s['name']} ({s.get('status','?').title()})" for s in species) if species else "—"
    pop_gr    = nation.get("pop_growth", 0.0)
    total_exp = sum(exp.values()) * ipeu + rbudget
    net_bal   = ipeu + trade["net"] - total_exp - debt["q_interest"]
    per_cap   = int(ipeu / pop) if pop else 0

    L = []
    A = L.append

    A(f"-# [{tag}] {nation['name'].upper()}")
    A(f"# NATIONAL PROFILE - Q{quarter} [{year}]")
    A("```")
    A(f"  Species          : {sp_str}")
    A(f"  Population       : {fmt_pop(pop)}")
    A(f"  Pop Growth       : {fmt_pct(pop_gr)} / yr")
    A(f"  Homeworld        : {homeworld}")
    A(f"  Civilisation     : {civ_lvl}")
    A(f"  Tier             : {civ_tier}")
    A(f"  Economic Model   : {eco_mdl}")
    A(f"  Status           : {eco_st}")
    A("```")

    A("# ECONOMY")
    A("```")
    A(f"  IPEU (base)      : {fmt_cr(ipeu)}")
    A(f"  IPEU Growth      : {fmt_pct(nation.get('ipeu_growth', 0.0))} / yr")
    A(f"  IPEU per Capita  : {per_cap:,} cr")
    A(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
    A(f"   - Exports       : {fmt_cr(trade['exports'])}")
    A(f"   - Imports       : {fmt_cr(trade['imports'])}")
    A(f"  Total Expenditure: {fmt_cr(total_exp)}")
    A(f"  Research Budget  : {fmt_cr(rbudget)} / turn")
    A(f"  Net Balance      : {fmt_cr(net_bal)}")
    A("```")

    A("## EXPENDITURE & BREAKDOWN")
    A("```")
    max_pct = max(exp.values(), default=0.01)
    for cat, pct in exp.items():
        bar = bar_str(pct / max_pct, 20)
        A(f"  {cat:<22} {pct*100:5.1f}%  {bar}  {fmt_cr(pct * ipeu)}")
    A(f"  {'─'*61}")
    A(f"  {'TOTAL':<22} {sum(exp.values())*100:5.1f}%  {'':20}  ({fmt_cr(total_exp)})")
    A("```")

    A("## ECONOMIC PROJECTS")
    A("```")
    active_p = [p for p in projects if p.get("status") in ("active","in_progress","complete")]
    if active_p:
        for p in active_p:
            tl  = p.get("duration_turns", 0) - p.get("turns_elapsed", 0)
            tag2 = "[COMPLETE]" if p.get("status") == "complete" else f"[{tl}t left]"
            A(f"  {p['name']} ({p.get('category','?')})  {tag2}")
    else:
        A("  None")
    A("```")

    A("## FISCAL REPORT")
    A("```")
    sf_icon = "🟢" if sfund >= 0 else "🔴"
    fd      = -debt["q_interest"]
    fd_s    = f"+{fmt_cr(fd)}" if fd >= 0 else fmt_cr(fd)
    A(f"  Debtor/ Creditor     : {'Debtor' if debt['is_debtor'] else 'Creditor'}")
    A(f"  Debt Balance         : {fmt_cr(debt['balance'])}")
    A(f"  Debt Load            : {debt['load_pct']:.1f}%")
    A(f"  Interest Rate        : {debt['rate']*100:.2f}%")
    A(f"  Quarterly Int.       : {fmt_cr(debt['q_interest'])}")
    A(f"  Debt Repayment       : {fmt_cr(debt['repayment'])}")
    A(f"  {'─'*61}")
    A(f"  Strategic Fund   : {sf_icon} {fmt_cr(sfund)}")
    A(f"  Fund Δ this turn : {fd_s}")
    A("```")

    A("## RESOURCES & STOCKPILES")
    for rname in ["Food","Minerals","Energy","Alloys","Consumer Goods"]:
        rd = res[rname]
        ns = f"+{fmt_res(rd['net'])}" if rd["net"] >= 0 else fmt_res(rd["net"])
        A("```")
        A(f"  {rname} Stockpile            : {fmt_res(rd['stockpile'])}")
        A(f"  {rname} Production per turn  : {fmt_res(rd['production'])}")
        A(f"  {rname} Consumption per turn : {fmt_res(rd['consumption'])}")
        A(f"  {rname} Net per turn         : {ns}")
        A(f"  {rname} Trend                : {rd['trend']}")
        A("```")

    A("# TERRITORIES")
    if star_sys:
        sys0 = star_sys[0]
        A(f"Home System: {sys0['name']}")
        for planet in sys0.get("planets", []):
            A("```")
            pop_a = planet.get("pop_assigned", pop)
            A(f"  Homeworld: {planet['name']}")
            A(f"    Population    : {fmt_pop(pop_a)}")
            setts = planet.get("settlements", [])
            if setts:
                A(f"    Settlements   : {len(setts)}")
                for s in setts:
                    A(f"      - {s['name']}")
                    dc: Dict[str,int] = {}
                    for d in s.get("districts", []):
                        dt = d.get("type","?"); dc[dt] = dc.get(dt,0)+1
                    for dt, cnt in dc.items():
                        A(f"        [{dt}] ×{cnt}")
            else:
                A("    Settlements   : None")
            A("```")
    else:
        A("No territorial data")

    A("# NATIONAL DEMOGRAPHICS")
    A("```")
    A(f"  Total Population     : {fmt_pop(pop)}")
    A(f"  Loyalty Modifier     : {nation.get('loyalty_modifier_cg', 1.0):.2f}")
    A("```")
    for s in species:
        dom   = s.get("status","") in ("dominant","majority")
        crown = "👑" if dom else "👥"
        sp_p  = s.get("population", 0)
        shr   = sp_p / pop * 100 if pop else 0
        loy   = s.get("loyalty", 0)
        li    = "🟢" if loy >= 70 else ("🟡" if loy >= 40 else "🔴")
        A(f"**{s['name']}**  {crown} {s.get('status','').title()}")
        A("```")
        A(f"  Population       : {fmt_pop(sp_p)}")
        A(f"  Share            : {shr:.1f}% — {s.get('status','?').title()}")
        A(f"  Growth Rate      : {fmt_pct(s.get('growth_rate',0))} / yr")
        A(f"  Culture          : {s.get('culture','—')}")
        A(f"  Language         : {s.get('language','—')}")
        A(f"  Religion         : {s.get('religion','—')}")
        A(f"  Loyalty          : {li} {loy}/100")
        A(f"  Happiness        : {s.get('happiness','—')}")
        A("```")

    A("# MILITARY")
    CAT_MAP = [
        ("## SPACEFLEET",       ["Spacefleet","Navy"]),
        ("## AEROSPACE FORCES", ["Air Force","Aerospace"]),
        ("## GROUND FORCES",    ["Ground Forces","Ground","Army"]),
    ]
    for hdr, cats in CAT_MAP:
        units = [u for u in afd if u.get("category") in cats]
        A(hdr)
        A("```")
        if units:
            grouped: Dict[str,list] = {}
            for u in units:
                ugid = u.get("ugid")
                grp  = ugroups[ugid]["name"] if ugid and ugid in ugroups else "—"
                grouped.setdefault(grp, []).append(u)
            for grp, us in grouped.items():
                if grp != "—": A(f"  {grp}")
                for u in us:
                    nm  = u.get("custom_name") or u["unit"]
                    vet = u.get("veterancy","?")
                    cnt = u.get("count",1)
                    sz  = u.get("size","?")
                    str_= u.get("strength","?")
                    mnt = u.get("maintenance","?")
                    A(f"    - {nm} | ×{cnt} | {sz} | {vet} | STR {str_} | {fmt_cr(mnt) if isinstance(mnt,(int,float)) else mnt} maint")
        else:
            A("  None on record")
        A("```")

    A("# ARSENAL")
    A("```")
    arsenal = nation.get("arsenal", []) or []
    if arsenal:
        for a in arsenal:
            A(f"  {a.get('name','?')} | {a.get('type','?')} | {a.get('size','?')} | Crew: {a.get('crew','?')} | {fmt_cr(a.get('maintenance',0))} maint | {a.get('production_time','?')} turns")
    else:
        A("  None")
    A("```")

    A("# RESEARCH")
    A("```")
    A(f"  RP per turn      : {fmt_cr(rbudget)}")
    A(f"  {'─'*61}")
    A("  Active Projects:")
    if active_r:
        for p in active_r:
            prog = p.get("progress", 0.0)
            A(f"    {p.get('name','?')} [{p.get('field','?')}]")
            A(f"      Progress : {prog:.1f}%  {bar_str(prog/100, 20)}")
            if p.get("benefits"): A(f"      Benefits : {p['benefits']}")
    else:
        A("    None")
    A("  Completed Projects:")
    if done_r:
        for t in (done_r[-8:]):
            tname = t if isinstance(t, str) else t.get("name", str(t))
            A(f"    ✓ {tname}")
    else:
        A("    None")
    A("```")

    return "\n".join(L)

# ─────────────────────────────────────────────
#  FONT CACHE
# ─────────────────────────────────────────────
_fonts: Dict[str, pygame.font.Font] = {}

def gf(size: int, mono: bool = True) -> pygame.font.Font:
    key = f"{'m' if mono else 's'}{size}"
    if key not in _fonts:
        if mono:
            for name in ("Courier New","Consolas","DejaVu Sans Mono","monospace"):
                try:
                    _fonts[key] = pygame.font.SysFont(name, size)
                    break
                except: pass
            else:
                _fonts[key] = pygame.font.Font(None, size)
        else:
            _fonts[key] = pygame.font.SysFont("Arial", size)
    return _fonts[key]

def tw(txt: str, font: pygame.font.Font) -> int:
    return font.size(txt)[0]

def draw_text(surf, txt, x, y, font, col=TEXT, clip=None):
    if not txt: return
    s = font.render(str(txt), True, col)
    if clip:
        r = s.get_rect(topleft=(x,y))
        r = r.clip(clip)
        if r.width > 0:
            surf.blit(s, (x,y), area=pygame.Rect(0,0,r.width,r.height))
    else:
        surf.blit(s, (x,y))

def draw_rect(surf, rect, col, border=0, radius=0):
    if radius:
        pygame.draw.rect(surf, col, rect, border_radius=radius)
    else:
        pygame.draw.rect(surf, col, rect, border)

# ─────────────────────────────────────────────
#  SCROLLBAR
# ─────────────────────────────────────────────
class Scrollbar:
    W = 8
    def __init__(self, x, y, h):
        self.rect = pygame.Rect(x, y, self.W, h)
        self.scroll = 0
        self.content_h = h
        self.view_h    = h
        self._dragging = False
        self._drag_y   = 0

    def set_content(self, ch, vh):
        self.content_h = max(ch, vh)
        self.view_h    = vh
        self.scroll    = max(0, min(self.scroll, self.content_h - self.view_h))

    def clamp(self):
        self.scroll = max(0, min(self.scroll, max(0, self.content_h - self.view_h)))

    def draw(self, surf):
        draw_rect(surf, self.rect, (12,20,32))
        if self.content_h <= self.view_h: return
        ratio  = self.view_h / self.content_h
        th     = max(24, int(self.rect.h * ratio))
        ty     = self.rect.y + int((self.scroll / self.content_h) * self.rect.h)
        ty     = min(ty, self.rect.bottom - th)
        draw_rect(surf, pygame.Rect(self.rect.x, ty, self.W, th), (44,88,130), radius=3)

    def on_event(self, ev, hovering=True):
        if ev.type == pygame.MOUSEWHEEL and hovering:
            self.scroll -= ev.y * 22
            self.clamp()
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self._dragging = True; self._drag_y = ev.pos[1]
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self._dragging = False
        if ev.type == pygame.MOUSEMOTION and self._dragging:
            dy = ev.pos[1] - self._drag_y; self._drag_y = ev.pos[1]
            self.scroll += int(dy * self.content_h / self.view_h)
            self.clamp()

# ─────────────────────────────────────────────
#  BUTTON
# ─────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, accent=False, small=False):
        self.rect   = pygame.Rect(rect)
        self.label  = label
        self.accent = accent
        self.small  = small
        self._hover = False

    def draw(self, surf):
        bg  = (BTNACC2 if self._hover else BTNACC) if self.accent else (BTNHOV if self._hover else BTNBG)
        bdr = ACCENT if self.accent else BORDER2
        draw_rect(surf, self.rect, bg, radius=3)
        draw_rect(surf, self.rect, bdr, border=1, radius=3)
        f   = gf(11 if self.small else 12)
        s   = f.render(self.label, True, BRIGHT)
        surf.blit(s, s.get_rect(center=self.rect.center))

    def on_event(self, ev) -> bool:
        if ev.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos): return True
        return False

# ─────────────────────────────────────────────
#  EDIT OVERLAY
# ─────────────────────────────────────────────
class EditOverlay:
    H = 80
    def __init__(self):
        self.active = False
        self.label  = ""
        self.text   = ""
        self.meta   = {}
        self._blink = 0.0

    def open(self, label, raw, meta):
        self.active = True
        self.label  = label
        self.text   = str(raw) if raw is not None else ""
        self.meta   = meta
        pygame.key.set_repeat(400, 40)

    def close(self):
        self.active = False
        self.text   = ""
        self.meta   = {}
        pygame.key.set_repeat(0, 0)

    def draw(self, surf, dt):
        if not self.active: return
        self._blink = (self._blink + dt) % 1.0
        y = SH - self.H - SBAR_H
        r = pygame.Rect(0, y, SW, self.H)
        draw_rect(surf, r, EDITBG)
        draw_rect(surf, r, EDITBDR, border=1)
        f12 = gf(12); f11 = gf(11)
        draw_text(surf, f"Edit: {self.label}", 14, y+8, f12, CYAN)
        draw_text(surf, "Enter = confirm   Esc = cancel", SW-280, y+8, f11, DIM)
        # input box
        bx = pygame.Rect(14, y+28, SW-28, 32)
        draw_rect(surf, bx, (8,18,30))
        draw_rect(surf, bx, EDITBDR, border=1)
        draw_text(surf, self.text, bx.x+6, bx.y+8, f12, BRIGHT)
        if self._blink < 0.5:
            cx = bx.x + 6 + tw(self.text, f12)
            pygame.draw.line(surf, CYAN, (cx, bx.y+6), (cx, bx.y+24), 1)

    def on_event(self, ev) -> Optional[str]:
        if not self.active: return None
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                v = self.text; self.close(); return v
            if ev.key == pygame.K_ESCAPE:
                self.close(); return None
            if ev.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                ch = ev.unicode
                if ch and ch.isprintable():
                    self.text += ch
        return None

# ─────────────────────────────────────────────
#  APPLY EDIT
# ─────────────────────────────────────────────
def apply_edit(nation: dict, meta: dict, raw: str) -> bool:
    path  = meta.get("path", [])
    dtype = meta.get("type", "float")
    try:
        if dtype == "float":
            val = float(raw.replace(",",""))
        elif dtype == "pct":
            val = float(raw.replace("%","").replace(",","")) / 100.0
        elif dtype == "int":
            val = int(raw.replace(",",""))
        else:
            val = raw
    except:
        return False

    # walk path
    obj = nation
    for key in path[:-1]:
        if isinstance(key, str):
            if isinstance(obj, dict): obj = obj.setdefault(key, {})
        elif isinstance(key, int):
            obj = obj[key]
    last = path[-1]
    if isinstance(obj, dict): obj[last] = val
    elif isinstance(obj, list): obj[last] = val
    return True

# ─────────────────────────────────────────────
#  RENDER ROWS — build display list from nation
# ─────────────────────────────────────────────
ROW_H  = 20
HDR1_H = 32
HDR2_H = 26
SEP_H  = 8

def _row(label, val, path=None, dtype="float", vcol=TEXT):
    meta = {"path": path, "type": dtype} if path else None
    return {"type": "row", "label": label, "val": str(val),
            "meta": meta, "vcol": vcol, "h": ROW_H}

def _hdr1(txt): return {"type": "hdr1", "txt": txt, "h": HDR1_H}
def _hdr2(txt): return {"type": "hdr2", "txt": txt, "h": HDR2_H}
def _sep():     return {"type": "sep",  "h": SEP_H}
def _bar(label, pct, txt, vcol=CYAN):
    return {"type": "bar", "label": label, "pct": pct, "txt": txt, "vcol": vcol, "h": ROW_H}

TABS = ["OVERVIEW", "ECONOMY", "MILITARY", "TERRITORY"]

def build_rows(nation: dict, state: dict, tab: str) -> List[dict]:
    ye   = years_elapsed(state)
    ipeu = nation.get("base_ipeu", 0.0)
    pop  = current_population(nation, ye)
    exp  = nation.get("expenditure", {}) if isinstance(nation.get("expenditure"), dict) else {}
    trade= compute_trade(nation, state.get("trade_routes", []))
    res  = compute_resources(nation, ipeu)
    debt = compute_debt(nation, ipeu)
    rb   = nation.get("research_budget", 0.0)
    sf   = nation.get("strategic_fund", 0.0)
    total_exp = sum(exp.values()) * ipeu + rb
    net_bal   = ipeu + trade["net"] - total_exp - debt["q_interest"]
    species   = nation.get("species_populations", []) or []
    star_sys  = nation.get("star_systems", []) or []
    afd       = nation.get("active_forces_detail", []) or []
    ugroups   = {ug["ugid"]: ug for ug in (nation.get("unit_groups") or [])}
    active_r  = nation.get("active_research_projects", []) or []
    done_r    = nation.get("completed_techs", []) or []
    projects  = nation.get("projects", []) or []

    R = []
    homeworld = "—"
    for sys in star_sys:
        for pl in sys.get("planets",[]):
            homeworld = pl["name"]; break
        break

    if tab == "OVERVIEW":
        sp_str = ", ".join(s["name"] for s in species) if species else "—"
        R.append(_hdr1(f"  {nation['name']}"))
        R.append(_row("Species",      sp_str))
        R.append(_row("Population",   fmt_pop(pop)))
        R.append(_row("Pop Growth",   fmt_pct(nation.get("pop_growth",0)), ["pop_growth"], "pct", CYAN))
        R.append(_row("Homeworld",    homeworld))
        R.append(_row("Civ Level",    nation.get("civ_level","—"), ["civ_level"], "str"))
        R.append(_row("Civ Tier",     nation.get("civ_tier","—"), ["civ_tier"], "int"))
        R.append(_row("Eco Model",    nation.get("economic_model","MIXED"), ["economic_model"], "str"))
        R.append(_row("Eco Status",   nation.get("eco_status","Stable"), ["eco_status"], "str"))
        R.append(_sep())

        R.append(_hdr2("DEMOGRAPHICS"))
        R.append(_row("Total Pop", fmt_pop(pop)))
        R.append(_row("Loyalty Mod", f"{nation.get('loyalty_modifier_cg',1.0):.2f}",
                       ["loyalty_modifier_cg"], "float", CYAN))
        for s in species:
            sp_p  = s.get("population", 0)
            shr   = sp_p / pop * 100 if pop else 0
            loy   = s.get("loyalty", 0)
            lc    = GREEN if loy >= 70 else (GOLD if loy >= 40 else RED_C)
            R.append(_sep())
            R.append({"type":"species_hdr","name":s["name"],"status":s.get("status",""),
                       "h":HDR2_H})
            R.append(_row("  Population", fmt_pop(sp_p)))
            R.append(_row("  Share",      f"{shr:.1f}% — {s.get('status','?').title()}"))
            R.append(_row("  Growth",     fmt_pct(s.get("growth_rate",0))))
            R.append(_row("  Culture",    s.get("culture","—")))
            R.append(_row("  Language",   s.get("language","—")))
            R.append(_row("  Religion",   s.get("religion","—")))
            R.append(_row("  Loyalty",    f"{loy}/100  {bar_str(loy/100,12)}", vcol=lc))
            R.append(_row("  Happiness",  str(s.get("happiness","—"))))
        R.append(_sep())

        R.append(_hdr2("RESEARCH"))
        R.append(_row("RP Budget/turn", fmt_cr(rb), ["research_budget"], "float", CYAN))
        if active_r:
            for p in active_r:
                prog = p.get("progress",0.0)
                R.append(_bar(f"  {p.get('name','?')}", prog/100, f"{prog:.1f}%", CYAN))
        else:
            R.append(_row("  Active", "None", vcol=DIM))
        if done_r:
            R.append(_row(f"  Completed", f"{len(done_r)} techs", vcol=GREEN))

    elif tab == "ECONOMY":
        nc = GREEN if net_bal >= 0 else RED_C
        R.append(_hdr1("ECONOMY"))
        R.append(_row("IPEU (base)",    fmt_cr(ipeu),  ["base_ipeu"],   "float", GOLD))
        R.append(_row("IPEU Growth",    fmt_pct(nation.get("ipeu_growth",0)), ["ipeu_growth"], "pct", CYAN))
        R.append(_row("IPEU/Capita",    f"{int(ipeu/pop):,} cr" if pop else "—"))
        R.append(_row("Trade Revenue",  fmt_cr(trade["net"])))
        R.append(_row("  Exports",      fmt_cr(trade["exports"]), vcol=GREEN))
        R.append(_row("  Imports",      fmt_cr(trade["imports"]), vcol=RED_C))
        R.append(_row("  Transit Inc.", fmt_cr(trade["transit_income"]), vcol=TEAL))
        R.append(_row("Research Bgt",   fmt_cr(rb), ["research_budget"], "float", CYAN))
        R.append(_row("Total Expend.",  fmt_cr(total_exp)))
        R.append(_row("Net Balance",    fmt_cr(net_bal), vcol=nc))
        R.append(_sep())

        R.append(_hdr2("EXPENDITURE"))
        max_pct = max(exp.values(), default=0.01)
        for cat, pct in exp.items():
            R.append(_bar(f"  {cat}", pct/max_pct, f"{pct*100:.1f}%  {fmt_cr(pct*ipeu)}"))
        R.append(_sep())

        R.append(_hdr2("ECONOMIC PROJECTS"))
        ap = [p for p in projects if p.get("status") in ("active","in_progress","complete")]
        if ap:
            for p in ap:
                tl = p.get("duration_turns",0) - p.get("turns_elapsed",0)
                st = "DONE" if p.get("status")=="complete" else f"{tl}t"
                R.append(_row(f"  {p['name']}", f"[{st}]  {p.get('category','?')}", vcol=GOLD))
        else:
            R.append(_row("  None", "—", vcol=DIM))
        R.append(_sep())

        R.append(_hdr2("FISCAL REPORT"))
        dc = RED_C if debt["is_debtor"] else GREEN
        R.append(_row("Status",         "Debtor" if debt["is_debtor"] else "Creditor", vcol=dc))
        R.append(_row("Debt Balance",   fmt_cr(debt["balance"]), ["debt_balance"], "float"))
        R.append(_row("Debt Load",      f"{debt['load_pct']:.1f}%"))
        R.append(_row("Interest Rate",  f"{debt['rate']*100:.2f}%", ["interest_rate"], "pct", CYAN))
        R.append(_row("Quarterly Int.", fmt_cr(debt["q_interest"])))
        R.append(_row("Debt Repayment", fmt_cr(debt["repayment"]), ["debt_repayment"], "float"))
        sf_c = GREEN if sf >= 0 else RED_C
        R.append(_row("Strategic Fund", fmt_cr(sf), ["strategic_fund"], "float", sf_c))
        fd   = -debt["q_interest"]
        R.append(_row("Fund Δ/turn",   (f"+{fmt_cr(fd)}" if fd>=0 else fmt_cr(fd)), vcol=sf_c))
        R.append(_sep())

        R.append(_hdr2("RESOURCES & STOCKPILES"))
        for rname in ["Food","Minerals","Energy","Alloys","Consumer Goods"]:
            rd = res[rname]
            tc = GREEN if rd["net"]>0 else (RED_C if rd["net"]<0 else DIM)
            R.append(_row(f"  {rname}", ""))
            R.append(_row("    Stockpile",   fmt_res(rd["stockpile"])))
            R.append(_row("    Production",  fmt_res(rd["production"])))
            R.append(_row("    Consumption", fmt_res(rd["consumption"])))
            R.append(_row("    Net/turn",    fmt_res(rd["net"]), vcol=tc))
            R.append(_row("    Trend",       rd["trend"], vcol=tc))
            R.append(_sep())

    elif tab == "MILITARY":
        R.append(_hdr1("MILITARY"))
        CAT_MAP = [
            ("SPACEFLEET",       ["Spacefleet","Navy"]),
            ("AEROSPACE FORCES", ["Air Force","Aerospace"]),
            ("GROUND FORCES",    ["Ground Forces","Ground","Army"]),
        ]
        for hdr, cats in CAT_MAP:
            units = [u for u in afd if u.get("category") in cats]
            R.append(_hdr2(hdr))
            if units:
                grouped: Dict[str,list] = {}
                for u in units:
                    ugid = u.get("ugid")
                    grp  = ugroups[ugid]["name"] if ugid and ugid in ugroups else "Unassigned"
                    grouped.setdefault(grp, []).append(u)
                for grp, us in grouped.items():
                    R.append(_row(f"  [{grp}]", "", vcol=GOLD))
                    for u in us:
                        nm  = u.get("custom_name") or u.get("unit","?")
                        vet = u.get("veterancy","?")
                        cnt = u.get("count",1)
                        mnt = u.get("maintenance",0)
                        R.append(_row(f"    {nm}", f"×{cnt} | {vet} | {fmt_cr(mnt) if isinstance(mnt,(int,float)) else mnt}", vcol=TEXT))
            else:
                R.append(_row("  None on record", "", vcol=DIM))
            R.append(_sep())

        R.append(_hdr2("ARSENAL"))
        arsenal = nation.get("arsenal", []) or []
        if arsenal:
            for a in arsenal:
                R.append(_row(f"  {a.get('name','?')}", f"{a.get('type','?')} | {a.get('size','?')} | Crew {a.get('crew','?')}"))
        else:
            R.append(_row("  None", "", vcol=DIM))

    elif tab == "TERRITORY":
        R.append(_hdr1("TERRITORIES"))
        if not star_sys:
            R.append(_row("No territorial data","",vcol=DIM))
        else:
            for si, sys in enumerate(star_sys):
                R.append(_hdr2(f"System: {sys['name']}"))
                R.append(_row("  Notes", sys.get("notes","—"), ["star_systems",si,"notes"],"str"))
                R.append(_row("  Coordinates", sys.get("coordinates","—"), ["star_systems",si,"coordinates"],"str"))
                for pi, planet in enumerate(sys.get("planets",[])):
                    R.append(_sep())
                    R.append({"type":"territory_planet","name":planet["name"],
                               "si":si,"pi":pi,"h":HDR2_H})
                    R.append(_row("    Type",        planet.get("type","—"),     ["star_systems",si,"planets",pi,"type"],"str"))
                    R.append(_row("    Size",         planet.get("size","—"),     ["star_systems",si,"planets",pi,"size"],"str"))
                    R.append(_row("    Habitability", planet.get("habitability","—"), ["star_systems",si,"planets",pi,"habitability"],"str"))
                    R.append(_row("    Devastation",  planet.get("devastation",0),    ["star_systems",si,"planets",pi,"devastation"],"float", RED_C))
                    R.append(_row("    Crime Rate",   planet.get("crime_rate",0),     ["star_systems",si,"planets",pi,"crime_rate"],"float"))
                    R.append(_row("    Unrest",       planet.get("unrest",0),         ["star_systems",si,"planets",pi,"unrest"],"float"))
                    pop_a = planet.get("pop_assigned", 0)
                    R.append(_row("    Population",   fmt_pop(pop_a)))
                    setts = planet.get("settlements", []) or []
                    R.append(_row("    Settlements",  f"{len(setts)}", vcol=CYAN))
                    for sti, s in enumerate(setts):
                        R.append(_row(f"      ◉ {s['name']}", f"Pop {fmt_pop(s.get('population',0))}  Loy {s.get('loyalty',0):.0f}%"))
                        dc: Dict[str,int] = {}
                        for d in s.get("districts",[]):
                            dt = d.get("type","?"); dc[dt] = dc.get(dt,0)+1
                        if dc:
                            dstr = "  ".join(f"{t}×{c}" for t,c in dc.items())
                            R.append(_row("        Districts", dstr, vcol=DIM))
                R.append(_sep())
    return R

# ─────────────────────────────────────────────
#  LEFT PANEL
# ─────────────────────────────────────────────
class LeftPanel:
    PAD = 8
    def __init__(self):
        bw = LWIDTH - self.PAD*2
        self.nations: List[str] = []
        self.selected = 0
        self._hover   = -1
        self.scroll   = Scrollbar(LWIDTH - Scrollbar.W - 2, TBAR_H + 4, SH - TBAR_H - SBAR_H - 80)
        self.btn_save = Button((self.PAD, SH-SBAR_H-62, bw, 26), "[ SAVE  S ]", accent=True)
        self.btn_disc = Button((self.PAD, SH-SBAR_H-32, bw, 26), "[ DISCORD  D ]")

    def set_nations(self, names, sel=0):
        self.nations  = names
        self.selected = sel
        self.scroll.set_content(len(names)*22, SH - TBAR_H - SBAR_H - 80)

    def draw(self, surf, turn, year, quarter):
        draw_rect(surf, pygame.Rect(0,0,LWIDTH,SH), PANEL)
        draw_rect(surf, pygame.Rect(LWIDTH-1,0,1,SH), BORDER)

        f11 = gf(11); f12 = gf(12); f10 = gf(10)
        # turn info
        draw_text(surf, f"T{turn} · {year} Q{quarter}", self.PAD, TBAR_H+8, f12, CYAN)
        draw_text(surf, f"{len(self.nations)} nations", self.PAD, TBAR_H+24, f10, DIM)

        # nation list
        clip  = pygame.Rect(0, TBAR_H+40, LWIDTH-Scrollbar.W-2, SH - TBAR_H - SBAR_H - 84)
        surf.set_clip(clip)
        y0    = TBAR_H + 40 - int(self.scroll.scroll)
        mx,my = pygame.mouse.get_pos()
        self._hover = -1
        for i, name in enumerate(self.nations):
            yr = pygame.Rect(self.PAD, y0 + i*22, LWIDTH - Scrollbar.W - self.PAD*2, 20)
            if yr.collidepoint(mx,my): self._hover = i
            if i == self.selected:
                draw_rect(surf, yr, SEL, radius=2)
                draw_rect(surf, yr, BORDER2, border=1, radius=2)
            elif self._hover == i:
                draw_rect(surf, yr, HOVER, radius=2)
            tag = nation_tag(name)
            draw_text(surf, f"[{tag}]", yr.x+2,     yr.y+3, f10, ACCENT)
            draw_text(surf,  name[:22], yr.x+36,    yr.y+3, f10, BRIGHT if i==self.selected else TEXT)
        surf.set_clip(None)

        self.scroll.draw(surf)
        self.btn_save.draw(surf)
        self.btn_disc.draw(surf)

    def on_event(self, ev) -> Optional[int]:
        # hover check for scrollbar
        mx,my = pygame.mouse.get_pos()
        in_list = mx < LWIDTH and my > TBAR_H+40 and my < SH-SBAR_H-84
        self.scroll.on_event(ev, in_list)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, name in enumerate(self.nations):
                yr = pygame.Rect(self.PAD, TBAR_H + 40 - int(self.scroll.scroll) + i*22,
                                 LWIDTH - Scrollbar.W - self.PAD*2, 20)
                if yr.collidepoint(ev.pos) and 0 < ev.pos[0] < LWIDTH:
                    return i
        return None

# ─────────────────────────────────────────────
#  MAIN PANEL
# ─────────────────────────────────────────────
class MainPanel:
    def __init__(self):
        self.rows: List[dict] = []
        self.scroll = Scrollbar(SW - Scrollbar.W - 2, MAIN_Y, MAIN_H)
        self._hover_row = -1
        self.edit = EditOverlay()
        self._tab = 0  # current tab index

    def set_rows(self, rows):
        self.rows = rows
        total = sum(r["h"] for r in rows)
        self.scroll.set_content(total, MAIN_H - (self.edit.H if self.edit.active else 0))
        self.scroll.scroll = 0

    def _row_rects(self):
        rects = []; y = MAIN_Y - int(self.scroll.scroll)
        for r in self.rows:
            rects.append(pygame.Rect(MAIN_X, y, MAIN_W - Scrollbar.W, r["h"]))
            y += r["h"]
        return rects

    def draw(self, surf):
        clip = pygame.Rect(MAIN_X, MAIN_Y, MAIN_W - Scrollbar.W,
                           MAIN_H - (self.edit.H if self.edit.active else 0))
        surf.set_clip(clip)
        f12 = gf(12); f11 = gf(11); f10 = gf(10); f13 = gf(13)
        mx,my = pygame.mouse.get_pos()
        rects  = self._row_rects()

        for i, (row, rect) in enumerate(zip(self.rows, rects)):
            if rect.bottom < MAIN_Y or rect.top > MAIN_Y + MAIN_H: continue
            rt = row["type"]

            if rt == "hdr1":
                draw_rect(surf, rect, (16,28,44))
                draw_rect(surf, pygame.Rect(MAIN_X, rect.y, 3, rect.h), ACCENT)
                draw_text(surf, row["txt"], rect.x+10, rect.y+8, f13, BRIGHT, clip)

            elif rt == "hdr2":
                draw_rect(surf, rect, (13,22,36))
                draw_rect(surf, pygame.Rect(rect.x, rect.bottom-1, rect.w, 1), BORDER)
                draw_text(surf, row["txt"], rect.x+10, rect.y+6, f12, CYAN, clip)

            elif rt == "species_hdr":
                draw_rect(surf, rect, (14,24,38))
                crown = "👑" if row["status"] in ("dominant","majority") else "👥"
                draw_text(surf, f"{crown}  {row['name']}  ({row['status'].title()})",
                          rect.x+10, rect.y+6, f12, GOLD, clip)

            elif rt == "territory_planet":
                draw_rect(surf, rect, (13,22,36))
                draw_rect(surf, pygame.Rect(rect.x, rect.bottom-1, rect.w, 1), BORDER2)
                draw_text(surf, f"◦ {row['name']}", rect.x+10, rect.y+6, f12, TEAL, clip)

            elif rt == "row":
                bg = HOVER if (rect.collidepoint(mx,my) and row.get("meta")) else (
                     (10,18,28) if i%2==0 else BG)
                draw_rect(surf, rect, bg)
                lw = 180
                draw_text(surf, row["label"], rect.x+8, rect.y+3, f11, DIM, clip)
                vcol = row.get("vcol", TEXT)
                if row.get("meta"):
                    vcol = EDITBDR if rect.collidepoint(mx,my) else vcol
                draw_text(surf, row["val"],   rect.x+8+lw, rect.y+3, f11, vcol, clip)

            elif rt == "bar":
                bg = (10,18,28) if i%2==0 else BG
                draw_rect(surf, rect, bg)
                lw = 160
                draw_text(surf, row["label"], rect.x+8, rect.y+3, f11, DIM, clip)
                bw = 100; bh = 10
                bx = rect.x+8+lw; by = rect.y+5
                draw_rect(surf, pygame.Rect(bx, by, bw, bh), (18,32,50), radius=2)
                fw = int(row["pct"] * bw)
                if fw > 0:
                    draw_rect(surf, pygame.Rect(bx, by, fw, bh), row.get("vcol",CYAN), radius=2)
                draw_text(surf, row["txt"], bx+bw+6, rect.y+3, f11, TEXT, clip)

            elif rt == "sep":
                pass  # just vertical space

        surf.set_clip(None)
        self.scroll.draw(surf)

    def on_click(self, ev) -> Optional[dict]:
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1: return None
        if not (MAIN_X <= ev.pos[0] < SW - Scrollbar.W and MAIN_Y <= ev.pos[1] < MAIN_Y+MAIN_H):
            return None
        for row, rect in zip(self.rows, self._row_rects()):
            if rect.collidepoint(ev.pos) and row.get("meta"):
                return row
        return None

    def on_event(self, ev):
        mx,my = pygame.mouse.get_pos()
        in_main = MAIN_X <= mx < SW and MAIN_Y <= my < MAIN_Y+MAIN_H
        self.scroll.on_event(ev, in_main)

# ─────────────────────────────────────────────
#  TOP BAR & STATUS BAR
# ─────────────────────────────────────────────
_status_msg  = ""
_status_col  = DIM
_status_time = 0.0

def set_status(msg, col=DIM):
    global _status_msg, _status_col, _status_time
    _status_msg  = msg; _status_col = col; _status_time = time.time()

def draw_top_bar(surf, name, turn, year, quarter, tab_idx, dirty):
    r = pygame.Rect(LWIDTH, 0, SW-LWIDTH, TBAR_H)
    draw_rect(surf, r, (10,16,26))
    draw_rect(surf, pygame.Rect(LWIDTH,TBAR_H-1,SW-LWIDTH,1), BORDER)
    f13 = gf(13, False); f11 = gf(11)
    draw_text(surf, name, LWIDTH+12, 10, f13, BRIGHT)
    if dirty:
        draw_text(surf, "● UNSAVED", SW-100, 12, f11, GOLD)

def draw_tab_bar(surf, tab_idx):
    r = pygame.Rect(LWIDTH, TBAR_H, SW-LWIDTH, TABBAR_H)
    draw_rect(surf, r, (10,16,26))
    draw_rect(surf, pygame.Rect(LWIDTH,TBAR_H+TABBAR_H-1,SW-LWIDTH,1), BORDER)
    f11 = gf(11)
    tw_tab = (SW-LWIDTH) // len(TABS)
    for i, tab in enumerate(TABS):
        tx = LWIDTH + i * tw_tab
        tr = pygame.Rect(tx, TBAR_H, tw_tab, TABBAR_H)
        if i == tab_idx:
            draw_rect(surf, tr, (18,36,58))
            draw_rect(surf, pygame.Rect(tx, TBAR_H+TABBAR_H-2, tw_tab, 2), CYAN)
            draw_text(surf, tab, 0, 0, f11, BRIGHT,
                      clip=None)
            s = f11.render(tab, True, BRIGHT)
            surf.blit(s, s.get_rect(center=tr.center))
        else:
            mx,my = pygame.mouse.get_pos()
            if tr.collidepoint(mx,my):
                draw_rect(surf, tr, HOVER)
            s = f11.render(tab, True, DIM)
            surf.blit(s, s.get_rect(center=tr.center))

def draw_status_bar(surf):
    r = pygame.Rect(0, SH-SBAR_H, SW, SBAR_H)
    draw_rect(surf, r, (8,14,22))
    draw_rect(surf, pygame.Rect(0,SH-SBAR_H,SW,1), BORDER)
    age = time.time() - _status_time
    col = _status_col if age < 3.0 else DIM
    draw_text(surf, _status_msg if age < 5.0 else "Ready", 10, SH-SBAR_H+4, gf(10), col)
    draw_text(surf, "S=save  D=discord  ↑↓=nation  Tab=tab",
              SW-320, SH-SBAR_H+4, gf(10), DIM2)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STATE
    sm = StateManager(filepath)
    if not sm.load():
        sys.exit(f"[FATAL] Cannot load: {filepath}")

    pygame.init()
    pygame.display.set_caption("Carmine NRP Engine — vAlpha0.3.0")
    surf = pygame.display.set_mode((SW, SH))
    clock = pygame.time.Clock()

    left  = LeftPanel()
    main_ = MainPanel()

    names   = sm.nation_names()
    sel_idx = 0
    tab_idx = 0

    left.set_nations(names, sel_idx)

    def load_nation(idx):
        nonlocal sel_idx
        sel_idx = max(0, min(idx, len(names)-1))
        left.selected = sel_idx
        n = sm.get_nation(names[sel_idx])
        if n:
            rows = build_rows(n, sm.state, TABS[tab_idx])
            main_.set_rows(rows)

    load_nation(0)
    set_status(f"Loaded: {filepath}", CYAN)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            # edit overlay gets first dibs
            if main_.edit.active:
                result = main_.edit.on_event(ev)
                if result is not None:
                    n = sm.get_nation(names[sel_idx])
                    if n and apply_edit(n, main_.edit.meta, result):
                        sm.mark_dirty()
                        sm.autosave()
                        load_nation(sel_idx)
                        set_status("Saved.", GREEN)
                elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    main_.edit.close()
                continue

            # keyboard
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_s:
                    sm.save()
                    set_status("Saved with backup rotation.", GREEN)
                elif ev.key == pygame.K_d:
                    n = sm.get_nation(names[sel_idx])
                    if n:
                        txt   = format_discord(n, sm.state)
                        fname = f"discord_{names[sel_idx].replace(' ','_')}_T{sm.state.get('turn',0)}.txt"
                        with open(fname,"w",encoding="utf-8") as f: f.write(txt)
                        set_status(f"Discord export → {fname}", CYAN)
                elif ev.key in (pygame.K_UP, pygame.K_LEFT):
                    load_nation(sel_idx - 1)
                elif ev.key in (pygame.K_DOWN, pygame.K_RIGHT):
                    load_nation(sel_idx + 1)
                elif ev.key == pygame.K_TAB:
                    tab_idx = (tab_idx + 1) % len(TABS)
                    load_nation(sel_idx)
                elif ev.key in (pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_4):
                    tab_idx = ev.key - pygame.K_1
                    load_nation(sel_idx)

            # tab bar click
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if LWIDTH <= ev.pos[0] < SW and TBAR_H <= ev.pos[1] < TBAR_H+TABBAR_H:
                    tw_tab = (SW-LWIDTH) // len(TABS)
                    ti = (ev.pos[0]-LWIDTH) // tw_tab
                    if 0 <= ti < len(TABS):
                        tab_idx = ti
                        load_nation(sel_idx)

            # left panel
            clicked = left.on_event(ev)
            if clicked is not None:
                load_nation(clicked)
            left.btn_save.on_event(ev) and (sm.save(), set_status("Saved.", GREEN))
            if left.btn_disc.on_event(ev):
                n = sm.get_nation(names[sel_idx])
                if n:
                    txt   = format_discord(n, sm.state)
                    fname = f"discord_{names[sel_idx].replace(' ','_')}_T{sm.state.get('turn',0)}.txt"
                    with open(fname,"w",encoding="utf-8") as f: f.write(txt)
                    set_status(f"Discord → {fname}", CYAN)

            # main panel scroll
            main_.on_event(ev)

            # row click → edit
            row = main_.on_click(ev)
            if row:
                raw = row.get("val","")
                main_.edit.open(row["label"], raw, row["meta"])

        # ─── DRAW ───────────────────────────────
        surf.fill(BG)
        n = sm.get_nation(names[sel_idx]) if names else None
        turn    = sm.state.get("turn",    1)
        year    = sm.state.get("year",    2200)
        quarter = sm.state.get("quarter", 1)

        draw_top_bar(surf, names[sel_idx] if names else "—", turn, year, quarter, tab_idx, sm.dirty)
        draw_tab_bar(surf, tab_idx)
        left.draw(surf, turn, year, quarter)
        main_.draw(surf)
        main_.edit.draw(surf, dt)
        draw_status_bar(surf)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()