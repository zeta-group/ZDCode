import re
import textwrap

from pyparsing import *


def decorate(o, *args, **kwargs):
    """Get the object's compiled DECORATE code."""
    print "Getting DECORATE code for a {}...".format(type(o).__name__)
    return o.__decorate__(*args, **kwargs)

def big_lit(s, indent=4, tab_size=4, strip_borders=True):
    """This function assists in the creation of
fancier triple-quoted literals, by removing
trailing indentation in lines and trailing
and leading spaces/newlines from formatting."""

    while s[0] in ("\n", "\r"): s = s[1:]
    while s[-1] in ("\n", "\r"): s = s[:-1]
    if strip_borders: s = s.strip(" \t")
    lines = s.splitlines()
    result = []

    for l in lines:
        i = indent
        while i > 0:
            if l.startswith("\t"):
                i -= tab_size
                l = l[1:]

            elif l.startswith(" "):
                i -= 1
                l = l[1:]

            else:
                break

        result.append(l)

    result = "\n".join(result)
    return result

assert big_lit("""
    YAY! I am
        Working!
""", 8) == "YAY! I am\nWorking!"

assert big_lit("""
    YAY! I am
        Working!
""", 4) == "YAY! I am\n    Working!"

assert big_lit("""
    Big
        Fluffy
    Furry.

    """, 4) == "Big\n    Fluffy\nFurry.\n"

def redent(code, spaces=8, unindent_first=True):
    b = textwrap.dedent(code).splitlines()
    r = []

    for l in b:
        r.append((" " * spaces) + l)

    r = "\n".join(r)

    if unindent_first:
        return r.lstrip("\t ")

    return r

# ZDCode Classes
class ZDProperty(object):
    def __init__(self, code, name, value):
        self.code = code
        self.name = name
        self.value = value

        self.code.properties[name] = self

    def __decorate__(self):
        return "    {} {}".format(self.name, self.value)

class ZDCall(object):
    def __init__(self, code, label, func, args=None, repeats=1):
        if not args:
            args = []

        repeats = int(repeats)

        self.func = func
        self.code = code
        self.args = args
        self.label = label
        self.repeats = repeats

        self.id = len(code.calls)
        code.calls.append(self)
        func.add_call(self)
        label.states.append(self)

        if repeats > 1:
            for _ in xrange(repeats):
                ZDCall(code, label, func, args, 1)

            del self

        else:
            ZDInventory(code, "_Call{}".format(self.id))

    def add_arg(a):
        self.args.append(a)

    def __decorate__(self):
        r = ""

        for i, a in enumerate(self.args):
            r += "TNT1 A 0 A_TakeInventory(\"{0}\")\n    TNT1 A 0 A_GiveInventory(\"{0}\", {1})\n".format(self.func.args[i], a)

        return r + "TNT1 A 0 A_GiveInventory(\"_Call{1}\")\n        Goto F_{0}\n    _CLabel{1}:\n        TNT1 A 0 A_TakeInventory(\"_Call{1}\")".format(self.func.name, self.id)

class ZDFunction(object):
    def __init__(self, code, actor, name, args=None, states=None):
        if not args:
            args = []

        if not states:
            states = []

        self.code = code
        self.name = name
        self.states = states
        self.calls = []
        self.actor = actor
        self.args = args

        self.id = len(actor.funcs)
        actor.funcs.append((name, self))

        for a in args:
            if a not in [x.name for x in code.inventories]:
                ZDInventory(code, a)

    def add_call(self, call):
        self.calls.append(call)

    def add_arg(self, argstr):
        self.args.append(argstr)

        for a in self.args:
            if a not in [x.name for x in self.code.inventories]:
                ZDInventory(self.code, a)

    def call_states(self):
        result = []

        for c in self.calls:
            result.append("TNT1 A 0 A_JumpIfInventory(\"_Call{0}\", 1, \"_CLabel{0}\")".format(c.id))

        return redent("\n".join(result), 8)

    def __decorate__(self):
        code = """    F_{}:
        {}
        {}
        Stop""".format(self.name, redent("\n".join(decorate(s) for s in self.states), 4), redent(self.call_states(), 0))

        return code

class ZDState(object):
    def __init__(self, sprite="TNT1", frame="A", duration=0, keywords=None, action=None):
        if not keywords:
            keywords = []

        self.sprite = sprite[:4]
        self.frame = frame
        self.keywords = keywords
        self.action = action
        self.duration = duration

    def __decorate__(self):
        if self.keywords:
            keywords = [" "] + self.keywords

        else:
            keywords = []

        action = ""
        if self.action:
            action = " " + str(self.action)

        return "{} {} {}{}{}".format(
            self.sprite.upper(),
            self.frame.upper(),
            str(self.duration),
            " ".join(keywords),
            action
        )

class ZDLabel(object):
    def __init__(self, _actor, name, states=None):
        if not states:
            states = []

        self.name = name
        self.states = states
        self._actor = _actor

        self._actor.labels.append(self)

    def add_state(self, state):
        self.states.append(state)

    def __decorate__(self):
        if self.name.startswith("F_"):
            self.name = "_" + self.name

        r = "    {}:".format(self.name)

        for s in self.states:
            r += "\n        {}".format(decorate(s))

        return r

class ZDRawDecorate(object):
    def __init__(self, raw):
        self.raw = raw

    def __decorate__(self):
        return self.raw

class ZDActor(object):
    def __init__(self, code, name="DefaultActor", inherit=None, replace=None, doomednum=None):
        self.code = code
        self.labels = []
        self.properties = {}
        self.flags = []
        self.antiflags = []
        self.inherit = inherit
        self.name = name
        self.replace = replace
        self.num = doomednum
        self.funcs = []
        self.raw = []

    def top(self):
        r = []

        for p in sorted(self.properties.values(), key=lambda p: p.name):
            r.append(decorate(p))

        r.append("")

        for f in self.flags:
            r.append("+{}".format(f))

        for a in self.antiflags:
            r.append("-{}".format(a))

        for rd in self.raw:
            r.append(rd)

        return redent(big_lit("\n".join(r), 8), 4, False)

    def label_code(self):
        r = []

        for f in self.funcs:
            r.append(decorate(f[1]))

        for l in self.labels:
            r.append(decorate(l))

        return redent("\n\n".join(r), 8, False)

    def header(self):
        r = self.name

        if self.inherit: r += " : {}".format(self.inherit)
        if self.replace: r += " replaces {}".format(self.replace)
        if self.num:     r += " {}".format(str(self.num))

        return r

    def __decorate__(self):
        if self.labels + self.funcs:
            return big_lit(
            """
            Actor {}
            {{
            {}

                States {{
                    {}
                }}
            }}
            """, 12).format(self.header(), redent(self.top(), 4, unindent_first=False), redent(self.label_code(), unindent_first=True))

        return big_lit(
        """
        Actor {}
        {{
        {}
        }}
        """, 8).format(self.header(), redent(self.top(), 4, unindent_first=False))

class ZDInventory(object):
    def __init__(self, code, name):
        self.name = name
        self.code = code

        code.inventories.append(self)

    def __decorate__(self):
        return "Actor {} : Inventory {{Inventory.MaxAmount 1}}".format(self.name)

# Parser!
class ZDCode(object):
    class ZDCodeError(BaseException):
        pass

    args = Forward()
    args << (Combine(CharsNotIn("()") + "(" + args + ")" + Optional("," + args)) | CharsNotIn(")"))
    inherit = Optional(":" + Word(alphanums + "_"))
    replace = Optional("->" + Word(alphanums + "_"))
    denum = Optional("*" + Word(nums))
    parser = Forward()
    st = Forward()
    actorargs = Forward()
    actorargs << (inherit ^ replace ^ denum) + (FollowedBy("{") | Optional(actorargs))
    action = Group(Word(alphanums + "_-") + Optional("(" + args + ")"))
    cond = "?" + SkipTo("==") + "==" + Word(nums) + "->" + Word(alphanums + "_-.") + ";"
    call = "(" + Word(alphas+"_", alphanums+"_") + ")" + Optional("(" + Optional(args) + ")") + ";"
    raw = "^" + SkipTo(";") + ";"
    normstate = Word(alphanums + "_-", exact=4) + Word(alphas + "[]") + Word(nums) + ZeroOrMore(Group("[" + SkipTo("]") + "]")) + Optional("@" + action) + ";"
    state = Optional("*" + Word(nums)) + ":" + (cond ^ call ^ raw ^ normstate)
    flagname = Word(alphanums + "_.")
    flag = "*" + flagname + ";"
    aflag = "!" + flagname + ";"
    aprop = "&" + Word(alphanums + "_.") + "=" + SkipTo(";") + ";"
    st << (state + Optional(st))
    afunc = "$" + Word(alphas+"_", alphanums+"_") + Optional("(" + Optional(args) + ")") + "{" + Optional(st) + "};"
    label = "#" + Optional("#") + Word(alphas + "_", alphanums + "_") + "{" + Optional(st) + "};"
    possib = afunc ^ label ^ aprop ^ aflag ^ flag ^ raw
    recurse = Forward()
    recurse << (possib + Optional(recurse))
    parser << ("%" + Word(alphanums + "_") + actorargs + "{" + Optional(recurse) + "};" + Optional(parser))

    comment = re.compile(r"\/\*(\*(?!\/)|[^*])*\*\/|\/\/[^\n$]+", re.MULTILINE)

    # args.setDebug()
    # inherit.setDebug()
    # replace.setDebug()
    # denum.setDebug()
    # actorargs.setDebug()
    # action.setDebug()
    # cond.setDebug()
    # call.setDebug()
    # raw.setDebug()
    # normstate.setDebug()
    # state.setDebug()
    # flagname.setDebug()
    # flag.setDebug()
    # aflag.setDebug()
    # aprop.setDebug()
    # st.setDebug()
    # afunc.setDebug()
    # label.setDebug()
    # possib.setDebug()
    # recurse.setDebug()
    # parser.setDebug()

    @classmethod
    def parse(cls, code):
        print "Syntax parsing..."
        code = cls.comment.sub("", code)
        syntax = cls.parser.parseString(code, parseAll=True)
        res = cls()

        for s in syntax:
            old = res._parse_state
            print "Parsing token '{}':".format(s),
            res.lexical(s)
            print "state changed from '{}' to '{}'.".format(old, res._parse_state)

        return res

    def __init__(self):
        self.inventories = []
        self.actors = []
        self.calls = []

        # Parsing
        self._parse_state = "actor"
        self._actor = None
        self._label = None
        self._func = None
        self._parse_temp = None

    def lexical(self, o):
        if not o:
            return

        if self._parse_state == "actor":
            if o == "%":
                self._parse_state = "actor.name"

            else:
                raise self.ZDCodeError("Unknown definition at global space! (expected '%' or '~', got '{}')".format(o))

            return

        # ================
        # ACTOR DEFINITION
        # ================
        if self._parse_state == "actor.name":
            self._actor_name = o
            self._parse_state = "actor.postname1"

            return

        if self._parse_state.startswith("actor.postname"):
            if self._parse_state == "actor.postname1":
                if o == ":":
                    self._parse_state = "actor.postname2"
                    return

                elif o == "->":
                    self._parse_state = "actor.postname3"
                    return

                elif o == "*":
                    self._parse_state = "actor.postname4"
                    return

                elif o == "{":
                    self._actor = ZDActor(self, self._actor_name, inherit=self.__dict__.get("_actor_inherit", None), replace=self.__dict__.get("_actor_replace", None), doomednum=self.__dict__.get("_actor_num", None))

                    try: del self._actor_inherit
                    except AttributeError: pass
                    try: del self._actor_replace
                    except AttributeError: pass
                    try: del self._actor_num
                    except AttributeError: pass

                    self._parse_state = "inner_actor"
                    return

                else:
                    raise self.ZDCodeError("Invalid actor definition: modifier '{}' not supported!".format(o))

            if self._parse_state == "actor.postname2":
                self._actor_inherit = o
                self._parse_state = "actor.postname1"

            if self._parse_state == "actor.postname3":
                self._actor_replace = o
                self._parse_state = "actor.postname1"

            if self._parse_state == "actor.postname4":
                self._actor_num = o
                self._parse_state = "actor.postname1"

            return

        # ===========
        # ACTOR STUFF
        # ===========
        if self._parse_state == "inner_actor":
            if o == "&":
                self._parse_state = "aprop"

            elif o == "*":
                self._parse_state = "flag"

            elif o == "^":
                    self._parse_state = "raw"
                    return

            elif o == "};":
                o = self._actor
                self.actors.append(o)
                self._actor = None
                self._parse_state = "actor"

            elif o == "!":
                self._parse_state = "aflag"

            elif o == "#":
                self._parse_state = "label"

            elif o == "$":
                self._parse_state = "afunc"

            else:
                raise self.ZDCodeError("Invalid definition at actor space: '{}'".format(o))

            return

        # ===
        # RAW
        # ===

        if self._parse_state == "raw":
            self._actor.raw.append(o)
            self._parse_state = "semicolon"

            return

        # =======
        # COMMONS
        # =======

        if self._parse_state == "semicolon":
            if o != ";":
                raise self.ZDCodeError("Invalid actor-space syntax; expected ';', got '{}' instead!".format(o))

            self._parse_state = "inner_actor"
            return

        # =====
        # FLAGS
        # =====

        if self._parse_state == "flag":
            self._actor.flags.append(o)
            self._parse_state = "semicolon"
            return

        if self._parse_state == "aflag":
            self._actor.antiflags.append(o)
            self._parse_state = "semicolon"
            return

        # ======
        # LABELS
        # ======
        if self._parse_state.startswith("label"):
            if self._parse_state == "label":
                if o == "#":
                    if hasattr(self, "_log_label") and self._log_label:
                        raise self.ZDCodeError("Three or more hashes found in a label definition! (expected label name, got '#')")

                    else:
                        self._log_label = True

                else:
                    self._label = ZDLabel(self._actor, o.strip())

                    if hasattr(self, "_log_label") and self._log_label:
                        del self._log_label
                        self._label.add_state(ZDRawDecorate("TNT1 A 0 A_Log(\"Reached state {}\")".format(o.strip())))

                    self._parse_state = "label.bracket"

            elif self._parse_state == "label.bracket":
                if o != "{":
                    raise self.ZDCodeError("Invalid label definition: expected '{{', got '{}'!".format(o))

                self._parse_state = "label.startstate"

            elif self._parse_state == "label.startstate":
                if o == "};":
                    self._parse_state = "inner_actor"

                elif o == ":":
                    self.repeat_num = 1
                    self._parse_state = "label.state"

                elif o == "*":
                    self._parse_state = "label.state.repeat"

                else:
                    raise self.ZDCodeError("Error reading state syntax! (Expected ':' or '*', got '{}' instead)".format(o))

            elif self._parse_state == "label.state":
                if o == "?":
                    self._parse_state = "label.argcheck"

                elif o == "^":
                    self._parse_state = "label.flow"

                elif o == "(":
                    self._parse_state = "label.call"

                else:
                    if len(o) != 4:
                        raise self.ZDCodeError("Sprite length must be exactly 4 letters: got '{}' instead!".format(o))

                    self._parse_temp = [o]
                    self._parse_state = "label.state.frame"

            elif self._parse_state == "label.flow":
                self._label.add_state(ZDRawDecorate(o))
                self._parse_state = "label.flow.semicolon"

            elif self._parse_state == "label.flow.semicolon":
                if o != ";":
                    raise self.ZDCodeError("Missing semicolon at raw DECORATE declaration: got '{}' instead!".format(o))

                self._parse_state = "label.startstate"

            elif self._parse_state.startswith("label.argcheck"):
                if self._parse_state == "label.argcheck":
                    self._parse_temp = [o]
                    self._parse_state = "label.argcheck.equal"

                elif self._parse_state == "label.argcheck.equal":
                    if o != "==":
                        raise self.ZDCodeError("Invalid argcheck! ('{}')".format(self._parse_temp[0]))

                    self._parse_state = "label.argcheck.num"

                elif self._parse_state == "label.argcheck.num":
                    self._parse_temp.append(o)
                    self._parse_state = "label.argcheck.arrow"

                elif self._parse_state == "label.argcheck.arrow":
                    if o != "->":
                        raise self.ZDCodeError("Invalid inventory check: no arrow (->), got '{}' instead!".format(o))

                    self._parse_state = "label.argcheck.state"

                elif self._parse_state == "label.argcheck.state":
                    for _ in xrange(self.repeat_num): self._label.states.append(ZDRawDecorate("TNT1 A 0 A_JumpIfInventory(\"{0}\", {3}, 2)\nTNT1 A 0 A_JumpIfInventory(\"{0}\", {1}, \"{2}\")").format(self._parse_temp[0], self._parse_temp[1], o, int(self._parse_temp[1]) + 1))
                    self._parse_state = "label.argcheck.semicolon"

                elif self._parse_state == "label.argcheck.semicolon":
                    if o != ";":
                        raise self.ZDCodeError("Missing semicolon in inventory-conditional jump; got '{}' instead! ([VERBOSE] Jump data: [{}])".format(o, "|".join(self._parse_temp)))

                    self._parse_state = "label.startstate"

                return

            elif self._parse_state.startswith("label.state"):
                if self._parse_state == "label.state.frame":
                    if o == ";":
                        raise self.ZDCodeError("Premature semicolon! (state data upon parsing: {})".format(self._parse_temp))

                    self._parse_temp.append(o)
                    self._parse_state = "label.state.duration"

                elif self._parse_state == "label.state.repeat":
                    print o
                    self.repeat_num = int(o)
                    self._parse_state = "label.state.repeat_end"

                elif self._parse_state == "label.state.repeat_end":
                    if o == ":":
                        self._parse_state = "label.state"

                    else:
                        raise self.ZDCodeError("Bad state repeating! (expected ':' after '*{}', got '{}')".format(self.repeat_num, o))

                elif self._parse_state == "label.state.duration":
                    if o == ";":
                        raise self.ZDCodeError("Premature semicolon! (state data upon parsing: {})".format(self._parse_temp))

                    self._parse_temp.append(o)
                    self._parse_state = "label.state.postduration"

                elif self._parse_state == "label.state.postduration":
                    if type(o) is list and o[0] == "[":
                        self._parse_temp.append(o[1])

                    elif o == ";":
                        self._label.add_state(ZDState(self._parse_temp[0], self._parse_temp[1], self._parse_temp[2], self._parse_temp[3:], self.__dict__.get("_state_action", None)))

                        try:
                            del self._state_action

                        except AttributeError:
                            pass

                        self._parse_state = "label.startstate"

                    elif o == "@":
                        self._parse_state = "label.state.postduration2"

                    else:
                        raise self.ZDCodeError("Invalid state space token! (expecting ';' or '@', got '{}')".format(o))

                elif self._parse_state == "label.state.postduration2":
                    self._state_action = "".join(o)
                    self._parse_state = "label.state.postduration"

            elif self._parse_state == "label.call":
                func_names = [x[0] for x in self._actor.funcs]
                functions_ = [x[1] for x in self._actor.funcs]

                if o not in func_names:
                    raise self.ZDCodeError("Call to nonexistant function '{}'!".format(o))

                print self.repeat_num
                self._call = ZDCall(self, self._actor.labels[-1], functions_[func_names.index(o)], repeats=self.repeat_num)

                self._parse_state = "label.call.arg"

            elif self._parse_state.startswith("label.call."):
                if self._parse_state == "label.call.arg":
                    if o != ")":
                        raise self.ZDCodeError("No parenthesis ending call to '{}': got '{}' instead!".format(self._call.func.name, o))

                    self._parse_state = "label.call.arg_start"

                elif self._parse_state == "label.call.arg_start":
                    if o not in ("(", ";"):
                        raise self.ZDCodeError("No parenthesis in function call to '{}'!".format(self._call.func.name))

                    if o == ";":
                        self._parse_state = "label.startstate"

                    else:
                        self._parse_state = "label.call.arg_mid"

                elif self._parse_state == "label.call.arg_mid":
                    if o == ")":
                        self._parse_state = "label.call.arg_end"

                    else:
                        self._call.args.append(o)
                        self._parse_state = "label.call.arg_mid2"

                elif self._parse_state == "label.call.arg_mid2":
                    if o == ")":
                        self._parse_state = "label.call.arg_end"

                    elif o != ",":
                        raise self.ZDCodeError("Missing comma in function call to '{}'!".format(self._call.func.name))

                    else:
                        self._parse_state = "label.call.arg_mid"

                elif self._parse_state == "label.call.arg_end":
                    if o != ";":
                        raise self.ZDCodeError("Missing semicolon in function call to '{}'!".format(self._call.func.name))

                    else:
                        self._parse_state = "label.startstate"

            return

        # ==========
        # PROPERTIES
        # ==========
        if self._parse_state.startswith("aprop"):
            if self._parse_state == "aprop":
                self._parse_temp = o
                self._parse_state = "aprop.equal"

            elif self._parse_state == "aprop.equal":
                if o != "=":
                    raise self.ZDCodeError("Invalid property definition: '{}' instead of '='!".format(o))

                else:
                    self._parse_state = "aprop.value"

            elif self._parse_state == "aprop.value":
                ZDProperty(self._actor, self._parse_temp, o)
                self._parse_state = "aprop.end"

            elif self._parse_state == "aprop.end":
                if o != ";":
                    raise self.ZDCodeError("Missing semicolon after property definition!")

                else:
                    self._parse_state = "inner_actor"

            return

        # =========
        # FUNCTIONS
        # =========
        if self._parse_state.startswith("afunc"):
            if self._parse_state == "afunc":
                self._func = ZDFunction(self, self._actor, o)
                self._parse_state = "afunc.argstart"

            elif self._parse_state == "afunc.argstart":
                if o == "(":
                    self._parse_state = "afunc.arg1"

                elif o == "{":
                    self._parse_state = "afunc.closure"

                else:
                    raise self.ZDCodeError("Invalid function definition: expected '(' or '{', got '{}'".format(o))

            elif self._parse_state == "afunc.arg1":
                if o == ")":
                    self._parse_state = "afunc.startclosure"

                else:
                    self._func.add_arg(o)
                    self._parse_state = "afunc.arg2"

            elif self._parse_state == "afunc.arg2":
                if o == ",":
                    self._parse_state = "afunc.arg1"

                elif o == ")":
                    self._parse_state = "afunc.startclosure"

                else:
                    raise self.ZDCodeError("Invalid argument list: expected ')' or ',', got '{}'".format(o))

            elif self._parse_state == "afunc.startclosure":
                if o != "{":
                    raise self.ZDCodeError("Invalid function start: expected '{{', got '{}'!".format(o))

                else:
                    self._parse_state = "afunc.closure"

            elif self._parse_state == "afunc.closure":
                if o == ":":
                    self.repeat_num = 1
                    self._parse_state = "afunc.state"

                elif o == "*":
                    self._parse_state = "afunc.state.repeat"

                elif o == "};":
                    self._parse_state = "inner_actor"

                else:
                    raise self.ZDCodeError("Invalid function-space definition: expected ':' or '}};', got '{}'!".format(o))

            elif self._parse_state == "afunc.state":
                if o == "?":
                    self._parse_state = "afunc.argcheck"

                elif o == "^":
                    self._parse_state = "afunc.flow"

                elif o == "(":
                    self._parse_state = "afunc.call"

                elif o == "};":
                    self._parse_state = "inner_actor"

                else:
                    self._parse_temp = [o]
                    self._parse_state = "afunc.state.frame"

            elif self._parse_state == "afunc.state.repeat":
                self.repeat_num = int(o)
                self._parse_state = "afunc.state.repeat_end"

            elif self._parse_state == "afunc.state.repeat_end":
                if o == ":":
                    self._parse_state = "afunc.state"

                else:
                    raise self.ZDCodeError("Bad state repeating! (expected ':' after '*{}', got '{}')".format(self.repeat_num, o))

            elif self._parse_state == "afunc.flow":
                for _ in xrange(self.repeat_num): self._func.states.append(ZDRawDecorate(o))

            elif self._parse_state.startswith("afunc.argcheck"):
                if self._parse_state == "afunc.argcheck":
                    self._parse_temp = [o]
                    self._parse_state = "afunc.argcheck.equal"

                elif self._parse_state == "afunc.argcheck.equal":
                    if o != "==":
                        raise self.ZDCodeError("Invalid argcheck! ('{}')".format(self._parse_temp[0]))

                    self._parse_state = "afunc.argcheck.num"

                elif self._parse_state == "afunc.argcheck.num":
                    self._parse_temp.append(o)
                    self._parse_state = "afunc.argcheck.arrow"

                elif self._parse_state == "afunc.argcheck.arrow":
                    if o != "->":
                        raise self.ZDCodeError("Invalid inventory check: no arrow (->), got '{}' instead!".format(o))

                    self._parse_state = "afunc.argcheck.state"

                elif self._parse_state == "afunc.argcheck.state":
                    for _ in xrange(self.repeat_num): self._func.states.append(ZDRawDecorate("TNT1 A 0 A_JumpIfInventory(\"{0}\", {3}, 2)\nTNT1 A 0 A_JumpIfInventory(\"{0}\", {1}, \"{2}\")".format(self._parse_temp[0], self._parse_temp[1], o, int(self._parse_temp[1]) + 1)))
                    self._parse_state = "afunc.argcheck.semicolon"

                elif self._parse_state == "afunc.argcheck.semicolon":
                    if o != ";":
                        raise self.ZDCodeError("Missing semicolon in inventory-conditional jump; got '{}' instead! ([VERBOSE] Jump data: [{}])".format(o, "|".join(self._parse_temp)))

                    self._parse_state = "afunc.closure"

                return

            elif self._parse_state.startswith("afunc.state."):
                if self._parse_state == "afunc.state.frame":
                    if o == ";":
                        raise self.ZDCodeError("Premature semicolon! (state data upon parsing: {})".format(self._parse_temp))

                    self._parse_temp.append(o)
                    self._parse_state = "afunc.state.duration"

                elif self._parse_state == "afunc.state.duration":
                    if o == ";":
                        raise self.ZDCodeError("Premature semicolon! (state data upon parsing: {})".format(self._parse_temp))

                    self._parse_temp.append(o)
                    self._parse_state = "afunc.state.postduration"

                elif self._parse_state.startswith("afunc.state.postduration"):
                    if self._parse_state == "afunc.state.postduration":
                        if type(o) is list and o[0] == "[":
                            self._parse_temp.append(o[1])

                        elif o == ";":
                            for _ in xrange(self.repeat_num): self._func.states.append(ZDState(self._parse_temp[0], self._parse_temp[1], self._parse_temp[2], self._parse_temp[3:], self.__dict__.get("_state_action", None)))

                            try:
                                del self._state_action

                            except AttributeError:
                                pass

                            self._parse_state = "afunc.closure"

                        elif o == "@":
                            self._parse_state = "afunc.state.postduration2"

                        else:
                            raise self.ZDCodeError("Invalid state space token! (expecting ';' or '@', got '{}')".format(o))

                    elif self._parse_state == "afunc.state.postduration2":
                        self._state_action = "".join(o)
                        self._parse_state = "afunc.state.postduration"

            elif self._parse_state == "afunc.call":
                func_names = [x[0] for x in self._actor.funcs]
                functions_ = [x[1] for x in self._actor.funcs]

                if o not in func_names:
                    raise self.ZDCodeError("Call to nonexistant function '{}'!".format(o))

                self._call = ZDCall(self, self._actor.labels[-1], functions_[func_names.index(o)], repeats=self.repeat_num)

                self._parse_state = "afunc.call.arg_start"

            elif self._parse_state.startswith("afunc.call."):
                if self._parse_state == "afunc.call.arg":
                    if o != ")":
                        raise self.ZDCodeError("No parenthesis ending call to '{}': got '{}' instead!".format(self._call.func.name, o))

                    self._parse_state = "afunc.call.arg_start"

                elif self._parse_state == "afunc.call.arg_start":
                    if o not in ("(", ";"):
                        raise self.ZDCodeError("No parenthesis in function call to '{}'!".format(self._call.func.name))

                    if o == ";":
                        self._parse_state = "afunc.state"

                    else:
                        self._parse_state = "afunc.call.arg_mid"

                elif self._parse_state == "afunc.call.arg_mid":
                    if o == ")":
                        self._parse_state = "afunc.call.arg_end"

                    else:
                        self._call.args.append(o)
                        self._parse_state = "afunc.call.arg_mid2"

                elif self._parse_state == "afunc.call.arg_mid2":
                    if o == ",":
                        self._parse_state = "afunc.call.arg_mid"

                    elif o == ")":
                        self._parse_state = "afunc.call.arg_end"

                    else:
                        raise self.ZDCodeError("No comma or closing parenthesis in function call to '{}'!".format(self._call.func.name))

                elif self._parse_state == "afunc.call.arg_end":
                    if o != ";":
                        raise self.ZDCodeError("Missing semicolon in function call to '{}'!".format(self._call.func.name))

                    else:
                        self._parse_state == "afunc.closure"

            return

    def __decorate__(self):
        if not self.inventories:
            return "\n\n\n".join(decorate(a) for a in sorted(self.actors, key=lambda v: v.name))

        return "\n\n\n".join(["\n".join(
            decorate(i) for i in self.inventories
        )] + [
            decorate(a) for a in sorted(self.actors, key=lambda v: v.name)
        ]) # lines split for debugging

    def decorate(self):
        print "\n\nGenerating DECORATE...\n\n"
        return self.__decorate__()
