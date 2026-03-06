"""carmine.territory — planet/system/platform helper tools"""
import random
from constants import *

# ── territory tools ───────────────────────────────────────────────────────────
def _rng_name(prefix,idx):
    suf=["Alpha","Beta","Gamma","Delta","Epsilon","Zeta","Prime","Secundus","Tertius","IV","V","VI"]
    return f"{prefix} {suf[idx%len(suf)]}"

def randomize_planet(planet,total_pop):
    planet["type"]=random.choice(_PLANET_TYPES); planet["size"]=random.choice(_PLANET_SIZES)
    planet["climate"]=random.choice(_CLIMATES); planet["habitability"]=round(random.uniform(10,95),1)
    planet["devastation"]=round(random.uniform(0,15),1); planet["crime_rate"]=round(random.uniform(0,25),1)
    planet["unrest"]=round(random.uniform(0,20),1)
    sz={"Tiny":0.05,"Small":0.10,"Medium":0.20,"Large":0.35,"Huge":0.50}
    pp=total_pop*sz.get(planet.get("size","Medium"),0.2)*(planet.get("habitability",50)/100.0)
    planet["pop_assigned"]=round(pp); n_s=random.randint(1,3); setts=[]; rem=pp
    for i in range(n_s):
        s_pop=rem/(n_s-i); n_d=random.randint(2,6)
        districts=[{"type":random.choice(_DISTRICT_TYPES),"status":"Operational","notes":"","built_turn":0,"workforce":0} for _ in range(n_d)]
        setts.append({"name":_rng_name(planet.get("name","S"),i),"population":round(s_pop),"loyalty":round(random.uniform(40,85),1),"amenities":round(random.uniform(30,80),1),"districts":districts})
        rem-=s_pop
    planet["settlements"]=setts; planet.setdefault("platforms",[])

def add_system(nation,name=""):
    si=len(nation.get("star_systems",[]))
    if not name: name=_rng_name("System",si)
    nation.setdefault("star_systems",[]).append({"name":name,"notes":"","coordinates":"","planets":[]})

def add_planet(system,nation_pop,name=""):
    pi=len(system.get("planets",[]))
    if not name: name=_rng_name(system["name"],pi)
    p={"name":name,"type":"Terrestrial","size":"Medium","climate":"Temperate","habitability":50.0,
       "devastation":0.0,"crime_rate":5.0,"unrest":5.0,"pop_assigned":0,"settlements":[],"platforms":[]}
    randomize_planet(p,nation_pop); system.setdefault("planets",[]).append(p)

def add_platform(planet,ptype="Mining"):
    planet.setdefault("platforms",[]).append({"type":ptype,"status":"Operational","name":f"{ptype} Platform"})

