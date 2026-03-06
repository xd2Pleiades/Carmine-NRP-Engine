"""carmine.npc — NPC nation military AI (budget-driven force building)"""
import random
from constants import *
from economy import (compute_trade, compute_planet_local_market, compute_debt,
                     compute_church_tithe, compute_tithe_income, fmt_cr)

# ── turn advancement ──────────────────────────────────────────────────────────
_NPC_UNITS = {
    "Corvette":           {"cost": 2e9,   "upkeep": 0.2e9,  "cat": "Spacefleet",    "tier": 1},
    "Frigate":            {"cost": 5e9,   "upkeep": 0.5e9,  "cat": "Spacefleet",    "tier": 2},
    "Destroyer":          {"cost": 12e9,  "upkeep": 1.0e9,  "cat": "Spacefleet",    "tier": 3},
    "Light Cruiser":      {"cost": 30e9,  "upkeep": 2.5e9,  "cat": "Spacefleet",    "tier": 4},
    "Heavy Cruiser":      {"cost": 80e9,  "upkeep": 6e9,    "cat": "Spacefleet",    "tier": 5},
    "Carrier":            {"cost": 200e9, "upkeep": 15e9,   "cat": "Spacefleet",    "tier": 6},
    "Fighter Wing":       {"cost": 3e9,   "upkeep": 0.3e9,  "cat": "Aerospace",     "tier": 1},
    "Bomber Wing":        {"cost": 8e9,   "upkeep": 0.8e9,  "cat": "Aerospace",     "tier": 2},
    "Interceptor Wing":   {"cost": 6e9,   "upkeep": 0.6e9,  "cat": "Aerospace",     "tier": 2},
    "Infantry Division":  {"cost": 1e9,   "upkeep": 0.1e9,  "cat": "Ground Forces", "tier": 1},
    "Artillery Brigade":  {"cost": 3e9,   "upkeep": 0.3e9,  "cat": "Ground Forces", "tier": 2},
    "Armoured Division":  {"cost": 8e9,   "upkeep": 0.7e9,  "cat": "Ground Forces", "tier": 3},
    "Marine Division":    {"cost": 5e9,   "upkeep": 0.5e9,  "cat": "Ground Forces", "tier": 2},
}
_NPC_FORCE_RATIO = {"Spacefleet": 0.45, "Aerospace": 0.20, "Ground Forces": 0.35}
_VET_LADDER = ["Green","Regular","Veteran","Elite"]

def _npc_pick_unit(budget, cat, rng):
    options = [(name,d) for name,d in _NPC_UNITS.items() if d["cat"]==cat and d["cost"]<=budget]
    if not options: return None, None
    options.sort(key=lambda x: x[1]["tier"])
    weights = [1.5**i for i in range(len(options))]
    total = sum(weights); r = rng.random()*total; acc = 0
    for (name,d),w in zip(options, weights):
        acc += w
        if r <= acc: return name, d
    return options[-1]

def npc_military_ai(nation, state, t, y, q):
    """Build forces until upkeep = 50% of net income. Never disband. Returns event list."""
    evs = []
    ipeu  = nation.get("base_ipeu", 0.0)
    sfund = nation.get("strategic_fund", 0.0)
    exp   = nation.get("expenditure") or {}
    afd   = list(nation.get("active_forces_detail") or [])
    rng   = random.Random(hash((nation["name"], t, "npc_mil")))
    if ipeu <= 0: return evs

    # ── Compute net income (same formula as economy tab) ─────────────────────
    rb        = nation.get("research_budget", 0.0)
    total_exp = sum(exp.values()) * ipeu + rb
    trade     = compute_trade(nation, state.get("trade_routes", []))
    _, tax    = compute_planet_local_market(nation, state, ipeu)
    tithe_out = compute_church_tithe(nation, state)
    tithe_in  = compute_tithe_income(nation, state)
    debt      = compute_debt(nation, ipeu)
    net_income = ipeu + trade["net"] + tax + tithe_in - total_exp - debt["q_interest"] - tithe_out
    # upkeep ceiling = 50% of net income (floor at 0 so we always allow some building)
    upkeep_ceiling = max(net_income * 0.50, 0.0)

    # ── Current total upkeep ──────────────────────────────────────────────────
    cur_upkeep = sum(_NPC_UNITS.get(u.get("unit", ""), {}).get("upkeep", 0.5e9) for u in afd)

    # ── Build loop: keep commissioning until ceiling is reached ───────────────
    # Cap at 5 new units per call to avoid infinite loops on npc automate
    builds = 0
    while cur_upkeep < upkeep_ceiling and sfund > 0 and builds < 5:
        # headroom = how much more upkeep we can afford
        headroom = upkeep_ceiling - cur_upkeep
        # pick category most underrepresented vs target ratio
        cat_counts = {c: sum(1 for u in afd if u.get("category") == c) for c in _NPC_FORCE_RATIO}
        total_units = max(1, len(afd))
        cat_deficit = {c: _NPC_FORCE_RATIO[c] - cat_counts[c] / total_units for c in _NPC_FORCE_RATIO}
        cats = list(cat_deficit.keys()); weights = [max(0, cat_deficit[c]) for c in cats]
        if sum(weights) == 0: weights = [1/3] * 3
        total_w = sum(weights); r = rng.random() * total_w; acc = 0; chosen_cat = cats[0]
        for c, w in zip(cats, weights):
            acc += w
            if r <= acc: chosen_cat = c; break
        # affordable = unit whose upkeep fits headroom AND cost fits sfund
        affordable = [(name, d) for name, d in _NPC_UNITS.items()
                      if d["cat"] == chosen_cat and d["upkeep"] <= headroom and d["cost"] <= sfund]
        if not affordable: break  # nothing fits — stop building
        # pick highest-tier affordable unit (weighted)
        affordable.sort(key=lambda x: x[1]["tier"])
        weights2 = [1.5 ** i for i in range(len(affordable))]
        total2 = sum(weights2); r2 = rng.random() * total2; acc2 = 0; uname, udata = affordable[-1]
        for (nm, d), w2 in zip(affordable, weights2):
            acc2 += w2
            if r2 <= acc2: uname, udata = nm, d; break
        # commission
        new_unit = {"gid": abs(hash((nation["name"], t, uname, builds))) % 999999,
                    "unit": uname, "category": chosen_cat, "count": 1,
                    "veterancy": "Green", "combat_turns": 0, "in_combat": False,
                    "promotion_pending": False, "notes": "NPC auto-raised"}
        afd.append(new_unit)
        sfund -= udata["cost"]
        cur_upkeep += udata["upkeep"]
        builds += 1
        evs.append({"turn": t, "year": y, "quarter": q, "type": "NPC", "nation": nation["name"],
                    "roll": "—", "label": "Force Raised",
                    "description": f"{nation['name']} commissioned {uname} ({chosen_cat})  cost {fmt_cr(udata['cost'])}",
                    "col_rgb": list(LIME)})

    nation["active_forces_detail"] = afd
    nation["strategic_fund"] = sfund - cur_upkeep  # deduct this turn's upkeep

    # ── Veterancy tick ────────────────────────────────────────────────────────
    for u in afd:
        u["combat_turns"] = u.get("combat_turns", 0) + 1
        vet = u.get("veterancy", "Green")
        vi  = _VET_LADDER.index(vet) if vet in _VET_LADDER else 0
        thresholds = [0, 8, 20, 40]
        if vi < len(_VET_LADDER)-1 and u["combat_turns"] >= thresholds[vi] and rng.random() < 0.08:
            u["veterancy"] = _VET_LADDER[vi+1]
            evs.append({"turn": t, "year": y, "quarter": q, "type": "NPC", "nation": nation["name"],
                        "roll": "—", "label": "Unit Promoted",
                        "description": f"{nation['name']} {u.get('unit','?')} promoted to {u['veterancy']}",
                        "col_rgb": list(CYAN)})

    return evs
