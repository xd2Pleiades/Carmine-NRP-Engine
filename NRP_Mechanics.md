# NATIONAL PROFILE - Q1 [YEAR]
```
  Species          : --- Species (%)
  Population       : --- Total Population
  Pop Growth       : --- Average % population growth
  Homeworld        : --- Homeworld
  Civilisation     : --- Civ Tier
  Tier             : --- Civ Tier
  Economic Model   : --- Economic Model, PLANNED, MIXED, MARKET, COLONY_START
  Status           : --- Economic Status, RAPIDLY FALLING, RAPIDLY RISING, STABLE, FALLING, RISING
```
- Planned economies has total control of their economic status, they can issue economic projects at a larger scale and largely relies on its resources.
    This is the economy that works with:
    Bureaucratic_Efficiency
        Greater economic output in the economy, and lastly can forcefully migrate populations.
    Construction_Efficiency
        Faster construction, lowering material costs and turns. 
        Mineral cost per district/building lowers
    Research_Efficiency
        More aligned researchers, faster research speed. Lowers cr to research point conversion.
    Resource Efficiency
        More industrial capacity and higher loyalty == 100% loyalty == 125% resource production efficiency (overflow loyalty too turns)
    Negative efficiency reduces output.
    Distribution
        More loyalty, replaces consumer goods ownership. Than MIXED and MARKET this economy can distribute food, consumer goods than automated through economic factors to raise loyaly, population growth.
- Market economies works with:
    Trade = cr from import and export, tax revenue (ALL ECONMICMODS HAS THIS) however market economies has better modifiers.
        Trade balance = import/export
        Subsidies, Investments
        Planets play more part, with it, its state actors
            Planets produces local_market_output
            Planets has domestic_production and foreign_import and it must compete against it
            In the end the country receive tax trades
            Attractiveness creates economic activity and more government revenue
- Mixed economies inherit everything except distribution.
- Colony start economies (whom starting one vessel for colonization)
    Focused on survival and resources, cr may matter only in importation and exportation. Budget does not appear here, only distribution of  resources.

Trade Routes
    Resources, any resources
    Resource Trade: Auto / Import + Export
    Resource Mode: Auto Calculated with Events
        Resource Unit: In % or raw numbers (with or without commas)
    Taxes by both naton:
    Transit Nations
    Piracy + Patrol Vessel allotment = Piracy events

Projects applies too nations, and as the GM I can apply effects based on it.

# ECONOMY
```
  IPEU (base)      : --- cr - GDP equivalent
  IPEU Growth      : ---
  IPEU per Capita  : --- cr
  Trade Revenue    : --- cr
   - Exports       : --- cr
   - Imports       : --- cr
  Total Expenditure: --- cr
  Research Budget  : --- cr / turn
  Net Balance      : --- cr
```


## EXPENDITURE & BREAKDOWN
```
  Military               %  ████████████████████  --- cr - MORE money spent means more combat power and unit morale (I have no valies given here for conversion)
  Infrastructure         %  ████████████████████  --- cr - MORE money spent means more trade and distribution (I have no valies given here for conversion)
  Agriculture            %  ████████████████████  --- cr - MORE money spent means more food (I have no valies given here for conversion)
  Industry               %  ████████████████████  --- cr - MORE money spent means more energy, more alloy and more consumer goods, and more resource tied to this category. (I have no valies given here for conversion)
  Population Development %  ████████████████████  --- cr - MORE money spent means more loyalty and happiness and less bad civil events
  Others                 %  ████████████████████  --- cr
  ─────────────────────────────────────────────────────────────
  TOTAL                          ---%            (--- cr)
```
## ECONOMIC PROJECTS
```
- Free form.

## FISCAL REPORT
```
  Debtor           : --- YOUR DEBTOR, can be replicated when multiple debtors
  Debt Balance     : ---
  Debt Load        : ---
  Interest Rate    : ---
  Quarterly Int.   : ---
  Debt Repayment   : ---
  ─────────────────────────────────────────────────────────────
  Strategic Fund   : --- cr
  Fund Δ this turn : --- cr
```

# TERRITORIES
```
STAR SYSTEMS AND STRS
```
```
  Home System: ---
  Planets:
      - --- Planet Name
        System         :
        Type           : ---
        Size           : ---
        Habitability   : ---
        Devastation    : ---
        Crime Rate     : ---
        Unrest         : ---
        Population     : ---
         - --- Population Name | Size | Loyalty | Happiness
    Homeworld: ---
      Population    : ---
      Settlements   : ---
      Urban Districts:
        - --- Provides population capacity
      Industrial Districts:
        - --- Provides 50/50 alloys and consumer goods
      Agricultural Districts:
        - --- Provides food
      Military Districts:
        - --- Provides military efficiency
    Other planets
```
## Space Platforms (Requires, space platform)
```
- Mining, Research, Dockyards, Hydroponics
```
- In UI must have territory manager, addable, editable star systems, planets, districts
- When empty, the engine randomize itself

# NATIONAL DEMOGRAPHICS
  Total Population     : ---
  Loyalty Modifier     : ---

  --- 👑 ---
    Population       : ---
    Share            : --- Dominant, Majority, Significant, Minority
    Growth Rate      : ---
    Culture          : ---
    Language         : ---
    Religion         : ---
    Loyalty          : --- Unrest * Consumer Goods
    Happiness        : --- Crime * Unrest / Consumer Goods

  --- 👑 ---
    Population       : ---
    Share            : --- Dominant, Majority, Significant, Minority
    Growth Rate      : ---
    Culture          : ---
    Language         : ---
    Religion         : --- Unrest * Consumer Goods
    Loyalty          : --- Unrest * Consumer Goods
    Happiness        : --- Crime * Unrest / Consumer Goods


# MILITARY
## SPACEFLEET
  --- (Fleet Name)
    - Ship Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

## AEROSPACE FORCES
  --- (Wing Name)
    - Aircraft Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

## GROUND FORCES
  --- (Division Name)
    - Unit Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

# ARSENAL
  --- (Asset Name)
  Type | Size (Large, Medium, Small) | Crew | Maintenance | Production Time

# RESEARCH
  RP per turn      : ---
  .00000001 RP Cost        : --- cr
  ─────────────────────────────────────────────────────────────
  Active Projects:
    --- (Project Name)
      Field    : ---
      Progress : --- %
      Benefits : ---
  Completed Projects:
    --- (Project Name)
      Field    : ---
      Benefits : ---

EVENTS: d20 determination
    Galatic Markets
        Price shocks
        Galactic Stockpile Updates - Galactic 
    Planetside Events
    Resource Events
    Civic Events (Populatin inside district, settlement, planet, system wide)

# TODO:
    Must have a UI
    Must have a have a 5 rotating backup and read this file: carmine_state_T5_Y2201Q1.json
    Must have a Discord Output exactly this:
 # NATIONAL PROFILE - Q1 [YEAR]
  Species          : --- Species (%)
  Population       : --- Total Population
  Pop Growth       : --- Average % population growth
  Homeworld        : --- Homeworld
  Civilisation     : --- Civ Tier
  Tier             : --- Civ Tier
  Economic Model   : --- Economic Model
  Status           : --- Economic Status

 # ECONOMY
  IPEU (base)      : --- cr
  IPEU Growth      : --- % per turn
  IPEU per Capita  : --- cr IPEU / pop
  Trade Revenue    : --- cr
   - Exports       : --- cr
   - Imports       : --- cr
  Total Expenditure: --- cr
  Research Budget  : --- cr / turn
  Net Balance      : --- cr

 ## EXPENDITURE & BREAKDOWN
  Military               %  ████████████████████  --- cr
  Infrastructure         %  ████████████████████  --- cr
  Agriculture            %  ████████████████████  --- cr
  Industry               %  ████████████████████  --- cr
  Population Development %  ████████████████████  --- cr
  Others                 %  ████████████████████  --- cr
  ─────────────────────────────────────────────────────────────
  TOTAL                          ---%            (--- cr)

 ## ECONOMIC PROJECTS
  ---
  ─────────────────────────────────────────────────────────────
  TOTAL                          ---%            (--- cr)
 ## FISCAL REPORT
  Debtor/ Creditor     : --- (Debtor/Creditor)
  Debt Balance         : ---
  Debt Load            : ---
  Interest Rate        : ---
  Quarterly Int.       : ---
  Debt Repayment       : ---
  ─────────────────────────────────────────────────────────────
  Strategic Fund   : --- cr
  Fund Δ this turn : --- cr

 ## RESOURCES & STOCKPILES
  Food Stockpile            : ---
  Food Production per turn  : ---
  Food Consumption per turn : ---
  Food Net per turn         : ---
  Food Trend                : ---
  Food Export               : --- cr

  Minerals Stockpile        : ---
  Minerals Production per turn: ---
  Minerals Consumption per turn: ---
  Minerals Net per turn     : ---
  Minerals Trend            : ---
  Minerals Export           : --- cr

  Energy Stockpile          : ---
  Energy Production per turn: ---
  Energy Consumption per turn: ---
  Energy Net per turn       : ---
  Energy Trend              : ---
  Energy Export             : --- cr

  Alloys Stockpile          : ---
  Alloys Production per turn: ---
  Alloys Consumption per turn: ---
  Alloys Net per turn       : ---
  Alloys Trend              : ---
  Alloys Export             : --- cr

  Consumer Goods Stockpile        : ---
  Consumer Goods Production/turn  : ---
  Consumer Goods Consumption/turn : ---
  Consumer Goods Net per turn     : ---
  Consumer Goods Trend            : ---
  Consumer Goods Export           : --- cr

 # TERRITORIES
  Home System: ---
  Planets:
      - --- Planet Name
        Type          : ---
        Size          : ---
        Habitability   : ---
        Devastation     : ---
        Crime Rate     : ---
        Unrest         : ---
        Population      : ---
         - --- Population Name | Size | Loyalty | Happiness
    Homeworld: ---
      Population    : ---
      Settlements   : ---
      Urban Districts:
        - --- Provides population capacity
      Industrial Districts:
        - --- Provides 50/50 alloys and consumer goods
      Agricultural Districts:
        - --- Provides food
      Military Districts:
        - --- Provides military efficiency

 # NATIONAL DEMOGRAPHICS
  Total Population     : ---
  Loyalty Modifier     : ---

  --- 👑 ---
    Population       : ---
    Share            : --- Dominant, Majority, Significant, Minority
    Growth Rate      : ---
    Culture          : ---
    Language         : ---
    Religion         : ---
    Loyalty          : --- Unrest * Consumer Goods
    Happiness        : --- Crime * Unrest / Consumer Goods

  --- 👑 ---
    Population       : ---
    Share            : --- Dominant, Majority, Significant, Minority
    Growth Rate      : ---
    Culture          : ---
    Language         : ---
    Religion         : --- Unrest * Consumer Goods
    Loyalty          : --- Unrest * Consumer Goods
    Happiness        : --- Crime * Unrest / Consumer Goods

 # MILITARY
 ## SPACEFLEET
  --- (Fleet Name)
    - Ship Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

 ## AEROSPACE FORCES
  --- (Wing Name)
    - Aircraft Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

## GROUND FORCES
  --- (Division Name)
    - Unit Name | Type | Size | Veterancy | Strength | Maintenance | Training Time

 # ARSENAL
  --- (Asset Name)
  Type | Size (Large, Medium, Small) | Crew | Maintenance | Production Time

 # RESEARCH
  RP per turn      : ---
  .00000001 RP Cost        : --- cr
  ─────────────────────────────────────────────────────────────
  Active Projects:
    --- (Project Name)
      Field    : ---
      Progress : --- %
      Benefits : ---
  Completed Projects:
    --- (Project Name)
      Field    : ---
      Benefits : ---