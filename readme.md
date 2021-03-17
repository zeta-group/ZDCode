# ZDCode 2.0

"The language that compiles to ye olde DECORATE!"

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

At one point, it was planned to create a rather standardized format for fetching ZDCode packages
using indexes stored in Git. However, this has been wholly deemed unnecessary. Instead, the
current roadmap is to add simple support via transports like HTTP, Git and FTP, and allowing
other transport implementations as well, using a termina-friendly URI-like format. This is very
reminiscent of the syntax Go package management uses, e.g. `go get github.com/someone/something`.

This deals with two issues at the same time: it ensures both that players can easily retrieve mods (and
updates thereof) directly from the Internet (automatically bundling them if necessary), whilst at
the same time enabling ZDCode mod authors to both obtain and share code more efficiently, both for libraries
and finished mods.


# Programming Constructs

Welcome to the main attractions!


## Code Blocking

This may seem like a primitive part of a programming language, but DECORATE uses states
and labels, instead of code blocking. It's more akin to Assembly (or oldschool C), with
jumps rather than groups of statements.

ZDCode allows the programmer to group their state code into blocks, useful for statements
like repetition (`x 5 { A_Print ("I'm said five times!") }`), control flow, or even
mere readability.



## Macros

Macros are a way to inject common behaviour into different locations, as states that are
used multiple times.

```
// Global macros!
macro ThrustUpward(amount) {
    TNT1 A 0 ThrustThingZ(0, amount, 0, 1);  // My, DECORATE has some convoluted things sometimes.
}

class YipYipHurrahMan extends ZombieMan {
    // Class-local macros!
    macro Yip {
        inject ThrustUpward(20);
    };

    macro Hurrah {
        inject ThrustUpward(90);
    };

    label Spawn {
        POSS A 12;   // '12' means short yips
          inject Yip;
        POSS B 12;
          inject Yip;
        POSS D 50;   // '50' means long hurrahs
          inject Hurrah;
          loop;
    };
}
```

They are simple, because the states in them are simply copied at compile time, instead of
called at runtime. (Functions are legacy, unreliable, and now deprecated.) They support
static parameters, as well. They can't change at runtime, but they do make life easier too.



## Conditions

In contrast to DECORATE's highly manual and tediously finnicky (and almost Assembly-like)
state jumps, ZDCode boasts a much nicer format, that does not require offset maintenance
in the source code, nor separate state labels, and that is easier to both integrate with
existing code, extend with new code, or nest with more conditions and other constructs.

```
class RedBlue {
    label Spawn {
        if (z > floorz + 64) {
            // Red sprite, normal gravity (except half, but you know).
            RDBL R 2 A_SetGravity(0.5);
        };

        else {
            // Blue sprite, reverse gravity.
            RDBL B 2 A_SetGravity(-0.5);
        };
        
        loop;
    };
}
```


## Preprocessor

Yes, there is a C-like preprocessor in ZDCode! It has the usual `#DEFINE`, `#IFDEF`,
`#IFNDEF`, and the fundamental part of using any library - `#INCLUDE`. Among other things,
too.

```
class LocalizedZombie extends Zombieman replaces Zombieman {
    // This is a merely illustrative example.
    // For actual locatization, please just use ZDoom's LANGUAGE lump instead.
    // Apart from that, it demonstrates the effectiveness of the otherwise
    // simple and rudimentary preprocessor ZDCode uses.

    macro SeeMessage(message) {
        invisi A_Print(message); // invisi == TNT1, also duration defaults to 0

        // Any better ideas for a message printing macro? I'm all ears!
    };

    label See {
        #ifdef LANG
            #ifeq LANG EN_US
                inject SeeMessage("Hey, you!");
            #else
            #ifeq LANG PT_BR
                inject SeeMessage("Ei, você!");
            #else // I know, not very pretty. Python gets away with it, though!
            #ifeq LANG DE_DE
                inject SeeMessage("Achtung! Halt!");
            #else
                inject SeeMessage("/!\"); // Attention?
            #endif
            #endif
            #endif
            #endif
        #endif
        goto Super.See;
    };
}
```


## Templates

It was already possible to have a class inherit another. It is very simple DECORATE
behaviour that ZDCode of course permits as well, although with a bit cleaner syntax.

In addition to that, ZDCode allows instantiating multiple classes that differ slightly
from a base _template_. The difference between this and inheritance is that, rather than
happening at load time (where ZDoom reads the DECORATE), it happens at compile-time, which
means many cool tricks can be done by using this alongside other ZDCode features.

```
class<size> ZombieSizes extends Zombieman {
    set Scale to size;
};

derive SmallZombie  as ZombieSizes::(0.5);
derive BiggerZombie as ZombieSizes::(1.3);
derive SuperZombie  as ZombieSizes::(2.2);
```

Derivations can optionally include extra definitions, including the ability to 'implement'
**abstract macros**, **abstract labels** and define the values of **abstract arrays** that
the template may specify.

```
class<> FiveNumbers {
    abstract array numbers;

    abstract macro PrintNumber(n);

    label Spawn {
        // for ranges are not supported yet
        
        inject PrintNumber(numbers[0]);
        inject PrintNumber(numbers[1]);
        inject PrintNumber(numbers[2]);
        inject PrintNumber(numbers[3]);
        inject PrintNumber(numbers[4]);

        stop;
    };
}

derive PlainFibonacci as FiveNumbers::() {
    macro PrintNumber(n) {
        TNT1 A 0 A_Log(n);
    };

    array numbers { 1, 1, 2, 3, 5 };
}
```

It is recommended that classes that derive a template also inherit a base class, even
if for purely symbolic reasons, since it helps organize the code a bit, and so classes
that derive from such templates can be listed property by ZDoom's `dumpclasses` command
(using the inheritance base class as an argument), among other things.


## Groups and Group Iteration

A _group_ is a compile-time sequence of literals that can be iterated using a `for in` loop.
Class syntax allows adding the class' name to a group. More importantly, templates can also
specify a group, but rather than the template itself, the names of all derived classes are
added to the group when the code is parsed by the ZDCode compiler.

```
group fruits;

class<name> Fruit group fruits {
    macro PrintMe() {
        TNT1 A 0 A_Print(name);
    };
}

derive Orange as Fruit::("Orange");
derive Banana as Fruit::("Banana");
derive Lemon  as Fruit::("Lemon");
derive Grapes as Fruit::("Grapes");

class FruitPrinter {
    label Spawn {
        // 'index ___' is optional, but retrieves
        // the # of the iteration, like the i in a
        // C 'for (i = 0; i < n; i++)' loop, and can be
        // quite useful
        
        for fruitname index ind in fruits {
            // Log the index and fruit classname, like some sort of debug example
            
            TNT1 A 0 A_Log("Fruit #, Fruit Name");
            TNT1 A 0 A_Log(ind);
            TNT1 A 0 A_Log(fruitname);

            // Call the derived class macro from FruitPrinter. Yes.
            // The 'from' keyword means that the macro is from a
            // different class. The at sign means that the class
            // name is taken from the parameter 'fruitname', rather
            // than it being the name of the class itself. It can
            // also be used in the macro name part for interesting
            // tricks, similar to C's function pointer syntax.

            from @fruitname inject PrintMe();
        };

        stop;
    };
}
```


## State Modifiers

Another powerful feature of ZDCode is the ability to modify states at runtime,
where each modifier applies certain effects based on certain selectors.

Each modifier is actually a list of clause, where a clause pairs a selector with
one or more effects.

```
class DiscoZombie extends Zombieman {
    mod DiscoLight {
        (sprite(TNT1)) suffix TNT1 A 0 A_PlaySound("disco/yeah"); // now we can use TNT1 frames to play some weird sound!

        (all) +flag Bright; // Always bright, all the time!
    };

    label Spawn {
        apply DiscoLight {
            POSS AB 4;
        };

        loop;
    };

    // You can also apply the modifier to other state labels (like See or Missile)
    // using the apply syntax, but you get the gist.
}
```




