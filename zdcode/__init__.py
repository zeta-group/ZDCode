from typing import List

import warnings
import textwrap
import string, random
import hashlib

try:
    from . import zdlexer

except ImportError:
    import zdlexer


actor_list = {}

_user_var_setters = {
    'int': 'A_SetUserVar',
    'float': 'A_SetUserVarFloat',
}

_user_array_setters = {
    'int': 'A_SetUserArray',
    'float': 'A_SetUserArrayFloat',
}

def stringify(content):
    if isinstance(content, str):
        if content[0] in "'\"" and content[-1] == content[0] and len(content) > 1:
            return content

        return '"' + repr(content)[1:-1] + '"'

    return repr(content)

def make_id(length = 30):
    """Returns an ID, which can be stored in the ZDCode
    to allow namespace compatibility between multiple
    ZDCode mods."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def decorate(o, *args, **kwargs):
    """Get the object's compiled DECORATE code."""
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
    def __init__(self, actor, name, value):
        self.actor = actor
        self.name = name.strip()
        self.value = value

        self.actor.properties.append(self)

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

        return r + "    TNT1 A 0 A_GiveInventory(\"ZDCode_Call_{2}_{1}\")\n    Goto ZDCode_Func_{0}\nZDCode_CLabel{1}:\n    TNT1 A 0 A_TakeInventory(\"ZDCode_Call_{2}_{1}\")".format(func.name, self.id, self.code.id)

class ZDFunction(object):
    def __init__(self, code, actor, name, args=None, states=None):
        if not args:
            args = []

        if not states:
            states = []

        self.code = code
        self.name = name.strip()
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
            result.append("TNT1 A 0 A_JumpIfInventory(\"ZDCode_Call_{1}_{0}\", 1, \"ZDCode_CLabel{0}\")".format(c.id, self.code.id))

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

        code += "\n    TNT1 A -1\n    Stop"

        return code

class ZDState(object):
    def __init__(self, sprite='"####"', frame='"#"', duration=0, keywords=None, action=None):
        if not keywords:
            keywords = []

        self.sprite = sprite
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
    def __init__(self, _actor, name, states=None, auto_append=True):
        if not states:
            states = []

        self.name = name.strip()
        self.states = states
        self._actor = _actor

        if auto_append:
            self._actor.labels.append(self)

    def __repr__(self):
        return "{}({} of {})".format(type(self).__name__, self.name, repr(self._actor.name))

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

    def num_states(self):
        return 0

    def __decorate__(self):
        return self.raw

class ZDActor(object):
    def __init__(self, code, name, inherit=None, replace=None, doomednum=None, _id=None, context=None):
        if context:
            self.context = context.derive()

        else:
            self.context = ZDCodeParseContext()

        ZDBaseActor.__init__(self, code, name, inherit, replace, doomednum, _id)

        self.labels = []
        self.properties = []
        self.flags = set()
        self.uservars = []
        self.antiflags = set()
        self.funcs = []
        self.namefuncs = {}
        self.raw = []

        if self.inherit and self.inherit in actor_list:
            self.all_funcs = list(actor_list[self.inherit].all_funcs)
            self.context.update(actor_list[self.inherit].context)

        else:
            self.all_funcs = []

        actor_list[name] = self

    def make_spawn_label(self):
        return ZDLabel(self, 'Spawn', [ZDRawDecorate('goto Super::Spawn' if self.inherit else 'stop')], auto_append=False)

    def get_spawn_label(self):
        for l in self.labels:
            if l.name.upper() == 'SPAWN':
                return l

        return None

    def _set_user_var_state(self, var):
        vtype, vlit = var['value']

        if vtype == 'val':
            return [ZDState(action='{}({}, {})'.format(_user_var_setters[var['type']], stringify(var['name']), vlit))]

        elif vtype == 'arr':
            return [ZDState(action='{}({}, {}, {})'.format(_user_array_setters[var['type']], stringify(var['name']), i, v)) for i, v in enumerate(vlit)]

    def _get_spawn_prelude(self):
        return sum([self._set_user_var_state(var) for var in self.uservars if var.get('value', None)], [])

    def prepare_spawn_label(self):
        label = self.get_spawn_label()

        if self.uservars:
            if not label:
                label = self.make_spawn_label()

            label.states = [ZDState()] + self._get_spawn_prelude() + label.states

        elif label:
            label.states.insert(0, ZDState())

    def get_context(self):
        new_ctx = self.context.derive()

        if self.inherit in actor_list:
            new_ctx.update(actor_list[self.inherit].get_context())

        return new_ctx

    def top(self):
        r = []

        for p in sorted(self.properties, key=lambda p: p.name):
            r.append(decorate(p))

        r.append("")

        for u in self.uservars:
            r.append('var {} {}{};'.format(u['type'], u['name'], '[{}]'.format(u['size']) if u.get('size', 0) else ''))

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

class ZDBaseActor(object):
    def __init__(self, code, name=None, inherit=None, replace=None, doomednum=None, _id=None):
        self.code = code
        self.name = name.strip()
        self.inherit = inherit
        self.replace = replace
        self.num = doomednum
        self.id = _id or make_id(30)

class ZDClassTemplate(ZDBaseActor):
    def __init__(self, template_parameters, parse_data, abstract_label_names, abstract_macro_names, abstract_array_names, code, name, inherit=None, replace=None, doomednum=None, _id=None):
        ZDBaseActor.__init__(self, code, name, inherit, replace, doomednum, _id)

        self.template_parameters = list(template_parameters)

        self.abstract_label_names = set(abstract_label_names)
        self.abstract_macro_names = dict(abstract_macro_names)
        self.abstract_array_names = dict(abstract_array_names)

        self.parse_data = parse_data
        self.parametric_table = {}

    def generated_class_name(self, parameter_values, new_id):
        hash = hashlib.sha1()

        hash.update(self.name.encode('utf-8'))
        hash.update(self.id.encode('utf-8'))
        hash.update(new_id.encode('utf-8'))

        for parm in parameter_values:
            hash.update(parm.encode('utf-8'))

        for name in self.abstract_label_names:
            hash.update(name.encode('utf-8'))

        for name, args in self.abstract_macro_names.items():
            hash.update(name.encode('utf-8'))

            for arg in args:
                hash.update(arg.encode('utf-8'))

        return '{}__deriv_{}'.format(self.name, hash.hexdigest())

    def generate_init_class(self, code, context, parameter_values, provided_label_names=(), provided_macro_names=(), provided_array_names=(), name=None, pending=None):
        if tuple(parameter_values) in self.parametric_table and not self.abstract_label_names and not self.abstract_macro_names:
            return (False, self.parametric_table[tuple(parameter_values)])

        provided_label_names = set(provided_label_names)
        provided_macro_names = dict(provided_macro_names)

        new_name = name if name is not None else self.generated_class_name(parameter_values, make_id(40))

        inh = self.inherit and context.replacements.get(self.inherit.upper(), self.inherit) or None
        rep = self.replace and context.replacements.get(self.replace.upper(), self.replace) or None

        res = ZDActor(self.code, new_name, inh, rep, self.num, context=context)

        for l in self.abstract_label_names:
            if l not in provided_label_names:
                raise RuntimeError("Tried to derive template {}, but abstract label {} does not have a definition!".format(self.name, l))

        for m, a in self.abstract_macro_names.items():
            if m not in provided_macro_names.keys():
                raise RuntimeError("Tried to derive template {}, but abstract macro {} does not have a definition!".format(self.name, m))

            if len(a) != len(provided_macro_names[m]):
                raise RuntimeError("Tried to derive template {}, but abstract macro {} has the wrong number of arguments: expected {}, got {}!".format(self.name, m, len(a), len(provided_macro_names[m])))

        for m, a in self.abstract_array_names.items():
            if m not in provided_array_names.keys():
                raise RuntimeError("Tried to derive template {}, but abstract array {} is not defined!".format(self.name, m))

            if a['size'] != 'any' and a['size'] != provided_array_names[m]:
                raise RuntimeError("Tried to derive template {}, but abstract array {} has a size constraint; expected {} array elements, got {}!".format(self.name, m, a['size'], provided_array_names[m]))

        self.parametric_table[tuple(parameter_values)] = res

        return (True, res)

    def get_init_replacements(self, code, context, parameter_values):
        return dict(zip((p.upper() for p in self.template_parameters), parameter_values))

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

    def num_states(self):
        return sum(x.num_states() for x in self.states) + 2

    def __decorate__(self):
        num_st = sum(x.num_states() for x in self.states)

        return redent("TNT1 A 0 A_Jump(255-(2.55*({})), {})\n".format(self.chance, num_st + 1) + '\n'.join(decorate(x) for x in self.states) + "\nTNT1 A 0", 4, unindent_first=False)

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
        return sum(x.num_states() for x in self.states) + 2

    def __decorate__(self):
        num_st = sum(x.num_states() for x in self.states)

        return redent("_WhileBlock{}:\n".format(self.id) + redent("TNT1 A 0 A_JumpIf(!({}), {})\n".format(self.condition, num_st + 1) + '\n'.join(decorate(x) for x in self.states) + "\nGoto _WhileBlock{}\nTNT1 A 0".format(self.id), 4, unindent_first=False), 0, unindent_first=False)

class ZDInventory(object):
    def __init__(self, code, name):
        self.name = name.strip()
        self.code = code

        code.inventories.append(self)

    def __decorate__(self):
        return "Actor {} : Inventory {{Inventory.MaxAmount 1}}".format(self.name)


# Parser!
class ZDCodeParseContext(object):
    def __init__(self, replacements=(), macros=(), templates=(), calls=(), actors=()):
        self.macros = dict(macros)
        self.replacements = dict(replacements)
        self.templates = dict(templates)
        self.call_lists = list(calls) if calls else [[]]
        self.actor_lists = list(actors) if actors else [[]]

    def derive(self) -> "ZDCodeParseContext":
        return ZDCodeParseContext(self.replacements, self.macros, self.templates, self.call_lists, self.actor_lists)

    def update(self, other_ctx: "ZDCodeParseContext"):
        self.macros.update(other_ctx.macros)
        self.replacements.update(other_ctx.replacements)
        self.templates.update(other_ctx.templates)

    def add_call(self, c: ZDCall):
        for cl in self.call_lists:
            cl.append(c)

    def add_actor(self, ac: ZDActor):
        for al in self.actor_lists:
            al.append(ac)

class ZDCode(object):
    class ZDCodeError(BaseException):
        pass

    @classmethod
    def parse(cls, code, fname=None, dirname='.', error_handler=None):
        data = zdlexer.parse_code(code.strip(' \t\n'), dirname=dirname, filename=fname, error_handler=error_handler)

        if data:
            res = cls()
            res._parse(data)

            return res

        else:
            return None

    def add(self, code, fname=None, dirname='.', error_handler=None):
        data = zdlexer.parse_code(code.strip(' \t\n'), dirname=dirname, filename=fname, error_handler=error_handler)

        if data:
            self._parse(data)

        return bool(data)

    def _parse_expression(self, expr, context):
        etype, exval = expr

        if etype == 'expr':
            return ' '.join(self._parse_expression(item, context) for item in exval)

        elif etype == 'literal':
            return self._parse_literal(exval, context)

        elif etype == 'array index':
            return '[' + self._parse_expression(exval, context) + ']'

        elif etype == 'oper':
            return exval

        elif etype == 'paren expr':
            return '(' + self._parse_expression(exval, context) + ')'

    def _parse_argument(self, arg, context):
        atype, aval = arg

        if atype == 'position arg':
            return self._parse_parameter(aval, context)

        elif atype == 'named arg':
            return '{}: {}'.format(aval[0], self._parse_parameter(aval[1], context))

    def _parse_parameter(self, parm, context):
        ptype, pval = parm

        if ptype == 'expression':
            return self._parse_expression(pval, context)

        elif ptype == 'template derivation':
            return self._parse_template_derivation(pval, context)

        elif ptype == 'anonymous class':
            return self._parse_anonym_class(pval, context)

    def _parse_literal(self, literal, context):
        if isinstance(literal, str):
            return literal

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
            return self._parse_action(literal[1], context)

        elif literal[0] == 'anonymous class':
            return self._parse_anonym_class(literal[1], context)

        elif literal[0] == 'template derivation':
            return self._parse_template_derivation(literal[1])

    def _parse_array(self, arr, context):
        arr = dict(arr)
        arr['value'] = ('array', [self._parse_expression(e, context) for e in arr['value'][1]])

        return arr

    def _parse_template_derivation(self, deriv, context, pending=None, name=None, stringify=True):
        template_name, template_parms, deriv_body = deriv
        template_parms = [self._parse_parameter(a, context) for a in template_parms]
        template_parms = [a for a in template_parms if a != '']

        template_labels = {}
        template_body = []
        template_macros = {}
        template_arrays = {}

        try:
            template = context.templates[template_name]

        except KeyError:
            raise RuntimeError("Unknown template to derive: '{}'".format(template_name))

        for btype, bdata in deriv_body:
            if btype in ('flag', 'unflag', 'user var', 'array'):
                if btype == 'array':
                    bdata = self._parse_array(bdata, context)
                    template_arrays[bdata['name']] = bdata

                template_body.append((btype, bdata))

            elif btype == 'label':
                if bdata['name'] in template.abstract_label_names:
                    template_labels[bdata['name']] = bdata

            elif btype == 'macro':
                if bdata['name'] in template.abstract_macro_names:
                    template_macros[bdata['name']] = bdata

        if len(template_parms) != len(template.template_parameters):
            raise RuntimeError("Bad number of template parameters for '{}': expected {}, got {}".format(
                template_name,
                len(template.template_parameters),
                len(template_parms)
            ))

        new_class = self._derive_class_from_template(template, template_parms, context, template_labels, template_macros, template_arrays, template_body, pending=pending, name=name)

        if stringify:
            return '"' + repr(new_class.name)[1:-1] + '"'

        else:
            return new_class

    def _parse_action(self, a, context):
        aname = a[0]
        aname = context.replacements.get(aname.upper(), aname)

        args = list(a[1]) if a[1] else []
        args = [(context.replacements.get(x.upper(), x) if isinstance(x, str) else x) for x in args]
        args = [self._parse_argument(x, context) for x in args]
        args = ', '.join(a for a in args if a)

        return "{}({})".format(aname, args)

    def _parse_state_action_or_body(self, a, context):
        if a[0] == 'action':
            return [self._parse_state_action(a[1], context)]

        else:
            res = []

            for x in a[1]:
                res.extend(self._parse_state_action_or_body(x, context))

            return res

    def _parse_state_action(self, a, context):
        args = list(a[1]) if a[1] else []
        args = [self._parse_argument(x, context) for x in args]
        args = [(context.replacements.get(x.upper(), x) if isinstance(x, str) else x) for x in args]
        args = ', '.join(a for a in args if a)

        if len(args) > 0:
            return "{}({})".format(a[0], args)

        else:
            return a[0]

    def _parse_replaceable_number(self, cval, context: ZDCodeParseContext):
        if isinstance(cval, str):
            cval = context.replacements.get(cval.upper(), cval)

        try:
            count = int(cval)

        except ValueError:
            raise ValueError("Invalid repeat count: expected valid integer, got {}".format(repr(cval)))

        else:
            return count

    def _parse_state(self, actor, context: ZDCodeParseContext, label, s, func=None, alabel=None):
        if s[0] == 'frames':
            (sprite_type, sprite_name), frames, duration, modifiers, action = s[1]

            if sprite_type == 'normal':
                name = sprite_name

            elif sprite_type == 'parametrized':
                try:
                    new_name = context.replacements[sprite_name.upper()]

                    if new_name[0] == "'" and new_name[-1] == "'":
                        new_name = new_name[1:-1]

                    elif new_name[0] == '"' and new_name[-1] == '"':
                        new_name = new_name[1:-1]

                    else:
                        raise RuntimeError("Parametrized sprite '{}' in {} needs to be passed a string; got {}".format(sprite_name, actor.name, repr(new_name)))

                    name = new_name

                except KeyError:
                    raise RuntimeError("No parameter {} for parametrized sprite name!".format(repr(sprite_name)))

            if frames == '"#"':
                frames = ['"#"']

            for f in frames:
                if action is None:
                    label.states.append(ZDState(name, f, duration, modifiers))

                else:
                    body = self._parse_state_action_or_body(action, context)

                    for i, a in enumerate(body):
                        label.states.append(ZDState(name, f, (0 if i + 1 < len(body) else duration), modifiers, action=a))

        elif s[0] == 'return':
            if not isinstance(func, ZDFunction):
                raise ValueError("Return statement in non-function label: " + repr(label.name))

            else:
                label.states.append(ZDReturnStatement(func))

        elif s[0] == 'call':
            context.add_call(ZDCall(self, label, s[1]))

        elif s[0] == 'flow':
            if s[1].upper().rstrip(';') == 'LOOP':
                label.states.append(ZDRawDecorate('goto {}'.format(label.name)))

            else:
                label.states.append(ZDRawDecorate(s[1].lower().rstrip(';')))

        elif s[0] == 'repeat':
            cval = s[1][0]

            count = self._parse_replaceable_number(cval, context)

            if count >= 1:
                for _ in range(count):
                    for a in s[1][1]:
                        self._parse_state(actor, context, label, a, func)

        elif s[0] == 'sometimes':
            s = dict(s[1])

            chance = self._parse_expression(s['chance'], context)
            sms = ZDSometimes(actor, chance, [])

            for a in s['body']:
                self._parse_state(actor, context, sms, a, func)

            label.states.append(sms)

        elif s[0] == 'if':
            ifs = ZDIfStatement(actor, self._parse_expression(s[1][0], context), [])
            elses = None

            for a in s[1][1]:
                self._parse_state(actor, context, ifs, a, func)

            if s[1][2] is not None:
                elses = ZDIfStatement(actor, self._parse_expression(s[1][0], context), [], inverted=True)

                for a in s[1][2]:
                    self._parse_state(actor, context, elses, a, func)

            label.states.append(ifs)

            if elses is not None:
                label.states.append(elses)

        elif s[0] == 'while':
            whs = ZDWhileStatement(actor, self._parse_expression(s[1][0], context), [])

            for a in s[1][1]:
                self._parse_state(actor, context, whs, a, func)

            label.states.append(whs)

        elif s[0] == 'inject':
            macros = dict(context.macros)
            r_name, r_args = s[1]

            if r_name in macros:
                new_context = context.derive()

                (m_args, m_body) = macros[r_name]

                for rn, an in zip(r_args, m_args):
                    new_context.replacements[an.upper()] = self._parse_argument(rn, context)

                for a in m_body:
                    self._parse_state(actor, new_context, label, a, label)

            else:
                raise ValueError("Unknown macro: {}".format(repr(r_name)))

    def _parse_inherit(self, inh, context):
        if inh is None:
            return None

        ptype, pval = inh

        if ptype == 'classname':
            return context.replacements.get(pval.upper(), pval)

        elif ptype == 'template derivation':
            return self._parse_template_derivation(pval, context, stringify=False).name

    def _parse_anonym_class(self, anonym_class, context):
        a = dict(anonym_class)
        new_context = context.derive()
        
        anonym_actor = ZDActor(self, '_AnonymClass_{}_{}'.format(self.id, len(self.anonymous_classes)), inherit=self._parse_inherit(a['inheritance'], context), context=new_context)

        self._parse_class_body(anonym_actor, new_context, a['body'])
        
        context.add_actor(anonym_actor)

        self.anonymous_classes.append(anonym_actor)
        self.inventories.append(anonym_actor)

        return stringify(anonym_actor.name)

    def _derive_class_from_template(self, template, param_values, context, labels=(), macros=(), arrays=(), body=(), name=None, pending=None):
        labels = dict(labels)
        macros = dict(macros)
        arrays = dict(arrays)
        body = list(body)

        name = name or template.generated_class_name(param_values, make_id(40))

        new_context = context.derive()
        new_context.replacements.update(template.get_init_replacements(self, context, param_values))
        new_context.replacements['SELF'] = '"' + repr(name)[1:-1] + '"'

        needs_init, actor = template.generate_init_class(self, new_context, param_values, set(labels.keys()), { m['name']: m['args'] for m in macros.values() }, { a['name']: len(a['value']) for a in arrays.values() }, name=name)

        new_context = actor.get_context()

        for name, macro in macros.items():
            new_context.macros[name] = (macro['args'], macro['body'])

        if needs_init:
            for btype, bdata in body:
                if btype == 'flag':
                    actor.flags.add(bdata)

                elif btype == 'antiflag':
                    actor.antiflags.add(bdata)

                elif btype == 'user var':
                    bdata = { **bdata, 'value': self._parse_expression(bdata['value'], context) }
                    actor.uservars.append(bdata)

                if btype == 'array':
                    try:
                        absarray = template.abstract_array_names[bdata['name']]

                    except KeyError:
                        pass

                    else:
                        actor.uservars.append({'name': bdata['name'], 'size': len(bdata['value'][1]), 'value': ('arr', bdata['value'][1]), 'type': absarray['type']})

            def pending_oper_gen():
                act = actor
                new_ctx = new_context
                temp = template
                labls = labels

                def pending_oper():
                    self._parse_class_body(act, new_ctx, temp.parse_data)

                    for lname, lval in labls:
                        label = ZDLabel(act, lname)

                        for s in lval['body']:
                            self._parse_state(act, new_ctx, label, s, None)

                return pending_oper

            if pending:
                pending.append(pending_oper_gen())

            else:
                pending_oper_gen()()

            self.actors.append(actor)

        return actor

    def _parse_class_body(self, actor, context, body):
        for btype, bdata in body:
            if btype == 'macro':
                context.macros[bdata['name']] = (bdata['args'], bdata['body'])

        for btype, bdata in body:
            if btype == 'property':
                ZDProperty(actor, bdata['name'], ', '.join(self._parse_parameter(x, context) for x in bdata['value']))

            elif btype == 'flag':
                actor.flags.add(bdata)

            elif btype == 'flag combo':
                actor.raw.append(bdata)

            elif btype == 'user var':
                bdata = { **bdata, 'value': self._parse_expression(bdata['value'], context) }
                actor.uservars.append(bdata)

            elif btype == 'unflag':
                actor.antiflags.add(bdata)

            elif btype == 'label':
                label = ZDLabel(actor, bdata['name'])

                for s in bdata['body']:
                    self._parse_state(actor, context, label, s, None)

            elif btype == 'function':
                func = ZDFunction(self, actor, bdata['name'])

                for s in bdata['body']:
                    self._parse_state(actor, context, func, s, func)

    def _parse(self, actors):
        calls = []
        parsed_actors = []
        
        context = ZDCodeParseContext(calls=[calls], actors=[parsed_actors])

        actors = list(actors)

        for class_type, a in actors:
            if class_type == 'class template':
                abstract_labels = set()
                abstract_macros = {}
                abstract_arrays = {}

                for btype, bdata in a['body']:
                    if btype == 'abstract label':
                        abstract_labels.add(bdata)

                    elif btype == 'abstract macro':
                        abstract_macros[bdata['name']] = bdata['args']

                    elif btype == 'abstract array':
                        abstract_arrays[bdata['name']] = bdata

                template = ZDClassTemplate(a['parameters'], a['body'], abstract_labels, abstract_macros, abstract_arrays, self, a['classname'], self._parse_inherit(a['inheritance'], context), a['replacement'], a['class number'])
                context.templates[a['classname']] = template

        pending = []

        for class_type, a in actors:
            if class_type == 'class':
                actor = ZDActor(self, a['classname'], self._parse_inherit(a['inheritance'], context), a['replacement'], a['class number'], context=context)
                ctx = actor.get_context()

                def pending_oper_gen():
                    actor_ = actor
                    ctx_ = ctx
                    body_ = a['body']

                    def pending_oper():
                        self._parse_class_body(actor_, ctx_, body_)

                    return pending_oper

                pending.append(pending_oper_gen())

                self.actors.append(actor)
                parsed_actors.append(actor)

            elif class_type == 'static template derivation':
                new_name = a['classname']

                parsed_actors.append(self._parse_template_derivation(a['source'][1], context, pending=pending, name=new_name, stringify=False))

        for p in pending:
            p()

        for c in calls:
            c.post_load()

        for a in parsed_actors:
            a.prepare_spawn_label()

    def __init__(self):
        self.inventories = []
        self.anonymous_classes = []
        self.actors = []
        self.id = make_id(35)
        self.calls = set()

    def __decorate__(self):
        if not self.inventories:
            return "\n\n\n".join(decorate(a) for a in self.actors)

        return "\n\n\n".join(["\n".join(
            decorate(i) for i in self.inventories
        )] + [
            decorate(a) for a in self.actors
        ]) # lines split for debugging

    def decorate(self):
        return self.__decorate__()
