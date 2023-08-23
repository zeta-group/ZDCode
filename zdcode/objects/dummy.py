from ..types import *


class ZDDummyActor(ZDObject):
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
        raise NotImplementedError

    def to_decorate(self) -> TextNode:
        raise NotImplementedError

    def get_context(self) -> None:
        return None

    def add_state(self, state: ZDStateObject) -> None:
        self.states.append(state)
