"""The ZDCode label object."""
from ..types.basic import ZDStateObject
from ..util import TextNode


class ZDLabel(ZDStateObject):
    """A label.

    Holds a sequence of states and other DECORATE logic which can be jumped to from any
    other state, and sometimes by internal ZDoom engine logic.
    """

    def __init__(self, _actor, name, states=None, auto_append=True):
        if not states:
            states = []

        self.name = name.strip()
        self.states: list[ZDStateObject] = states
        self._actor = _actor

        if auto_append:
            self._actor.labels.append(self)

    def spawn_safe(self) -> bool:
        return self.states[0].spawn_safe()

    def __repr__(self):
        return f"{type(self).__name__}({self.name} of {repr(self._actor.name)})"

    def label_name(self) -> str:
        """Returns the name of the label."""
        return self.name

    def add_state(self, state) -> None:
        """Adds a state to this label."""
        self.states.append(state)

    def to_decorate(self) -> TextNode:
        if self.name.startswith("F_"):
            self.name = "_" + self.name

        text = TextNode()
        text.add_line(f"{self.name}:")

        for state in self.states:
            text.add_line(state.to_decorate())

        return text
