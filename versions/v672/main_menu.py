#!/usr/bin/env python3
"""
Carmine NRP Engine - Main Menu v672
Entry point. Scans for save files, lets the GM pick one, then launches the engine.
Run this instead of vAlpha0.6.71.py directly.
"""
import sys, os, json, math, time, random
import pygame
from pathlib import Path

# ── resolve engine dir ─────────────────────────────────────────────────────────
HERE = Path(__file__).parent

# ── palette (matches engine) ───────────────────────────────────────────────────
BG      = (8, 12, 20)
PANEL   = (12, 18, 28)
BORDER  = (28, 52, 80)
BORDER2 = (44, 86, 128)
ACCENT  = (190, 38, 25)
CYAN    = (0, 190, 214)
TEAL    = (0, 138, 158)
TEXT    = (198, 226, 246)
DIM     = (84, 114, 136)
DIM2    = (50, 72, 92)
BRIGHT  = (238, 248, 255)
GREEN   = (22, 184, 82)
RED_C   = (216, 54, 40)
GOLD    = (198, 150, 22)
SEL     = (18, 40, 65)
HOVER   = (14, 30, 50)
BTNACC  = (140, 24, 16)
BTNACC2 = (190, 38, 25)

SW, SH  = 1280, 720
FPS     = 60

# ── helpers ────────────────────────────────────────────────────────────────────
def gf(size, mono=True):
    try:
        name = "Courier New" if mono else "Segoe UI"
        return pygame.font.SysFont(name, size, bold=False)
    except Exception:
        return pygame.font.SysFont("monospace" if mono else "sans", size)

def draw_text(surf, txt, x, y, font, col=TEXT, clip=None):
    s = font.render(str(txt), True, col)
    if clip:
        surf.set_clip(clip)
    surf.blit(s, (x, y))
    if clip:
        surf.set_clip(None)

def draw_rect(surf, rect, col, border=0, radius=4):
    if border:
        pygame.draw.rect(surf, col, rect, border, border_radius=radius)
    else:
        pygame.draw.rect(surf, col, rect, border_radius=radius)

def lerp_col(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

# ── star field ─────────────────────────────────────────────────────────────────
class StarField:
    def __init__(self, n=180):
        rng = random.Random(42)
        self.stars = [
            (rng.randint(0, SW), rng.randint(0, SH),
             rng.uniform(0.3, 1.0), rng.uniform(0.2, 0.6))
            for _ in range(n)
        ]
        self.t = 0.0

    def draw(self, surf, dt):
        self.t += dt
        for x, y, brightness, speed in self.stars:
            pulse = 0.5 + 0.5 * math.sin(self.t * speed * 2.0)
            alpha = int(brightness * pulse * 200)
            r = 1 if brightness < 0.6 else 2
            c = (alpha, alpha, min(255, alpha + 40))
            pygame.draw.circle(surf, c, (int(x), int(y)), r)

# ── save file scanner ──────────────────────────────────────────────────────────
def scan_saves(directory: Path):
    """Return list of dicts with path, name, turn, year, nations."""
    saves = []
    for f in sorted(directory.glob("carmine_state_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        entry = {"path": str(f), "name": f.name, "turn": "?", "year": "?", "nations": "?", "mtime": f.stat().st_mtime}
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            turn = data.get("turn", 1)
            year = 2200 + (turn - 1) * 0.25
            q = ((turn - 1) % 4) + 1
            yr = int(year)
            entry["turn"]    = turn
            entry["year"]    = f"Y{yr} Q{q}"
            entry["nations"] = len(data.get("nations", {}))
        except Exception:
            pass
        saves.append(entry)
    return saves

# ── button ─────────────────────────────────────────────────────────────────────
class MenuButton:
    def __init__(self, rect, label, sublabel="", accent=False):
        self.rect     = pygame.Rect(rect)
        self.label    = label
        self.sublabel = sublabel
        self.accent   = accent
        self.hovered  = False
        self._anim    = 0.0

    def update(self, dt):
        target = 1.0 if self.hovered else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def on_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                return True
        return False

    def draw(self, surf, f_main, f_sub):
        t   = self._anim
        bg  = lerp_col(PANEL, SEL, t)
        bdr = lerp_col(BORDER, BORDER2 if not self.accent else BTNACC2, t)
        draw_rect(surf, self.rect, bg, radius=6)
        draw_rect(surf, self.rect, bdr, border=1, radius=6)
        lx = self.rect.x + 18
        cy = self.rect.centery
        if self.sublabel:
            th = f_main.get_height() + 2 + f_sub.get_height()
            draw_text(surf, self.label, lx, cy - th//2, f_main,
                      BRIGHT if t > 0.3 else TEXT)
            draw_text(surf, self.sublabel, lx, cy - th//2 + f_main.get_height() + 2,
                      f_sub, DIM)
        else:
            draw_text(surf, self.label, lx, cy - f_main.get_height()//2, f_main,
                      RED_C if self.accent else (BRIGHT if t > 0.3 else TEXT))

# ── save entry row ─────────────────────────────────────────────────────────────
class SaveRow:
    def __init__(self, rect, save_dict, index):
        self.rect   = pygame.Rect(rect)
        self.save   = save_dict
        self.index  = index
        self.hovered = False
        self._anim   = 0.0

    def update(self, dt):
        target = 1.0 if self.hovered else 0.0
        self._anim += (target - self._anim) * min(1.0, dt * 12)

    def on_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                return True
        return False

    def draw(self, surf, selected, f_main, f_sub):
        t   = self._anim
        is_sel = selected == self.index
        bg  = SEL if is_sel else lerp_col(PANEL, HOVER, t)
        bdr = CYAN if is_sel else lerp_col(BORDER, BORDER2, t)
        draw_rect(surf, self.rect, bg, radius=4)
        draw_rect(surf, self.rect, bdr, border=1, radius=4)

        s = self.save
        x, y = self.rect.x + 12, self.rect.y + 6
        draw_text(surf, s["name"], x, y, f_main, BRIGHT if is_sel else TEXT)
        meta = f"Turn {s['turn']}  ·  {s['year']}  ·  {s['nations']} nations"
        draw_text(surf, meta, x, y + f_main.get_height() + 2, f_sub, CYAN if is_sel else DIM)

# ── screens ────────────────────────────────────────────────────────────────────
class MainMenuScreen:
    """Title screen with New Game / Load Game / Exit."""
    def __init__(self, saves):
        self.saves   = saves
        self.f_title = gf(42, mono=False)
        self.f_sub   = gf(14, mono=False)
        self.f_main  = gf(16)
        self.f_hint  = gf(13)
        self.stars   = StarField()
        self._t      = 0.0

        bw, bh = 340, 54
        cx = SW // 2 - bw // 2
        self.btn_load = MenuButton((cx, 310, bw, bh), "LOAD GAME",
                                   sublabel=f"{len(saves)} save file(s) found")
        self.btn_new  = MenuButton((cx, 378, bw, bh), "NEW GAME",
                                   sublabel="Start from default state")
        self.btn_exit = MenuButton((cx, 446, bw, bh), "EXIT", accent=True)

    def on_event(self, ev):
        for btn in (self.btn_load, self.btn_new, self.btn_exit):
            if btn.on_event(ev):
                if btn is self.btn_load:
                    return "goto_load"
                if btn is self.btn_new:
                    default = str(HERE / "carmine_state_T5_Y2201Q1.json")
                    return ("launch", default)
                if btn is self.btn_exit:
                    return "quit"
        return None

    def update(self, dt):
        self._t += dt
        for btn in (self.btn_load, self.btn_new, self.btn_exit):
            btn.update(dt)

    def draw(self, surf, dt):
        surf.fill(BG)
        self.stars.draw(surf, dt)

        # decorative top line
        pygame.draw.line(surf, TEAL, (120, 180), (SW - 120, 180), 1)
        pygame.draw.line(surf, BORDER, (120, 184), (SW - 120, 184), 1)

        # title
        pulse = 0.85 + 0.15 * math.sin(self._t * 1.2)
        col   = tuple(int(c * pulse) for c in CYAN)
        title = self.f_title.render("CARMINE NRP ENGINE", True, col)
        surf.blit(title, (SW//2 - title.get_width()//2, 110))

        ver = self.f_sub.render("vAlpha 0.6.71  ·  Galactic Year 2201", True, DIM)
        surf.blit(ver, (SW//2 - ver.get_width()//2, 162))

        for btn in (self.btn_load, self.btn_new, self.btn_exit):
            btn.draw(surf, self.f_main, self.f_hint)

        hint = self.f_hint.render("[ run main_menu.py to start ]", True, DIM2)
        surf.blit(hint, (SW//2 - hint.get_width()//2, SH - 32))


class LoadGameScreen:
    """Scrollable list of detected save files."""
    def __init__(self, saves):
        self.saves    = saves
        self.f_title  = gf(20)
        self.f_main   = gf(15)
        self.f_sub    = gf(12)
        self.f_hint   = gf(13)
        self.stars    = StarField()
        self.selected = 0
        self.scroll   = 0
        self._rows    = []
        self._rebuild_rows()

        bw, bh = 160, 36
        self.btn_back   = MenuButton((40, SH - 58, bw, bh),   "← BACK")
        self.btn_launch = MenuButton((SW - 40 - bw, SH - 58, bw, bh), "LAUNCH →")

    # row geometry
    ROW_H   = 52
    ROW_GAP = 6
    LIST_X  = 80
    LIST_W  = SW - 160
    LIST_Y  = 80
    LIST_H  = SH - 80 - 70  # leave room for buttons

    def _rebuild_rows(self):
        self._rows = []
        for i, s in enumerate(self.saves):
            y = self.LIST_Y + i * (self.ROW_H + self.ROW_GAP) - self.scroll
            r = pygame.Rect(self.LIST_X, y, self.LIST_W, self.ROW_H)
            self._rows.append(SaveRow(r, s, i))

    def on_event(self, ev):
        if ev.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - ev.y * 30)
            self._rebuild_rows()

        if self.btn_back.on_event(ev):
            return "goto_main"
        if self.btn_launch.on_event(ev):
            if self.saves:
                return ("launch", self.saves[self.selected]["path"])

        for row in self._rows:
            if row.on_event(ev):
                self.selected = row.index
        return None

    def update(self, dt):
        self._rebuild_rows()
        for row in self._rows:
            row.update(dt)
        self.btn_back.update(dt)
        self.btn_launch.update(dt)

    def draw(self, surf, dt):
        surf.fill(BG)
        self.stars.draw(surf, dt)

        draw_text(surf, "SELECT SAVE FILE", self.LIST_X, 36, self.f_title, CYAN)

        clip = pygame.Rect(self.LIST_X - 4, self.LIST_Y - 4,
                           self.LIST_W + 8, self.LIST_H + 8)
        surf.set_clip(clip)
        for row in self._rows:
            if row.rect.bottom < self.LIST_Y or row.rect.top > self.LIST_Y + self.LIST_H:
                continue
            row.draw(surf, self.selected, self.f_main, self.f_sub)
        surf.set_clip(None)

        # dividers
        pygame.draw.line(surf, BORDER, (self.LIST_X, self.LIST_Y - 2),
                         (self.LIST_X + self.LIST_W, self.LIST_Y - 2), 1)
        pygame.draw.line(surf, BORDER, (self.LIST_X, self.LIST_Y + self.LIST_H),
                         (self.LIST_X + self.LIST_W, self.LIST_Y + self.LIST_H), 1)

        if not self.saves:
            msg = self.f_main.render("No carmine_state_*.json files found in this directory.", True, DIM)
            surf.blit(msg, (SW//2 - msg.get_width()//2, SH//2))

        self.btn_back.draw(surf, self.f_main, self.f_hint)
        self.btn_launch.draw(surf, self.f_main, self.f_hint)

        if self.saves:
            sel = self.saves[self.selected]
            hint_txt = f"Selected: {sel['name']}  ·  {sel['year']}"
        else:
            hint_txt = "No saves available."
        hint = self.f_hint.render(hint_txt, True, DIM)
        surf.blit(hint, (SW//2 - hint.get_width()//2, SH - 22))


# ── main ───────────────────────────────────────────────────────────────────────
def run_menu():
    pygame.init()
    pygame.display.set_caption("Carmine NRP Engine – Main Menu")
    surf  = pygame.display.set_mode((SW, SH))
    clock = pygame.time.Clock()

    saves = scan_saves(HERE)

    screen_name = "main"
    screens = {
        "main": MainMenuScreen(saves),
        "load": LoadGameScreen(saves),
    }

    while True:
        dt = clock.tick(FPS) / 1000.0
        screen = screens[screen_name]

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            result = screen.on_event(ev)
            if result == "quit":
                pygame.quit(); sys.exit()
            elif result == "goto_load":
                screen_name = "load"
            elif result == "goto_main":
                screen_name = "main"
            elif isinstance(result, tuple) and result[0] == "launch":
                filepath = result[1]
                pygame.quit()
                _launch_engine(filepath)
                return  # engine took over; we're done

        screen.update(dt)
        screen.draw(surf, dt)
        pygame.display.flip()


def _launch_engine(filepath: str):
    """Import and run the engine with the chosen save file."""
    import importlib.util, sys as _sys
    engine_path = str(HERE / "engine.py")
    spec = importlib.util.spec_from_file_location("carmine_engine", engine_path)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    engine.main(filepath)


if __name__ == "__main__":
    run_menu()