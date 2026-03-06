TODO 0.6.1.md
Bugs Report
Editing IPEU base crashes the engine

log:
Traceback (most recent call last):
  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 2522, in <module>
    main()
    ~~~~^^
  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 2369, in main
    if n and apply_edit(n,main_.edit.meta,result):
             ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 1126, in apply_edit
    last=path[-1]
         ~~~~^^^^
IndexError: list index out of range
PS C:\Users\acer> 

When editing conscription % in species


  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 2522, in <module>
    main()
    ~~~~^^
  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 2369, in main
    if n and apply_edit(n,main_.edit.meta,result):
             ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\acer\Desktop\Carmine NRP\PYTHON\Tests\vAlpha0.6.6.py", line 1126, in apply_edit
    last=path[-1]
         ~~~~^^^^
IndexError: list index out of range


(Before 0.6.1) -> 0.6.7.8 
Features
- Make a main menu, and select, edit nations to view nations
- Galactic Trade Confederation, as Galactic Creditor, currently Regnum Dei pays them and has a debt of 6 T since T1
- Galactic Market Report
  - Explain Reasons why
- Add to remove systems
- Update Discord Output, use current: NRP_Profile_Discord_Output.md
- Add assign/create/edit/ unit group in military tab
  - Remove Qty in record but instead split all (run upon initialization to split them up)
  - Add remove unit button in add/edit unit
  - Build unit queue
    - Do not remove Qty in add/edit unit

# LONG TERM
RESEARCH TACKLE
Research Tech Tree
Research Custom Tech
- Ship/Aircraft Unit Creator


Ship
```
Speed:
Components:
Hull: HP
Size:
Armor:
Hull Type: T0
Fire Control System:
Complement:
- 25% Officers
- 50% Crew
- 25% Marines

Engine: 
Drive:

Armaments (Give Defaults)
- N mm 
```

Aircraft
```
Speed
Range: (Turns until Refuel)
HP:

Armament:
- N mm
```