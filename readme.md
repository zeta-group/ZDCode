# ZDCode II
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
          POSS AB 5 A_Recoil(-0.7);
          TNT1 A 0 A_Chase;
          POSS A 0 A_FaceTarget();
          POSS AB 4 A_Recoil(-0.7);
          TNT1 A 0 A_Chase;
          POSS A 0 A_FaceTarget();
          POSS ABCD 3 A_Recoil(-0.7);
          TNT1 A 0 A_Chase;
          POSS A 0 A_FaceTarget();
          goto RunLoop;
      };

      function Jump
      {
          while ( z == floorz )
          {
              POSS A 5 [Bright];
              POSS A 11 ThrustThingZ(0, 30, 0, 1);
          };
          POSS AB 2 A_Chase;
      };

      label RunLoop
      {
          x3
          {
              POSS ABCD 2 A_Recoil(-0.7);
              TNT1 A 0 A_Chase;
              POSS A 0 A_FaceTarget();
          };

          if ( health > 5 )
              call Jump;

          loop;
      };
  }
```

This is what happens when that beauty goes through **DCode II**:

```
  Actor _Call0 : Inventory {Inventory.MaxAmount 1}


  Actor RunZombie : ZombieMan replaces ZombieMan 2055
  {
      Gravity 0.4
      Speed 0.0
      
      +NOBLOCKMONST
      
      States {
          F_Jump:
          _WhileBlock0:
              TNT1 A 0 A_JumpIf(!(z == floorz), 4)
              POSS A 5  Bright
              POSS A 11 ThrustThingZ(0.0, 30.0, 0.0, 1.0)
              TNT1 A 0 A_Jump(255, "_WhileBlock0")
              TNT1 A 0
              POSS A 2 A_Chase
              POSS B 2 A_Chase
          
          
          See:
              POSS A 5 A_Recoil(-0.7)
              POSS B 5 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              POSS A 4 A_Recoil(-0.7)
              POSS B 4 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              POSS A 3 A_Recoil(-0.7)
              POSS B 3 A_Recoil(-0.7)
              POSS C 3 A_Recoil(-0.7)
              POSS D 3 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              goto RunLoop
          
          RunLoop:
              POSS A 2 A_Recoil(-0.7)
              POSS B 2 A_Recoil(-0.7)
              POSS C 2 A_Recoil(-0.7)
              POSS D 2 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              POSS A 2 A_Recoil(-0.7)
              POSS B 2 A_Recoil(-0.7)
              POSS C 2 A_Recoil(-0.7)
              POSS D 2 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              POSS A 2 A_Recoil(-0.7)
              POSS B 2 A_Recoil(-0.7)
              POSS C 2 A_Recoil(-0.7)
              POSS D 2 A_Recoil(-0.7)
              TNT1 A 0 A_Chase
              POSS A 0 A_FaceTarget
              TNT1 A 0 A_JumpIf(!(health > 5.0), 3)
                  TNT1 A 0 A_GiveInventory("_Call0")
                  Goto F_Jump
              _CLabel0:
                  TNT1 A 0 A_TakeInventory("_Call0")
              TNT1 A 0
              loop
      }
  }
```

Yes, I know; the output code is quite cryptic, but you're not meant to touch that!

Just slap the output in your WAD and... look at what happens!

![Wow!](https://i.imgur.com/mr5wJ85.gif)