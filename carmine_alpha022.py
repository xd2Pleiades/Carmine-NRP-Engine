#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║  Carmine NRP Engine — vAlpha0.2.2            ║
║  State Manager | Discord Profiles | Settle.  ║
╚══════════════════════════════════════════════╝
Features:
  • JSON state load / save with 5-slot backup rotation
  • Autosave on destructive operations
  • Discord-formatted National Profile generator
  • Settlement & district initializer from production values
"""

import json
import os
import shutil
import math
import random
from pathlib import Path
from typing import Optional

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BACKUP_COUNT = 5
DEFAULT_STATE = "carmine_state_T5_Y2201Q1.json"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FORMATTING HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fmt_cr(v: float) -> str:
    """Format a credits value with appropriate suffix."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e15:
        return f"{v/1e15:.3f} Qcr"
    elif a >= 1e12:
        return f"{v/1e12:.3f} Tcr"
    elif a >= 1e9:
        return f"{v/1e9:.3f} Bcr"
    elif a >= 1e6:
        return f"{v/1e6:.3f} Mcr"
    elif a >= 1e3:
        return f"{v/1e3:.2f} Kcr"
    return f"{v:.0f} cr"


def fmt_pop(v: float) -> str:
    """Format population with suffix."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:.3f}B"
    elif a >= 1e6:
        return f"{v/1e6:.3f}M"
    elif a >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:.0f}"


def fmt_res(v: float) -> str:
    """Format a resource quantity."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e12:
        return f"{v/1e12:.3f}T"
    elif a >= 1e9:
        return f"{v/1e9:.3f}B"
    elif a >= 1e6:
        return f"{v/1e6:.3f}M"
    elif a >= 1e3:
        return f"{v/1e3:.2f}K"
    return f"{v:.2f}"


def bar_graph(pct: float, width: int = 18) -> str:
    """ASCII progress bar — pct should be 0.0–1.0."""
    pct = max(0.0, min(1.0, pct))
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


def pad(s: str, n: int) -> str:
    return str(s)[:n].ljust(n)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE MANAGER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StateManager:
    """
    Loads/saves the Carmine JSON state.
    Maintains a 5-slot rotating backup system:
      state.json
      state.backup1.json  ← most recent previous save
      state.backup2.json
      ...
      state.backup5.json  ← oldest kept
    When saving, backup5 is discarded, everything shifts +1,
    and the current file becomes backup1 before the new state is written.
    """

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.state: dict = {}
        self._dirty: bool = False

    # ── I/O ──────────────────────────────────

    def load(self) -> bool:
        if not self.filepath.exists():
            print(f"  [ERROR] File not found: {self.filepath}")
            return False
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.state = json.load(f)
        t = self.state.get("turn", "?")
        y = self.state.get("year", "?")
        q = self.state.get("quarter", "?")
        print(f"  [OK] Loaded: {self.filepath.name}  (T{t} Y{y}Q{q})")
        self._dirty = False
        return True

    def save(self, filepath: Optional[str] = None) -> bool:
        target = Path(filepath) if filepath else self.filepath
        self._rotate_backups(target)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)
        self._dirty = False
        print(f"  [OK] Saved → {target.name}")
        return True

    def autosave(self) -> bool:
        """Save immediately. Called after any mutation."""
        return self.save()

    def mark_dirty(self):
        self._dirty = True

    # ── BACKUP ROTATION ───────────────────────

    def _rotate_backups(self, target: Path):
        parent = target.parent
        stem   = target.stem
        ext    = target.suffix

        def backup_path(n: int) -> Path:
            return parent / f"{stem}.backup{n}{ext}"

        # Drop slot 5, shift 4→5, 3→4, 2→3, 1→2
        for i in range(BACKUP_COUNT, 0, -1):
            src = backup_path(i)
            dst = backup_path(i + 1)
            if i == BACKUP_COUNT:
                if src.exists():
                    src.unlink()   # oldest slot gone
            else:
                if src.exists():
                    shutil.copy2(src, dst)

        # Current file → backup1
        if target.exists():
            shutil.copy2(target, backup_path(1))

    # ── QUERIES ──────────────────────────────

    def get_nation(self, name: str) -> Optional[dict]:
        for n in self.state.get("nations", []):
            if n["name"].lower() == name.lower():
                return n
        return None

    def nation_names(self) -> list:
        return [n["name"] for n in self.state.get("nations", [])]

    def trade_routes(self) -> list:
        return self.state.get("trade_routes", [])

    def market(self) -> dict:
        return self.state.get("market", {})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ECONOMIC CALCULATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def years_elapsed(state: dict) -> float:
    """
    Each turn = 1 quarter = 0.25 years.
    Turn 1 = Q1 base_year → elapsed = 0.
    """
    turn = state.get("turn", 1)
    return (turn - 1) * 0.25


def current_ipeu(nation: dict, ye: float) -> float:
    base   = nation.get("base_ipeu", 0.0)
    growth = nation.get("ipeu_growth", 0.0)
    return base * (1.0 + growth) ** ye


def current_population(nation: dict, ye: float) -> float:
    pop    = nation.get("population", 0.0)
    growth = nation.get("pop_growth", 0.0)
    return pop * (1.0 + growth) ** ye


def compute_trade(nation: dict, trade_routes: list) -> dict:
    """
    Compute trade revenue for a nation.
    Exporters receive credits_per_turn MINUS transit taxes they owe.
    Transit nations receive their tax slice.
    Importers pay credits_per_turn (shown as cost).
    """
    name = nation["name"]
    exports        = 0.0
    imports        = 0.0
    transit_income = 0.0
    transit_paid   = 0.0
    export_routes  = []
    import_routes  = []

    for route in trade_routes:
        if route.get("status") != "active":
            continue
        credits  = route.get("credits_per_turn", 0.0)
        transits = route.get("transit_nations", [])

        if route["exporter"] == name:
            tax_out = sum(credits * t.get("tax_rate", 0.0)
                          for t in transits if t.get("status") == "active")
            net_export = credits - tax_out
            exports      += net_export
            transit_paid += tax_out
            export_routes.append({
                "id": route["id"], "name": route.get("name",""),
                "importer": route["importer"],
                "resource": route["resource"],
                "credits": net_export
            })

        if route["importer"] == name:
            imports += credits
            import_routes.append({
                "id": route["id"], "name": route.get("name",""),
                "exporter": route["exporter"],
                "resource": route["resource"],
                "credits": credits
            })

        for t in transits:
            if t.get("nation") == name and t.get("status") == "active":
                inc = credits * t.get("tax_rate", 0.0)
                transit_income += inc

    return {
        "exports":        exports,
        "imports":        imports,
        "transit_income": transit_income,
        "transit_paid":   transit_paid,
        "net":            exports - imports + transit_income,
        "export_routes":  export_routes,
        "import_routes":  import_routes,
    }


def compute_resources(nation: dict, ipeu: float) -> dict:
    """
    Return per-resource dict with production/consumption/net/trend.
    Uses flat values when mode='flat', otherwise marks as 'derived (est.)'.
    """
    expenditure = nation.get("expenditure", {})
    resources_out = {}

    RESOURCE_NAMES = ["Food", "Minerals", "Energy", "Alloys", "Consumer Goods"]

    for rname in RESOURCE_NAMES:
        sd = nation.get("resource_stockpiles", {}).get(rname, {})
        mode      = sd.get("production_mode", "derived")
        stockpile = sd.get("stockpile", 0.0)

        if mode == "flat":
            prod = sd.get("flat_production", 0.0)
            cons = sd.get("flat_consumption", 0.0)
            estimated = False
        else:
            # Estimate from IPEU slices — approximations only
            agri  = expenditure.get("Agriculture", 0.0) * ipeu
            ind   = expenditure.get("Industry",    0.0) * ipeu

            food_eff  = nation.get("food_efficiency",      1.0)
            food_cons = nation.get("food_consumption_rate",0.1)
            cg_eff    = nation.get("cg_efficiency",        1.0)
            cg_cons   = nation.get("cg_consumption_rate",  0.1)
            min_pct   = nation.get("mineral_workforce_pct",0.3)
            min_fac   = nation.get("mineral_ipeu_factor",  0.05)
            alloy_r   = nation.get("mineral_to_alloy_ratio",0.5)
            pop       = nation.get("population", 1.0)

            if rname == "Food":
                prod = agri * food_eff / 1e6
                cons = pop  * food_cons
            elif rname == "Minerals":
                prod = ind * min_pct * min_fac / 1e3
                cons = prod * 0.4
            elif rname == "Energy":
                prod = ind * 0.002 / 1e3
                cons = prod * 0.6
            elif rname == "Alloys":
                prod = ind * alloy_r * 0.001 / 1e3
                cons = prod * 0.3
            elif rname == "Consumer Goods":
                prod = ind * cg_eff * 0.0005 / 1e3
                cons = pop * cg_cons
            else:
                prod = cons = 0.0

            estimated = True

        net   = prod - cons
        trend = "▲ Surplus" if net > 0 else ("▼ Deficit" if net < 0 else "─ Stable")

        resources_out[rname] = {
            "stockpile":   stockpile,
            "production":  prod,
            "consumption": cons,
            "net":         net,
            "trend":       trend,
            "estimated":   estimated,
        }

    return resources_out


def compute_debt(nation: dict, ipeu: float) -> dict:
    balance    = nation.get("debt_balance",  0.0)
    rate       = nation.get("interest_rate", 0.0)
    repayment  = nation.get("debt_repayment",0.0)
    q_interest = balance * rate / 4.0 if balance > 0 else 0.0
    load_pct   = (balance / ipeu * 100) if ipeu > 0 else 0.0
    return {
        "balance":    balance,
        "rate":       rate,
        "repayment":  repayment,
        "q_interest": q_interest,
        "load_pct":   load_pct,
        "is_debtor":  balance > 0,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DISCORD PROFILE FORMATTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def format_discord_profile(nation: dict, state: dict) -> str:
    """
    Generate a Discord-ready monospace National Profile block.
    Wrap in triple-backtick for fixed-width rendering on Discord.
    """
    ye   = years_elapsed(state)
    ipeu = current_ipeu(nation, ye)
    pop  = current_population(nation, ye)
    trade     = compute_trade(nation, state.get("trade_routes", []))
    resources = compute_resources(nation, ipeu)
    debt      = compute_debt(nation, ipeu)

    turn    = state.get("turn",    "?")
    year    = state.get("year",    "?")
    quarter = state.get("quarter", "?")

    expenditure   = nation.get("expenditure", {})
    research_bgt  = nation.get("research_budget", 0.0)
    strategic_fund= nation.get("strategic_fund",  0.0)

    exp_credits   = {k: v * ipeu for k, v in expenditure.items()}
    total_exp     = sum(exp_credits.values()) + research_bgt
    net_balance   = ipeu + trade["net"] - total_exp - debt["q_interest"]

    species       = nation.get("species_populations", [])
    star_systems  = nation.get("star_systems", [])
    afd           = nation.get("active_forces_detail", [])
    if not isinstance(afd, list):
        afd = []
    unit_groups   = {ug["ugid"]: ug for ug in nation.get("unit_groups", [])}

    active_research  = nation.get("active_research_projects", [])
    completed_techs  = nation.get("completed_techs", [])
    projects         = [p for p in nation.get("projects", [])
                        if p.get("status") in ("active", "in_progress")]

    L = []  # output lines

    def ln(s=""):
        L.append(s)

    # ── HEADER ──────────────────────────────────────────────────────────
    W = 62
    ln("```")
    ln("╔" + "═"*W + "╗")
    title = f"  NATIONAL PROFILE — Turn {turn} | {year} Q{quarter}"
    ln("║" + title.ljust(W) + "║")
    sub   = f"  {nation['name']}"
    ln("║" + sub.ljust(W) + "║")
    ln("╚" + "═"*W + "╝")
    ln()

    # ── PROFILE OVERVIEW ────────────────────────────────────────────────
    home_system = "—"
    home_planet = "—"
    for sys in star_systems:
        note = sys.get("notes", "").lower()
        if "home" in note or "capital" in note or home_system == "—":
            home_system = sys["name"]
            for pl in sys.get("planets", []):
                if pl.get("settlements") and home_planet == "—":
                    home_planet = pl["name"]
            break

    species_line = ", ".join(
        f"{s['name']} ({s.get('status','?').title()})" for s in species
    ) if species else "—"

    ln(f"  Species          : {species_line}")
    ln(f"  Population       : {fmt_pop(pop)}")
    ln(f"  Pop Growth       : {nation.get('pop_growth',0)*100:.2f}% / yr")
    ln(f"  Home System      : {home_system}")
    ln(f"  Home Planet      : {home_planet}")
    ln()

    # ── ECONOMY ─────────────────────────────────────────────────────────
    ln("# ECONOMY")
    ln(f"  IPEU (current)   : {fmt_cr(ipeu)}")
    ln(f"  IPEU Growth      : {nation.get('ipeu_growth',0)*100:.2f}% / yr")
    ln(f"  IPEU per Capita  : {fmt_cr(ipeu/pop) if pop else '—'}")
    ln(f"  Trade Revenue    : {fmt_cr(trade['net'])}")
    ln(f"   - Exports       : {fmt_cr(trade['exports'])}")
    ln(f"   - Imports       : {fmt_cr(-trade['imports'])}")
    if trade["transit_income"] > 0:
        ln(f"   - Transit Inc.  : {fmt_cr(trade['transit_income'])}")
    ln(f"  Research Budget  : {fmt_cr(research_bgt)}")
    ln(f"  Total Expenditure: {fmt_cr(total_exp)}")
    ln(f"  Net Balance      : {fmt_cr(net_balance)}")
    ln()

    # ── EXPENDITURE BREAKDOWN ────────────────────────────────────────────
    ln("## EXPENDITURE & BREAKDOWN")
    max_pct = max(expenditure.values(), default=0.01)
    exp_total_pct = sum(expenditure.values())
    for cat, pct in expenditure.items():
        amt     = exp_credits[cat]
        bg      = bar_graph(pct / max_pct)
        ln(f"  {pad(cat,26)} {pct*100:5.1f}%  {bg}  {fmt_cr(amt)}")
    ln(f"  {'─'*W}")
    ln(f"  {'TOTAL':<26} {exp_total_pct*100:5.1f}%  {'':18}  {fmt_cr(total_exp)}")
    ln()

    # ── ECONOMIC PROJECTS ────────────────────────────────────────────────
    ln("## ECONOMIC PROJECTS")
    if projects:
        for p in projects:
            turns_left = p.get("duration_turns", 0) - p.get("turns_elapsed", 0)
            ln(f"  [{p.get('category','?')}] {p['name']}")
            ln(f"    Cost: {fmt_cr(p.get('cost',0))}  |  {turns_left}t remaining")
    else:
        ln("  None active")
    ln(f"  {'─'*W}")
    ln()

    # ── FISCAL REPORT ────────────────────────────────────────────────────
    ln("## FISCAL REPORT")
    status_str = "Debtor" if debt["is_debtor"] else "Creditor"
    ln(f"  Debtor / Creditor    : {status_str}")
    ln(f"  Debt Balance         : {fmt_cr(debt['balance'])}")
    ln(f"  Debt Load            : {debt['load_pct']:.1f}%")
    ln(f"  Interest Rate        : {debt['rate']*100:.2f}%")
    ln(f"  Quarterly Int.       : {fmt_cr(debt['q_interest'])}")
    ln(f"  Debt Repayment       : {fmt_cr(debt['repayment'])}")
    ln(f"  {'─'*W}")
    ln(f"  Strategic Fund   : {fmt_cr(strategic_fund)}")
    ln()

    # ── RESOURCES & STOCKPILES ───────────────────────────────────────────
    ln("## RESOURCES & STOCKPILES")
    RES_ICONS = {
        "Food":           "🌾",
        "Minerals":       "⛏",
        "Energy":         "⚡",
        "Alloys":         "🔩",
        "Consumer Goods": "📦",
    }
    for rname, rd in resources.items():
        icon    = RES_ICONS.get(rname, "•")
        est_tag = " [est.]" if rd["estimated"] else ""
        ln(f"  {rname}{est_tag}")
        ln(f"    Stockpile           : {fmt_res(rd['stockpile'])}")
        ln(f"    Food Production/turn: {fmt_res(rd['production'])}"
           .replace("Food Production", f"{rname} Production"))
        ln(f"    Consumption/turn    : {fmt_res(rd['consumption'])}")
        ln(f"    Net per turn        : {fmt_res(rd['net'])}  {rd['trend']}")
        ln()

    # ── TERRITORIES ──────────────────────────────────────────────────────
    ln("# TERRITORIES")
    if star_systems:
        for sys in star_systems:
            coord = sys.get("coordinates","") or "—"
            ln(f"  System: {sys['name']}  [{coord}]  {sys.get('notes','')}")
            for planet in sys.get("planets", []):
                ln(f"    Planet : {planet['name']} | Climate: {planet.get('climate','?')}")
                ln(f"      Colonization: {planet.get('colonization_pct',0):.0f}%"
                   f"  Urban: {planet.get('urbanization_pct',0):.0f}%"
                   f"  Industrial: {planet.get('industrialization_pct',0):.0f}%")
                settlements = planet.get("settlements", [])
                if settlements:
                    for s in settlements:
                        s_pop = s.get("population", 0)
                        loy   = s.get("loyalty", 0)
                        amen  = s.get("amenities", 0)
                        ln(f"      Settlement: {s['name']}")
                        ln(f"        Pop: {fmt_pop(s_pop)}"
                           f"  Loyalty: {loy:.0f}%"
                           f"  Amenities: {amen:.0f}%")
                        dcounts: dict = {}
                        for d in s.get("districts", []):
                            dtype = d.get("type", "?")
                            dcounts[dtype] = dcounts.get(dtype, 0) + 1
                        if dcounts:
                            dist_str = "  ".join(f"{t}×{c}" for t, c in dcounts.items())
                            ln(f"        Districts: {dist_str}")
                else:
                    ln("      No settlements")
    else:
        ln("  No territorial data")
    ln()

    # ── NATIONAL DEMOGRAPHICS ────────────────────────────────────────────
    ln("# NATIONAL DEMOGRAPHICS")
    ln(f"  Total Population     : {fmt_pop(pop)}")
    ln(f"  Loyalty Modifier     : {nation.get('loyalty_modifier_cg', 1.0):.2f}")
    ln()
    for s in species:
        is_dom = s.get("status", "") in ("dominant", "majority")
        crown  = "👑" if is_dom else "  "
        ln(f"  {crown} {s['name']}")
        ln(f"    Population       : {fmt_pop(s.get('population', 0))}")
        ln(f"    Share            : {s.get('status','?').title()}")
        ln(f"    Growth Rate      : {s.get('growth_rate', 0)*100:.2f}% / yr")
        ln(f"    Culture          : {s.get('culture', '—')}")
        ln(f"    Language         : {s.get('language', '—')}")
        ln(f"    Religion         : {s.get('religion', '—')}")
        ln(f"    Loyalty          : {s.get('loyalty', '—')}")
        ln()

    # ── MILITARY ─────────────────────────────────────────────────────────
    ln("# MILITARY")

    CAT_SECTIONS = [
        ("## SPACEFLEET",       ["Spacefleet", "Navy"]),
        ("## AEROSPACE FORCES", ["Air Force",  "Aerospace"]),
        ("## GROUND FORCES",    ["Ground Forces","Ground","Army"]),
    ]

    for section_label, cats in CAT_SECTIONS:
        units_in_cat = [u for u in afd if u.get("category") in cats]
        ln(section_label)
        if units_in_cat:
            # Group by ugid → unit group name, else "Fleet" / "Wing" / "Division"
            grouped: dict = {}
            for u in units_in_cat:
                ugid = u.get("ugid")
                if ugid and ugid in unit_groups:
                    grp_name = unit_groups[ugid]["name"]
                else:
                    grp_name = "—"
                grouped.setdefault(grp_name, []).append(u)

            for grp_name, units in grouped.items():
                if grp_name != "—":
                    ln(f"  {grp_name}")
                for u in units:
                    cname = u.get("custom_name") or u["unit"]
                    vet   = u.get("veterancy", "?")
                    cnt   = u.get("count", 1)
                    ln(f"    - {cname} | ×{cnt} | {vet}")
        else:
            ln("  None on record")
        ln()

    # ── RESEARCH ─────────────────────────────────────────────────────────
    ln("# RESEARCH")
    ln(f"  RP Budget/turn   : {fmt_cr(research_bgt)}")
    ln()

    if active_research:
        ln("  Active Projects:")
        for proj in active_research:
            prog = proj.get("progress", 0.0)
            bg   = bar_graph(prog / 100.0)
            ln(f"    [{proj.get('field','?')}] {proj.get('name','?')}")
            ln(f"      Progress: {prog:.1f}%  {bg}")
            if proj.get("benefits"):
                ln(f"      Benefits: {proj['benefits']}")
    else:
        ln("  Active Projects: None")

    ln()
    if completed_techs:
        display = completed_techs[-8:]  # last 8
        ln(f"  Completed ({len(completed_techs)}):")
        for t in display:
            tname = t if isinstance(t, str) else t.get("name", str(t))
            ln(f"    ✓ {tname}")

    ln()
    ln("```")
    return "\n".join(L)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETTLEMENT INITIALIZER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISTRICT_TYPES = [
    "Residential",
    "Urban",
    "Industrial Civilian",
    "Industrial Military",
    "Agricultural",
    "Mining",
    "Power",
    "Military",
]

# Production effects per district type (used in tooltips / future calcs)
DISTRICT_EFFECTS = {
    "Residential":         "Population capacity",
    "Urban":               "Consumer Goods production",
    "Industrial Civilian": "Alloys + Consumer Goods (50/50)",
    "Industrial Military": "Military production",
    "Agricultural":        "Food production",
    "Mining":              "Minerals production",
    "Power":               "Energy production",
    "Military":            "Military efficiency",
}

# Climate modifiers: weight multipliers per district type
CLIMATE_MODIFIERS = {
    "Temperate": {"Agricultural": 1.4, "Residential": 1.2},
    "Arid":      {"Mining": 1.4, "Power": 1.2},
    "Oceanic":   {"Agricultural": 1.3, "Residential": 1.2},
    "Arctic":    {"Mining": 1.2, "Power": 1.4},
    "Toxic":     {"Industrial Civilian": 1.3, "Industrial Military": 1.3},
    "Jungle":    {"Agricultural": 1.5, "Residential": 0.7},
    "Desert":    {"Mining": 1.5, "Power": 1.3},
}


def _expenditure_weights(nation: dict) -> dict:
    """
    Derive raw district-type preference weights from nation expenditure ratios.
    Heavier military spend → more Military / Industrial Military districts, etc.
    """
    exp = nation.get("expenditure", {})
    mil   = exp.get("Military", 0.1)
    infra = exp.get("Infrastructure", 0.1)
    agri  = exp.get("Agriculture", 0.1)
    ind   = exp.get("Industry", 0.1)
    popd  = exp.get("Population Development", 0.05)

    return {
        "Residential":         1.0 + popd * 8,
        "Urban":               1.0 + popd * 6,
        "Industrial Civilian": 0.5 + ind  * 7,
        "Industrial Military": 0.3 + mil  * 5,
        "Agricultural":        0.5 + agri * 10,
        "Mining":              0.5 + ind  * 4,
        "Power":               0.5 + infra* 5,
        "Military":            0.3 + mil  * 6,
    }


def _apply_climate(weights: dict, climate: str) -> dict:
    """Apply climate modifiers to district weights, return normalized dict."""
    w = dict(weights)
    for dtype, mult in CLIMATE_MODIFIERS.get(climate, {}).items():
        if dtype in w:
            w[dtype] *= mult
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


def _make_settlement(
    name: str,
    nation_name: str,
    population: float,
    climate: str,
    n_districts: int,
    base_weights: dict,
    is_capital: bool = False,
) -> dict:
    """Build a single settlement dict with randomized districts."""
    weights = _apply_climate(base_weights, climate)

    districts = []

    # Capital always anchored with a Residential district
    if is_capital:
        districts.append({
            "type": "Residential",
            "status": "Operational",
            "notes": "Capital district",
            "built_turn": 0,
            "workforce": 0,
        })
        n_districts = max(0, n_districts - 1)

    dtypes   = list(weights.keys())
    dweights = list(weights.values())
    picked   = random.choices(dtypes, weights=dweights, k=n_districts)
    for dtype in picked:
        districts.append({
            "type": dtype,
            "status": "Operational",
            "notes": "",
            "built_turn": 0,
            "workforce": 0,
        })

    amenities     = round(random.uniform(40, 80), 1)
    loyalty       = round(random.uniform(55, 90) if is_capital else random.uniform(45, 80), 1)
    attractiveness= round((amenities + loyalty) / 2 + random.uniform(-5, 8), 2)

    return {
        "name":                name,
        "controlling_nation":  nation_name,
        "population":          round(population),
        "amenities":           amenities,
        "loyalty":             loyalty,
        "attractiveness":      attractiveness,
        "multi_nation_pct":    {},
        "districts":           districts,
    }


def _gen_names(nation_name: str, planet_name: str, count: int) -> list:
    """Generate settlement names — capital first, then varied."""
    PREFIXES  = ["Nova", "New", "Fort", "Port", "Station", "Outpost",
                  "Citadel", "Haven", "Reach", "Gate"]
    SUFFIXES  = ["Prime", "Alpha", "Beta", "Delta", "Sigma", "Omega"]
    n_word    = nation_name.split()[0]
    p_word    = planet_name.split()[0] if planet_name != "N/A" else n_word

    names = []
    if count >= 1:
        names.append(f"{n_word} Capital")
    if count >= 2:
        names.append(f"{random.choice(PREFIXES)} {p_word}")
    for i in range(2, count):
        names.append(f"{p_word} {random.choice(SUFFIXES)}")
    return names[:count]


def initialize_settlements(nation: dict, state: dict, force: bool = False) -> int:
    """
    Auto-populate settlements and districts for all planets in a nation.

    Args:
        nation : the nation dict (mutated in-place)
        state  : global state (for years_elapsed / IPEU)
        force  : if True, re-initialize planets that already have settlements

    Returns:
        number of planets processed
    """
    ye   = years_elapsed(state)
    ipeu = current_ipeu(nation, ye)
    pop  = current_population(nation, ye)

    base_weights = _expenditure_weights(nation)

    star_systems = nation.get("star_systems", [])
    if not star_systems:
        print(f"    [SKIP] {nation['name']}: no star_systems data.")
        return 0

    # Count total planets to distribute population
    all_planets = [
        (sys, planet)
        for sys in star_systems
        for planet in sys.get("planets", [])
    ]
    if not all_planets:
        print(f"    [SKIP] {nation['name']}: no planets found.")
        return 0

    pop_per_planet = pop / len(all_planets)
    processed      = 0
    planet_idx     = 0

    for sys, planet in all_planets:
        existing = planet.get("settlements", [])
        if existing and not force:
            planet_idx += 1
            continue

        if force:
            planet["settlements"] = []

        climate  = planet.get("climate", "Temperate")
        col_pct  = planet.get("colonization_pct", 100.0) / 100.0
        urb_pct  = planet.get("urbanization_pct",  30.0) / 100.0
        planet_pop = pop_per_planet * col_pct

        # Number of settlements scales with colonization
        if col_pct >= 0.8:
            n_settle = random.randint(2, 4)
        elif col_pct >= 0.4:
            n_settle = random.randint(1, 3)
        else:
            n_settle = 1

        # Districts per settlement scales with urbanization
        n_districts = max(3, int(urb_pct * 16) + random.randint(1, 3))

        s_names = _gen_names(nation["name"], planet["name"], n_settle)
        for i, s_name in enumerate(s_names):
            is_cap  = (planet_idx == 0 and i == 0)
            s_pop   = planet_pop / n_settle
            s = _make_settlement(
                name        = s_name,
                nation_name = nation["name"],
                population  = s_pop,
                climate     = climate,
                n_districts = n_districts,
                base_weights= base_weights,
                is_capital  = is_cap,
            )
            planet["settlements"].append(s)

        processed  += 1
        planet_idx += 1

    print(f"    [OK] {nation['name']}: settlements created on {processed} planet(s).")
    return processed


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI MENU HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def menu_pick_nation(sm: StateManager) -> Optional[dict]:
    names = sm.nation_names()
    print()
    for i, n in enumerate(names):
        print(f"  {i+1:3}. {n}")
    try:
        raw = input("\n  Nation # (or partial name): ").strip()
        idx = int(raw) - 1
        if 0 <= idx < len(names):
            return sm.get_nation(names[idx])
    except ValueError:
        # Try partial name match
        low = raw.lower()
        matches = [n for n in names if low in n.lower()]
        if len(matches) == 1:
            return sm.get_nation(matches[0])
        elif matches:
            print("  Ambiguous — matches:")
            for m in matches:
                print(f"    {m}")
    except KeyboardInterrupt:
        pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Carmine NRP Engine — vAlpha0.2.2            ║")
    print("╚══════════════════════════════════════════════╝")

    raw = input(f"\n  State file [{DEFAULT_STATE}]: ").strip()
    filepath = raw if raw else DEFAULT_STATE

    sm = StateManager(filepath)
    if not sm.load():
        print("  Aborting.")
        return

    while True:
        print()
        print("  ─── MAIN MENU ───────────────────────────────")
        print("  [P]  Generate Discord Profile")
        print("  [PA] Generate ALL nation profiles")
        print("  [I]  Initialize Settlements (missing only)")
        print("  [IA] Initialize Settlements — ALL nations")
        print("  [S]  Save state")
        print("  [Q]  Quit")
        print()
        cmd = input("  > ").strip().upper()

        # ── PROFILE ──────────────────────────────────────────
        if cmd == "P":
            nation = menu_pick_nation(sm)
            if not nation:
                print("  [!] Nation not found.")
                continue
            output = format_discord_profile(nation, sm.state)
            print("\n" + output)
            fname = f"profile_{nation['name'].replace(' ','_')}_T{sm.state.get('turn','?')}.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\n  [OK] Saved → {fname}")

        elif cmd == "PA":
            for nation in sm.state.get("nations", []):
                output = format_discord_profile(nation, sm.state)
                fname  = f"profile_{nation['name'].replace(' ','_')}_T{sm.state.get('turn','?')}.txt"
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"  [OK] {nation['name']} → {fname}")

        # ── INIT SETTLEMENTS ─────────────────────────────────
        elif cmd == "I":
            nation = menu_pick_nation(sm)
            if not nation:
                print("  [!] Nation not found.")
                continue
            force = input("  Force re-init existing settlements? [y/N]: ").strip().lower() == "y"
            n = initialize_settlements(nation, sm.state, force=force)
            if n > 0:
                sm.mark_dirty()
                sm.autosave()

        elif cmd == "IA":
            force = input("  Force re-init ALL existing settlements? [y/N]: ").strip().lower() == "y"
            total = 0
            for nation in sm.state.get("nations", []):
                total += initialize_settlements(nation, sm.state, force=force)
            if total > 0:
                sm.mark_dirty()
                sm.autosave()
            print(f"  [OK] Processed {total} planet(s) across all nations.")

        # ── SAVE ─────────────────────────────────────────────
        elif cmd == "S":
            sm.save()

        # ── QUIT ─────────────────────────────────────────────
        elif cmd == "Q":
            if sm._dirty:
                if input("  Unsaved changes — save before quit? [Y/n]: ").strip().lower() != "n":
                    sm.save()
            print("  Goodbye.")
            break

        else:
            print("  [?] Unknown command.")


if __name__ == "__main__":
    main()
