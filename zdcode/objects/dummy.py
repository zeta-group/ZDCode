"""Dummy objects, for internal use only."""
from ..compiler.context import ZDCodeParseContext
from ..types.basic import ZDObject
from ..types.basic import ZDStateObject
from ..util import TextNode
from .actor import ZDBaseActor


class ZDDummyActor(ZDBaseActor, ZDObject):
    """A dummy actor.

    Used in internal logic only - cannot be compiled to DECORATE."""

    def __init__(self, code, context=None, _id=None):
        if context:
            self.context = context.derive()

        else:
            self.context = ZDCodeParseContext()

        ZDBaseActor.__init__(self, code, "__dummy__", None, None, None, _id)

    def get_context(self) -> ZDCodeParseContext:
        return self.context

    def to_decorate(self) -> TextNode:
        raise NotImplementedError


class ZDDummyLabel(ZDObject):
    """A dummy label.

    Used for internal logic only. Cannot be compiled to DECORATE."""

    def __init__(self, actor, states=None):
        if not states:
            states = []

        self.name = None
        self.states: list[ZDStateObject] = states
        self._actor = actor

    def __repr__(self):
        return "[dummy state]"

    def label_name(self) -> str:
        """Returns the name of this label."""
        raise NotImplementedError

    def to_decorate(self) -> TextNode:
        raise NotImplementedError

    def get_context(self) -> None:
        """Returns the context of this label.

        Since this is a dummy label. returns simply None."""
        return None

    def add_state(self, state: ZDStateObject) -> None:
        """Adds a state to this label."""
        self.states.append(state)
