"""
Carmine NRP Engine — vAlpha0.2.2 UI
Pygame GM Tool  |  1280 × 720  |  Sci-Fi Dark Theme
Run: python3 carmine_alpha022_ui.py [state_file.json]

Requires carmine_alpha022.py in the same directory.
"""

import pygame
import sys, os, json, math, time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE IMPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
try:
    from carmine_alpha022 import (
        StateManager, years_elapsed, current_ipeu,
        current_population, compute_trade, compute_resources,
        compute_debt, fmt_cr, fmt_pop, fmt_res,
        initialize_settlements,
    )
except ImportError:
    sys.exit(
        "[FATAL] carmine_alpha022.py not found.\n"
        "Place carmine_alpha022_ui.py in the same directory as carmine_alpha022.py"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYOUT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SW, SH   = 1280, 720
LWIDTH   = 272          # left sidebar
TBAR_H   = 46           # top bar
SBAR_H   = 26           # status bar
SCRL_W   = 10           # scrollbar width
MAIN_X   = LWIDTH
MAIN_Y   = TBAR_H
MAIN_W   = SW - LWIDTH - SCRL_W
MAIN_H   = SH - TBAR_H - SBAR_H
FPS      = 60

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COLOUR PALETTE — Carmine Sci-Fi Dark
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BG        = (  8, 12, 20)
PANEL     = ( 11, 17, 27)
PANEL2    = ( 15, 23, 35)
PANEL3    = ( 18, 28, 42)
BLOCK_BG  = (  7, 13, 21)
BLOCK_ALT = (  9, 16, 25)
BORDER    = ( 26, 50, 76)
BORDER2   = ( 42, 82,122)
ACCENT    = (190, 38, 25)    # Carmine red
ACCENT2   = (130, 22, 16)
CYAN      = (  0,190,214)
TEAL      = (  0,138,158)
TEAL2     = (  0,100,118)
TEXT      = (198,226,246)
DIM       = ( 84,114,136)
DIM2      = ( 55, 80,100)
BRIGHT    = (238,248,255)
GREEN     = ( 22,184, 82)
GREEN2    = ( 14,120, 54)
RED_C     = (216, 54, 40)
RED2      = (140, 28, 20)
GOLD      = (198,150, 22)
GOLD2     = (140,100, 12)
SELECTED  = ( 18, 40, 65)
HOVER     = ( 14, 30, 50)
EDITBG    = (  5, 14, 28)
EDITBDR   = (  0,172,194)
SCRLBG    = (  9, 17, 27)
SCRLTMB   = ( 38, 76,116)
BTNBG     = ( 18, 36, 56)
BTNHOV    = ( 28, 54, 82)
BTNACC    = (130, 24, 16)
BTNACC_H  = (190, 38, 25)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER ITEM TYPES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TN_HDR  = "nation_hdr"
T_HDR1  = "hdr1"
T_HDR2  = "hdr2"
T_ROW   = "row"
T_BAR   = "bar"
T_SEP   = "sep"
T_SPC   = "spc"
T_SPHDR = "species_hdr"
T_DEBT  = "debt_bar"

ROW_H   = 22
HDR1_H  = 36
HDR2_H  = 30
NHDR_H  = 62
SPC_H   =  8
SEP_H   = 10
BAR_H   = 22
SPHDR_H = 28
DEBT_H  = 22

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def nation_tag(name: str) -> str:
    """Derive 2-4 char abbreviation."""
    stop = {"of","the","and","or","for","in","to","a","an",
             "des","du","de","von","van"}
    words = [w for w in name.split() if w.lower() not in stop and w.isalpha()]
    tag = "".join(w[0].upper() for w in words[:4])
    return tag if tag else name[:3].upper()


def fmt_int(v: float) -> str:
    """Format as comma-separated integer."""
    return f"{int(v):,}"


def fmt_pct_plus(v: float) -> str:
    return f"+{v*100:.1f}%" if v >= 0 else f"{v*100:.1f}%"


def loyalty_bar(score: float, width: int = 20) -> str:
    pct    = max(0.0, min(1.0, score / 100.0))
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


def debt_bar_str(pct: float, width: int = 20) -> str:
    filled = round(min(1.0, pct) * width)
    return "▓" * filled + "░" * (width - filled)


def exp_bar_str(pct: float, width: int = 16) -> str:
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


def resource_export_credits(nation_name: str, resource: str, routes: list) -> float:
    total = 0.0
    for route in routes:
        if route.get("status") != "active":
            continue
        if route.get("exporter") == nation_name and route.get("resource") == resource:
            credits = route.get("credits_per_turn", 0.0)
            tax_out = sum(credits * t.get("tax_rate", 0.0)
                          for t in route.get("transit_nations", [])
                          if t.get("status") == "active")
            total += credits - tax_out
    return total

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROFILE → RENDER ITEM LIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_render_items(nation: dict, state: dict) -> List[dict]:
    items: List[dict] = []
    y = 8  # top padding

    def add(item: dict):
        nonlocal y
        item["y"] = y
        items.append(item)
        y += item["h"]

    ye        = years_elapsed(state)
    ipeu_base = nation.get("base_ipeu", 0.0)
    pop       = current_population(nation, ye)
    exp_dict  = nation.get("expenditure", {})
    routes    = state.get("trade_routes", [])
    trade     = compute_trade(nation, routes)
    res_d     = compute_resources(nation, ipeu_base)
    debt_d    = compute_debt(nation, ipeu_base)
    rbudget   = nation.get("research_budget", 0.0)
    sfund     = nation.get("strategic_fund", 0.0)
    star_sys  = nation.get("star_systems", [])
    species   = nation.get("species_populations", [])
    projects  = nation.get("projects", [])
    afd       = nation.get("active_forces_detail", [])
    ug_map    = {u["ugid"]: u for u in nation.get("unit_groups", [])}
    comp_tech = nation.get("completed_techs", [])
    act_res   = nation.get("active_research_projects", [])

    civ_level = nation.get("civ_level",  "Interplanetary Industrial")
    civ_tier  = nation.get("civ_tier",   2)
    eco_status= nation.get("eco_status", "Stable")
    tag       = nation_tag(nation["name"])

    # Homeworld from star_systems
    homeworld = "—"
    for sys in star_sys:
        for planet in sys.get("planets", []):
            homeworld = planet["name"]
            break
        break

    total_exp  = sum(exp_dict.values()) * ipeu_base + rbudget
    net_bal    = ipeu_base + trade["net"] - total_exp - debt_d["q_interest"]
    export_cr  = trade["exports"] + trade["transit_income"]
    fund_delta = -debt_d["q_interest"]

    def em(path, etype, key=None):
        raw = nation.get(key or path[-1], 0) if key != "_none" else 0
        return {"path": path, "type": etype, "raw": raw}

    # ── NATION HEADER ────────────────────────────────────
    add({"type": TN_HDR, "h": NHDR_H, "tag": tag, "name": nation["name"]})
    add({"type": T_SPC,  "h": SPC_H})

    # ── PROFILE OVERVIEW ─────────────────────────────────
    species_str = ", ".join(s["name"] for s in species) if species else "—"
    PROF = [
        ("Species",       species_str,                                          None,               None),
        ("Population",    fmt_pop(pop),                                         "population",       "pop"),
        ("Pop Growth",    fmt_pct_plus(nation.get("pop_growth",0)) + " / yr",  "pop_growth",       "pct"),
        ("Homeworld",     homeworld,                                             None,               None),
        ("Civilisation",  civ_level,                                             "civ_level",        "str"),
        ("Tier",          str(civ_tier),                                         "civ_tier",         "int"),
        ("Status",        eco_status,                                            "eco_status",       "str"),
    ]
    for label, value, key, etype in PROF:
        meta = {"path": [key], "type": etype, "raw": nation.get(key, value)} if key else None
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": label, "value": value, "label_w": 16,
             "editable": meta is not None, "edit_meta": meta,
             "val_color": CYAN if key else TEXT})
    add({"type": T_SPC, "h": SPC_H})

    # ── # ECONOMY ────────────────────────────────────────
    add({"type": T_HDR1, "h": HDR1_H, "text": "# ECONOMY"})
    per_cap = (ipeu_base / pop) if pop else 0
    ECO = [
        ("IPEU (base)",        fmt_cr(ipeu_base),                                           "base_ipeu",      "float"),
        ("IPEU Growth",        fmt_pct_plus(nation.get("ipeu_growth",0)) + " / yr",         "ipeu_growth",    "pct"),
        ("IPEU per Capita",    f"{int(per_cap):,} cr",                                      None,             None),
        ("Export Credits",     fmt_cr(export_cr),                                           None,             None),
        ("Total Expenditure",  f"{fmt_cr(total_exp)}  ({sum(exp_dict.values())*100:.1f}%)", None,             None),
        ("Research Budget",    fmt_cr(rbudget) + " / turn",                                 "research_budget","float"),
        ("Net Balance",        fmt_cr(net_bal),                                             None,             None),
    ]
    for label, value, key, etype in ECO:
        meta  = {"path": [key], "type": etype, "raw": nation.get(key, 0)} if key else None
        vcol  = (GREEN if net_bal >= 0 else RED_C) if label == "Net Balance" else (CYAN if key else TEXT)
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": label, "value": value, "label_w": 18,
             "editable": meta is not None, "edit_meta": meta, "val_color": vcol})
    add({"type": T_SPC, "h": SPC_H})

    # ── ## EXPENDITURE ───────────────────────────────────
    add({"type": T_HDR2, "h": HDR2_H, "text": "## EXPENDITURE & BREAKDOWN"})
    for cat, pct in exp_dict.items():
        meta = {"path": ["expenditure", cat], "type": "pct", "raw": pct}
        add({"type": T_BAR, "h": BAR_H, "in_block": True,
             "label": cat, "pct": pct,
             "amount": fmt_cr(pct * ipeu_base),
             "editable": True, "edit_meta": meta})
    add({"type": T_SEP, "h": SEP_H, "in_block": True})
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "TOTAL",
         "value": f"{sum(exp_dict.values())*100:.1f}%   ({fmt_cr(total_exp)})",
         "label_w": 18, "editable": False, "edit_meta": None, "val_color": GOLD})
    add({"type": T_SPC, "h": SPC_H})

    # ── ## ECONOMIC PROJECTS ─────────────────────────────
    add({"type": T_HDR2, "h": HDR2_H, "text": "## ECONOMIC PROJECTS"})
    all_projs = [p for p in projects if p.get("status") in ("active","in_progress","complete")]
    if all_projs:
        for proj in all_projs:
            done  = proj.get("status") == "complete"
            turns_left = proj.get("duration_turns",0) - proj.get("turns_elapsed",0)
            tag_str = "[COMPLETE]" if done else f"[{turns_left}t left]"
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": f"{proj['name']}  ({proj.get('category','?')})",
                 "value": tag_str, "label_w": 38,
                 "editable": False, "edit_meta": None,
                 "val_color": GREEN if done else GOLD})
    else:
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": "None active", "value": "", "label_w": 38,
             "editable": False, "edit_meta": None, "val_color": DIM})
    add({"type": T_SPC, "h": SPC_H})

    # ── ## FISCAL REPORT ─────────────────────────────────
    add({"type": T_HDR2, "h": HDR2_H, "text": "## FISCAL REPORT"})
    FISCAL = [
        ("Debt Balance",    f"{fmt_cr(debt_d['balance'])}  ({debt_d['load_pct']:.1f}% of IPEU)",
         "debt_balance",  "float"),
        ("Interest Rate",   f"{debt_d['rate']*100:.1f}% / yr",       "interest_rate",  "pct"),
        ("Quarterly Int.",  fmt_cr(debt_d["q_interest"]),              None,             None),
        ("Debt Repayment",  fmt_cr(debt_d["repayment"]) + " / qtr",  "debt_repayment", "float"),
    ]
    for label, value, key, etype in FISCAL:
        meta = {"path": [key], "type": etype, "raw": nation.get(key, 0)} if key else None
        vcol = RED_C if (label == "Debt Balance" and debt_d["balance"] > 0) else TEXT
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": label, "value": value, "label_w": 18,
             "editable": meta is not None, "edit_meta": meta, "val_color": vcol})
    # Debt Load visual bar
    add({"type": T_DEBT, "h": DEBT_H, "in_block": True,
         "pct": debt_d["load_pct"] / 100.0})
    add({"type": T_SEP, "h": SEP_H, "in_block": True})
    sf_col = GREEN if sfund > 0 else RED_C
    fd_col = GREEN if fund_delta >= 0 else RED_C
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "Strategic Fund",
         "value": fmt_cr(sfund), "label_w": 18,
         "editable": True, "val_color": sf_col,
         "edit_meta": {"path": ["strategic_fund"], "type": "float", "raw": sfund}})
    fd_sign = "+" if fund_delta >= 0 else ""
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "Fund Δ this turn",
         "value": f"{fd_sign}{fmt_cr(fund_delta)}", "label_w": 18,
         "editable": False, "edit_meta": None, "val_color": fd_col})
    add({"type": T_SPC, "h": SPC_H})

    # ── ## RESOURCES ─────────────────────────────────────
    add({"type": T_HDR2, "h": HDR2_H, "text": "## RESOURCES & STOCKPILES"})
    RESOURCES = ["Food", "Minerals", "Energy", "Alloys", "Consumer Goods"]
    for rname in RESOURCES:
        sd    = nation.get("resource_stockpiles", {}).get(rname, {})
        stock = sd.get("stockpile", 0.0)
        mode  = sd.get("production_mode", "derived")
        if mode == "flat":
            prod = sd.get("flat_production", 0.0)
            cons = sd.get("flat_consumption", 0.0)
        else:
            rd   = res_d.get(rname, {})
            prod = rd.get("production", 0.0)
            cons = rd.get("consumption", 0.0)
        net   = prod - cons
        ncol  = GREEN if net >= 0 else RED_C
        eps   = max(prod * 0.05, 1.0)
        trend = "Stable" if abs(net) < eps else ("Surplus ▲" if net > 0 else "Deficit ▼")
        tcol  = GREEN if "Surplus" in trend else (RED_C if "Deficit" in trend else GOLD)
        exp_c = resource_export_credits(nation["name"], rname, routes)
        net_s = (f"+{fmt_int(net)}" if net >= 0 else fmt_int(int(net)))

        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": f"{rname} Stockpile", "value": fmt_int(stock),
             "label_w": 28, "editable": True, "val_color": TEXT,
             "edit_meta": {"path": ["resource_stockpiles", rname, "stockpile"],
                           "type": "float", "raw": stock}})
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": f"{rname} Production/turn",
             "value": fmt_int(prod), "label_w": 28,
             "editable": mode == "flat", "val_color": TEXT,
             "edit_meta": {"path": ["resource_stockpiles", rname, "flat_production"],
                           "type": "float", "raw": prod} if mode == "flat" else None})
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": f"{rname} Net/turn", "value": net_s,
             "label_w": 28, "editable": False, "edit_meta": None, "val_color": ncol})
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": f"{rname} Trend", "value": trend,
             "label_w": 28, "editable": False, "edit_meta": None, "val_color": tcol})
        if exp_c > 0:
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": f"{rname} Export", "value": fmt_cr(exp_c),
                 "label_w": 28, "editable": False, "edit_meta": None, "val_color": CYAN})
        add({"type": T_SPC, "h": 4})
    add({"type": T_SPC, "h": SPC_H})

    # ── # TERRITORIES ────────────────────────────────────
    add({"type": T_HDR1, "h": HDR1_H, "text": "# TERRITORIES"})
    if star_sys:
        for sys in star_sys:
            sname  = sys["name"]
            coords = sys.get("coordinates","") or "—"
            notes  = sys.get("notes","")
            add({"type": T_ROW, "h": ROW_H, "in_block": False,
                 "label": f"System: {sname}  [{coords}]",
                 "value": notes, "label_w": 36,
                 "editable": False, "edit_meta": None, "val_color": CYAN})
            for planet in sys.get("planets",[]):
                pname = planet["name"]
                cli   = planet.get("climate","?")
                col   = planet.get("colonization_pct",0)
                urb   = planet.get("urbanization_pct",0)
                add({"type": T_ROW, "h": ROW_H, "in_block": True,
                     "label": f"  ▸ {pname}",
                     "value": f"{cli}  col:{col:.0f}%  urb:{urb:.0f}%",
                     "label_w": 22, "editable": False, "edit_meta": None, "val_color": TEXT})
                for s in planet.get("settlements",[]):
                    sp  = s.get("population",0)
                    loy = s.get("loyalty",0)
                    ds  = len(s.get("districts",[]))
                    add({"type": T_ROW, "h": ROW_H, "in_block": True,
                         "label": f"      › {s['name']}",
                         "value": f"pop:{fmt_pop(sp)}  loy:{loy:.0f}%  districts:{ds}",
                         "label_w": 26, "editable": False, "edit_meta": None, "val_color": DIM})
    else:
        add({"type": T_ROW, "h": ROW_H, "in_block": True,
             "label": "No territorial data", "value": "", "label_w": 40,
             "editable": False, "edit_meta": None, "val_color": DIM})
    add({"type": T_SPC, "h": SPC_H})

    # ── ## DEMOGRAPHICS ──────────────────────────────────
    add({"type": T_HDR2, "h": HDR2_H, "text": "## NATIONAL DEMOGRAPHICS"})
    loy_mod = nation.get("loyalty_modifier_cg", 1.0)
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "Total Population", "value": fmt_pop(pop),
         "label_w": 22, "editable": False, "edit_meta": None, "val_color": TEXT})
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "Loyalty Modifier", "value": f"{loy_mod*100:.0f}%",
         "label_w": 22, "editable": False, "edit_meta": None, "val_color": TEXT})
    add({"type": T_SPC, "h": 6})
    for sp in species:
        is_dom = sp.get("status","") in ("dominant","majority")
        add({"type": T_SPHDR, "h": SPHDR_H,
             "name": sp["name"], "status": sp.get("status","?").title(),
             "dominant": is_dom})
        loy   = sp.get("loyalty", 0)
        sp_pop= sp.get("population", 0)
        shr   = (sp_pop / pop * 100) if pop > 0 else 0
        lc    = GREEN if loy >= 70 else (GOLD if loy >= 40 else RED_C)
        SPROWS = [
            ("Population",  fmt_pop(sp_pop),                            None),
            ("Share",       f"{shr:.1f}% of total",                    None),
            ("Growth Rate", fmt_pct_plus(sp.get("growth_rate",0)) + " / yr", None),
            ("Culture",     sp.get("culture","—"),                     None),
            ("Language",    sp.get("language","—"),                    None),
            ("Religion",    sp.get("religion","—"),                    None),
            ("Loyalty",     f"{loy}/100  {loyalty_bar(loy)}",          lc),
        ]
        for label, value, vcol in SPROWS:
            vc = vcol or TEXT
            is_loy = label == "Loyalty"
            meta = {"path": ["_species", sp["name"], "loyalty"],
                    "type": "int", "raw": loy} if is_loy else None
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": label, "value": value, "label_w": 16,
                 "editable": is_loy, "edit_meta": meta, "val_color": vc})
        add({"type": T_SPC, "h": 6})

    # ── # MILITARY ───────────────────────────────────────
    add({"type": T_HDR1, "h": HDR1_H, "text": "# MILITARY"})
    if not isinstance(afd, list):
        afd_list = []
    else:
        afd_list = afd
    CAT_MAP = [
        ("## SPACEFLEET",       ["Spacefleet","Navy"]),
        ("## AEROSPACE FORCES", ["Air Force","Aerospace"]),
        ("## GROUND FORCES",    ["Ground Forces","Ground","Army"]),
    ]
    for sec_label, cats in CAT_MAP:
        add({"type": T_HDR2, "h": HDR2_H, "text": sec_label})
        units = [u for u in afd_list if u.get("category") in cats]
        if units:
            for u in units:
                cname = u.get("custom_name") or u.get("unit","?")
                vet   = u.get("veterancy","?")
                cnt   = u.get("count",1)
                add({"type": T_ROW, "h": ROW_H, "in_block": True,
                     "label": f"  {cname}", "value": f"×{cnt}  {vet}",
                     "label_w": 30, "editable": False, "edit_meta": None,
                     "val_color": DIM})
        else:
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": "  None on record", "value": "", "label_w": 30,
                 "editable": False, "edit_meta": None, "val_color": DIM2})
    add({"type": T_SPC, "h": SPC_H})

    # ── # RESEARCH ───────────────────────────────────────
    add({"type": T_HDR1, "h": HDR1_H, "text": "# RESEARCH"})
    add({"type": T_ROW, "h": ROW_H, "in_block": True,
         "label": "Budget/turn", "value": fmt_cr(rbudget),
         "label_w": 18, "editable": True, "val_color": CYAN,
         "edit_meta": {"path": ["research_budget"], "type": "float", "raw": rbudget}})
    if act_res:
        for proj in act_res:
            prog = proj.get("progress", 0.0)
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": f"  [{proj.get('field','?')}] {proj.get('name','?')}",
                 "value": f"{prog:.1f}%", "label_w": 38,
                 "editable": False, "edit_meta": None, "val_color": GOLD})
    if comp_tech:
        shown = comp_tech[-6:]
        for t in shown:
            tname = t if isinstance(t, str) else t.get("name", str(t))
            add({"type": T_ROW, "h": ROW_H, "in_block": True,
                 "label": f"  ✓ {tname}", "value": "", "label_w": 40,
                 "editable": False, "edit_meta": None, "val_color": GREEN})

    add({"type": T_SPC, "h": 20})   # bottom padding
    return items


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISCORD FORMAT  (1:1 reference)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def format_discord_v2(nation: dict, state: dict) -> str:
    ye        = years_elapsed(state)
    ipeu_base = nation.get("base_ipeu", 0.0)
    pop       = current_population(nation, ye)
    exp_dict  = nation.get("expenditure", {})
    routes    = state.get("trade_routes", [])
    trade     = compute_trade(nation, routes)
    res_d     = compute_resources(nation, ipeu_base)
    debt_d    = compute_debt(nation, ipeu_base)
    rbudget   = nation.get("research_budget", 0.0)
    sfund     = nation.get("strategic_fund", 0.0)
    star_sys  = nation.get("star_systems", [])
    species   = nation.get("species_populations", [])
    projects  = nation.get("projects", [])
    tag       = nation_tag(nation["name"])
    year      = state.get("year",    2200)
    quarter   = state.get("quarter", 1)
    civ_level = nation.get("civ_level",  "Interplanetary Industrial")
    civ_tier  = nation.get("civ_tier",   2)
    eco_status= nation.get("eco_status", "Stable")

    homeworld = "—"
    for sys in star_sys:
        for planet in sys.get("planets", []):
            homeworld = planet["name"]
            break
        break

    species_str = ", ".join(s["name"] for s in species) if species else "—"
    total_exp   = sum(exp_dict.values()) * ipeu_base + rbudget
    net_bal     = ipeu_base + trade["net"] - total_exp - debt_d["q_interest"]
    export_cr   = trade["exports"] + trade["transit_income"]
    fund_delta  = -debt_d["q_interest"]
    per_cap     = int(ipeu_base / pop) if pop else 0

    L = []
    L.append(f"-# [{tag}] {nation['name'].upper()}")
    L.append(f"# NATIONAL PROFILE - Q{quarter} {year}")
    L.append("```")
    L.append(f"  Species          : {species_str}")
    L.append(f"  Population       : {fmt_pop(pop)}")
    L.append(f"  Pop Growth       : {fmt_pct_plus(nation.get('pop_growth',0))} / yr")
    L.append(f"  Homeworld        : {homeworld}")
    L.append(f"  Civilisation     : {civ_level}")
    L.append(f"  Tier             : {civ_tier}")
    L.append(f"  Status           : {eco_status}")
    L.append("```")

    L.append("# ECONOMY")
    L.append("```")
    L.append(f"  IPEU (base)      : {fmt_cr(ipeu_base)}")
    L.append(f"  IPEU Growth      : {fmt_pct_plus(nation.get('ipeu_growth',0))} / yr")
    L.append(f"  IPEU per Capita  : {per_cap:,} cr")
    L.append(f"  Export Credits   : {fmt_cr(export_cr)}")
    L.append(f"  Total Expenditure: {fmt_cr(total_exp)}  ({sum(exp_dict.values())*100:.1f}%)")
    L.append(f"  Research Budget  : {fmt_cr(rbudget)} / turn")
    L.append(f"  Net Balance      : {fmt_cr(net_bal)}")
    L.append("```")

    L.append("## EXPENDITURE & BREAKDOWN")
    L.append("```")
    for cat, pct in exp_dict.items():
        bar = exp_bar_str(pct)
        L.append(f"  {cat:<22} {pct*100:5.1f}%   {bar}   {fmt_cr(pct*ipeu_base)}")
    L.append(f"  {'─'*61}")
    L.append(f"  {'TOTAL':<22} {sum(exp_dict.values())*100:5.1f}%              ({fmt_cr(total_exp)})")
    L.append("```")

    L.append("## ECONOMIC PROJECTS")
    L.append("```")
    all_projs = [p for p in projects if p.get("status") in ("active","in_progress","complete")]
    if all_projs:
        for proj in all_projs:
            done  = proj.get("status") == "complete"
            turns_left = proj.get("duration_turns",0) - proj.get("turns_elapsed",0)
            tag_str = "[COMPLETE]" if done else f"[{turns_left} turns remaining]"
            L.append(f"  {proj['name']} ({proj.get('category','?')})  {tag_str}")
    else:
        L.append("  None")
    L.append("```")

    L.append("## FISCAL REPORT")
    L.append("```")
    L.append(f"  Debt Balance     : {fmt_cr(debt_d['balance'])}  ({debt_d['load_pct']:.1f}% of IPEU)")
    L.append(f"  Debt Load        : {debt_bar_str(debt_d['load_pct']/100)}")
    L.append(f"  Interest Rate    : {debt_d['rate']*100:.1f}% / yr")
    L.append(f"  Quarterly Int.   : {fmt_cr(debt_d['q_interest'])}")
    L.append(f"  Debt Repayment   : {fmt_cr(debt_d['repayment'])} / qtr")
    L.append(f"  {'─'*61}")
    sf_icon = "🟢" if sfund >= 0 else "🔴"
    L.append(f"  Strategic Fund   : {sf_icon} {fmt_cr(sfund)}")
    fd_sign = "+" if fund_delta >= 0 else ""
    L.append(f"  Fund Δ this turn : {fd_sign}{fmt_cr(fund_delta)}")
    L.append("```")

    L.append("## RESOURCES & STOCKPILES")
    RESOURCES = ["Food","Minerals","Energy","Alloys","Consumer Goods"]
    for rname in RESOURCES:
        sd    = nation.get("resource_stockpiles",{}).get(rname,{})
        stock = sd.get("stockpile", 0.0)
        mode  = sd.get("production_mode","derived")
        if mode == "flat":
            prod = sd.get("flat_production",  0.0)
            cons = sd.get("flat_consumption", 0.0)
        else:
            rd   = res_d.get(rname, {})
            prod = rd.get("production",  0.0)
            cons = rd.get("consumption", 0.0)
        net    = prod - cons
        eps    = max(prod * 0.05, 1.0)
        trend  = "Stable" if abs(net) < eps else ("Surplus" if net > 0 else "Deficit")
        net_s  = f"+{fmt_int(net)}" if net >= 0 else fmt_int(int(net))
        exp_c  = resource_export_credits(nation["name"], rname, routes)
        L.append("```")
        L.append(f"  {rname} Stockpile            : {fmt_int(stock)}")
        L.append(f"  {rname} Production per turn  : {fmt_int(prod)}")
        L.append(f"  {rname} Net per turn         : {net_s}")
        L.append(f"  {rname} Trend                : {trend}")
        if exp_c > 0:
            L.append(f"  {rname} Export              : {fmt_cr(exp_c)}")
        L.append("```")

    L.append("# TERRITORIES")
    if star_sys:
        sys0 = star_sys[0]
        L.append(f"Home System: {sys0['name']}")
        for planet in sys0.get("planets",[]):
            L.append("```")
            pop_a = planet.get("pop_assigned", pop)
            L.append(f"  Homeworld: {planet['name']}")
            L.append(f"    Population    : {fmt_pop(pop_a)}")
            setts = planet.get("settlements", [])
            if setts:
                L.append(f"    Settlements   : {len(setts)}")
                for s in setts:
                    L.append(f"      - {s['name']}")
                    dcounts: Dict[str,int] = {}
                    for d in s.get("districts",[]):
                        dt = d.get("type","?")
                        dcounts[dt] = dcounts.get(dt, 0) + 1
                    for dt, cnt in dcounts.items():
                        L.append(f"        [{dt}] ×{cnt}")
            else:
                L.append("    Settlements   : (UNNAMED = Capital (UNNAMED))")
                L.append("    Urban Districts: UNKNOWN")
            L.append("```")
    else:
        L.append("No territorial data")

    L.append("## NATIONAL DEMOGRAPHICS")
    L.append("```")
    L.append(f"  Total Population: {fmt_pop(pop)}")
    L.append(f"  Loyalty Modifier: {nation.get('loyalty_modifier_cg',1.0)*100:.0f}%")
    L.append("```")

    for sp in species:
        is_dom   = sp.get("status","") in ("dominant","majority")
        crown    = "👑" if is_dom else "👥"
        sp_pop   = sp.get("population", 0)
        shr      = (sp_pop / pop * 100) if pop > 0 else 0
        loy      = sp.get("loyalty", 0)
        loy_icon = "🟢" if loy >= 70 else ("🟡" if loy >= 40 else "🔴")
        L.append(f"**{sp['name']}**  {crown} {sp.get('status','').title()}")
        L.append("```")
        L.append(f"  Population       : {fmt_pop(sp_pop)}")
        L.append(f"  Share            : {shr:.1f}% of total")
        L.append(f"  Growth Rate      : {fmt_pct_plus(sp.get('growth_rate',0))} / yr")
        L.append(f"  Culture          : {sp.get('culture','—')}")
        L.append(f"  Language         : {sp.get('language','—')}")
        L.append(f"  Religion         : {sp.get('religion','—')}")
        L.append(f"  Loyalty          : {loy_icon} {loy}/100  {loyalty_bar(loy)}")
        L.append("```")

    return "\n".join(L)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FONT CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_fonts: Dict[str, pygame.font.Font] = {}

def gf(size: int, mono: bool = True) -> pygame.font.Font:
    key = f"{'m' if mono else 's'}{size}"
    if key not in _fonts:
        if mono:
            for name in ("Courier New","Courier","Consolas","DejaVu Sans Mono","monospace"):
                try:
                    f = pygame.font.SysFont(name, size)
                    _fonts[key] = f
                    break
                except Exception:
                    continue
        else:
            for name in ("Segoe UI","Calibri","Arial","Helvetica","sans"):
                try:
                    f = pygame.font.SysFont(name, size)
                    _fonts[key] = f
                    break
                except Exception:
                    continue
        if key not in _fonts:
            _fonts[key] = pygame.font.Font(None, size + 4)
    return _fonts[key]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DRAWING UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_text(surf, txt: str, x: int, y: int,
              font: pygame.font.Font, col=TEXT) -> int:
    s = font.render(txt, True, col)
    surf.blit(s, (x, y))
    return s.get_width()


def tw(txt: str, font: pygame.font.Font) -> int:
    return font.size(txt)[0]


def draw_bar(surf, x, y, w, h, pct,
             fg=CYAN, bg=BLOCK_BG, border=BORDER):
    pygame.draw.rect(surf, bg, (x, y, w, h))
    fill = max(0, int(w * max(0.0, min(1.0, pct))))
    if fill:
        pygame.draw.rect(surf, fg, (x, y, fill, h))
    pygame.draw.rect(surf, border, (x, y, w, h), 1)


def corner_deco(surf, x, y, w, h, col, s=10):
    pts = [
        [(x, y+s),     (x, y),     (x+s, y)],
        [(x+w-s, y),   (x+w, y),   (x+w, y+s)],
        [(x, y+h-s),   (x, y+h),   (x+s, y+h)],
        [(x+w-s, y+h), (x+w, y+h), (x+w, y+h-s)],
    ]
    for p in pts:
        pygame.draw.lines(surf, col, False, p, 2)


def draw_panel(surf, rect, bg=PANEL, border=BORDER,
               accent=None, corner=False):
    pygame.draw.rect(surf, bg, rect)
    pygame.draw.rect(surf, border, rect, 1)
    if corner and accent:
        corner_deco(surf, rect[0], rect[1], rect[2], rect[3], accent, 10)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCROLLBAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Scrollbar:
    def __init__(self, x, y, w, h):
        self.rect      = pygame.Rect(x, y, w, h)
        self.thumb_r   = pygame.Rect(x, y, w, 20)
        self._drag     = False
        self._drag_off = 0
        self.scroll    = 0
        self.content_h = 1
        self.view_h    = h

    def set_content(self, ch, vh):
        self.content_h = max(1, ch)
        self.view_h    = vh

    def clamp(self):
        self.scroll = max(0, min(self.scroll, max(0, self.content_h - self.view_h)))

    def _update_thumb(self):
        max_s    = max(1, self.content_h - self.view_h)
        ratio    = self.view_h / self.content_h
        t_h      = max(20, int(self.rect.h * ratio))
        t_y      = self.rect.y + int((self.scroll / max_s) * (self.rect.h - t_h))
        self.thumb_r = pygame.Rect(self.rect.x, t_y, self.rect.w, t_h)

    def draw(self, surf):
        pygame.draw.rect(surf, SCRLBG, self.rect)
        self._update_thumb()
        pygame.draw.rect(surf, SCRLTMB, self.thumb_r, border_radius=3)
        pygame.draw.rect(surf, BORDER,  self.rect, 1)

    def on_event(self, event, over: bool):
        if event.type == pygame.MOUSEWHEEL and over:
            self.scroll -= event.y * 40
            self.clamp()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.thumb_r.collidepoint(event.pos):
                self._drag     = True
                self._drag_off = event.pos[1] - self.thumb_r.y
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._drag = False
        elif event.type == pygame.MOUSEMOTION and self._drag:
            rel     = event.pos[1] - self.rect.y - self._drag_off
            travel  = max(1, self.rect.h - self.thumb_r.h)
            self.scroll = int((rel / travel) * max(0, self.content_h - self.view_h))
            self.clamp()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUTTON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class Button:
    def __init__(self, rect, label, accent=False, small=False):
        self.rect    = pygame.Rect(rect)
        self.label   = label
        self.accent  = accent
        self.small   = small
        self._hov    = False

    def draw(self, surf):
        if self.accent:
            bg  = BTNACC_H if self._hov else BTNACC
            bdr = ACCENT
        else:
            bg  = BTNHOV if self._hov else BTNBG
            bdr = BORDER2
        pygame.draw.rect(surf, bg, self.rect, border_radius=3)
        pygame.draw.rect(surf, bdr, self.rect, 1, border_radius=3)
        f  = gf(11 if self.small else 13)
        tw_ = tw(self.label, f)
        tx  = self.rect.x + (self.rect.w - tw_) // 2
        ty  = self.rect.y + (self.rect.h - f.get_height()) // 2
        draw_text(surf, self.label, tx, ty, f, BRIGHT)

    def on_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hov = self.rect.collidepoint(event.pos)
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EDIT OVERLAY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EditOverlay:
    H = 50

    def __init__(self):
        self.active      = False
        self.label       = ""
        self.text        = ""
        self.cursor      = 0
        self.meta        = None
        self._blink      = 0.0
        self._cur_vis    = True

    def open(self, label: str, raw, meta: dict):
        self.active   = True
        self.label    = label
        self.text     = str(raw)
        self.cursor   = len(self.text)
        self.meta     = meta
        self._blink   = 0.0
        self._cur_vis = True

    def close(self):
        self.active = False
        self.text   = ""
        self.meta   = None

    def draw(self, surf, dt: float):
        if not self.active:
            return
        self._blink += dt
        if self._blink > 0.45:
            self._cur_vis = not self._cur_vis
            self._blink   = 0.0

        y = SH - SBAR_H - self.H
        r = pygame.Rect(MAIN_X, y, SW - MAIN_X, self.H)
        pygame.draw.rect(surf, EDITBG, r)
        pygame.draw.rect(surf, EDITBDR, r, 2)
        corner_deco(surf, r.x, r.y, r.w, r.h, EDITBDR, 7)

        f   = gf(13)
        lbl = f"EDIT  {self.label}  ▸ "
        lw_ = tw(lbl, f)
        draw_text(surf, lbl, r.x + 14, r.y + 16, f, DIM)

        tx = r.x + 14 + lw_
        ty = r.y + 16
        draw_text(surf, self.text, tx, ty, f, BRIGHT)
        if self._cur_vis:
            cx = tx + tw(self.text[:self.cursor], f)
            pygame.draw.line(surf, EDITBDR, (cx, ty), (cx, ty + f.get_height()), 2)

        hint = "[ENTER] Confirm   [ESC] Cancel"
        hw   = tw(hint, f)
        draw_text(surf, hint, r.right - hw - 14, r.y + 16, f, DIM)

    def on_event(self, event) -> Optional[str]:
        if not self.active:
            return None
        if event.type != pygame.KEYDOWN:
            return None
        k = event.key
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return "confirm"
        if k == pygame.K_ESCAPE:
            return "cancel"
        if k == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.text   = self.text[:self.cursor-1] + self.text[self.cursor:]
                self.cursor -= 1
        elif k == pygame.K_DELETE:
            self.text = self.text[:self.cursor] + self.text[self.cursor+1:]
        elif k == pygame.K_LEFT:
            self.cursor = max(0, self.cursor - 1)
        elif k == pygame.K_RIGHT:
            self.cursor = min(len(self.text), self.cursor + 1)
        elif k == pygame.K_HOME:
            self.cursor = 0
        elif k == pygame.K_END:
            self.cursor = len(self.text)
        elif event.unicode and event.unicode.isprintable():
            self.text   = self.text[:self.cursor] + event.unicode + self.text[self.cursor:]
            self.cursor += 1
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# APPLY EDIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def apply_edit(nation: dict, meta: dict, raw_text: str) -> bool:
    path  = meta["path"]
    etype = meta["type"]
    try:
        clean = raw_text.strip().replace(",","").replace("_","")
        if etype == "float":
            value = float(clean)
        elif etype == "pct":
            v = float(clean.replace("%",""))
            value = v / 100.0 if v > 1.5 else v
        elif etype == "int":
            value = int(float(clean))
        elif etype == "pop":
            v = float(clean.rstrip("BbMmKk"))
            if clean[-1] in "Bb": v *= 1e9
            elif clean[-1] in "Mm": v *= 1e6
            elif clean[-1] in "Kk": v *= 1e3
            value = v
        else:
            value = raw_text.strip()
    except (ValueError, IndexError):
        return False

    # Species nested edit
    if path[0] == "_species" and len(path) == 3:
        for sp in nation.get("species_populations", []):
            if sp["name"] == path[1]:
                sp[path[2]] = value
                return True
        return False

    # Resource stockpile nested edit
    if path[0] == "resource_stockpiles" and len(path) == 3:
        nation.setdefault("resource_stockpiles", {}) \
              .setdefault(path[1], {})[path[2]] = value
        return True

    # Expenditure nested edit
    if path[0] == "expenditure" and len(path) == 2:
        nation.setdefault("expenditure", {})[path[1]] = value
        return True

    # Top-level
    if len(path) == 1:
        nation[path[0]] = value
        return True

    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LEFT PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LeftPanel:
    ROW_H  = 38
    PAD    = 8

    def __init__(self, w, h):
        self.rect     = pygame.Rect(0, 0, w, h)
        self.names    : List[str] = []
        self.scroll   = 0
        self.selected = 0
        self._hover   = -1
        # Buttons (absolute screen coords)
        bw = w - self.PAD * 2
        self.btn_save = Button((self.PAD, h - 90, bw, 26), "[ SAVE  S ]", accent=True)
        self.btn_disc = Button((self.PAD, h - 60, bw, 26), "[ DISCORD EXPORT  D ]")
        self.btn_init = Button((self.PAD, h - 30, bw, 26), "[ INIT SETTLEMENTS ]", small=True)

    def set_nations(self, names: List[str], sel: int = 0):
        self.names    = names
        self.selected = sel

    # ── draw ──────────────────────────────────

    def draw(self, surf, turn, year, quarter):
        r = self.rect
        # Panel bg + border
        pygame.draw.rect(surf, PANEL, r)
        pygame.draw.rect(surf, BORDER, r, 1)
        corner_deco(surf, r.x, r.y, r.w, r.h, ACCENT, 10)

        # Top accent stripe
        pygame.draw.rect(surf, ACCENT2, (r.x, r.y, r.w, 3))

        f_title = gf(14, mono=False)
        f_sub   = gf(11)
        f_item  = gf(13)
        f_tag   = gf(11)

        draw_text(surf, "CARMINE NRP",
                  r.x + self.PAD, r.y + 8, f_title, ACCENT)
        draw_text(surf, f"T{turn}  ·  {year} Q{quarter}",
                  r.x + self.PAD, r.y + 28, f_sub, TEAL)

        # Separator
        yd = r.y + 48
        pygame.draw.line(surf, BORDER2, (r.x+4, yd), (r.right-4, yd), 1)

        list_y0 = yd + 4
        list_h  = r.h - (yd - r.y) - 100
        clip    = pygame.Rect(r.x, list_y0, r.w, list_h)
        surf.set_clip(clip)

        for i, name in enumerate(self.names):
            iy = list_y0 + i * self.ROW_H - self.scroll
            if iy + self.ROW_H < list_y0 or iy > list_y0 + list_h:
                continue
            rr = pygame.Rect(r.x + 4, iy, r.w - 8, self.ROW_H - 3)
            if i == self.selected:
                pygame.draw.rect(surf, SELECTED, rr, border_radius=3)
                pygame.draw.rect(surf, CYAN, rr, 1, border_radius=3)
                # left glow bar
                pygame.draw.rect(surf, CYAN, (r.x, iy, 3, self.ROW_H - 3))
                nc = BRIGHT
            elif i == self._hover:
                pygame.draw.rect(surf, HOVER, rr, border_radius=3)
                nc = TEXT
            else:
                nc = DIM

            tag = f"[{nation_tag(name)}]"
            draw_text(surf, tag,  r.x + self.PAD + 2, iy + 4,  f_tag, TEAL if i==self.selected else DIM2)
            ns = name if len(name) <= 22 else name[:20] + ".."
            draw_text(surf, ns,   r.x + self.PAD + 2, iy + 18, f_item, nc)

        surf.set_clip(None)

        self.btn_save.draw(surf)
        self.btn_disc.draw(surf)
        self.btn_init.draw(surf)

    # ── events ────────────────────────────────

    def on_event(self, event) -> Optional[int]:
        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            if self.rect.collidepoint(pos):
                yd     = self.rect.y + 52
                rel    = pos[1] - yd + self.scroll
                i      = rel // self.ROW_H
                self._hover = i if 0 <= i < len(self.names) else -1
            else:
                self._hover = -1

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, self.scroll - event.y * self.ROW_H)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.rect.collidepoint(pos):
                yd  = self.rect.y + 52
                rel = pos[1] - yd + self.scroll
                i   = rel // self.ROW_H
                if 0 <= i < len(self.names):
                    self.selected = i
                    return i
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MainPanel:
    LPAD = 18

    def __init__(self):
        self.rect      = pygame.Rect(MAIN_X, MAIN_Y, MAIN_W, MAIN_H)
        self.items     : List[dict] = []
        self.content_h = 0
        self.scroll    = Scrollbar(MAIN_X + MAIN_W, MAIN_Y, SCRL_W, MAIN_H)
        self._hov_i    = -1

    def set_items(self, items: List[dict]):
        self.items     = items
        self.content_h = (items[-1]["y"] + items[-1]["h"]) if items else 0
        self.scroll.set_content(self.content_h, MAIN_H)
        self.scroll.scroll = 0
        self.scroll.clamp()
        self._hov_i    = -1

    def _sy(self, iy: int) -> int:
        return self.rect.y + iy - self.scroll.scroll

    def draw(self, surf):
        pygame.draw.rect(surf, BG, self.rect)
        surf.set_clip(self.rect)

        f_mono  = gf(13)
        f_small = gf(11)
        f_hdr1  = gf(16, mono=False)
        f_hdr2  = gf(14, mono=False)
        f_nhdr  = gf(19, mono=False)
        f_sp    = gf(13, mono=False)

        x0 = self.rect.x + self.LPAD
        rw = self.rect.w

        for i, item in enumerate(self.items):
            sy = self._sy(item["y"])
            sh = item["h"]
            if sy + sh < self.rect.y or sy > self.rect.bottom:
                continue

            t = item["type"]

            # ── Nation Header ──────────────────────────
            if t == TN_HDR:
                pygame.draw.rect(surf, PANEL2, (self.rect.x, sy, rw, sh))
                pygame.draw.rect(surf, ACCENT, (self.rect.x, sy, 4, sh))
                # Subtle hex grid bg
                for gx in range(self.rect.x, self.rect.x + rw, 32):
                    pygame.draw.line(surf, (16, 24, 36),
                                     (gx, sy), (gx, sy + sh), 1)
                name_str = item["name"]
                tag_str  = f"[{item['tag']}]"
                tw_tag   = tw(tag_str, f_hdr1)
                draw_text(surf, tag_str,  x0, sy + 14, f_hdr1, ACCENT)
                draw_text(surf, "  " + name_str, x0 + tw_tag, sy + 12, f_nhdr, BRIGHT)
                pygame.draw.line(surf, BORDER2,
                                 (self.rect.x, sy + sh - 1),
                                 (self.rect.right, sy + sh - 1), 1)

            # ── Section Header 1 ────────────────────────
            elif t == T_HDR1:
                pygame.draw.rect(surf, PANEL2, (self.rect.x, sy, rw, sh))
                pygame.draw.rect(surf, ACCENT, (self.rect.x, sy, 3, sh))
                draw_text(surf, item["text"], x0, sy + 10, f_hdr1, CYAN)
                pygame.draw.line(surf, BORDER,
                                 (self.rect.x, sy + sh - 1),
                                 (self.rect.right, sy + sh - 1), 1)

            # ── Section Header 2 ────────────────────────
            elif t == T_HDR2:
                pygame.draw.rect(surf, PANEL3, (self.rect.x, sy, rw, sh))
                pygame.draw.rect(surf, TEAL2, (self.rect.x, sy, 2, sh))
                draw_text(surf, item["text"], x0, sy + 8, f_hdr2, TEAL)

            # ── Row ─────────────────────────────────────
            elif t == T_ROW:
                bg = BLOCK_ALT if (item.get("in_block") and i % 2 == 0) else BLOCK_BG if item.get("in_block") else BG
                pygame.draw.rect(surf, bg, (self.rect.x, sy, rw, sh))
                if i == self._hov_i and item.get("editable"):
                    pygame.draw.rect(surf, HOVER, (self.rect.x, sy, rw, sh))

                label   = item.get("label", "")
                value   = str(item.get("value", ""))
                lw_     = item.get("label_w", 18)
                vcol    = item.get("val_color", TEXT)
                lbl_str = f"{label:<{lw_}}: "
                draw_text(surf, lbl_str, x0, sy + 4, f_mono, DIM)
                loffset = tw(lbl_str, f_mono)
                draw_text(surf, value, x0 + loffset, sy + 4, f_mono, vcol)

                if item.get("editable"):
                    pygame.draw.rect(surf, TEAL, (self.rect.right - 4, sy, 2, sh))

            # ── Bar Row ─────────────────────────────────
            elif t == T_BAR:
                bg = BLOCK_ALT if i % 2 == 0 else BLOCK_BG
                pygame.draw.rect(surf, bg, (self.rect.x, sy, rw, sh))
                if i == self._hov_i and item.get("editable"):
                    pygame.draw.rect(surf, HOVER, (self.rect.x, sy, rw, sh))

                label  = item.get("label","")
                pct    = item.get("pct", 0.0)
                amount = item.get("amount","")
                lbl_s  = f"{label:<22} {pct*100:5.1f}%"
                draw_text(surf, lbl_s, x0, sy + 5, f_small, DIM)
                base_x = x0 + tw(lbl_s, f_small) + 8
                bar_h  = 10
                bar_y  = sy + (sh - bar_h) // 2
                draw_bar(surf, base_x, bar_y, 160, bar_h, pct, fg=CYAN)
                draw_text(surf, amount, base_x + 168, sy + 5, f_small, GOLD)

                if item.get("editable"):
                    pygame.draw.rect(surf, TEAL, (self.rect.right - 4, sy, 2, sh))

            # ── Debt Bar ────────────────────────────────
            elif t == T_DEBT:
                pygame.draw.rect(surf, BLOCK_BG, (self.rect.x, sy, rw, sh))
                pct    = item.get("pct", 0.0)
                lbl_s  = f"{'Debt Load':<18}: "
                draw_text(surf, lbl_s, x0, sy + 5, f_mono, DIM)
                base_x = x0 + tw(lbl_s, f_mono)
                fc     = RED_C if pct > 0.5 else (GOLD if pct > 0.2 else GREEN)
                draw_bar(surf, base_x, sy + 6, 200, 10, pct, fg=fc)
                draw_text(surf, f"  {pct*100:.1f}%", base_x + 208, sy + 5, f_mono, DIM)

            # ── Separator ───────────────────────────────
            elif t == T_SEP:
                my = sy + sh // 2
                pygame.draw.line(surf, BORDER2,
                                 (self.rect.x + 6, my),
                                 (self.rect.right - 6, my), 1)

            # ── Species Header ──────────────────────────
            elif t == T_SPHDR:
                pygame.draw.rect(surf, PANEL3, (self.rect.x, sy, rw, sh))
                pygame.draw.rect(surf, GOLD2, (self.rect.x, sy, 3, sh))
                crown  = "👑" if item.get("dominant") else "👥"
                sname  = item["name"]
                status = item["status"]
                label  = f"{crown}  {sname}"
                draw_text(surf, label, x0, sy + 6, f_sp, GOLD)
                lw_ = tw(label, f_sp)
                draw_text(surf, f"  {status}", x0 + lw_, sy + 7, gf(12, mono=False), TEAL)

            # T_SPC is a no-op

        surf.set_clip(None)
        pygame.draw.rect(surf, BORDER, self.rect, 1)
        self.scroll.draw(surf)

    def on_event(self, event) -> Optional[dict]:
        over = pygame.Rect(self.rect.x, self.rect.y,
                            self.rect.w + SCRL_W, self.rect.h)
        self.scroll.on_event(event, over.collidepoint(pygame.mouse.get_pos()))

        if event.type == pygame.MOUSEMOTION:
            pos = event.pos
            if self.rect.collidepoint(pos):
                abs_y = pos[1] - self.rect.y + self.scroll.scroll
                self._hov_i = -1
                for i, item in enumerate(self.items):
                    if item["y"] <= abs_y < item["y"] + item["h"]:
                        self._hov_i = i if item.get("editable") else -1
                        break
            else:
                self._hov_i = -1

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            scrl_r = pygame.Rect(MAIN_X + MAIN_W, MAIN_Y, SCRL_W, MAIN_H)
            if self.rect.collidepoint(pos) and not scrl_r.collidepoint(pos):
                abs_y = pos[1] - self.rect.y + self.scroll.scroll
                for item in self.items:
                    if item["y"] <= abs_y < item["y"] + item["h"]:
                        if item.get("editable") and item.get("edit_meta"):
                            return {
                                "label": item.get("label","Field"),
                                "raw":   item["edit_meta"].get("raw",""),
                                "meta":  item["edit_meta"],
                            }
                        break
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOP BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_top_bar(surf, nation_name: str, turn, year, quarter, dirty: bool):
    pygame.draw.rect(surf, PANEL, (0, 0, SW, TBAR_H))
    pygame.draw.rect(surf, ACCENT, (0, TBAR_H - 2, SW, 2))
    # subtle grid
    for gx in range(0, LWIDTH, 20):
        pygame.draw.line(surf, (14, 20, 30), (gx, 0), (gx, TBAR_H))

    f_s  = gf(11)
    f_m  = gf(14, mono=False)
    draw_text(surf, "CARMINE NRP ENGINE  ·  vAlpha 0.2.2",
              LWIDTH + 14, 6, f_s, DIM)
    if nation_name:
        draw_text(surf, nation_name,
                  LWIDTH + 14, 22, f_m, BRIGHT)
    tag  = f"T{turn}  |  Y{year} Q{quarter}"
    if dirty:
        tag += "  ●"
    draw_text(surf, tag, SW - tw(tag, f_s) - 14, 17, f_s, TEAL)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS BAR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_status    = "Ready.  Double-click fields to edit."
_status_c  = DIM
_status_t  = 0.0


def set_status(msg: str, col=DIM):
    global _status, _status_c, _status_t
    _status   = msg
    _status_c = col
    _status_t = time.time()


def draw_status_bar(surf):
    y = SH - SBAR_H
    pygame.draw.rect(surf, PANEL,  (0, y, SW, SBAR_H))
    pygame.draw.line(surf, BORDER, (0, y), (SW, y), 1)
    f = gf(11)
    draw_text(surf, _status, 12, y + 7, f, _status_c)
    keys = "S=Save  D=Export  ESC=Cancel/Quit  ↑↓=Navigate  Click=Edit"
    draw_text(surf, keys, SW - tw(keys, f) - 12, y + 7, f, DIM2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKGROUND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_bg(surf):
    surf.fill(BG)
    gc = (11, 18, 28)
    for x in range(0, SW, 36):
        pygame.draw.line(surf, gc, (x, 0), (x, SH))
    for y in range(0, SH, 36):
        pygame.draw.line(surf, gc, (0, y), (SW, y))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    pygame.init()
    pygame.display.set_caption("Carmine NRP Engine  —  vAlpha 0.2.2")
    screen = pygame.display.set_mode((SW, SH))
    clock  = pygame.time.Clock()

    filepath = sys.argv[1] if len(sys.argv) > 1 else "carmine_state_T5_Y2201Q1.json"
    sm       = StateManager(filepath)
    if not sm.load():
        pygame.quit()
        sys.exit(f"[FATAL] Cannot load: {filepath}")

    set_status(f"Loaded: {filepath}", GREEN)

    names    = sm.nation_names()
    sel_idx  = 0
    turn     = sm.state.get("turn",    1)
    year     = sm.state.get("year",    2200)
    quarter  = sm.state.get("quarter", 1)

    left    = LeftPanel(LWIDTH, SH)
    left.set_nations(names, sel_idx)
    main_p  = MainPanel()
    edit_ov = EditOverlay()

    cur_nation: Optional[dict] = None

    def load_nation(idx: int):
        nonlocal cur_nation, sel_idx
        sel_idx    = idx
        left.selected = idx
        n = sm.get_nation(names[idx])
        if n:
            cur_nation = n
            items = build_render_items(n, sm.state)
            main_p.set_items(items)
            set_status(f"Viewing: {n['name']}   Click any cyan-edged field to edit.", CYAN)
        return n

    load_nation(0)

    prev_t = time.time()
    running = True

    while running:
        now = time.time()
        dt  = now - prev_t
        prev_t = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # ── Edit overlay captures all events ──────
            if edit_ov.active:
                res = edit_ov.on_event(event)
                if res == "confirm":
                    ok = apply_edit(cur_nation, edit_ov.meta, edit_ov.text)
                    if ok:
                        sm.mark_dirty()
                        sm.autosave()
                        main_p.set_items(build_render_items(cur_nation, sm.state))
                        set_status(f"Updated: {edit_ov.meta['path'][-1]}", GREEN)
                    else:
                        set_status(f"Invalid value: '{edit_ov.text}'", RED_C)
                    edit_ov.close()
                elif res == "cancel":
                    edit_ov.close()
                    set_status("Edit cancelled.", DIM)
                continue

            # ── Keyboard shortcuts ────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    sm.save()
                    set_status("Saved with backup rotation.", GREEN)
                elif event.key == pygame.K_d:
                    if cur_nation:
                        txt   = format_discord_v2(cur_nation, sm.state)
                        fname = f"discord_{cur_nation['name'].replace(' ','_')}_T{turn}.txt"
                        with open(fname, "w", encoding="utf-8") as fo:
                            fo.write(txt)
                        set_status(f"Discord export → {fname}", CYAN)
                elif event.key == pygame.K_UP:
                    if sel_idx > 0:
                        load_nation(sel_idx - 1)
                elif event.key == pygame.K_DOWN:
                    if sel_idx < len(names) - 1:
                        load_nation(sel_idx + 1)
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_SPACE):
                    main_p.scroll.scroll += MAIN_H // 2
                    main_p.scroll.clamp()
                elif event.key == pygame.K_PAGEUP:
                    main_p.scroll.scroll -= MAIN_H // 2
                    main_p.scroll.clamp()

            # ── Left panel ───────────────────────────
            clicked = left.on_event(event)
            if clicked is not None:
                load_nation(clicked)

            if left.btn_save.on_event(event):
                sm.save()
                set_status("Saved. Backups rotated.", GREEN)
            if left.btn_disc.on_event(event):
                if cur_nation:
                    txt   = format_discord_v2(cur_nation, sm.state)
                    fname = f"discord_{cur_nation['name'].replace(' ','_')}_T{turn}.txt"
                    with open(fname, "w", encoding="utf-8") as fo:
                        fo.write(txt)
                    set_status(f"Discord export → {fname}", CYAN)
            if left.btn_init.on_event(event):
                if cur_nation:
                    n = initialize_settlements(cur_nation, sm.state, force=False)
                    if n > 0:
                        sm.mark_dirty()
                        sm.autosave()
                        main_p.set_items(build_render_items(cur_nation, sm.state))
                        set_status(f"Settlements created on {n} planet(s).", GREEN)
                    else:
                        set_status("Settlements already exist. Use force to re-init.", GOLD)

            # ── Main panel ───────────────────────────
            ed = main_p.on_event(event)
            if ed:
                edit_ov.open(ed["label"], ed["raw"], ed["meta"])

        # ── DRAW ─────────────────────────────────────
        draw_bg(screen)
        draw_top_bar(screen,
                     cur_nation["name"] if cur_nation else "—",
                     turn, year, quarter, sm._dirty)
        main_p.draw(screen)
        left.draw(screen, turn, year, quarter)
        edit_ov.draw(screen, dt)
        draw_status_bar(screen)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
