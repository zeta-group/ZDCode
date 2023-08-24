"""The ZDCode verbatim text object. For internal use only."""
from typing import Generator
from typing import Iterable

from ..types.basic import ZDStateObject
from ..util import TextNode


class ZDRawDecorate(ZDStateObject):
    """Verbatim text, to be pasted directly. Internal use only."""

    def __init__(self, raw: str, num_states: int = 0):
        self.raw = raw
        self._num_states = num_states

    def spawn_safe(self) -> bool:
        return False

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        return
        yield

    def num_states(self) -> int:
        return self._num_states

    def to_decorate(self) -> TextNode:
        return TextNode([self.raw], 0)
