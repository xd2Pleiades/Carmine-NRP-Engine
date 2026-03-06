"""carmine.constants — colours, tables, formatting helpers"""
import sys, os, json, shutil, math, time, random
from pathlib import Path

# ── church tithe constants ───────────────────────────────────────────────────
CHRISTIAN_KEYWORDS=["christian","catholic","protestant","orthodox","evangelical","church"]
TITHE_RATE=0.10

# ── territory tables ─────────────────────────────────────────────────────────
_PLANET_TYPES=["Terrestrial","Continental","Arid","Desert","Ocean","Arctic","Toxic","Jungle","Barren","Gas Giant"]
_PLANET_SIZES=["Tiny","Small","Medium","Large","Huge"]
_CLIMATES=["Temperate","Arid","Oceanic","Arctic","Toxic","Jungle","Desert"]
_DISTRICT_TYPES=["Residential","Urban","Industrial Civilian","Industrial Military","Farming","Agricultural",
                 "Mining","Energy Plant","Power","Military","Research Lab"]
_PLATFORM_TYPES=["Mining","Hydroponics","Research","Dockyards"]

__all__ = [
    # paths & config
    'DEFAULT_STATE','BACKUP_COUNT','DISCORD_DIR',
    # layout
    'SW','SH','LWIDTH','TBAR_H','TABBAR_H','SBAR_H','FPS',
    'MAIN_X','MAIN_Y','MAIN_W','MAIN_H',
    'TABS','TABS_COLONY','TABS_CORP','GALACTIC_SUBS','GSUB_H',
    'PLAYER_NATIONS',
    # colours
    'BG','PANEL','BORDER','BORDER2','ACCENT','CYAN','TEAL','TEXT','DIM','DIM2',
    'BRIGHT','GREEN','RED_C','GOLD','SEL','HOVER','EDITBG','EDITBDR',
    'BTNBG','BTNHOV','BTNACC','BTNACC2','PURPLE','ORANGE','LIME',
    # format helpers
    'fmt_cr','fmt_pop','fmt_res','fmt_pct','bar_str','nation_tag',
    # resource/econ tables
    '_RESOURCES','RES_BASE_PRICE','ECON_MODELS',
    'DISTRICT_PROD','DISTRICT_CONS','DISTRICT_MINERAL_COST','DISTRICT_BUILD_TURNS','PLATFORM_PROD',
    # military tables
    'UNIT_CREW','UNIT_ALLOY_CON','GROUND_DIVISION_SIZE','GROUND_FOOD_PER_SOLDIER','GROUND_ALLOY_PER_DIVISION',
    # event tables
    '_COLONY_EVENTS',
    # helpers
    'years_elapsed','_avg_loyalty','is_colony','get_tabs',
    # tithe
    'CHRISTIAN_KEYWORDS','TITHE_RATE',
    # territory tables
    '_PLANET_TYPES','_PLANET_SIZES','_CLIMATES','_DISTRICT_TYPES','_PLATFORM_TYPES',
    # unit tables
    '_UNIT_CATS','_CAT_NORM','_UNIT_TYPES_BY_CAT','_UNIT_VETERANCY',
]



DEFAULT_STATE = str(Path(__file__).parent / "carmine_state_T5_Y2201Q1.json")
BACKUP_COUNT  = 5
DISCORD_DIR   = Path(__file__).parent / "discord_exports"
SW, SH        = 1280, 720
LWIDTH        = 240
TBAR_H        = 40
TABBAR_H      = 30
SBAR_H        = 22
FPS           = 60
MAIN_X = LWIDTH; MAIN_Y = TBAR_H + TABBAR_H
MAIN_W = SW - LWIDTH; MAIN_H = SH - TBAR_H - TABBAR_H - SBAR_H
TABS         = ["OVERVIEW","ECONOMY","MILITARY","TERRITORY","MARKET","GALACTIC","EVENTS"]
TABS_COLONY  = ["OVERVIEW","COLONY","MILITARY","TERRITORY","MARKET","GALACTIC","EVENTS"]
TABS_CORP    = ["OVERVIEW","ECONOMY","MILITARY","TERRITORY","MARKET","GALACTIC","CORP","EVENTS"]
GALACTIC_SUBS= ["OVERVIEW","PRICE REPORT"]
GSUB_H       = 22
PLAYER_NATIONS = {"Regnum Dei","Zenith Collective","Imperium Poenus Lunaria",
                  "Yorigami Inter-Planetary Industrial Enterprises","Union of the Red Horizon"}

BG=(8,12,20);PANEL=(12,18,28);BORDER=(28,52,80);BORDER2=(44,86,128);ACCENT=(190,38,25)
CYAN=(0,190,214);TEAL=(0,138,158);TEXT=(198,226,246);DIM=(84,114,136);DIM2=(50,72,92)
BRIGHT=(238,248,255);GREEN=(22,184,82);RED_C=(216,54,40);GOLD=(198,150,22)
SEL=(18,40,65);HOVER=(14,30,50);EDITBG=(5,14,28);EDITBDR=(0,172,194)
BTNBG=(18,36,56);BTNHOV=(28,54,82);BTNACC=(140,24,16);BTNACC2=(190,38,25)
PURPLE=(130,60,200);ORANGE=(200,100,30);LIME=(120,220,60)

def fmt_cr(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e15: return f"{v/1e15:.3f} Qcr"
    if a>=1e12: return f"{v/1e12:.3f} Tcr"
    if a>=1e9:  return f"{v/1e9:.3f} Bcr"
    if a>=1e6:  return f"{v/1e6:.3f} Mcr"
    if a>=1e3:  return f"{v/1e3:.2f} Kcr"
    return f"{v:.0f} cr"
def fmt_pop(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e9: return f"{v/1e9:.3f}B"
    if a>=1e6: return f"{v/1e6:.3f}M"
    if a>=1e3: return f"{v/1e3:.2f}K"
    return f"{v:.0f}"
def fmt_res(v):
    if v is None: return chr(8212)
    a=abs(v)
    if a>=1e9: return f"{v/1e9:.3f}B"
    if a>=1e6: return f"{v/1e6:.3f}M"
    if a>=1e3: return f"{v/1e3:.2f}K"
    return f"{v:.2f}"
def fmt_pct(v): return f"{v*100:+.2f}%" if v!=0 else "0.00%"
def bar_str(pct,w=18):
    pct=max(0.0,min(1.0,pct)); f=round(pct*w)
    return "█"*f+"░"*(w-f)
def nation_tag(name):
    words=name.split()
    if len(words)>=2: return "".join(w[0].upper() for w in words[:4])
    return name[:4].upper()

_RESOURCES=["Food","Minerals","Energy","Alloys","Consumer Goods"]
RES_BASE_PRICE={"Food":1.0,"Minerals":2.0,"Energy":4.0,"Alloys":5.0,"Consumer Goods":2.0}
ECON_MODELS=["PLANNED","MARKET","MIXED","COLONY_START"]

# ── district & platform production tables ─────────────────────────────────────
DISTRICT_PROD={
    "Farming":            {"Food":50e6},
    "Agricultural":       {"Food":40e6},
    "Mining":             {"Minerals":20e6},
    "Industrial Civilian":{"Alloys":8e6,"Consumer Goods":12e6},
    "Industrial Military":{"Alloys":18e6},
    "Energy Plant":       {"Energy":25e6},
    "Power":              {"Energy":20e6},
    "Urban":{}, "Residential":{}, "Military":{}, "Research Lab":{},
}
DISTRICT_CONS={
    "Farming":            {"Energy":2e6},
    "Agricultural":       {"Energy":1e6},
    "Mining":             {"Energy":4e6},
    "Industrial Civilian":{"Minerals":10e6,"Energy":8e6},
    "Industrial Military":{"Minerals":20e6,"Energy":12e6},
    "Energy Plant":       {"Minerals":3e6},
    "Power":              {"Minerals":2e6},
}
DISTRICT_MINERAL_COST={"Farming":20,"Agricultural":15,"Mining":30,"Industrial Civilian":40,
    "Industrial Military":60,"Energy Plant":35,"Power":25,"Urban":10,"Residential":8,
    "Military":50,"Research Lab":45}
DISTRICT_BUILD_TURNS={"Farming":2,"Agricultural":2,"Mining":3,"Industrial Civilian":4,
    "Industrial Military":5,"Energy Plant":3,"Power":2,"Urban":2,"Residential":1,
    "Military":4,"Research Lab":5}
PLATFORM_PROD={"Mining":{"Minerals":30e6},"Hydroponics":{"Food":60e6},"Research":{},"Dockyards":{}}

# ── military consumption tables ───────────────────────────────────────────────
# Food = crew headcount, Alloys = per unit (not per count)
UNIT_CREW = {
    "Siegebreaker":85000,"World Cracker":85000,"Dreadnaughts":50000,"Dreadnaught":50000,
    "Battleship":50000,"Battlecruiser":45000,"Heavy Cruiser":40000,"Cruiser":35000,
    "Light Cruiser":10000,"Destroyer":500,"Frigate":150,"Corvette":50,
    "Space patrol Vessels":10,"Space Patrol Vessel":10,"Shipyard Tender":50000,
    "Transport Vessel":10,"Dockyard":100000,
    "Fighter Aircraft":1,"Fighter Aircrafts":1,"Tactical Bomber":4,"Strategic Bomber":4,
    "Strategic Bombers":4,"Attack Aircraft":2,"Reconnaissance & Surveillance Aircraft":2,
    "Unmanned Aerial Vehicle":0,"Tanker Aircraft":2,"Gunship":5,"Transport Aircraft":10,
}
UNIT_ALLOY_CON = {
    "Siegebreaker":100000,"World Cracker":100000,"Dreadnaughts":50000,"Dreadnaught":50000,
    "Battleship":50000,"Battlecruiser":45000,"Heavy Cruiser":30000,"Cruiser":20000,
    "Light Cruiser":10000,"Destroyer":5000,"Frigate":2500,"Corvette":1000,
    "Space patrol Vessels":500,"Space Patrol Vessel":500,"Shipyard Tender":50000,
    "Transport Vessel":50000,"Dockyard":50000,
    "Fighter Aircraft":100,"Fighter Aircrafts":100,"Tactical Bomber":250,"Strategic Bomber":500,
    "Strategic Bombers":500,"Attack Aircraft":300,"Reconnaissance & Surveillance Aircraft":80,
    "Unmanned Aerial Vehicle":50,"Tanker Aircraft":300,"Gunship":250,"Transport Aircraft":250,
}
GROUND_DIVISION_SIZE = 10000  # soldiers per division
GROUND_FOOD_PER_SOLDIER = 1   # food units per soldier per turn
GROUND_ALLOY_PER_DIVISION = 2000  # alloys per division per turn

# ── colony event table ────────────────────────────────────────────────────────
_COLONY_EVENTS=[
    (1,1,"Catastrophic Failure",{"colonization_pct":(-15,-10),"pop_change":(-0.20,-0.10)},RED_C),
    (2,3,"Supply Shortage",{"colonization_pct":(-5,-2)},  (200,80,40)),
    (4,5,"Harsh Conditions",{"colonization_pct":(-3,-1)}, GOLD),
    (6,10,"Steady Progress",{"colonization_pct":(1,3)},   DIM),
    (11,15,"Good Survey",{"colonization_pct":(2,5)},      GREEN),
    (16,18,"Resource Discovery",{"colonization_pct":(3,6),"mineral_bonus":(10,30)}, CYAN),
    (19,19,"Population Surge",{"colonization_pct":(2,4),"pop_change":(0.05,0.15)}, GREEN),
    (20,20,"Golden Founding",{"colonization_pct":(5,10),"pop_change":(0.10,0.20),"mineral_bonus":(20,50)}, GOLD),
]

# ── helpers ───────────────────────────────────────────────────────────────────
def years_elapsed(state): return (state.get("turn",1)-1)*0.25

def _avg_loyalty(nation):
    sp=nation.get("species_populations") or []
    if not sp: return 50.0
    total=sum(s.get("population",0) for s in sp) or 1
    return sum(s.get("loyalty",50)*s.get("population",0) for s in sp)/total

def is_colony(nation): return bool(nation.get("is_colony_start"))

def get_tabs(nation):
    if is_colony(nation): return TABS_COLONY
    if nation.get("is_megacorp") or "corporate_data" in nation: return TABS_CORP
    return TABS

# ── unit builder tables ──────────────────────────────────────────────────────
_UNIT_CATS=["Spacefleet","Aerospace","Ground Forces"]
# Normalise JSON category aliases to canonical _UNIT_CATS values
_CAT_NORM={"Navy":"Spacefleet","Spacefleet":"Spacefleet",
           "Air Force":"Aerospace","Aerospace":"Aerospace",
           "Ground Forces":"Ground Forces","Ground":"Ground Forces","Army":"Ground Forces"}
# _TIER_MULT and _CORP_EV_TABLE moved to corporateAlpha0671.py
_UNIT_TYPES_BY_CAT={
    "Spacefleet":["Corvette","Frigate","Destroyer","Light Cruiser","Cruiser","Heavy Cruiser",
                  "Battlecruiser","Battleship","Dreadnaught","Siegebreaker","Transport Vessel",
                  "Shipyard Tender","Space patrol Vessels"],
    "Aerospace":["Fighter Aircraft","Tactical Bomber","Strategic Bomber","Attack Aircraft",
                 "Reconnaissance & Surveillance Aircraft","Unmanned Aerial Vehicle",
                 "Tanker Aircraft","Gunship","Transport Aircraft"],
    "Ground Forces":["Infantry Division","Armored Division","Artillery Division",
                     "Marines Division","Special Forces Division"],
}
_UNIT_VETERANCY=["Green","Regular","Veteran","Elite","Legendary"]

# compute_corp_income/market_cap/roll_corp_events moved to corporateAlpha0671.py

