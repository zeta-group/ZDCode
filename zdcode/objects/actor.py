from ..types import *


class ZDBaseActor(object):
    def __init__(
        self,
        code: "ZDCode",
        name=None,
        inherit=None,
        replace=None,
        doomednum=None,
        _id=None,
    ):
        self.code = code
        self.name = name.strip()
        self.inherit = inherit
        self.replace = replace
        self.num = doomednum
        self.id = _id or make_id(30)


class ZDActor(ZDBaseActor):
    def __init__(
        self,
        code,
        name,
        inherit=None,
        replace=None,
        doomednum=None,
        _id=None,
        context=None,
    ):
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
        self.doomednum = doomednum

        if self.inherit and self.inherit.upper() in code.actor_names:
            self.all_funcs = list(code.actor_names[self.inherit.upper()].all_funcs)
            self.context.update(code.actor_names[self.inherit.upper()].context)

        else:
            self.all_funcs = []

        # code.actor_names[name.upper()] = self

    def __repr__(self):
        return "<ZDActor({}{}{}{})>".format(
            self.name,
            self.inherit and ("extends " + self.inherit) or "",
            self.replace and ("replaces " + self.replace or "") or "",
            self.doomednum and ("#" + str(self.doomednum)) or "",
        )

    def get_context(self):
        return self.context

    def make_spawn_label(self):
        return ZDLabel(
            self,
            "Spawn",
            [ZDRawDecorate("goto Super::Spawn" if self.inherit else "stop")],
            auto_append=False,
        )

    def get_spawn_label(self):
        for l in self.labels:
            if l.name.upper() == "SPAWN":
                return self.transform_spawn(l)

        return None

    def _set_user_var_state(self, var):
        vtype, vlit = var["value"]

        if vtype == "val":
            return [
                ZDState(
                    action="{}({}, {})".format(
                        _user_var_setters[var["type"]], stringify(var["name"]), vlit
                    )
                )
            ]

        elif vtype == "arr":
            return [
                ZDState(
                    action="{}({}, {}, {})".format(
                        _user_array_setters[var["type"]], stringify(var["name"]), i, v
                    )
                )
                for i, v in enumerate(vlit)
            ]

    def _get_spawn_prelude(self):
        return sum(
            [
                self._set_user_var_state(var)
                for var in self.uservars
                if var.get("value", None)
            ],
            [],
        )

    def prepare_spawn_label(self):
        label = self.get_spawn_label()

        if not label:
            label = self.make_spawn_label()

        if self.uservars:
            label.states = self._get_spawn_prelude() + label.states

    def top(self):
        r = TextNode()

        for p in sorted(self.properties, key=lambda p: p.name):
            r.add_line(decorate(p))

        r.add_line("")

        for u in self.uservars:
            r.add_line(
                "var {} {}{};".format(
                    u["type"],
                    u["name"],
                    "[{}]".format(u["size"]) if u.get("size", 0) else "",
                )
            )

        for f in self.flags:
            r.add_line("+{}".format(f))

        for a in self.antiflags:
            r.add_line("-{}".format(a))

        for rd in self.raw:
            r.add_line(rd)

        if len(r) == 1 and r[0].strip() == "":
            return "    "

        return r

    def transform_spawn(self, label: ZDLabel):
        if label.states[0].spawn_safe():
            return label

        # TODO: more comprehensive error handling and warning handling
        # (sike, ZDCode is not going to get new features!)
        print(
            f"Warning: Spawn label of class '{repr(self.name)}' is not spawn safe: "
            "auto-padding with 'TNT1 A 0'! Silence this warning by manually adding a "
            "'TNT1 A 0' at the start of the Spawn label."
        )

        new_label = ZDLabel(self, label.name, label.states, False)
        new_label.states.insert(0, ZDState.tnt1())
        return new_label

    def label_code(self):
        r = TextNode()

        for f in self.funcs:
            r.add_line(decorate(f[1]))

        for l in self.labels:
            if l.name.upper() == "SPAWN":
                l = self.transform_spawn(l)

            r.add_line(decorate(l))

        return r

    def header(self):
        r = self.name

        if self.inherit:
            r += " : {}".format(self.inherit)
        if self.replace:
            r += " replaces {}".format(self.replace)
        if self.num:
            r += " {}".format(str(self.num))

        return r

    def to_decorate(self):
        if self.labels + self.funcs:
            return TextNode(
                [
                    "Actor " + self.header(),
                    "{",
                    self.top(),
                    TextNode(
                        [
                            "States {",
                            self.label_code(),
                            "}",
                        ]
                    ),
                    "}",
                ],
                0,
            )

        return TextNode(["Actor " + self.header(), "{", self.top(), "}"], 0)
