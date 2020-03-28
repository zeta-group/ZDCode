# ZDCode 2.0
## The language that compiles to ye olde DECORATE!

ZDCode is a project that aims to make writing DECORATE _better_; that is,
to expand the possibilities not only of what the code itself can do, but
also of how it can be written, or concerted with other ZDCode projects
and authors, or distributed to modders and players alike. ZDCode is
an attempt to make modding for ZDoom-based platforms, like Zandronum,
much more similar to the ecosystem of an actual language, like a C linker,
or a JavaScript web bundler.

Take this example:

```c
#UNDEFINE ANNOYING

class RunZombie inherits ZombieMan replaces ZombieMan #2055
{
    set Gravity to 0.4; // high up...
    set Speed to 0;
    is NOBLOCKMONST;
    set Speed to 0;
 
    label See
    {
        inject SeeCheck;
        POSS AB 5 A_Recoil(-0.7);
        inject SeeCheck;
        POSS AB 4 A_Recoil(-0.7);
        inject SeeCheck;
        POSS ABCD 3 A_Recoil(-0.7);
        inject SeeCheck;
        goto RunLoop;
    };

    macro SeeCheck
    {
        TNT1 A 0 A_Chase;
        POSS A 0 A_FaceTarget();
    };

    macro ZombieJump
    {
        if ( health > 5 )
            return;

        while ( z == floorz )
        {
            POSS A 5 [Bright];
            POSS A 11 ThrustThingZ(0, 30, 0, 1);
        };

        #ifndef ANNOYING
        while ( z > floorz )
        {
            POSS AB 4;
        };

        POSS G 9;
        POSS B 22;
        #endif
        
        POSS AB 2 A_Chase;
    };

    label RunLoop
    {
        x 2
        {
            POSS ABCD 2 A_Recoil(-0.7);
            inject SeeCheck;
        };

        inject ZombieJump;
        loop;
    };
}
```

This is what happens when that beauty goes through **ZDCode 2.0**:

```
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_0 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_1 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_2 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_3 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_4 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_5 : Inventory {Inventory.MaxAmount 1}
Actor _Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_6 : Inventory {Inventory.MaxAmount 1}


Actor RunZombie : ZombieMan replaces ZombieMan 2055
{
    Gravity 0.4
    Speed 0
    Speed 0
    
    +NOBLOCKMONST
    
    States {
        F_SeeCheck:
            TNT1 A 0 A_Chase
            POSS A 0 A_FaceTarget
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_0", 1, "_CLabel0")
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_1", 1, "_CLabel1")
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_2", 1, "_CLabel2")
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_3", 1, "_CLabel3")
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_4", 1, "_CLabel4")
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_5", 1, "_CLabel5")
            TNT1 A -1
        
            F_ZombieJump:
            TNT1 A 0 A_JumpIf(!(health > 5), 2)
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_6", 1, "_CLabel6")
            Stop
            TNT1 A 0
        _WhileBlock0:
            TNT1 A 0 A_JumpIf(!(z == floorz), 3)
            POSS A 5  Bright
            POSS A 11 ThrustThingZ(0, 30, 0, 1)
            Goto _WhileBlock0
            TNT1 A 0
        _WhileBlock1:
            TNT1 A 0 A_JumpIf(!(z > floorz), 3)
            POSS A 4
            POSS B 4
            Goto _WhileBlock1
            TNT1 A 0
            POSS G 9
            POSS B 22
            POSS A 2 A_Chase
            POSS B 2 A_Chase
            TNT1 A 0 A_JumpIfInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_6", 1, "_CLabel6")
            TNT1 A -1
        
        See:
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_0")
            Goto F_SeeCheck
        _CLabel0:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_0")
            POSS A 5 A_Recoil(-0.7)
            POSS B 5 A_Recoil(-0.7)
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_1")
            Goto F_SeeCheck
        _CLabel1:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_1")
            POSS A 4 A_Recoil(-0.7)
            POSS B 4 A_Recoil(-0.7)
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_2")
            Goto F_SeeCheck
        _CLabel2:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_2")
            POSS A 3 A_Recoil(-0.7)
            POSS B 3 A_Recoil(-0.7)
            POSS C 3 A_Recoil(-0.7)
            POSS D 3 A_Recoil(-0.7)
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_3")
            Goto F_SeeCheck
        _CLabel3:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_3")
            goto RunLoop
        
        RunLoop:
            POSS A 2 A_Recoil(-0.7)
            POSS B 2 A_Recoil(-0.7)
            POSS C 2 A_Recoil(-0.7)
            POSS D 2 A_Recoil(-0.7)
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_4")
            Goto F_SeeCheck
        _CLabel4:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_4")
            POSS A 2 A_Recoil(-0.7)
            POSS B 2 A_Recoil(-0.7)
            POSS C 2 A_Recoil(-0.7)
            POSS D 2 A_Recoil(-0.7)
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_5")
            Goto F_SeeCheck
        _CLabel5:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_5")
            TNT1 A 0 A_GiveInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_6")
            Goto F_ZombieJump
        _CLabel6:
            TNT1 A 0 A_TakeInventory("_Call_NPaLK2i4Etrk1DERaszVFVbnG6JiT6KwJHX_6")
            Goto RunLoop
    }
}
```

While the compile output does look unreadable, expecting readability from it is akin to expecting
readability from a binary executable file. This is the principle of using ZDCode instead of
DECORATE, after all – a more readable, concise, and organized, way to write DECORATE.

Just slap the output in your WAD and... [look at what happens!](https://i.imgur.com/mr5wJ85.gifv)



# Design Concepts


### Ecosystem

The ZDCode ecosystem is meant to simplify writing DECORATE code, mostly in the occasion that a
mod is built from a directory, instead of modified directly in the PK3. It is still possible to
modify the contents of a PK3 like a directory, but it is a Linux-only technique, that involves
mounting the file into a folder using `fuse-zip`. Thus, it is meant to be integrated with
another build system, which automatically builds an InfoZIP file (with `.pk3` extension).


### Bundling

Similar to web bundling technologies, such as Browserify, ZDCode tackles the issue of incompatibilities
among different generated DECORATE files by instead focusing on _bundling_ the ZDCode input into a single
DECORATE file.

The compiled output of ZDCode, much like a compiled C program after being linked, is treated as an
indivisible, integral, and immutable chunk of instructions, to be read and interpreted exclusively by
ZDoom. Instead of attempting to merge separate DECORATE outputs, it is much easier, and in fact more
plausible, to link other ZDCode projects, libraries, and source code in general, akin to libraries
in interpreted languages, like Python. This is also how web bundling technologies operate.


### Non-[Imperativity](https://en.wikipedia.org/wiki/Imperative_programming) and other lower-level limitations

Unlike other programming languages, ZDCode has a very specific purpose.

C is a portable way of writing a relatively abstract representation of machine instructions (e.g.
`myNum += 1` instead of `ADD EAX, 1`), and interpreted languages are instructions for an interpreter's
virtual machine, whose computations do still, in the end, reflect machine code.

ZDCode does not have the same capabilities of using any arbitrary computer resources, because DECORATE
itself doesn't. Rather, DECORATE is a mere form of expressing "classes" (which are only templates for
objects in ZDoom-based source ports, rather than actual object-oriented programming constructs), which
in turn guide "actors" (fancy name for game objects, instead of being strictly actor model constructs),
including their actions, properties, and states (frames).

For this reason, ZDCode is not concerned with concepts of actual imperative programming, like actual `for`
loops that actually increment a discrete integer variable towards an arbitrary limit. Rather, it tries
to make it easier, simpler, more programming-friendly and more systematic to write DECORATE behaviour for
ZDoom, without relying on ZScript and requiring modern GZDoom versions for mere language support
reasons. Zandronum does not support ZScript.

DECORATE itself does not support sharing behaviour between separate actor classes; rather, it supports
using actor classes from other classes, but only in indirect ways, such as spawning other actors. It
has very limited interaction among different actors, which are more centered around basic concepts that
every physical actor has (such as collision, movement, and to an extent AI behaviour), without allowing
actual actor-model-esque messages to be passed directly between those game objects. At this point,
writing DECORATE in any way that attempts to concert multiple objects becomes contrived and relies on
mostly unrelated behaviour intended for very different things; trying to send a message between two
actors is similar to using a bottle, usually a small liquid container, as a means of propagating a
message across a river, or a lake. It does work, but it relies on the buoyancy and imperviousness
of the bottle. It's much better to use something designed for this, like in this example, it could be
radio waves, or an actual wire.

Unfortunately, ZDCode is not able to overcome these limitations at run-time. It still cannot have
imp Bob tell imp Joe that the marine is coming, and that they should ambush from different hiding
spots. What it _can_ do, however, is make the _writing_ part of the code a lot simpler, by providing
tools to exploit behaviours.


### Distribution

The concept of _distribution_ in ZDCode is intimately related to that of bundling, specifically
because it concerns with the ease of availability of libraries to the programmer, and also the
ease of distribution and dependency management.

It is planned to create a ZDCode packaging and distribution format, akin to npm or PyPI, to aid
the users of this project in their endeavors. Instead of being a centralized service, this subproject
will consist merely of client software, whose purpose is to read _channels_ from existing Git repositories,
which are listings of other Git repositories which, in turn, contain the actual packages. This client
software has two purposes:

 * fetching a desired ZDCode library to include in a project;
 * fetching the ZDCode libraries required to build a project into DECORATE.

This will help ensure that ZDCode authors will always have many options, and is part of the
expansion of possibilities in DECORATE.



# Programming Constructs

Welcome to the main attractions!


## Code Blocking

This may seem like a primitive part of a programming language, but DECORATE uses states
and labels, instead of code blocking. It's more akin to Assembly (or oldschool C), with
jumps rather than groups of statements.

ZDCode allows the programmer to group their state code into blocks, useful for statements
like repetition (`x 5 { A_Print ("I'm said five times!") }`), control flow, or even
mere readability. There can be both blocks of states and blocks of _state actions_.



## Condition Templates

Condition templates are a way to describe a DECORATE conditional check in a way ZScript
can generalize and apply to other situations. Example:

```
class JumpNearby extends RedTorch {
    condition target_closer(dist) { A_JumpIfCloser(dist, @target) };
    condition on_floor() { A_JumpIf(z == floorz, @target) };

    macro DoTheJump {
        // ...
    }

    label Spawn {
        TRED ABCD 4 [Bright] {
            if target_closer(128) && on_floor() {
                inject DoTheJump;
            };
        };
        Loop;
    }
}
```

This is actually a nice feature, and a bit more than just syntax sugar. The reason is
unfortunately longer than convenient, so hold tight.

DECORATE has a very simple state label system. A state lasts for X frames, and once all the
frames have elapsed, the actor goes to the next state, which, in turn, lasts for Y frames.
Some actions, however, can override this behaviour; they jump to different states. `A_Jump*`
state actions do exactly this: they go forward, or backward, a specific number of states
from the current one, instead of rolling to the next state. However, as the number of states
in an actor grows and grows, it becomes more difficult to maintain jump offsets. To combat
this, DECORATE comes with a state label system, where a label is inserted between states,
as a sort of grouping. Instead of jumping N states forward or backward, a state can instead
also jump to the state right after label L.

Therefore, for example,

```
PrevLabel:
- A
- B
MyLabel:
- C goto PrevLabel if happy
- D goto MyLabel   if sad
```

becomes equivalent to

```
    - A                                      _  -2
                                            |     
    - B                                     | 
                                            |
    - C jump by -2 if happy   0   # happy >' _  -1
                                            |
    - D jump by -1 if sad     0   #   sad >' 
```

but has a much clearer intent, and does not require maintenance of jump offsets ~~if~~ when the
number of states changes. Much convenience!

However, this is still not enough. Conditions are usally poorly expressable; you can say

```
class BunnyhoppingImp extends DoomImp replaces DoomImp {
    // ....
    States {
        See:
            TNT1 A 0 A_JumpIf(z == floorz, "Jump")   // any imp born after 1993 can't double-jump... https://www.reddit.com/r/copypasta/comments/fqcgst/imps_after_1993_cant_doublejump/
            Goto Run
            
        Run:
            // ...
            Goto See
            
        Jump:
            TNT1 A 0 A_MoveUpAndActuallyJump(...)
            // ...
            Goto Run
    }
}
```

But there is no way to parametrize it. Let's say you want to define a common condition,
`higher_than(height)`, where the actual condition is `z > floorz + height`. Sure, this
isn't really necessary, and isn't a particularly significant instance of extracting
duplicate code. But it already has its use case – what if you want to change the `>` to
a `>=` later on, or likewise alter the behaviour of this use case? Also, it becomes
even more important as the size of the actual condition grows, or the number of parameters
increase.

Plus, there are many `A_Jump*` actions; some conditions can't be expressed as DECORATE expressions,
and thus need to be expressed natively, and exposed via different actions. Like `A_JumpIfCloser` to
detect the proximity between a game object and its target (for a monster, this is usually player
proximity, with exceptions like during a monster infighting scenario). There is no `target_proximity`
value you can use in DECORATE.

ZDCode fixes those issues by abridging actions that jump with common syntax, which are those condition
templates. It also takes advantage of the label system, making it possible to insert labels _inside_
the code of other labels, to perform conditional jumps and loops.

It is possible to do conditional jumping in plain DECORATE, and even to do a jump that only happens if
two conditional jumps occur:

```
States {
    Spawn:
        TRED ABCD 4 Bright
        // 'TNT1 A' is invisible; 0 means the frame runs instantly. So it just
        // performs the state action without waiting, so all of the code below
        // executes instantly, like C code would.
        TNT1 A 0 A_JumpIfCloser(128, 2) // player must be closer than 128 units
        TNT1 A 0
          Goto GoBack // control flow does not count as states, hence jumping by 2, not by 3
        TNT1 A 0 A_JumpIf(z == floorz, 2) // torch must still be in ground, *as well*
        TNT1 A 0
          Goto GoBack
        // if either of these conditions is not satisfied, the code does not reach here
        // therefore, this is basically an 'if (a && b)' thing
        TNT1 A 0 // ...and this is the else
          Loop

    IfBody:
        TNT1 A 0
          Goto DoTheJump
        
    GoBack:
        TNT1 A 0
          Goto Spawn
}
```

But ZDCode helps clean this syntax up, and it also makes conditions more easily parametrized, as well
as providing support for some sorts of code blocks.


## Macros

Macros are a way to inject common behaviour into different locations, as states that are
used multiple times.

```
class YipYipHurrahMan extends ZombieMan {
    macro Yip {
        TNT1 A 0 A_ThrustUpward(20);
    }

    macro Hurrah {
        TNT1 A 0 A_ThrustUpward(90);
    }

    label Spawn {
        POSS A 12;   // '12' means short yips
          inject Yip;
        POSS B 12;
          inject Yip;
        POSS D 50;   // '50' means long hurrahs
          inject Hurrah;
          loop;
    }
}
```

They are simple, because the states in them are simply copied at compile time, instead of
called at runtime. (Functions are legacy, unreliable, and now deprecated.) They support
static parameters, as well. They can't change at runtime, but they do make life easier too.


## Preprocessor

Yes, there is a C-like preprocessor in ZDCode! It has the usual `#DEFINE`, `#IFDEF`,
`#IFNDEF`, and the staple of any library - `#INCLUDE`. Among other things.