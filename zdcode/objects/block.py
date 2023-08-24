"""The ZDCode state container."""
from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateContainer
from ..types.basic import ZDStateObject
from ..util import TextNode
from .actor import ZDActor


class ZDBlock(ZDStateContainer):
    """A block of [ZDStateObject], used as a container."""

    def __init__(self, actor: "ZDActor", states: Iterable[ZDStateObject] | None = None):
        self._actor = actor
        self.states: list[ZDStateObject] = states or []

    def spawn_safe(self) -> bool:
        return self.states[0].spawn_safe()

    def clone(self) -> Self:
        return ZDBlock(self._actor, (s.clone() for s in self.states))

    def num_states(self) -> int:
        return sum(x.num_states() for x in self.states)

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        yield self.states

    def to_decorate(self) -> TextNode:
        return TextNode(x.to_decorate() for x in self.states)
