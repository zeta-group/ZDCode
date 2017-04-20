# ZDCode
----
## About
ZDCode is a [ZDoom](http://zdoom.org) [DECORATE](https://zdoom.org/wiki/DECORATE_format_specifications)
compiler written by Gustavo6046 (Gustavo Rehermann) in 2017. It's purpose is to
shorten and make DECORATE writing convenient while making it similar to DECORATE.

It's just DECORATE, with a bit of sugar. :)

## Syntax

Symbols determine how actors, functions, and other things are recognized and
defined, due to pyparsing's limited capabilities.

* `%`    -> actor (`%actor :inherit ->replace *doomednum { stuff };`)
* `$`    -> function (`$func(args) {states};`)
* `*`    -> positive actor flag (`*flag;`)
* `!`    -> negative actor flag (`!flag;`)
* `&`    -> actor property (`&name=value;`)
* `#`    -> state label (`#label {states};`)
* `:`    -> state (`:^RAW DECORATE;` for raw DECORATE, `:(funcname)(args);`
for function call, `:? arg == num -> label;` for conditional jump that
checks if a variable is equal to a number before jumping to a state or
number, otherwise `:SPRT F 0 [Key1] [Key2(Arg)] Action(arg1, arg2...);`,
and yes, keywords are between square brackets)

Whitespace is ignored.

For all functions you can reference an argument in an action via `"argname"`. e.g.
`A_JumpIfInventory("argname", 0, "argFalse")`, because of how ZDScript is converted
to a similar DECORATE.

For an example of ZDCode.

  %FlemCell : Ammo *5251 {
    &Inventory.Amount = 8;
    &Inventory.MaxAmount = 80;
    &Ammo.BackpackMaxAmount = 160;
  };

  %FlemPoweredBootspork : SuperBootspork *5250 {
    &Damage=6;
    &Weapon.AmmoType="FlemCell";
    &Weapon.AmmoUse=1;
    &Weapon.SlotNumber=1;
    &Weapon.SlotPriority=0.5;

    !WEAPON.WIMPY_WEAPON;

    $Recharge(amount) {
      :?amount==0->QuickRecharge;
      :TNT1A0 @A_GiveInventory("FlemCell", 1);
      :TNT1A0 @A_TakeInventory("amount", 1);
      :?amount==1->F_Recharge;
    };

    #QuickRecharge {
      :(Recharge)(5);
      :^Goto Ready;
    };

    #AltFire {
      :SAWGAB5 @A_Saw;
      :TNT1A0 @A_JumpIfCloser(64, "GetFlem");
      :^Goto Ready;
    };

    #GetFlem {
      :(Recharge)(2);
      :TNT1A0 @A_Refire("AltFire");
      :^Goto Ready;
    };
  };

## How-to
Converting an input .zdc file to an output .dec file is simple:

    python zdcode.py <input> <output>

Then you can use the .dec file as a DECORATE lump in your own WAD!

## Copyright
Check `license.md` for more.
©2017 Gustavo Ramos "Gustavo6046" Rehermann. MIT license.
