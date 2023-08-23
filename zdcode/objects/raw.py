from ..types import *


class ZDRawDecorate(ZDStateObject):
    def __init__(self, raw: str, num_states: int = 0):
        self.raw = raw
        self.num_states = num_states

    def spawn_safe(self) -> bool:
        return False

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        return
        yield

    def num_states(self) -> int:
        return self.num_states

    def to_decorate(self) -> TextNode:
        return TextNode([self.raw], 0)
