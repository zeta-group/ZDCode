from ..types import *


class ZDSometimes(ZDStateContainer):
    """A ZDCode sometimes statement."""

    def __init__(
        self,
        actor: "ZDActor",
        chance: float,
        states: Iterable[ZDStateObject] | None = None,
    ):
        self._actor = actor
        self.chance = chance
        self.states: list[ZDStateObject] = list(states or [])

    def clone(self) -> Self:
        return ZDSometimes(self._actor, self.chance, (s.clone() for s in self.states))

    def num_states(self) -> int:
        return sum(x.num_states() for x in self.states) + 2

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        yield self.states

    def spawn_safe(self) -> bool:
        return False

    def to_decorate(self) -> TextNode:
        num_st = sum(x.num_states() for x in self.states)

        res = TextNode()
        res.add_line(f"{zerotic} A_Jump(256-(256*({self.chance})/100), {num_st + 1})")

        for x in self.states:
            res.add_line(x.to_decorate())

        res.add_line(str(zerotic))

        return res
