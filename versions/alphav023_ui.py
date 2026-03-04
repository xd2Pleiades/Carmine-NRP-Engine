"""
carmine_alpha023_ui.py — Carmine NRP GM Tool v0.2.3
=====================================================
Pygame-based GM interface.  Requires carmine_alpha023.py in same directory.

Run
---
  python3 carmine_alpha023_ui.py [state_file.json]

Features
--------
  • Resizable window (proportional layout recalculated on every resize)
  • Tab navigation: PROFILE | SYSTEM MAP | EVENT LOG | GALACTIC MARKET
  • [ADVANCE TURN] — full tick + d20 event modal showing all rolls
  • Trade Route Builder modal — live calculation preview, pirate risk,
    transit taxes, quantity auto-calc per economic model
  • Event Log panel — filter, approve, edit, export Galactic News
  • Galactic Market panel — editable prices/modifiers, [FLUCTUATE]
  • System Map panel — 2D orbital diagram, clickable planets,
    planet detail drawer, [EXPORT SYSTEM] Discord output
  • All sections export to Discord format via [D] key or buttons
  • Autosave + 5-slot backup rotation on every mutation
"""

from __future__ import annotations
import pygame, sys, os, json, math, random, time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

try:
    from carmine_alpha023 import (
        StateManager, advance_turn, TradeRouteEngine, MarketEngine, EventLog,
        discord_profile, discord_trade_route, discord_galactic_news, discord_market_report,
        compute_trade, compute_resource_flows, compute_debt, current_population,
        recalc_loyalty_happiness, fmt_cr, fmt_pop, fmt_int, fmt_pct, fmt_res,
        nation_tag, loyalty_bar, debt_bar,
        RESOURCE_NAMES, EXPENDITURE_ORDER, ECONOMIC_MODELS,
        PLANET_TYPES, PLANET_SIZES, ORBITAL_BLDG_TYPES,
        PIRATE_BASE_RISK, SEVERITY_EMOJI, D20_EVENT_POOL,
        VERSION,
    )
except ImportError as e:
    sys.exit(f"[FATAL] carmine_alpha023.py not found or has errors.\n{e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLOUR PALETTE — Carmine Sci-Fi Dark
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BG       = (  8, 12, 20); PANEL  = ( 11, 17, 27); PANEL2 = ( 15, 23, 35)
PANEL3   = ( 18, 28, 42); BLOCK  = (  7, 13, 21); BLOCK2 = (  9, 16, 25)
BORDER   = ( 26, 50, 76); BORDER2= ( 42, 82,122)
ACCENT   = (190, 38, 25); ACCENT2= (130, 22, 16)
CYAN     = (  0,190,214); TEAL   = (  0,138,158); TEAL2  = (  0,100,118)
TEXT     = (198,226,246); DIM    = ( 84,114,136); DIM2   = ( 55, 80,100)
BRIGHT   = (238,248,255); GREEN  = ( 22,184, 82); GREEN2 = ( 14,120, 54)
RED_C    = (216, 54, 40); RED2   = (140, 28, 20)
GOLD     = (198,150, 22); GOLD2  = (140,100, 12)
SEL      = ( 18, 40, 65); HOV    = ( 14, 30, 50)
EDITBG   = (  5, 14, 28); EDITBDR= (  0,172,194)
SCRLBG   = (  9, 17, 27); SCRLTMB= ( 38, 76,116)
BTNBG    = ( 18, 36, 56); BTNHOV = ( 28, 54, 82)
BTNACC   = (130, 24, 16); BTNACC2= (190, 38, 25)
MODALBG  = (  4,  8, 16); MODALBDR=(  0,150,180)
TABACT   = ( 18, 40, 68); TABHOV = ( 12, 28, 48)
TABINACT = (  9, 17, 27)

TAB_NAMES  = ["PROFILE", "SYSTEM MAP", "EVENT LOG", "MARKET"]
FPS        = 60

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROPORTIONAL LAYOUT (recalculates on resize)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Layout:
    """
    All geometry derived from window size (sw, sh).
    Call update(sw, sh) after every VIDEORESIZE event.
    """
    MIN_W = 900; MIN_H = 600

    def __init__(self, sw: int = 1280, sh: int = 720):
        self.update(sw, sh)

    def update(self, sw: int, sh: int):
        """Recalculate all geometry from new window dimensions."""
        self.sw = max(sw, self.MIN_W)
        self.sh = max(sh, self.MIN_H)
        self.lw     = max(210, int(self.sw * 0.205))   # left sidebar width
        self.tbar_h = 46                                 # top bar height
        self.sbar_h = 26                                 # status bar height
        self.scrl_w = 10                                 # scrollbar width
        self.tab_h  = 34                                 # tab bar height
        # Main panel
        self.mx  = self.lw
        self.my  = self.tbar_h + self.tab_h
        self.mw  = self.sw - self.lw - self.scrl_w
        self.mh  = self.sh - self.tbar_h - self.tab_h - self.sbar_h

    @property
    def main_rect(self):
        return pygame.Rect(self.mx, self.my, self.mw, self.mh)

    @property
    def tab_rect(self):
        return pygame.Rect(self.lw, self.tbar_h, self.sw - self.lw, self.tab_h)

    @property
    def scrl_rect(self):
        return pygame.Rect(self.sw - self.scrl_w, self.my, self.scrl_w, self.mh)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FONT CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_FONTS: Dict[str, pygame.font.Font] = {}

def gf(size: int, mono: bool = True) -> pygame.font.Font:
    """Return a cached font.  mono=True → monospace, False → sans-serif."""
    key = f"{'m' if mono else 's'}{size}"
    if key not in _FONTS:
        if mono:
            for name in ("Courier New","Consolas","DejaVu Sans Mono","monospace"):
                try: _FONTS[key] = pygame.font.SysFont(name, size); break
                except: pass
        else:
            for name in ("Segoe UI","Calibri","Arial","Helvetica","sans"):
                try: _FONTS[key] = pygame.font.SysFont(name, size); break
                except: pass
        if key not in _FONTS:
            _FONTS[key] = pygame.font.Font(None, size + 4)
    return _FONTS[key]

def tw(text: str, font: pygame.font.Font) -> int:
    return font.size(text)[0]

def blit_text(surf, text: str, x: int, y: int,
              font: pygame.font.Font, col=TEXT) -> int:
    """Blit text and return rendered width."""
    s = font.render(text, True, col)
    surf.blit(s, (x, y))
    return s.get_width()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DRAWING UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_bar(surf, x, y, w, h, pct,
             fg=CYAN, bg=BLOCK, bdr=BORDER):
    """Draw a filled progress bar with border."""
    pygame.draw.rect(surf, bg, (x, y, w, h))
    fill = max(0, int(w * max(0.0, min(1.0, pct))))
    if fill: pygame.draw.rect(surf, fg, (x, y, fill, h))
    pygame.draw.rect(surf, bdr, (x, y, w, h), 1)

def corner_deco(surf, x, y, w, h, col, s=10):
    """Draw corner bracket decorations."""
    for pts in [[(x,y+s),(x,y),(x+s,y)], [(x+w-s,y),(x+w,y),(x+w,y+s)],
                [(x,y+h-s),(x,y+h),(x+s,y+h)], [(x+w-s,y+h),(x+w,y+h),(x+w,y+h-s)]]:
        pygame.draw.lines(surf, col, False, pts, 2)

def panel_bg(surf, rect, bg=PANEL, bdr=BORDER, accent_col=None, corners=False):
    """Draw a panel with optional corner brackets."""
    pygame.draw.rect(surf, bg, rect)
    pygame.draw.rect(surf, bdr, rect, 1)
    if corners and accent_col:
        corner_deco(surf, rect[0], rect[1], rect[2], rect[3], accent_col)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCROLLBAR WIDGET
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Scrollbar:
    """Vertical scrollbar with drag and mousewheel support."""

    def __init__(self, x, y, w, h):
        self.rect   = pygame.Rect(x, y, w, h)
        self._drag  = False; self._doff = 0
        self.scroll = 0; self.content_h = 1; self.view_h = h

    def set_content(self, ch: int, vh: int):
        self.content_h = max(1, ch); self.view_h = vh

    def clamp(self):
        self.scroll = max(0, min(self.scroll, max(0, self.content_h - self.view_h)))

    def update_rect(self, x, y, w, h):
        """Update geometry on window resize."""
        self.rect = pygame.Rect(x, y, w, h); self.view_h = h

    def _thumb(self):
        ms = max(1, self.content_h - self.view_h)
        th = max(20, int(self.rect.h * self.view_h / self.content_h))
        ty = self.rect.y + int((self.scroll / ms) * (self.rect.h - th))
        return pygame.Rect(self.rect.x, ty, self.rect.w, th)

    def draw(self, surf):
        pygame.draw.rect(surf, SCRLBG, self.rect)
        pygame.draw.rect(surf, SCRLTMB, self._thumb(), border_radius=3)
        pygame.draw.rect(surf, BORDER,  self.rect, 1)

    def on_event(self, event, over: bool):
        t = self._thumb()
        if event.type == pygame.MOUSEWHEEL and over:
            self.scroll -= event.y * 36; self.clamp()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if t.collidepoint(event.pos):
                self._drag = True; self._doff = event.pos[1] - t.y
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False
        elif event.type == pygame.MOUSEMOTION and self._drag:
            rel    = event.pos[1] - self.rect.y - self._doff
            travel = max(1, self.rect.h - t.h)
            self.scroll = int((rel / travel) * max(0, self.content_h - self.view_h))
            self.clamp()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUTTON WIDGET
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Button:
    """Simple clickable button with hover state."""

    def __init__(self, rect, label: str, accent: bool = False, small: bool = False):
        self.rect   = pygame.Rect(rect)
        self.label  = label
        self.accent = accent
        self.small  = small
        self._hov   = False

    def draw(self, surf):
        bg  = (BTNACC2 if self._hov else BTNACC) if self.accent else (BTNHOV if self._hov else BTNBG)
        bdr = ACCENT if self.accent else BORDER2
        pygame.draw.rect(surf, bg, self.rect, border_radius=3)
        pygame.draw.rect(surf, bdr, self.rect, 1, border_radius=3)
        f   = gf(11 if self.small else 13)
        lbl = self.label
        tx  = self.rect.x + (self.rect.w - tw(lbl, f)) // 2
        ty  = self.rect.y + (self.rect.h - f.get_height()) // 2
        blit_text(surf, lbl, tx, ty, f, BRIGHT)

    def on_event(self, event) -> bool:
        """Returns True on click."""
        if event.type == pygame.MOUSEMOTION:
            self._hov = self.rect.collidepoint(event.pos)
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INLINE EDIT OVERLAY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EditOverlay:
    """
    Single-line text editor shown at the bottom of the window.
    Returns 'confirm' or 'cancel' from on_event().
    """
    H = 50

    def __init__(self):
        self.active = False; self.label = ""; self.text = ""
        self.cursor = 0; self.meta = None; self._blink = 0.0; self._cv = True

    def open(self, label: str, raw, meta: dict):
        self.active = True; self.label = label; self.text = str(raw)
        self.cursor = len(self.text); self.meta = meta
        self._blink = 0.0; self._cv = True

    def close(self): self.active = False; self.text = ""; self.meta = None

    def draw(self, surf, lay: Layout, dt: float):
        if not self.active: return
        self._blink += dt
        if self._blink > 0.45: self._cv = not self._cv; self._blink = 0.0
        y = lay.sh - lay.sbar_h - self.H
        r = pygame.Rect(lay.lw, y, lay.sw - lay.lw, self.H)
        pygame.draw.rect(surf, EDITBG, r)
        pygame.draw.rect(surf, EDITBDR, r, 2)
        corner_deco(surf, r.x, r.y, r.w, r.h, EDITBDR, 7)
        f   = gf(13)
        lbl = f"EDIT  {self.label}  ▸ "
        lw_ = tw(lbl, f)
        blit_text(surf, lbl, r.x + 14, r.y + 16, f, DIM)
        tx = r.x + 14 + lw_; ty = r.y + 16
        blit_text(surf, self.text, tx, ty, f, BRIGHT)
        if self._cv:
            cx = tx + tw(self.text[:self.cursor], f)
            pygame.draw.line(surf, EDITBDR, (cx, ty), (cx, ty + f.get_height()), 2)
        hint = "[ENTER] Confirm   [ESC] Cancel"
        blit_text(surf, hint, r.right - tw(hint, f) - 14, r.y + 16, f, DIM)

    def on_event(self, event) -> Optional[str]:
        if not self.active or event.type != pygame.KEYDOWN: return None
        k = event.key
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER): return "confirm"
        if k == pygame.K_ESCAPE: return "cancel"
        if k == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.text = self.text[:self.cursor-1] + self.text[self.cursor:]
                self.cursor -= 1
        elif k == pygame.K_DELETE:
            self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
        elif k == pygame.K_LEFT:  self.cursor = max(0, self.cursor-1)
        elif k == pygame.K_RIGHT: self.cursor = min(len(self.text), self.cursor+1)
        elif k == pygame.K_HOME:  self.cursor = 0
        elif k == pygame.K_END:   self.cursor = len(self.text)
        elif event.unicode and event.unicode.isprintable():
            self.text = self.text[:self.cursor] + event.unicode + self.text[self.cursor:]
            self.cursor += 1
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# APPLY EDIT HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_edit(nation: dict, meta: dict, raw: str) -> bool:
    """
    Write an edited value back into the nation dict.
    meta.path determines nesting; meta.type determines parsing.
    Returns True on success.
    """
    path = meta["path"]; etype = meta["type"]
    try:
        clean = raw.strip().replace(",","").replace("_","")
        if etype == "float": value = float(clean)
        elif etype == "pct":
            v = float(clean.replace("%",""))
            value = v/100.0 if v > 1.5 else v
        elif etype == "int":   value = int(float(clean))
        elif etype == "pop":
            v = float(clean.rstrip("BbMmKk"))
            if clean[-1] in "Bb": v *= 1e9
            elif clean[-1] in "Mm": v *= 1e6
            elif clean[-1] in "Kk": v *= 1e3
            value = v
        else: value = raw.strip()
    except (ValueError, IndexError): return False
    if path[0] == "_species" and len(path) == 3:
        for sp in nation.get("species_populations",[]):
            if sp["name"] == path[1]: sp[path[2]] = value; return True
        return False
    if path[0] == "resource_stockpiles" and len(path) == 3:
        nation.setdefault("resource_stockpiles",{}).setdefault(path[1],{})[path[2]] = value
        return True
    if path[0] == "expenditure" and len(path) == 2:
        nation.setdefault("expenditure",{})[path[1]] = value; return True
    if len(path) == 1: nation[path[0]] = value; return True
    return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS BAR STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_status = "Ready."; _status_c = DIM

def set_status(msg: str, col = DIM):
    global _status, _status_c
    _status = msg; _status_c = col

def draw_status_bar(surf, lay: Layout):
    y = lay.sh - lay.sbar_h
    pygame.draw.rect(surf, PANEL, (0, y, lay.sw, lay.sbar_h))
    pygame.draw.line(surf, BORDER, (0, y), (lay.sw, y), 1)
    f = gf(11)
    blit_text(surf, _status, 12, y + 7, f, _status_c)
    keys = "S=Save  D=Export  T=Advance Turn  ↑↓=Nation  ESC=Close/Quit"
    blit_text(surf, keys, lay.sw - tw(keys, f) - 12, y + 7, f, DIM2)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOP BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_top_bar(surf, lay: Layout, nation_name: str, turn, year, quarter, dirty: bool):
    pygame.draw.rect(surf, PANEL, (0, 0, lay.sw, lay.tbar_h))
    pygame.draw.rect(surf, ACCENT, (0, lay.tbar_h - 2, lay.sw, 2))
    f_s = gf(11); f_m = gf(14, mono=False)
    blit_text(surf, f"CARMINE NRP ENGINE  ·  {VERSION}", lay.lw + 14, 6, f_s, DIM)
    if nation_name:
        blit_text(surf, nation_name, lay.lw + 14, 22, f_m, BRIGHT)
    tag = f"T{turn}  |  Y{year} Q{quarter}" + ("  ●" if dirty else "")
    blit_text(surf, tag, lay.sw - tw(tag, f_s) - 14, 17, f_s, TEAL)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TabBar:
    """Horizontal tab bar with active-tab highlighting."""

    def __init__(self, lay: Layout, tabs: List[str]):
        self.lay  = lay
        self.tabs = tabs
        self.active = 0
        self._hov   = -1
        self._rects: List[pygame.Rect] = []

    def update_layout(self, lay: Layout):
        self.lay = lay

    def _build_rects(self) -> List[pygame.Rect]:
        tab_w   = max(80, self.lay.mw // len(self.tabs))
        x0      = self.lay.lw
        y0      = self.lay.tbar_h
        return [pygame.Rect(x0 + i * tab_w, y0, tab_w, self.lay.tab_h)
                for i in range(len(self.tabs))]

    def draw(self, surf):
        self._rects = self._build_rects()
        f = gf(12, mono=False)
        for i, (r, name) in enumerate(zip(self._rects, self.tabs)):
            if i == self.active:
                bg  = TABACT; col = BRIGHT
                pygame.draw.rect(surf, bg, r)
                pygame.draw.rect(surf, CYAN, r, 1)
                pygame.draw.rect(surf, CYAN, (r.x, r.bottom - 2, r.w, 2))
            elif i == self._hov:
                pygame.draw.rect(surf, TABHOV, r)
                pygame.draw.rect(surf, BORDER, r, 1)
                col = TEXT
            else:
                pygame.draw.rect(surf, TABINACT, r)
                pygame.draw.rect(surf, BORDER,   r, 1)
                col = DIM
            tx = r.x + (r.w - tw(name, f)) // 2
            ty = r.y + (r.h - f.get_height()) // 2
            blit_text(surf, name, tx, ty, f, col)

    def on_event(self, event) -> Optional[int]:
        """Returns new active tab index on click, else None."""
        if event.type == pygame.MOUSEMOTION:
            self._hov = next((i for i, r in enumerate(self._rects)
                              if r.collidepoint(event.pos)), -1)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self._rects):
                if r.collidepoint(event.pos):
                    self.active = i; return i
        return None
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLIPBOARD HELPER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard.  Tries pygame.scrap, then pyperclip, then file."""
    try:
        pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        return True
    except Exception:
        pass
    try:
        import pyperclip  # type: ignore
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    try:
        out = Path("/tmp/carmine_export.txt")
        out.write_text(text, encoding="utf-8")
        return True
    except Exception:
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT SIDEBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Sidebar:
    """
    Left panel: logo strip, nation list, advance-turn button.
    """
    BTN_H = 34
    ROW_H = 28

    def __init__(self, lay: Layout):
        self.lay   = lay
        self.sel   = 0
        self._hov  = -1
        self._adv_hov = False
        self._tr_hov  = False
        self._adv_btn: pygame.Rect = pygame.Rect(0,0,1,1)
        self._tr_btn:  pygame.Rect = pygame.Rect(0,0,1,1)
        self._rects:   List[pygame.Rect] = []

    def update_layout(self, lay: Layout): self.lay = lay

    def draw(self, surf, nations: List[str]):
        L = self.lay
        # Background
        pygame.draw.rect(surf, PANEL, (0, 0, L.lw, L.sh))
        pygame.draw.line(surf, BORDER, (L.lw-1, 0), (L.lw-1, L.sh), 1)
        # Logo strip
        pygame.draw.rect(surf, ACCENT2, (0, 0, L.lw, L.tbar_h))
        pygame.draw.line(surf, ACCENT, (0, L.tbar_h-1), (L.lw, L.tbar_h-1), 1)
        f_lg = gf(13, mono=False)
        blit_text(surf, "CARMINE NRP", 10, 8, f_lg, BRIGHT)
        blit_text(surf, VERSION, 10, 26, gf(10), DIM)

        y0 = L.tbar_h + L.tab_h + 8
        f  = gf(12)
        blit_text(surf, "NATIONS", 10, y0, gf(10), DIM)
        y0 += 18

        self._rects = []
        for i, name in enumerate(nations):
            r = pygame.Rect(4, y0, L.lw - 8, self.ROW_H)
            self._rects.append(r)
            if i == self.sel:
                pygame.draw.rect(surf, SEL, r, border_radius=3)
                pygame.draw.rect(surf, CYAN, r, 1, border_radius=3)
            elif i == self._hov:
                pygame.draw.rect(surf, HOV, r, border_radius=3)
            tag = nation_tag(name)
            blit_text(surf, tag, r.x+6, r.y+8, gf(10), TEAL)
            blit_text(surf, name[:20], r.x+36, r.y+8, f, BRIGHT if i==self.sel else TEXT)
            y0 += self.ROW_H + 2

        # Advance Turn button
        bot = L.sh - L.sbar_h
        self._adv_btn = pygame.Rect(6, bot - self.BTN_H*2 - 8, L.lw-12, self.BTN_H)
        bg_a = BTNACC2 if self._adv_hov else BTNACC
        pygame.draw.rect(surf, bg_a, self._adv_btn, border_radius=4)
        pygame.draw.rect(surf, ACCENT, self._adv_btn, 1, border_radius=4)
        fa = gf(12)
        blit_text(surf, "▶  ADVANCE TURN",
                  self._adv_btn.x + (self._adv_btn.w - tw("▶  ADVANCE TURN",fa))//2,
                  self._adv_btn.y + (self._adv_btn.h - fa.get_height())//2, fa, BRIGHT)

        # Trade Route Builder button
        self._tr_btn = pygame.Rect(6, bot - self.BTN_H - 2, L.lw-12, self.BTN_H)
        bg_t = BTNHOV if self._tr_hov else BTNBG
        pygame.draw.rect(surf, bg_t, self._tr_btn, border_radius=4)
        pygame.draw.rect(surf, BORDER2, self._tr_btn, 1, border_radius=4)
        blit_text(surf, "⇌  TRADE ROUTE",
                  self._tr_btn.x + (self._tr_btn.w - tw("⇌  TRADE ROUTE",fa))//2,
                  self._tr_btn.y + (self._tr_btn.h - fa.get_height())//2, fa, CYAN)

    def on_event(self, event, nations: List[str]) -> Optional[str]:
        """Returns 'advance', 'trade', nation-name, or None."""
        if event.type == pygame.MOUSEMOTION:
            p = event.pos
            self._hov = next((i for i,r in enumerate(self._rects) if r.collidepoint(p)), -1)
            self._adv_hov = self._adv_btn.collidepoint(p)
            self._tr_hov  = self._tr_btn.collidepoint(p)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self._adv_btn.collidepoint(p): return "advance"
            if self._tr_btn.collidepoint(p):  return "trade"
            for i, r in enumerate(self._rects):
                if r.collidepoint(p):
                    self.sel = i
                    return nations[i]
        return None

    def select_delta(self, d: int, n: int):
        self.sel = (self.sel + d) % max(1, n)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEXT PANEL (scrollable multi-line renderer)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TextPanel:
    """
    Renders a list of strings into a clipped, scrollable area.
    Used by Profile and Galactic News tabs.
    """
    LH = 16  # line height

    def __init__(self, scrl: Scrollbar):
        self.scrl  = scrl
        self.lines: List[Tuple[str, Any]] = []  # (text, colour)

    def set_lines(self, lines):
        """Accept list of str or (str, colour) tuples."""
        self.lines = [(l, TEXT) if isinstance(l, str) else l for l in lines]

    def draw(self, surf, rect: pygame.Rect):
        surf.set_clip(rect)
        y = rect.y - self.scrl.scroll
        fh = self.LH; fm = gf(12); fhd = gf(13)
        for txt, col in self.lines:
            if y + fh > rect.y and y < rect.bottom:
                # Heading lines
                if txt.startswith("# "):
                    blit_text(surf, txt[2:], rect.x+8, y, fhd, CYAN)
                elif txt.startswith("## "):
                    blit_text(surf, txt[3:], rect.x+8, y, fhd, TEAL)
                elif txt.startswith("-# "):
                    blit_text(surf, txt[3:], rect.x+8, y, gf(10), DIM)
                elif txt.startswith("**") and txt.endswith("**"):
                    blit_text(surf, txt[2:-2], rect.x+8, y, fhd, GOLD)
                elif txt.startswith("```") or txt == "```":
                    pass  # fence markers – skip drawing
                else:
                    blit_text(surf, txt, rect.x+8, y, fm, col)
            y += fh
        surf.set_clip(None)
        total = len(self.lines) * fh + 20
        self.scrl.set_content(total, rect.h)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProfilePanel:
    """
    Tab 0 – National Profile.
    Shows discord_profile() output.  Editable fields via double-click.
    Edit rows emit (label, raw_value, meta) for the EditOverlay.
    """
    LH = 16

    def __init__(self, scrl: Scrollbar):
        self.scrl  = scrl
        self._rows: List[Tuple[str,str,Any]] = []  # (display_line, raw_val, meta|None)
        self._hov  = -1
        self._rects: List[pygame.Rect] = []

    def rebuild(self, nation, state):
        if not nation:
            self._rows = [("No nation loaded.", "", None)]; return
        raw = discord_profile(nation, state)
        rows = []
        for line in raw.split("\n"):
            # Detect editable "  Key : value" patterns inside code fences
            meta = _detect_edit_meta(line, nation)
            rows.append((line, line.strip(), meta))
        self._rows = rows

    def draw(self, surf, rect: pygame.Rect, mx: int, my: int):
        surf.set_clip(rect)
        y   = rect.y - self.scrl.scroll
        lh  = self.LH
        fm  = gf(12); fh  = gf(13); fs  = gf(10)
        self._rects = []
        for i, (line, _, meta) in enumerate(self._rows):
            ry = pygame.Rect(rect.x, y, rect.w, lh)
            self._rects.append(ry)
            if y + lh > rect.y and y < rect.bottom:
                is_hov = (i == self._hov)
                if is_hov and meta:
                    pygame.draw.rect(surf, HOV, ry)
                col = _line_colour(line)
                if line.startswith("# "):
                    pygame.draw.line(surf, BORDER, (rect.x, y+lh-1), (rect.right, y+lh-1))
                    blit_text(surf, line[2:], rect.x+8, y+1, fh, CYAN)
                elif line.startswith("## "):
                    blit_text(surf, line[3:], rect.x+8, y+1, fh, TEAL)
                elif line.startswith("-# "):
                    blit_text(surf, line[3:], rect.x+8, y+1, fs, DIM)
                elif line.startswith("**") and line.endswith("**"):
                    blit_text(surf, line[2:-2], rect.x+8, y+2, fh, GOLD)
                elif line.strip() not in ("```",""):
                    blit_text(surf, line, rect.x+8, y+1, fm, col)
                if meta and is_hov:
                    hint = "✎"
                    blit_text(surf, hint, rect.right-18, y+1, fs, TEAL)
            y += lh
        surf.set_clip(None)
        total = len(self._rows) * lh + 20
        self.scrl.set_content(total, rect.h)

    def on_event(self, event, rect: pygame.Rect):
        """Returns (label, raw, meta) on double-click of editable row, else None."""
        if event.type == pygame.MOUSEMOTION:
            p = event.pos
            if rect.collidepoint(p):
                ry = p[1] + self.scrl.scroll - rect.y
                self._hov = ry // self.LH
            else:
                self._hov = -1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and rect.collidepoint(event.pos):
            p = event.pos
            ry = (p[1] + self.scrl.scroll - rect.y) // self.LH
            if 0 <= ry < len(self._rows):
                line, raw, meta = self._rows[ry]
                if meta:
                    label = line.strip().split(":")[0].strip().lstrip()
                    val   = line.split(":",1)[1].strip() if ":" in line else raw
                    return (label, val, meta)
        return None


def _line_colour(line: str):
    s = line.strip()
    if not s or s == "```": return DIM2
    if s.startswith("─"): return BORDER2
    # Values after colon — key is DIM, value is TEXT
    return TEXT


def _detect_edit_meta(line: str, nation: dict) -> Optional[dict]:
    """
    Heuristic: if a profile line looks like '  Key : value'
    and maps to a known editable field, return a meta dict.
    """
    FIELD_MAP = {
        "IPEU (base)":    {"path":["base_ipeu"],         "type":"float"},
        "IPEU Growth":    {"path":["ipeu_growth"],       "type":"pct"},
        "Pop Growth":     {"path":["pop_growth"],        "type":"pct"},
        "Population":     {"path":["population"],        "type":"pop"},
        "Debt Balance":   {"path":["debt_balance"],      "type":"float"},
        "Interest Rate":  {"path":["interest_rate"],     "type":"pct"},
        "Debt Repayment": {"path":["debt_repayment"],    "type":"float"},
        "Strategic Fund": {"path":["strategic_fund"],    "type":"float"},
        "Research Budget":{"path":["research_budget"],   "type":"float"},
        "Economic Model": {"path":["economic_model"],    "type":"str"},
        "Status":         {"path":["eco_status"],        "type":"str"},
        "Civilisation":   {"path":["civ_level"],         "type":"str"},
        "Tier":           {"path":["civ_tier"],          "type":"int"},
        "Investments":    {"path":["investments"],       "type":"float"},
        "Subsidies":      {"path":["subsidies"],         "type":"float"},
        "Domestic Prod.": {"path":["domestic_production"],"type":"float"},
        "Construction Eff.":{"path":["construction_efficiency"],"type":"pct"},
        "Research Eff.":  {"path":["research_efficiency"],"type":"pct"},
        "Bureaucracy Eff.":{"path":["bureaucracy_efficiency"],"type":"pct"},
    }
    # Expenditure rows
    for cat in EXPENDITURE_ORDER:
        if cat in line and "%" in line:
            return {"path":["expenditure", cat], "type":"pct"}
    for key, meta in FIELD_MAP.items():
        if key in line and ":" in line:
            return meta
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM MAP PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PLANET_COLOURS = {
    "Terrestrial": (60,160,100), "Gas Giant": (200,160,80),
    "Ice World": (140,200,230), "Barren": (130,110,90),
    "Oceanic": (60,100,200),
}

class SystemMapPanel:
    """
    Tab 1 – 2-D orbital diagram of the selected nation's home system.
    Click a planet to show a detail drawer on the right.
    """
    def __init__(self):
        self._sel_planet: Optional[dict] = None
        self._planet_rects: List[Tuple[pygame.Rect, dict]] = []

    def draw(self, surf, rect: pygame.Rect, nation: Optional[dict]):
        pygame.draw.rect(surf, BG, rect)
        if not nation:
            blit_text(surf, "No nation selected.", rect.x+20, rect.y+20, gf(12), DIM)
            return

        sys_list = nation.get("star_systems", [])
        if not sys_list:
            blit_text(surf, "No star systems defined.", rect.x+20, rect.y+20, gf(12), DIM)
            return

        system = sys_list[0]
        planets = system.get("planets", [])
        name    = system.get("name", "Unknown System")

        f_t = gf(13, mono=False)
        blit_text(surf, f"◈  {name}", rect.x+14, rect.y+10, f_t, CYAN)

        # Star
        cx = rect.x + rect.w // 3
        cy = rect.y + rect.h // 2
        pygame.draw.circle(surf, GOLD, (cx, cy), 22)
        pygame.draw.circle(surf, (255,230,160), (cx, cy), 14)

        self._planet_rects = []
        n = max(1, len(planets))
        for i, pl in enumerate(planets):
            orbit_r = 70 + i * 60
            # Draw orbit ring
            pygame.draw.circle(surf, BORDER, (cx, cy), orbit_r, 1)
            angle = -math.pi/2 + (i / n) * 2 * math.pi
            px = int(cx + orbit_r * math.cos(angle))
            py = int(cy + orbit_r * math.sin(angle))
            ptype  = pl.get("type", "Terrestrial")
            pcol   = PLANET_COLOURS.get(ptype, (140,140,140))
            prad   = {"Tiny":5,"Small":7,"Medium":9,"Large":12,"Massive":15}.get(pl.get("size","Medium"),9)
            is_sel = (pl is self._sel_planet)
            if is_sel:
                pygame.draw.circle(surf, BRIGHT, (px,py), prad+4, 2)
            pygame.draw.circle(surf, pcol, (px,py), prad)
            prect = pygame.Rect(px-prad-4, py-prad-4, prad*2+8, prad*2+8)
            self._planet_rects.append((prect, pl))
            # Label
            blit_text(surf, pl.get("name","?"), px-20, py+prad+4, gf(10), DIM)

        # Detail drawer
        if self._sel_planet:
            self._draw_detail(surf, rect, self._sel_planet, nation)

    def _draw_detail(self, surf, rect, pl, nation):
        dw = min(260, rect.w // 3)
        dr = pygame.Rect(rect.right - dw, rect.y, dw, rect.h)
        pygame.draw.rect(surf, PANEL2, dr)
        pygame.draw.line(surf, BORDER2, (dr.x, dr.y), (dr.x, dr.bottom), 1)
        f = gf(11); fh = gf(12)
        y = dr.y + 10
        def ln(label, val, col=TEXT):
            nonlocal y
            blit_text(surf, label, dr.x+8, y, f, DIM)
            blit_text(surf, str(val), dr.x+120, y, f, col)
            y += 15
        blit_text(surf, pl.get("name","?"), dr.x+8, y, fh, BRIGHT); y += 20
        ln("Type",        pl.get("type","?"))
        ln("Size",        pl.get("size","?"))
        ln("Habitability",f"{pl.get('habitability',75):.0f}%")
        ln("Devastation", f"{pl.get('devastation',0):.0f}%", RED_C if pl.get("devastation",0)>25 else TEXT)
        ln("Crime Rate",  f"{pl.get('crime_rate',10):.0f}%", RED_C if pl.get("crime_rate",10)>30 else TEXT)
        ln("Unrest",      f"{pl.get('unrest',5):.0f}%",      RED_C if pl.get("unrest",5)>20 else TEXT)
        y += 6
        blit_text(surf, "SETTLEMENTS", dr.x+8, y, gf(10), DIM); y += 14
        for s in pl.get("settlements",[]):
            blit_text(surf, f"  {s['name']}", dr.x+8, y, f, TEAL); y += 14
            blit_text(surf, f"    pop: {fmt_pop(s.get('population',0))}", dr.x+8, y, f, DIM); y += 13
        y += 6
        blit_text(surf, "ORBITAL BUILDINGS", dr.x+8, y, gf(10), DIM); y += 14
        for ob in pl.get("orbital_buildings",[]):
            blit_text(surf, f"  {ob.get('type','?')}", dr.x+8, y, f, GOLD); y += 13

    def on_event(self, event, rect: pygame.Rect):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for prect, pl in self._planet_rects:
                if prect.collidepoint(event.pos):
                    self._sel_planet = None if pl is self._sel_planet else pl
                    return True
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EVENT LOG PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SEV_COLS = {"Critical": RED_C, "Major": GOLD, "Minor": CYAN, "Info": DIM}

class EventLogPanel:
    """
    Tab 2 – Event log with filter, approve toggle, edit body, delete.
    """
    ROW_H = 56
    BTN_W = 60

    def __init__(self, scrl: Scrollbar):
        self.scrl  = scrl
        self._filter_nation: Optional[str] = None
        self._filter_sev:    Optional[str] = None
        self._hov  = -1
        self._rects: List[pygame.Rect] = []
        self._appr_rects: List[pygame.Rect] = []
        self._del_rects:  List[pygame.Rect] = []
        self._events: List[dict] = []

    def rebuild(self, state: dict, nation_filter: Optional[str] = None):
        elog = EventLog(state)
        self._events = elog.filter(nation=nation_filter)
        self._filter_nation = nation_filter

    def draw(self, surf, rect: pygame.Rect):
        surf.set_clip(rect)
        f  = gf(11); fh = gf(12); fs = gf(10)
        y  = rect.y - self.scrl.scroll
        rh = self.ROW_H
        self._rects = []; self._appr_rects = []; self._del_rects = []

        if not self._events:
            surf.set_clip(None)
            blit_text(surf, "No events recorded.", rect.x+16, rect.y+20, fh, DIM)
            self.scrl.set_content(1, rect.h)
            return

        for i, ev in enumerate(self._events):
            r = pygame.Rect(rect.x+2, y, rect.w-4, rh-2)
            self._rects.append(r)
            if y + rh > rect.y and y < rect.bottom:
                bg = PANEL3 if i % 2 == 0 else PANEL2
                if i == self._hov: bg = HOV
                pygame.draw.rect(surf, bg, r, border_radius=2)
                sev = ev.get("severity","Info")
                scol = SEV_COLS.get(sev, DIM)
                pygame.draw.rect(surf, scol, (r.x, r.y, 3, r.h), border_radius=2)
                icon = SEVERITY_EMOJI.get(sev,"📊")
                blit_text(surf, f"{icon} {ev.get('title','?')}", r.x+10, r.y+4, fh, BRIGHT)
                blit_text(surf, f"[{ev['event_id']}]  T{ev['turn']} Y{ev['year']}Q{ev['quarter']}  {ev.get('nation','?')}",
                          r.x+10, r.y+20, fs, DIM)
                # Body (truncated)
                body = ev.get("body","")[:90] + ("…" if len(ev.get("body",""))>90 else "")
                blit_text(surf, body, r.x+10, r.y+34, fs, TEXT)
                # Approve button
                appr = ev.get("gm_approved",False)
                ab = pygame.Rect(r.right - self.BTN_W*2 - 6, r.y+4, self.BTN_W, 22)
                self._appr_rects.append(ab)
                abg = GREEN2 if appr else BTNBG
                acol = GREEN if appr else DIM
                pygame.draw.rect(surf, abg, ab, border_radius=3)
                pygame.draw.rect(surf, acol, ab, 1, border_radius=3)
                blit_text(surf, "✓ APPR" if appr else "APPROVE",
                          ab.x+(ab.w-tw("APPROVE",fs))//2, ab.y+5, fs, acol)
                # Delete button
                db = pygame.Rect(r.right - self.BTN_W - 2, r.y+4, self.BTN_W, 22)
                self._del_rects.append(db)
                pygame.draw.rect(surf, RED2, db, border_radius=3)
                pygame.draw.rect(surf, RED_C, db, 1, border_radius=3)
                blit_text(surf, "DELETE", db.x+(db.w-tw("DELETE",fs))//2, db.y+5, fs, RED_C)
            y += rh

        surf.set_clip(None)
        self.scrl.set_content(len(self._events)*rh + 20, rect.h)

    def on_event(self, event, rect: pygame.Rect, state: dict) -> Optional[str]:
        """
        Returns:
          'approve:<event_id>'  on approve click
          'delete:<event_id>'   on delete click
          'edit:<event_id>'     on row body click (for EditOverlay)
          None otherwise
        """
        if event.type == pygame.MOUSEMOTION and rect.collidepoint(event.pos):
            ry = (event.pos[1] + self.scrl.scroll - rect.y) // self.ROW_H
            self._hov = ry
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            for i, (ab, db, r, ev) in enumerate(
                    zip(self._appr_rects, self._del_rects, self._rects, self._events)):
                if ab.collidepoint(p):
                    EventLog(state).approve(ev["event_id"])
                    return f"approve:{ev['event_id']}"
                if db.collidepoint(p):
                    EventLog(state).delete(ev["event_id"])
                    return f"delete:{ev['event_id']}"
                if r.collidepoint(p):
                    return f"edit:{ev['event_id']}"
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MARKET PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MarketPanel:
    """
    Tab 3 – Galactic market prices, editable modifiers, [FLUCTUATE].
    """
    ROW_H = 42

    def __init__(self):
        self._fluct_btn: pygame.Rect = pygame.Rect(0,0,1,1)
        self._fluct_hov  = False
        self._row_rects:  List[pygame.Rect] = []
        self._hov         = -1

    def draw(self, surf, rect: pygame.Rect, state: dict):
        pygame.draw.rect(surf, BG, rect)
        me   = MarketEngine(state.get("market",{}))
        rows = me.get_prices()
        f    = gf(12); fh = gf(13, mono=False); fs = gf(11)

        # Header
        hx = rect.x + 10
        blit_text(surf, "GALACTIC MARKET", hx, rect.y+8, fh, CYAN)
        blit_text(surf, "Click a row to edit modifier", hx, rect.y+26, fs, DIM)

        # Column headers
        hy = rect.y + 48
        pygame.draw.line(surf, BORDER, (rect.x, hy+16), (rect.right, hy+16), 1)
        for label, xoff in [("RESOURCE",0),("BASE",200),("×MOD",280),("EFFECTIVE",360),("TREND",470)]:
            blit_text(surf, label, rect.x+10+xoff, hy, fs, DIM)

        self._row_rects = []
        y = hy + 24
        for i, row in enumerate(rows):
            r = pygame.Rect(rect.x+2, y, rect.w-4, self.ROW_H-2)
            self._row_rects.append(r)
            bg = PANEL3 if i%2==0 else PANEL2
            if i == self._hov: bg = HOV
            pygame.draw.rect(surf, bg, r, border_radius=2)
            # Resource name
            blit_text(surf, row["resource"], r.x+12, r.y+6, f, BRIGHT)
            blit_text(surf, f"{row['base']:.2f}", r.x+210, r.y+6, f, DIM)
            mcol = (GREEN if row["modifier"] > 1.0 else (RED_C if row["modifier"] < 1.0 else TEXT))
            blit_text(surf, f"×{row['modifier']:.3f}", r.x+290, r.y+6, f, mcol)
            blit_text(surf, f"{row['effective']:.4f} cr", r.x+370, r.y+6, f, GOLD)
            tcol = (GREEN if row["trend"]=="▲" else (RED_C if row["trend"]=="▼" else DIM))
            blit_text(surf, row["trend"], r.x+480, r.y+6, fh, tcol)
            # Price history sparkline
            hist = row.get("history",[row["effective"]])
            if len(hist) > 1:
                self._draw_spark(surf, r.x+12, r.y+22, 160, 14, hist)
            blit_text(surf, "✎ click to edit", r.right-100, r.y+6, gf(10), DIM2)
            y += self.ROW_H

        # Fluctuate button
        self._fluct_btn = pygame.Rect(rect.x+10, rect.bottom-42, 140, 30)
        fbg = BTNHOV if self._fluct_hov else BTNBG
        pygame.draw.rect(surf, fbg, self._fluct_btn, border_radius=4)
        pygame.draw.rect(surf, BORDER2, self._fluct_btn, 1, border_radius=4)
        blit_text(surf, "⟳  FLUCTUATE", self._fluct_btn.x+8, self._fluct_btn.y+8, fs, CYAN)

        # Export hint
        blit_text(surf, "[D] Copy Market Report", rect.right-160, rect.bottom-30, fs, DIM2)

    def _draw_spark(self, surf, x, y, w, h, data):
        mn, mx = min(data), max(data)
        span = max(mx-mn, 0.0001)
        pts = []
        for i, v in enumerate(data):
            px = x + int(i/(len(data)-1)*w)
            py = y + h - int((v-mn)/span*h)
            pts.append((px,py))
        if len(pts) >= 2:
            pygame.draw.lines(surf, TEAL2, False, pts, 1)

    def on_event(self, event, rect, state) -> Optional[Tuple[str,float,str]]:
        """Returns (resource_name, current_mod, 'modifier') on row click, or None."""
        if event.type == pygame.MOUSEMOTION:
            self._hov = -1; self._fluct_hov = False
            p = event.pos
            self._fluct_hov = self._fluct_btn.collidepoint(p)
            for i, r in enumerate(self._row_rects):
                if r.collidepoint(p): self._hov = i
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self._fluct_btn.collidepoint(p):
                me = MarketEngine(state.get("market",{}))
                me.fluctuate_all()
                return ("__fluctuate__", 0, "")
            me = MarketEngine(state.get("market",{}))
            rows = me.get_prices()
            for i, r in enumerate(self._row_rects):
                if r.collidepoint(p) and i < len(rows):
                    row = rows[i]
                    return (row["resource"], row["modifier"], "modifier")
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADVANCE TURN MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AdvanceTurnModal:
    """
    Shown after advance_turn() completes.
    Displays every d20 roll and event summary; dismiss with ENTER/ESC/click.
    """
    def __init__(self):
        self.active  = False
        self.events: List[dict] = []
        self._scrl   = Scrollbar(0,0,10,400)
        self._ok_btn: pygame.Rect = pygame.Rect(0,0,1,1)
        self._ok_hov = False

    def open(self, events: List[dict]):
        self.active  = True
        self.events  = sorted(events, key=lambda e: (
            ["Critical","Major","Minor","Info",""].index(e.get("severity","Info"))
            if e.get("severity","Info") in ["Critical","Major","Minor","Info"] else 4))
        self._scrl.scroll = 0

    def close(self): self.active = False

    def draw(self, surf, lay: Layout):
        if not self.active: return
        # Dim overlay
        ov = pygame.Surface((lay.sw, lay.sh), pygame.SRCALPHA)
        ov.fill((0,0,0,160))
        surf.blit(ov,(0,0))

        mw = min(700, lay.sw-80); mh = min(520, lay.sh-80)
        mx = (lay.sw-mw)//2;     my = (lay.sh-mh)//2
        mr = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(surf, MODALBG, mr, border_radius=6)
        pygame.draw.rect(surf, MODALBDR, mr, 2, border_radius=6)
        corner_deco(surf, mx, my, mw, mh, CYAN, 12)

        f = gf(12); fh = gf(14, mono=False); fs = gf(11)
        blit_text(surf, "TURN ADVANCED — EVENT SUMMARY", mx+16, my+12, fh, CYAN)
        blit_text(surf, f"{len(self.events)} events generated", mx+16, my+32, fs, DIM)

        clip_r = pygame.Rect(mx+4, my+52, mw-24, mh-100)
        surf.set_clip(clip_r)
        y = clip_r.y - self._scrl.scroll
        LH = 50
        for ev in self.events:
            if y + LH > clip_r.y and y < clip_r.bottom:
                scol = SEV_COLS.get(ev.get("severity","Info"), DIM)
                icon = SEVERITY_EMOJI.get(ev.get("severity","Info"),"📊")
                roll = ev.get("d20_roll","?")
                blit_text(surf, f"{icon} [{roll:>2}]  {ev.get('title','?')}", mx+16, y+4, f, BRIGHT)
                loc = ev.get("nation","?")
                if ev.get("planet"): loc += f" | {ev['planet']}"
                blit_text(surf, loc, mx+16, y+20, fs, scol)
                body = (ev.get("body",""))[:100]+"…" if len(ev.get("body",""))>100 else ev.get("body","")
                blit_text(surf, body, mx+16, y+34, fs, DIM)
            y += LH
        surf.set_clip(None)
        self._scrl.set_content(len(self.events)*LH+20, clip_r.h)
        self._scrl.update_rect(mx+mw-12, clip_r.y, 10, clip_r.h)
        self._scrl.draw(surf)

        self._ok_btn = pygame.Rect(mx+mw//2-50, my+mh-42, 100, 30)
        bg = BTNACC2 if self._ok_hov else BTNACC
        pygame.draw.rect(surf, bg, self._ok_btn, border_radius=4)
        pygame.draw.rect(surf, ACCENT, self._ok_btn, 1, border_radius=4)
        blit_text(surf, "DISMISS", self._ok_btn.x+18, self._ok_btn.y+8, fs, BRIGHT)

    def on_event(self, event) -> bool:
        """Returns True if modal should close."""
        if not self.active: return False
        self._scrl.on_event(event, True)
        if event.type == pygame.MOUSEMOTION:
            self._ok_hov = self._ok_btn.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._ok_btn.collidepoint(event.pos): return True
        return False

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADE ROUTE BUILDER MODAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TradeRouteModal:
    """
    Full trade route builder with live calculation preview.
    Fields: exporter, importer, resource, quantity, pirate_distance, escort %.
    One optional transit nation with tax rate.
    """

    FIELDS = [
        ("Exporter",  "exporter",   "str"),
        ("Importer",  "importer",   "str"),
        ("Resource",  "resource",   "str"),
        ("Qty/turn",  "quantity",   "float"),
        ("Pirate Dist","pirate_dist","str"),
        ("Escort %",  "escort_pct", "float"),
        ("Transit Nation","transit_nation","str"),
        ("Transit Tax %", "transit_tax",   "float"),
        ("Route Mod ×",   "route_mod",     "float"),
    ]

    def __init__(self):
        self.active   = False
        self.values   = {}
        self.preview  = None
        self._focused = 0
        self._field_rects: List[pygame.Rect] = []
        self._calc_btn: pygame.Rect = pygame.Rect(0,0,1,1)
        self._add_btn:  pygame.Rect = pygame.Rect(0,0,1,1)
        self._cls_btn:  pygame.Rect = pygame.Rect(0,0,1,1)
        self._calc_hov = self._add_hov = self._cls_hov = False

    def open(self, nation_names: List[str], state: dict):
        self.active  = True
        self._state  = state
        self._nnames = nation_names
        self.values  = {
            "exporter":  nation_names[0] if nation_names else "",
            "importer":  nation_names[1] if len(nation_names)>1 else "",
            "resource":  RESOURCE_NAMES[0],
            "quantity":  "1000",
            "pirate_dist":"near",
            "escort_pct": "0",
            "transit_nation":"",
            "transit_tax":   "0",
            "route_mod":     "1.0",
        }
        self.preview  = None
        self._focused = 0

    def close(self): self.active = False

    def draw(self, surf, lay: Layout):
        if not self.active: return
        ov = pygame.Surface((lay.sw, lay.sh), pygame.SRCALPHA)
        ov.fill((0,0,0,160)); surf.blit(ov,(0,0))

        mw = min(680, lay.sw-60); mh = min(580, lay.sh-60)
        mx = (lay.sw-mw)//2;     my = (lay.sh-mh)//2
        mr = pygame.Rect(mx, my, mw, mh)
        pygame.draw.rect(surf, MODALBG, mr, border_radius=6)
        pygame.draw.rect(surf, MODALBDR, mr, 2, border_radius=6)
        corner_deco(surf, mx, my, mw, mh, CYAN, 12)

        fh = gf(14, mono=False); f = gf(12); fs = gf(11)
        blit_text(surf, "TRADE ROUTE BUILDER", mx+16, my+12, fh, CYAN)

        # Fields
        self._field_rects = []
        fy = my + 44
        col_x = [mx+14, mx+mw//2+8]
        for i, (label, key, _) in enumerate(self.FIELDS):
            cx = col_x[i % 2]
            if i % 2 == 0 and i > 0: fy += 36
            blit_text(surf, label, cx, fy-14 if i%2==0 else fy-14, f, DIM)
            fr = pygame.Rect(cx, fy, mw//2-24, 24)
            self._field_rects.append(fr)
            bdr = EDITBDR if i == self._focused else BORDER
            pygame.draw.rect(surf, EDITBG, fr, border_radius=3)
            pygame.draw.rect(surf, bdr, fr, 1, border_radius=3)
            blit_text(surf, self.values.get(key,""), fr.x+6, fr.y+5, f, BRIGHT)
            if i % 2 == 1: fy += 36

        # Buttons
        by = my + mh - 120
        self._calc_btn = pygame.Rect(mx+14, by, 120, 28)
        self._add_btn  = pygame.Rect(mx+144, by, 140, 28)
        self._cls_btn  = pygame.Rect(mx+mw-90, by, 76, 28)
        for btn, lbl, hov, accent in [
            (self._calc_btn, "CALCULATE",  self._calc_hov, False),
            (self._add_btn,  "ADD TO STATE", self._add_hov,  True),
            (self._cls_btn,  "CANCEL",      self._cls_hov,  False),
        ]:
            bg = (BTNACC2 if hov else BTNACC) if accent else (BTNHOV if hov else BTNBG)
            bdr = ACCENT if accent else BORDER2
            pygame.draw.rect(surf, bg, btn, border_radius=3)
            pygame.draw.rect(surf, bdr, btn, 1, border_radius=3)
            blit_text(surf, lbl, btn.x+(btn.w-tw(lbl,fs))//2, btn.y+8, fs, BRIGHT)

        # Preview pane
        if self.preview:
            pr = pygame.Rect(mx+14, by+38, mw-28, 70)
            pygame.draw.rect(surf, BLOCK, pr, border_radius=3)
            pygame.draw.rect(surf, BORDER, pr, 1, border_radius=3)
            p = self.preview
            blit_text(surf, f"Gross: {fmt_cr(p['gross'])}  →  Net: {fmt_cr(p['net_income'])}  |  Pirate risk: {p['pirate_risk_pct']:.1f}%",
                      pr.x+10, pr.y+8, fs, GOLD)
            taxes = "  ".join(f"{t['nation']}: -{fmt_cr(t['amount'])} ({t['rate']*100:.1f}%)"
                              for t in p.get("transit_taxes",[]))
            blit_text(surf, taxes or "No transit taxes.", pr.x+10, pr.y+24, fs, DIM)
            blit_text(surf, f"Expected pirate loss/turn: {fmt_cr(p['expected_pirate_loss'])}",
                      pr.x+10, pr.y+40, fs, RED_C if p["pirate_risk"]>0.15 else DIM)
            blit_text(surf, f"Unit price: {p['effective_price']:.4f} cr  ×  {fmt_int(p['quantity_per_turn'])} = {fmt_cr(p['gross'])}",
                      pr.x+10, pr.y+54, fs, DIM)

    def on_event(self, event, state) -> Optional[str]:
        """Returns 'added:<route_id>', 'close', or None."""
        if not self.active: return None
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE: return "close"
            if k == pygame.K_TAB:
                d = -1 if (pygame.key.get_mods() & pygame.KMOD_SHIFT) else 1
                self._focused = (self._focused + d) % len(self.FIELDS)
                return None
            # Type into focused field
            key = self.FIELDS[self._focused][1]
            val = self.values.get(key,"")
            if k == pygame.K_BACKSPACE: val = val[:-1]
            elif event.unicode and event.unicode.isprintable(): val += event.unicode
            self.values[key] = val

        if event.type == pygame.MOUSEMOTION:
            p = event.pos
            self._calc_hov = self._calc_btn.collidepoint(p)
            self._add_hov  = self._add_btn.collidepoint(p)
            self._cls_hov  = self._cls_btn.collidepoint(p)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self._cls_btn.collidepoint(p): return "close"
            for i, fr in enumerate(self._field_rects):
                if fr.collidepoint(p): self._focused = i
            if self._calc_btn.collidepoint(p) or self._add_btn.collidepoint(p):
                self._do_calculate(state)
            if self._add_btn.collidepoint(p) and self.preview:
                tre = TradeRouteEngine(state)
                route = tre.build(self.preview,
                                   self.values.get("pirate_dist","near"),
                                   self.values.get("escort_pct","0")+"%")
                state.setdefault("trade_routes",[]).append(route)
                return f"added:{route['id']}"
        return None

    def _do_calculate(self, state):
        try:
            tre = TradeRouteEngine(state)
            exp_name = self.values.get("exporter","")
            imp_name = self.values.get("importer","")
            resource = self.values.get("resource", RESOURCE_NAMES[0])
            qty      = float(self.values.get("quantity","0").replace(",",""))
            dist     = self.values.get("pirate_dist","near")
            escort   = float(self.values.get("escort_pct","0").replace(",",""))
            rmod     = float(self.values.get("route_mod","1.0").replace(",",""))
            tnat     = self.values.get("transit_nation","").strip()
            ttax     = float(self.values.get("transit_tax","0").replace(",","").replace("%",""))
            if ttax > 1.5: ttax /= 100.0
            transits = [{"nation":tnat,"tax_rate":ttax}] if tnat else []
            self.preview = tre.calculate(exp_name, imp_name, resource, qty,
                                          transits, dist, escort, rmod)
        except Exception as ex:
            self.preview = None
            set_status(f"Calculation error: {ex}", RED_C)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN APPLICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class App:
    """
    Carmine NRP GM Tool — main application.
    Owns all panels, modals, widgets, and the event loop.
    """

    def __init__(self, state_path: str):
        pygame.init()
        pygame.display.set_caption(f"Carmine NRP GM Tool {VERSION}")
        flags = pygame.RESIZABLE
        self.screen = pygame.display.set_mode((1280, 720), flags)
        self.clock  = pygame.time.Clock()
        self.lay    = Layout(1280, 720)

        # State
        self.sm = StateManager(state_path)
        if not self.sm.load():
            # Bootstrap a minimal empty state
            self.sm.state = {
                "turn": 0, "year": 2200, "quarter": 4,
                "nations": [], "trade_routes": [],
                "market": {
                    "price_base":     {r: 1.0 for r in RESOURCE_NAMES},
                    "market_modifier":{r: 1.0 for r in RESOURCE_NAMES},
                    "price_history":  {},
                },
                "events": [], "event_counter": 0,
            }
            set_status(f"New state (no file found at {state_path})", GOLD)
        else:
            set_status(f"Loaded: {Path(state_path).name}", GREEN)

        # Widgets
        sr = self.lay.scrl_rect
        self._scrl      = Scrollbar(sr.x, sr.y, sr.w, sr.h)
        self._sidebar   = Sidebar(self.lay)
        self._tabs      = TabBar(self.lay, TAB_NAMES)
        self._edit      = EditOverlay()

        # Panels
        self._profile   = ProfilePanel(self._scrl)
        self._sysmap    = SystemMapPanel()
        self._eventlog  = EventLogPanel(self._scrl)
        self._market    = MarketPanel()

        # Modals
        self._adv_modal = AdvanceTurnModal()
        self._tr_modal  = TradeRouteModal()

        # Runtime state
        self._dirty     = False
        self._nation_idx= 0
        self._rebuild_profile()

    # ── helpers ──────────────────────────────

    @property
    def _nations(self) -> List[dict]:
        return self.sm.state.get("nations", [])

    @property
    def _nation_names(self) -> List[str]:
        return [n["name"] for n in self._nations]

    @property
    def _cur_nation(self) -> Optional[dict]:
        if not self._nations: return None
        idx = max(0, min(self._nation_idx, len(self._nations)-1))
        return self._nations[idx]

    def _rebuild_profile(self):
        n = self._cur_nation
        if n:
            self._profile.rebuild(n, self.sm.state)
            self._eventlog.rebuild(self.sm.state, n["name"])

    def _mark_dirty(self):
        self._dirty = True
        self.sm.mark_dirty()

    # ── main loop ────────────────────────────

    def run(self):
        running = True
        prev_t  = time.time()
        while running:
            now = time.time(); dt = now - prev_t; prev_t = now
            for event in pygame.event.get():
                result = self._handle_event(event)
                if result == "quit": running = False
            self._draw(dt)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    # ── event handling ────────────────────────

    def _handle_event(self, event) -> Optional[str]:
        sw, sh = pygame.display.get_surface().get_size()

        if event.type == pygame.QUIT: return "quit"

        if event.type == pygame.VIDEORESIZE:
            self.lay.update(event.w, event.h)
            sr = self.lay.scrl_rect
            self._scrl.update_rect(sr.x, sr.y, sr.w, sr.h)
            self._sidebar.update_layout(self.lay)
            self._tabs.update_layout(self.lay)
            return None

        # Modals have priority
        if self._adv_modal.active:
            if self._adv_modal.on_event(event):
                self._adv_modal.close()
            return None

        if self._tr_modal.active:
            res = self._tr_modal.on_event(event, self.sm.state)
            if res == "close":
                self._tr_modal.close()
            elif res and res.startswith("added:"):
                rid = res.split(":")[1]
                self._tr_modal.close()
                self._mark_dirty()
                self.sm.autosave()
                self._rebuild_profile()
                set_status(f"Trade route {rid} added & saved.", GREEN)
            return None

        # Edit overlay
        if self._edit.active:
            res = self._edit.on_event(event)
            if res == "confirm":
                n = self._cur_nation
                if n and apply_edit(n, self._edit.meta, self._edit.text):
                    self._mark_dirty()
                    self._rebuild_profile()
                    set_status("Field updated.", GREEN)
                else:
                    set_status("Invalid value — not applied.", RED_C)
                self._edit.close()
            elif res == "cancel":
                self._edit.close()
            return None

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            k = event.key
            if k == pygame.K_ESCAPE: return "quit"
            if k == pygame.K_s:
                self.sm.save(); self._dirty = False
                set_status("Saved.", GREEN)
            if k == pygame.K_d: self._do_export()
            if k == pygame.K_t: self._do_advance()
            if k == pygame.K_UP:
                self._sidebar.select_delta(-1, len(self._nations))
                self._nation_idx = self._sidebar.sel
                self._rebuild_profile()
                self._scrl.scroll = 0
            if k == pygame.K_DOWN:
                self._sidebar.select_delta(1, len(self._nations))
                self._nation_idx = self._sidebar.sel
                self._rebuild_profile()
                self._scrl.scroll = 0

        # Scrollbar (only for non-modal, non-edit state)
        mr = self.lay.main_rect
        over_main = mr.collidepoint(pygame.mouse.get_pos())
        self._scrl.on_event(event, over_main)

        # Tab bar
        tab_res = self._tabs.on_event(event)
        if tab_res is not None:
            self._scrl.scroll = 0

        # Sidebar
        sb_res = self._sidebar.on_event(event, self._nation_names)
        if sb_res == "advance":
            self._do_advance()
        elif sb_res == "trade":
            self._tr_modal.open(self._nation_names, self.sm.state)
        elif isinstance(sb_res, str) and sb_res in self._nation_names:
            self._nation_idx = self._nation_names.index(sb_res)
            self._sidebar.sel = self._nation_idx
            self._rebuild_profile()
            self._scrl.scroll = 0
            set_status(f"Selected: {sb_res}", TEAL)

        # Per-tab events
        tab = self._tabs.active
        rect = self.lay.main_rect

        if tab == 0:  # Profile
            res = self._profile.on_event(event, rect)
            if res:
                label, val, meta = res
                self._edit.open(label, val, meta)

        elif tab == 1:  # System Map
            self._sysmap.on_event(event, rect)

        elif tab == 2:  # Event Log
            res = self._eventlog.on_event(event, rect, self.sm.state)
            if res:
                if res.startswith("approve:") or res.startswith("delete:"):
                    self._mark_dirty()
                    self.sm.autosave()
                    self._eventlog.rebuild(self.sm.state, self._cur_nation["name"] if self._cur_nation else None)
                    set_status(res.replace(":", ": "), TEAL)
                elif res.startswith("edit:"):
                    eid = res.split(":")[1]
                    ev  = next((e for e in self.sm.state.get("events",[]) if e["event_id"]==eid), None)
                    if ev:
                        self._edit.open(f"Event body [{eid}]", ev["body"],
                                        {"path": ["__event_body__", eid], "type": "str"})

        elif tab == 3:  # Market
            res = self._market.on_event(event, rect, self.sm.state)
            if res:
                rname, cur_mod, field = res
                if rname == "__fluctuate__":
                    self._mark_dirty()
                    self.sm.autosave()
                    set_status("Market fluctuated.", GOLD)
                else:
                    self._edit.open(f"{rname} {field}", f"{cur_mod:.3f}",
                                    {"path": ["__market__", rname, field], "type": "float"})
        return None

    # ── drawing ───────────────────────────────

    def _draw(self, dt: float):
        sw, sh = self.screen.get_width(), self.screen.get_height()
        surf   = self.screen
        surf.fill(BG)

        n = self._cur_nation
        state = self.sm.state
        turn    = state.get("turn", 0)
        year    = state.get("year", 2200)
        quarter = state.get("quarter", 1)

        draw_top_bar(surf, self.lay, n["name"] if n else "— No Nation —",
                     turn, year, quarter, self._dirty)
        self._tabs.draw(surf)
        self._sidebar.draw(surf, self._nation_names)

        rect = self.lay.main_rect
        tab  = self._tabs.active

        if tab == 0:
            self._profile.draw(surf, rect, *pygame.mouse.get_pos())
        elif tab == 1:
            self._sysmap.draw(surf, rect, n)
        elif tab == 2:
            self._eventlog.draw(surf, rect)
        elif tab == 3:
            self._market.draw(surf, rect, state)

        # Scrollbar only for scrollable tabs
        if tab in (0, 2):
            self._scrl.draw(surf)

        draw_status_bar(surf, self.lay)
        self._edit.draw(surf, self.lay, dt)
        self._adv_modal.draw(surf, self.lay)
        self._tr_modal.draw(surf, self.lay)

    # ── actions ───────────────────────────────

    def _do_advance(self):
        set_status("Advancing turn…", GOLD)
        try:
            events = advance_turn(self.sm)
            self._dirty = False
            self._rebuild_profile()
            self._adv_modal.open(events)
            set_status(f"Turn advanced → T{self.sm.state['turn']}  ({len(events)} events)", GREEN)
        except Exception as ex:
            set_status(f"Advance failed: {ex}", RED_C)

    def _do_export(self):
        tab   = self._tabs.active
        state = self.sm.state
        n     = self._cur_nation
        try:
            if tab == 0 and n:
                text = discord_profile(n, state)
                label = f"Profile: {n['name']}"
            elif tab == 2:
                text = discord_galactic_news(state, state.get("turn",1))
                label = "Galactic News"
            elif tab == 3:
                text = discord_market_report(state)
                label = "Market Report"
            elif tab == 1 and n:
                # System map export as text summary
                lines = [f"# {n['name']} — System Map Export"]
                for sys in n.get("star_systems",[]):
                    lines.append(f"\n{sys['name']}")
                    for pl in sys.get("planets",[]):
                        lines.append(f"  {pl['name']}  ({pl.get('type','?')}, {pl.get('size','?')})")
                text  = "\n".join(lines)
                label = "System Map"
            else:
                set_status("Nothing to export for this tab.", DIM)
                return
            ok = copy_to_clipboard(text)
            if ok:
                set_status(f"Copied to clipboard: {label}", GREEN)
            else:
                # Fallback: save to /tmp
                Path("/tmp/carmine_export.txt").write_text(text, encoding="utf-8")
                set_status("Exported to /tmp/carmine_export.txt", GOLD)
        except Exception as ex:
            set_status(f"Export error: {ex}", RED_C)

    def _apply_market_edit(self, raw: str, rname: str, field: str):
        try:
            v = float(raw.strip())
            me = MarketEngine(self.sm.state.get("market",{}))
            if field == "modifier": me.set_modifier(rname, v)
            elif field == "base":   me.set_base(rname, v)
            self._mark_dirty()
            self.sm.autosave()
            set_status(f"Market {rname} {field} → {v:.3f}", GREEN)
        except Exception as ex:
            set_status(f"Invalid market value: {ex}", RED_C)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EDIT ROUTING PATCH
# Override apply_edit to handle __market__ and __event_body__ paths
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_orig_apply_edit = apply_edit

def apply_edit(nation: dict, meta: dict, raw: str) -> bool:  # type: ignore[override]
    path = meta.get("path", [])
    if path and path[0] == "__market__" and len(path) == 3:
        # handled externally in App — just return True as signal
        meta["__market_handled__"] = True; return True
    if path and path[0] == "__event_body__" and len(path) == 2:
        meta["__event_handled__"] = True; return True
    return _orig_apply_edit(nation, meta, raw)


# Patch App._handle_event to correctly route market/event edits post-confirm
_orig_handle = App._handle_event

def _patched_handle(self, event):
    result = _orig_handle(self, event)
    return result

# Extend the confirm branch in App to handle special paths
_orig_run = App.run

def _patched_run(self):
    running = True
    prev_t  = time.time()
    while running:
        now = time.time(); dt = now - prev_t; prev_t = now
        for event in pygame.event.get():
            result = self._handle_event_full(event)
            if result == "quit": running = False
        self._draw(dt)
        pygame.display.flip()
        self.clock.tick(FPS)
    pygame.quit()

def _handle_event_full(self, event):
    """Extended event handler that routes special edit paths."""
    if event.type == pygame.QUIT: return "quit"

    if event.type == pygame.VIDEORESIZE:
        self.lay.update(event.w, event.h)
        sr = self.lay.scrl_rect
        self._scrl.update_rect(sr.x, sr.y, sr.w, sr.h)
        self._sidebar.update_layout(self.lay)
        self._tabs.update_layout(self.lay)
        return None

    if self._adv_modal.active:
        if self._adv_modal.on_event(event): self._adv_modal.close()
        return None

    if self._tr_modal.active:
        res = self._tr_modal.on_event(event, self.sm.state)
        if res == "close":
            self._tr_modal.close()
        elif res and res.startswith("added:"):
            rid = res.split(":")[1]
            self._tr_modal.close()
            self._mark_dirty(); self.sm.autosave()
            self._rebuild_profile()
            set_status(f"Trade route {rid} added & saved.", GREEN)
        return None

    if self._edit.active:
        res = self._edit.on_event(event)
        if res == "confirm":
            meta = self._edit.meta
            path = meta.get("path",[])
            # Special: market edit
            if path and path[0] == "__market__" and len(path) == 3:
                self._apply_market_edit(self._edit.text, path[1], path[2])
            # Special: event body edit
            elif path and path[0] == "__event_body__" and len(path) == 2:
                eid = path[1]
                EventLog(self.sm.state).edit_body(eid, self._edit.text)
                self._mark_dirty(); self.sm.autosave()
                self._eventlog.rebuild(self.sm.state,
                    self._cur_nation["name"] if self._cur_nation else None)
                set_status(f"Event {eid} body updated.", GREEN)
            else:
                n = self._cur_nation
                if n and _orig_apply_edit(n, meta, self._edit.text):
                    self._mark_dirty(); self._rebuild_profile()
                    set_status("Field updated.", GREEN)
                else:
                    set_status("Invalid value — not applied.", RED_C)
            self._edit.close()
        elif res == "cancel":
            self._edit.close()
        return None

    if event.type == pygame.KEYDOWN:
        k = event.key
        if k == pygame.K_ESCAPE: return "quit"
        if k == pygame.K_s:
            self.sm.save(); self._dirty = False; set_status("Saved.", GREEN)
        if k == pygame.K_d: self._do_export()
        if k == pygame.K_t: self._do_advance()
        if k == pygame.K_UP:
            self._sidebar.select_delta(-1, len(self._nations))
            self._nation_idx = self._sidebar.sel
            self._rebuild_profile(); self._scrl.scroll = 0
        if k == pygame.K_DOWN:
            self._sidebar.select_delta(1, len(self._nations))
            self._nation_idx = self._sidebar.sel
            self._rebuild_profile(); self._scrl.scroll = 0

    mr = self.lay.main_rect
    over_main = mr.collidepoint(pygame.mouse.get_pos())
    self._scrl.on_event(event, over_main)
    self._tabs.on_event(event)

    sb_res = self._sidebar.on_event(event, self._nation_names)
    if sb_res == "advance":
        self._do_advance()
    elif sb_res == "trade":
        self._tr_modal.open(self._nation_names, self.sm.state)
    elif isinstance(sb_res, str) and sb_res in self._nation_names:
        self._nation_idx = self._nation_names.index(sb_res)
        self._sidebar.sel = self._nation_idx
        self._rebuild_profile(); self._scrl.scroll = 0
        set_status(f"Selected: {sb_res}", TEAL)

    tab  = self._tabs.active
    rect = self.lay.main_rect

    if tab == 0:
        res = self._profile.on_event(event, rect)
        if res:
            label, val, meta = res
            self._edit.open(label, val, meta)

    elif tab == 1:
        self._sysmap.on_event(event, rect)

    elif tab == 2:
        res = self._eventlog.on_event(event, rect, self.sm.state)
        if res:
            if res.startswith("approve:") or res.startswith("delete:"):
                self._mark_dirty(); self.sm.autosave()
                self._eventlog.rebuild(self.sm.state,
                    self._cur_nation["name"] if self._cur_nation else None)
                set_status(res.replace(":", ": "), TEAL)
            elif res.startswith("edit:"):
                eid = res.split(":")[1]
                ev  = next((e for e in self.sm.state.get("events",[])
                             if e["event_id"]==eid), None)
                if ev:
                    self._edit.open(f"Event body [{eid}]", ev["body"],
                                    {"path": ["__event_body__", eid], "type": "str"})

    elif tab == 3:
        res = self._market.on_event(event, rect, self.sm.state)
        if res:
            rname, cur_mod, field = res
            if rname == "__fluctuate__":
                self._mark_dirty(); self.sm.autosave()
                set_status("Market fluctuated.", GOLD)
            else:
                self._edit.open(f"{rname} {field}", f"{cur_mod:.3f}",
                                {"path": ["__market__", rname, field], "type": "float"})
    return None

# Bind the extended handler & run loop onto App
App._handle_event_full = _handle_event_full
App.run = _patched_run


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    state_file = sys.argv[1] if len(sys.argv) > 1 else "carmine_state.json"
    App(state_file).run()
