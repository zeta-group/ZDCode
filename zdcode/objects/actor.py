"""The DECORATE actor class and related classes."""
from typing import TYPE_CHECKING
from typing import Iterable

from .. import _user_array_setters
from .. import _user_var_setters
from ..compiler.context import ZDCodeParseContext
from ..types.basic import ZDObject
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


class ZDBaseActor:
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
        self.identifier = _id or make_id(30)


class ZDActor(ZDBaseActor, ZDObject):
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
        return (
            f"<ZDActor({self.name}{self.inherit and 'extends ' + self.inherit or ''}"
            f"{self.replace and ('replaces ' + self.replace or '') or ''}"
            f"{self.doomednum and '#' + str(self.doomednum) or ''})>"
        )

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
                    action=f"{_user_var_setters[var['type']]}"
                    f"({stringify(var['name'])}, {vlit})"
                )
            ]

        if vtype == "arr":
            return [
                ZDState(
                    action=f"{_user_array_setters[var['type']]}"
                    f"({stringify(var['name'])}, {i}, {v})"
                )
                for i, v in enumerate(vlit)
            ]

        raise ValueError(f"Unknown user var type: {vtype}")

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
        text = TextNode()

        for prop in sorted(self.properties, key=lambda prop: prop.name):
            text.add_line(decorate(prop))

        text.add_line("")

        for user_var in self.uservars:
            array_suffix = f"[{user_var['size']}]" if user_var.get("size", 0) else ""
            text.add_line(f"var {user_var['type']} {user_var['name']}{array_suffix};")

        for flag in self.flags:
            text.add_line(f"+{flag}")

        for antiflag in self.antiflags:
            text.add_line(f"-{antiflag}")

        for verbatim in self.raw:
            text.add_line(verbatim)

        if len(text) == 1 and text[0].strip() == "":
            return "    "

        return text

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
        text = TextNode()

        for func in self.funcs:
            text.add_line(decorate(func[1]))

        for label in self.labels:
            if label.name.upper() == "SPAWN":
                label = self.transform_spawn(label)

            text.add_line(decorate(label))

        return text

    def header(self) -> str:
        """Returns the header of the class.

        The header is the portion that comes right after the classname in
        DECCORATE. It contains informatino such as inheritancce, replacement,
        and the editor number (DoomEdNum).
        """
        text = self.name

        if self.inherit:
            text += f" : {self.inherit}"
        if self.replace:
            text += f" replaces {self.replace}"
        if self.num:
            text += f" {str(self.num)}"

        return text

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
