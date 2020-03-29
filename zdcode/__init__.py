import textwrap
import string, random
import hashlib

try:
    from . import zdlexer

except ImportError:
    import zdlexer


actor_list = {}

def make_id(length = 30):
    """Returns an ID, which can be stored in the ZDCode
    to allow namespace compatibility between multiple
    ZDCode mods."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def decorate(o, *args, **kwargs):
    """Get the object's compiled DECORATE code."""
    # print("Getting DECORATE code for a {}...".format(type(o).__name__))
    return o.__decorate__(*args, **kwargs)

def big_lit(s, indent=4, tab_size=4, strip_borders=True):
    """This function assists in the creation of
fancier triple-quoted literals, by removing
trailing indentation in lines and trailing
and leading spaces/newlines from formatting."""

    if s == "":
        return ""

    while s[0] in "\n\r": s = s[1:]
    while s[-1] in "\n\r": s = s[:-1]
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

        self.code.properties.append(self)

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
        self.actor = label._actor
        self.repeats = repeats

        self.id = len(code.calls)

        code.calls.add(self)

        label.states.append(self)

        if repeats > 1:
            for _ in range(repeats):
                ZDCall(code, label, func, args, 1)

            del self

        elif "ZDCode_Call_{}_{}".format(code.id, self.id) not in [x.name for x in code.inventories]:
            ZDInventory(code, "ZDCode_Call_{}_{}".format(code.id, self.id))

    def post_load(self):
        if self.func in self.actor.namefuncs:
            self.actor.namefuncs[self.func].add_call(self)

    def num_states(self):
        return 2

    def add_arg(self, a):
        self.args.append(a)

    def __decorate__(self):
        r = ""
        func = self.actor.namefuncs[self.func]

        return r + "    TNT1 A 0 A_GiveInventory(\"_Call_{2}_{1}\")\n    Goto F_{0}\n_CLabel{1}:\n    TNT1 A 0 A_TakeInventory(\"_Call_{2}_{1}\")".format(func.name, self.id, self.code.id)

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

        self.id = len(actor.all_funcs)
        actor.funcs.append((name, self))
        actor.namefuncs[name] = self
        actor.all_funcs.append((name, self))

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
            result.append("TNT1 A 0 A_JumpIfInventory(\"_Call_{1}_{0}\", 1, \"_CLabel{0}\")".format(c.id, self.code.id))

        return ("    " + redent("\n".join(result), 4) if len(result) > 0 else "")

    def state_code(self):
        r = ""

        for s in self.states:
            if type(s) in (ZDState, ZDRawDecorate):
                r += "    {}\n".format(decorate(s))

            else:
                r += "{}\n".format(decorate(s))

        return r[:-1]

    def label_name(self):
        return "ZDCode_Func_" + self.name

    def __decorate__(self):
        code = "    ZDCode_Func_{}:".format(self.name)
        code += '\n' + self.state_code()

        cst = self.call_states()

        if cst != '':
            code += '\n' + cst

        code += "\n    TNT1 A -1"

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

    def num_states(self):
        return 1

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

    def label_name(self):
        return self.name

    def add_state(self, state):
        self.states.append(state)

    def __decorate__(self):
        if self.name.startswith("F_"):
            self.name = "_" + self.name

        r = "{}:".format(self.name)

        for s in self.states:
            if type(s) in (ZDState, ZDRawDecorate):
                r += "\n    {}".format(decorate(s))

            else:
                r += "\n{}".format(decorate(s))

        return r

class ZDReturnStatement(object):
    def __init__(self, func):
        self.func = func

    def num_states(self):
        return len(self.func.calls)

    def __decorate__(self):
        return big_lit(self.func.call_states() + "\n    Stop", 4)

class ZDRawDecorate(object):
    def __init__(self, raw):
        self.raw = raw

    def __decorate__(self):
        return self.raw

class ZDActor(object):
    def __init__(self, code, name="DefaultActor", inherit=None, replace=None, doomednum=None):
        self.code = code
        self.labels = []
        self.properties = []
        self.flags = []
        self.antiflags = []
        self.inherit = inherit
        self.name = name
        self.replace = replace
        self.num = doomednum
        self.funcs = []
        self.namefuncs = {}
        self.all_funcs = []
        self.raw = []

        actor_list[name] = self

        if inherit in actor_list:
            self.all_funcs = actor_list[inherit].all_funcs

    def top(self):
        r = []

        for p in sorted(self.properties, key=lambda p: p.name):
            r.append(decorate(p))

        r.append("")

        for f in self.flags:
            r.append("+{}".format(f))

        for a in self.antiflags:
            r.append("-{}".format(a))

        for rd in self.raw:
            r.append(rd)

        if len(r) == 1 and r[0] == "":
            return "    "

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
            t = self.top()
            return big_lit(
            """Actor {}
            {{
            {}
                States {{
                    {}
                }}
            }}""", 12).format(self.header(), redent(t, 4, unindent_first=False), redent(self.label_code(), unindent_first=True))

        return big_lit(
        """
        Actor {}
        {{
        {}
        }}""", 8).format(self.header(), redent(self.top(), 4, unindent_first=False))

class ZDClassTemplate(object):
    def __init__(self, template_parameters, parse_data, code, name="DefaultActor", inherit=None, replace=None, doomednum=None):
        self.template_parameters = list(template_parameters)
        self.code = code
        self.name = name
        self.inherit = inherit
        self.replace = replace
        self.doomednum = doomednum
        self.parse_data = parse_data

    def generated_class_name(self, parameter_values):
        hash = hashlib.md5()

        for parm in parameter_values:
            hash.update(parm.encode('utf-8'))

        return '{}__deriv_{}'.format(self.name, hash.hexdigest())

    def generate_init_class(self, parameter_values, name=None):
        new_name = name if name is not None else self.generated_class_name(parameter_values)

        return ZDActor(self.code, new_name, self.inherit, self.replace, self.doomednum)

    def get_init_replacements(self, parameter_values):
        return dict(zip((p.upper() for p in self.template_parameters), parameter_values))

class ZDRepeat(object):
    def __init__(self, actor, repeats, states):
        self._actor = actor
        self.states = states
        self.repeats = repeats

    def num_states(self):
        return sum(x.num_states() for x in self.states) * self.repeats

    def __decorate__(self):
        return redent('\n'.join([decorate(x) for x in self.states] * self.repeats), 4, unindent_first=False)

class ZDIfStatement(object):
    def __init__(self, actor, condition, states, inverted=False):
        self._actor = actor
        self.condition = condition
        self.states = states
        self.inverted = inverted

        if self.inverted:
            self.true_condition = condition

        else:
            self.true_condition = "!({})".format(condition)

    def num_states(self):
        return sum(x.num_states() for x in self.states) + 2

    def __decorate__(self):
        num_st = sum(x.num_states() for x in self.states)

        return redent("TNT1 A 0 A_JumpIf({}, {})\n".format(self.true_condition, num_st + 1) + '\n'.join(decorate(x) for x in self.states) + "\nTNT1 A 0", 4, unindent_first=False)


class ZDSometimes(object):
    def __init__(self, actor, chance, states):
        self._actor = actor
        self.chance = chance
        self.states = states
        self.real_fail_chance = str(int(2.55 * (100 - float(self.chance))))

    def num_states(self):
        return sum(x.num_states() for x in self.states) + 2

    def __decorate__(self):
        num_st = sum(x.num_states() for x in self.states)

        return redent("TNT1 A 0 A_Jump({}, {})\n".format(self.real_fail_chance, num_st + 1) + '\n'.join(decorate(x) for x in self.states) + "\nTNT1 A 0", 4, unindent_first=False)

num_whiles = 0

class ZDWhileStatement(object):
    def __init__(self, actor, condition, states):
        global num_whiles

        self._actor = actor
        self.condition = condition
        self.states = states
        self.id = num_whiles
        num_whiles += 1

    def num_states(self):
        return sum(x.num_states() for x in self.states) + 3

    def __decorate__(self):
        num_st = sum(x.num_states() for x in self.states)

        return redent("_WhileBlock{}:\n".format(self.id) + redent("TNT1 A 0 A_JumpIf(!({}), {})\n".format(self.condition, num_st + 1) + '\n'.join(decorate(x) for x in self.states) + "\nGoto _WhileBlock{}\nTNT1 A 0".format(self.id), 4, unindent_first=False), 0, unindent_first=False)

class ZDInventory(object):
    def __init__(self, code, name):
        self.name = name
        self.code = code

        code.inventories.append(self)

    def __decorate__(self):
        return "Actor {} : Inventory {{Inventory.MaxAmount 1}}".format(self.name)


# Parser!
class ZDCodeParseContext(object):
    def __init__(self, replacements=(), macros=(), templates=(), calls=()):
        self.macros = dict(macros)
        self.replacements = dict(replacements)
        self.templates = dict(templates)
        self.calls = list(calls)

    def derive(self):
        return ZDCodeParseContext(self.replacements, self.macros, self.templates, self.calls)

class ZDCode(object):
    class ZDCodeError(BaseException):
        pass

    @classmethod
    def parse(cls, code, dirname='.', error_handler=None):
        data = zdlexer.parse_code(code.strip(' \t\n'), dirname=dirname, error_handler=error_handler)

        if data:
            res = cls()
            res._parse(data)

            return res

        else:
            return None

    def _parse_literal(self, literal, context):
        if isinstance(literal, (tuple, list)):
            if literal[0] == 'number':
                return str(literal[1])

            elif literal[0] == 'string':
                return '"' + repr(literal[1])[1:-1] + '"'

            elif literal[0] == 'actor variable':
                if literal[1].upper() in context.replacements:
                    return context.replacements[literal[1].upper()]

                else:
                    return literal[1]

            elif literal[0] == 'call expr':
                return self._parse_action(literal[1])

            elif literal[0] == 'anonymous class':
                return self._parse_anonym_class(literal[1], context)

            elif literal[0] == 'template derivation':
                template_name, template_parms = literal[1]

                try:
                    template = context.templates[template_name]

                except KeyError:
                    raise RuntimeError("Unknown template to derive: '{}'".format(template_name))

                if len(template_parms) != len(template.template_parameters):
                    raise RuntimeError("Bad number of template parameters for '{}': expected {}, got {}".format(
                        template_name,
                        len(template.template_parameters),
                        len(template_parms)
                    ))

                new_class = self._derive_class_from_template(template, template_parms, context)

                return '"' + repr(new_class.name)[1:-1] + '"'

    def _parse_action(self, a, context):
        return "{}({})".format(a[0], (', '.join(self._parse_literal(x, context) for x in a[1]) if a[1] is not None else []))

    def _parse_state_action_or_body(self, a, context):
        if a[0] == 'action':
            return [self._parse_state_action(a[1], context)]

        else:
            res = []

            for x in a[1]:
                res.extend(self._parse_state_action_or_body(x, context))

            return res

    def _parse_state_action(self, a, context):
        args = ((context.replacements.get(x.upper(), x) if isinstance(x, str) else self._parse_literal(x, context)) for x in a[1] if x) if a[1] is not None else []

        args = ', '.join(a for a in args if a)

        if len(args) > 0:
            return "{}({})".format(a[0], args)

        else:
            return a[0]

    def _parse_state(self, actor, context: ZDCodeParseContext, label, s, func=None, alabel=None):
        if s[0] == 'frames':
            name, frames, duration, modifiers, action = s[1]

            for f in frames:
                if action is None:
                    label.states.append(ZDState(name, f, duration, modifiers))

                else:
                    body = self._parse_state_action_or_body(action, context)

                    for i, a in enumerate(body):
                        label.states.append(ZDState(name, f, (0 if i + 1 < len(body) else duration), modifiers, action=a))

        elif s[0] == 'return':
            if not isinstance(func, ZDFunction):
                raise ValueError("Return statement in non-function label: " + label.name)

            else:
                label.states.append(ZDReturnStatement(func))

        elif s[0] == 'call':
            ZDCall(self, label, s[1])

        elif s[0] == 'flow':
            if s[1].upper() == 'LOOP' and func != None:
                label.states.append(ZDRawDecorate('Goto {}'.format(func.label_name())))

            else:
                label.states.append(ZDRawDecorate(s[1].rstrip(';')))

        elif s[0] == 'repeat':
            #rep = ZDRepeat(actor, s[1][0], [])

            for _ in range(s[1][0]):
                for a in s[1][1]:
                    self._parse_state(actor, context, label, a, func)

        elif s[0] == 'sometimes':
            s = dict(s[1])
            sms = ZDSometimes(actor, float(s['chance'][1]), [])

            for a in s['body']:
                self._parse_state(actor, context, sms, a, func)

            label.states.append(sms)

        elif s[0] == 'if':
            ifs = ZDIfStatement(actor, s[1][0], [])
            elses = None

            for a in s[1][1]:
                self._parse_state(actor, context, ifs, a, func)

            if s[1][2] is not None:
                elses = ZDIfStatement(actor, s[1][0], [], inverted=True)

                for a in s[1][2]:
                    self._parse_state(actor, context, elses, a, func)

            label.states.append(ifs)

            if elses is not None:
                label.states.append(elses)

        elif s[0] == 'while':
            whs = ZDWhileStatement(actor, s[1][0], [])

            for a in s[1][1]:
                self._parse_state(actor, context, whs, a, func)

            label.states.append(whs)

        elif s[0] == 'inject':
            macros = dict(context.macros)
            r_name, r_args = s[1]

            if r_name in macros:
                new_context = context.derive()
                r = new_context.replacements

                (m_args, m_body) = macros[r_name]

                for rn, an in zip(r_args, m_args):
                    r[an.upper()] = rn

                for a in m_body:
                    self._parse_state(actor, new_context, label, a, label)

            else:
                raise ValueError("Unknown macro: {}".format(repr(r_name)))


    def stringify(self, content):
        if isinstance(content, str):
            return '"' + repr(content)[1:-1] + '"'

        return repr(content)

    def _parse_anonym_class(self, anonym_class, context):
        a = dict(anonym_class)
        anonym_actor = ZDActor(self, '_AnonymClass_{}_{}'.format(self.id, len(self.anonymous_classes)), a['inheritance'])

        new_context = context.derive()

        self._parse_class_body(anonym_actor, new_context, a['body'])

        self.anonymous_classes.append(anonym_actor)
        self.inventories.append(anonym_actor)

        return self.stringify(anonym_actor.name)

    def _derive_class_from_template(self, template, param_values, context, name=None):
        new_context = context.derive()

        actor = template.generate_init_class(param_values, name=name)
        new_context.replacements.update(template.get_init_replacements(param_values))

        self._parse_class_body(actor, new_context, template.parse_data)

        self.actors.append(actor)

        return actor

    def _parse_class_body(self, actor, context, body):
        for btype, bdata in body:
            if btype == 'macro':
                context.macros[bdata['name']] = (bdata['args'], bdata['body'])

        for btype, bdata in body:
            if btype == 'property':
                ZDProperty(actor, bdata['name'], ', '.join(self._parse_literal(x, context) for x in bdata['value']))

            elif btype == 'flag':
                actor.flags.append(bdata)

            elif btype == 'flag combo':
                actor.raw.append(bdata)

            elif btype == 'unflag':
                actor.antiflags.append(bdata)

            elif btype == 'label':
                label = ZDLabel(actor, bdata['name'])

                for s in bdata['body']:
                    self._parse_state(actor, context, label, s, None)

            elif btype == 'function':
                func = ZDFunction(self, actor, bdata['name'])

                for s in bdata['body']:
                    self._parse_state(actor, context, func, s, func)

    def _parse(self, actors):
        context = ZDCodeParseContext()

        actors = list(actors)

        for class_type, a in actors:
            if class_type == 'class template':
                template = ZDClassTemplate(a['parameters'], a['body'], self, a['classname'], a['inheritance'], a['replacement'], a['class number'])
                context.templates[a['classname']] = template

        for class_type, a in actors:
            if class_type == 'class':
                actor = ZDActor(self, a['classname'], a['inheritance'], a['replacement'], a['class number'])

                self._parse_class_body(actor, context, a['body'])

                self.actors.append(actor)

            elif class_type == 'static template derivation':
                new_name = a['classname']

                template_name, template_parms = a['source'][1]

                try:
                    template = context.templates[template_name]

                except KeyError:
                    raise RuntimeError("Unknown template to derive: '{}'".format(template_name))

                if len(template_parms) != len(template.template_parameters):
                    raise RuntimeError("Bad number of template parameters for '{}': expected {}, got {}".format(
                        template_name,
                        len(template.template_parameters),
                        len(template_parms)
                    ))

                actor = self._derive_class_from_template(template, template_parms, context, name=new_name)

        for c in self.calls:
            c.post_load()

    def __init__(self):
        self.inventories = []
        self.anonymous_classes = []
        self.actors = []
        self.id = make_id(35)
        self.calls = set()

    def __decorate__(self):
        if not self.inventories:
            return "\n\n\n".join(decorate(a) for a in sorted(self.actors, key=lambda v: v.name))

        return "\n\n\n".join(["\n".join(
            decorate(i) for i in self.inventories
        )] + [
            decorate(a) for a in sorted(self.actors, key=lambda v: v.name)
        ]) # lines split for debugging

    def decorate(self):
        print("Generating DECORATE...")
        return self.__decorate__()
