# ZDCode 2.0
## The language that compiles to ye olde DECORATE!

Take this example:
```
    class RunZombie inherits ZombieMan replaces ZombieMan #2055
    {
        set Gravity to 0.4; // high up...
        set Speed to 0;
        is NOBLOCKMONST;
        set Speed to 0;
    
        label See
        {
            call SeeCheck;
            POSS AB 5 A_Recoil(-0.7);
            call SeeCheck;
            POSS AB 4 A_Recoil(-0.7);
            call SeeCheck;
            POSS ABCD 3 A_Recoil(-0.7);
            call SeeCheck;
            goto RunLoop;
        };

        function SeeCheck
        {
            TNT1 A 0 A_Chase;
            POSS A 0 A_FaceTarget();
        };

        function ZombieJump
        {
            if ( health > 5 )
                return;

            while ( z == floorz )
            {
                POSS A 5 [Bright];
                POSS A 11 ThrustThingZ(0, 30, 0, 1);
            };
            
            POSS AB 2 A_Chase;
        };

        label RunLoop
        {
            x 2
            {
                POSS ABCD 2 A_Recoil(-0.7);
                call SeeCheck;
            };

            call ZombieJump;
            loop;
        };
    }
```

This is what happens when that beauty goes through **ZDCode 2.0**:

```
    Actor _Call0 : Inventory {Inventory.MaxAmount 1}
    Actor _Call1 : Inventory {Inventory.MaxAmount 1}
    Actor _Call2 : Inventory {Inventory.MaxAmount 1}
    Actor _Call3 : Inventory {Inventory.MaxAmount 1}
    Actor _Call4 : Inventory {Inventory.MaxAmount 1}
    Actor _Call5 : Inventory {Inventory.MaxAmount 1}


    Actor RunZombie : ZombieMan replaces ZombieMan 2055
    {
        Gravity 0.4
        Speed 0
        
        +NOBLOCKMONST
        
        States {
            F_SeeCheck:
                TNT1 A 0 A_Chase
                POSS A 0 A_FaceTarget
                TNT1 A 0 A_JumpIfInventory("_Call0", 1, "_CLabel0")
                TNT1 A 0 A_JumpIfInventory("_Call1", 1, "_CLabel1")
                TNT1 A 0 A_JumpIfInventory("_Call2", 1, "_CLabel2")
                TNT1 A 0 A_JumpIfInventory("_Call3", 1, "_CLabel3")
                TNT1 A 0 A_JumpIfInventory("_Call4", 1, "_CLabel4")
                Stop
            
                F_ZombieJump:
                TNT1 A 0 A_JumpIf(!(health > 5), 2)
                TNT1 A 0 A_JumpIfInventory("_Call5", 1, "_CLabel5")
                Stop
                TNT1 A 0
            _WhileBlock0:
                TNT1 A 0 A_JumpIf(!(z == floorz), 4)
                POSS A 5  Bright
                POSS A 11 ThrustThingZ(0, 30, 0, 1)
                TNT1 A 0 A_Jump(255, "_WhileBlock0")
                TNT1 A 0
                POSS A 2 A_Chase
                POSS B 2 A_Chase
                TNT1 A 0 A_JumpIfInventory("_Call5", 1, "_CLabel5")
                Stop
            
            See:
                TNT1 A 0 A_GiveInventory("_Call0")
                Goto F_SeeCheck
            _CLabel0:
                TNT1 A 0 A_TakeInventory("_Call0")
                POSS A 5 A_Recoil(-0.7)
                POSS B 5 A_Recoil(-0.7)
                TNT1 A 0 A_GiveInventory("_Call1")
                Goto F_SeeCheck
            _CLabel1:
                TNT1 A 0 A_TakeInventory("_Call1")
                POSS A 4 A_Recoil(-0.7)
                POSS B 4 A_Recoil(-0.7)
                TNT1 A 0 A_GiveInventory("_Call2")
                Goto F_SeeCheck
            _CLabel2:
                TNT1 A 0 A_TakeInventory("_Call2")
                POSS A 3 A_Recoil(-0.7)
                POSS B 3 A_Recoil(-0.7)
                POSS C 3 A_Recoil(-0.7)
                POSS D 3 A_Recoil(-0.7)
                TNT1 A 0 A_GiveInventory("_Call3")
                Goto F_SeeCheck
            _CLabel3:
                TNT1 A 0 A_TakeInventory("_Call3")
                goto RunLoop
            
            RunLoop:
                POSS A 2 A_Recoil(-0.7)
                POSS B 2 A_Recoil(-0.7)
                POSS C 2 A_Recoil(-0.7)
                POSS D 2 A_Recoil(-0.7)
                    TNT1 A 0 A_GiveInventory("_Call4")
                    Goto F_SeeCheck
                _CLabel4:
                    TNT1 A 0 A_TakeInventory("_Call4")
                POSS A 2 A_Recoil(-0.7)
                POSS B 2 A_Recoil(-0.7)
                POSS C 2 A_Recoil(-0.7)
                POSS D 2 A_Recoil(-0.7)
                    TNT1 A 0 A_GiveInventory("_Call4")
                    Goto F_SeeCheck
                _CLabel4:
                    TNT1 A 0 A_TakeInventory("_Call4")
                TNT1 A 0 A_GiveInventory("_Call5")
                Goto F_ZombieJump
            _CLabel5:
                TNT1 A 0 A_TakeInventory("_Call5")
                loop
        }
    }
```

Yes, I know; the output code is quite cryptic, but you're not meant to touch that!

Just slap the output in your WAD and... [look at what happens!](https://i.imgur.com/mr5wJ85.gifv)