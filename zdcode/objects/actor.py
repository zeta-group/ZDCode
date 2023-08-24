from typing import TYPE_CHECKING
from typing import Iterable

from .. import _user_array_setters
from .. import _user_var_setters
from ..compiler.context import ZDCodeParseContext
from ..types.basic import ZDStateObject
from ..util import TextNode
from ..util import decorate
from ..util import make_id
from ..util import stringify
from .label import ZDLabel
from .raw import ZDRawDecorate
from .state import ZDState

if TYPE_CHECKING:
    from ..compiler.compiler import ZDCode


class ZDBaseActor(object):
    """A basic actor-like class."""

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
    """A DECORATE class."""

    def __init__(
        self,
        code,
        name,
        inherit=None,
        replace=None,
        doomednum=None,
        _id=None,
        context: ZDCodeParseContext | None = None,
    ):
        if context:
            self.context = context.derive()

        else:
            raise ValueError("context must be set")

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

    def __repr__(self) -> str:
        return f"<ZDActor({self.name}{self.inherit and 'extends ' + self.inherit or ''}{self.replace and ('replaces ' + self.replace or '') or ''}{self.doomednum and '#' + str(self.doomednum) or ''})>"

    def get_context(self) -> ZDCodeParseContext:
        """Returns the [ZDCodeParseContext] of this Actor."""
        return self.context

    def make_spawn_label(self) -> ZDLabel:
        """Creates a dummy Spawn label.

        It is not registered."""
        return ZDLabel(
            self,
            "Spawn",
            [ZDRawDecorate("goto Super::Spawn" if self.inherit else "stop")],
            auto_append=False,
        )

    def get_spawn_label(self) -> ZDLabel | None:
        """Returns the Spawn label, if there is one."""
        for label in self.labels:
            if label.name.upper() == "SPAWN":
                return self.transform_spawn(label)

        return None

    def _set_user_var_state(self, var) -> Iterable[ZDState]:
        """Returns states that set the initial values of the actor's user vars."""
        vtype, vlit = var["value"]

        if vtype == "val":
            return [
                ZDState(
                    action=f"{_user_var_setters[var['type']]}({stringify(var['name'])}, {vlit})"
                )
            ]

        elif vtype == "arr":
            return [
                ZDState(
                    action=f"{_user_array_setters[var['type']]}({stringify(var['name'])}, {i}, {v})"
                )
                for i, v in enumerate(vlit)
            ]

    def _get_spawn_prelude(self) -> Iterable[ZDStateObject]:
        """Returns the prelude of the Spawn funtion."""
        return sum(
            [
                self._set_user_var_state(var)
                for var in self.uservars
                if var.get("value", None)
            ],
            [],
        )

    def prepare_spawn_label(self):
        """Prepares the Spawn label by adding a prelude."""
        label = self.get_spawn_label()

        if not label:
            label = self.make_spawn_label()

        if self.uservars:
            label.states = self._get_spawn_prelude() + label.states

    def top(self):
        """Returns the 'top' section of the class code.

        The top holds every property, flag, combo, and user variable declaration in
        the DECORATE class.
        """
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
            r.add_line(f"+{f}")

        for a in self.antiflags:
            r.add_line(f"-{a}")

        for rd in self.raw:
            r.add_line(rd)

        if len(r) == 1 and r[0].strip() == "":
            return "    "

        return r

    def transform_spawn(self, label: ZDLabel) -> ZDLabel:
        """Transforms the Spawn label, making it spawn safe."""
        if label.states[0].spawn_safe():
            return label

        # WIP: more comprehensive error handling and warning handling
        # (sike, ZDCode is not going to get new features!)

        # WIP: add "strict mode", error out here in sttict mode
        print(
            f"Warning: Spawn label of class '{repr(self.name)}' is not spawn safe: "
            "auto-padding with 'TNT1 A 0'! Silence this warning by manually adding a "
            "'TNT1 A 0' at the start of the Spawn label."
        )

        new_label = ZDLabel(self, label.name, label.states, False)
        new_label.states.insert(0, ZDState.tnt1())
        return new_label

    def label_code(self) -> TextNode:
        """Returns a single TextNode holding DECORATE for the class's label code.

        Any code that isn't the class declaration or the top is considered 'label code'.
        """
        r = TextNode()

        for f in self.funcs:
            r.add_line(decorate(f[1]))

        for label in self.labels:
            if label.name.upper() == "SPAWN":
                label = self.transform_spawn(label)

            r.add_line(decorate(label))

        return r

    def header(self) -> str:
        """Returns the header of the class.

        The header is the portion that comes right after the classname in
        DECCORATE. It contains informatino such as inheritancce, replacement,
        and the editor number (DoomEdNum).
        """
        r = self.name

        if self.inherit:
            r += f" : {self.inherit}"
        if self.replace:
            r += f" replaces {self.replace}"
        if self.num:
            r += f" {str(self.num)}"

        return r

    def to_decorate(self) -> TextNode:
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
