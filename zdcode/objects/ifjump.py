"""The ZDCode ifjump statement."""
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateContainer
from ..types.basic import ZDStateObject
from ..util import TextNode
from .actor import ZDActor
from .state import zerotic


class ZDIfJumpStatement(ZDStateContainer):
    """A ZDCode ifjump statement.

    Allows the use of any DECORATE jump action (e.g. A_JumpIfTargetCloser)
    as a ZDCode block.
    """

    def __init__(
        self,
        actor: "ZDActor",
        condition_gen: Callable[[int], str],
        states: Iterable[ZDStateObject] | None = (),
    ):
        self._actor: ZDActor = actor
        self.true_condition: Callable[[int], str] = condition_gen
        self.states: list[ZDStateObject] = list(states or [])
        self.else_block: list[ZDStateObject] | None = None

    def spawn_safe(self):
        return False

    def clone(self) -> Self:
        res = ZDIfJumpStatement(
            self._actor, self.true_condition, (s.clone() for s in self.states)
        )
        res.set_else(self.else_block.clone())

        return res

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        yield self.states

        if self.else_block:
            yield from self.else_block.state_containers()

    def set_else(self, else_block: Iterable[ZDStateObject] | None):
        self.else_block = else_block

    @classmethod
    def generate(cls, actor: "ZDActor", states: Iterable[ZDStateObject] | None = ()):
        def _decorator(condition_gen):
            return cls(actor, condition_gen, states)

        return _decorator

    def num_block_states(self) -> int:
        """The number of states in this block,
        not counting the else block if applicable."""
        return sum(x.num_states() for x in self.states)

    def num_else_states(self) -> int:
        """The number of states in the else block if applicable, or 0 otherwise."""
        return self.else_block and self.else_block.num_states() or 0

    def num_states(self) -> int:
        if self.else_block:
            return self.num_block_states() + self.num_else_states() + 3

        else:
            return self.num_block_states() + 3

    def to_decorate(self) -> TextNode:
        num_st_bl = self.num_block_states()

        if self.else_block:
            num_st_el = self.num_else_states()

            return TextNode(
                [
                    f"{zerotic} {self.true_condition(num_st_el + 2)}",
                    self.else_block.to_decorate(),
                    f"{zerotic} A_Jump(256, {num_st_bl + 1})\n",
                    TextNode([x.to_decorate() for x in self.states]),
                    zerotic,
                ]
            )

        else:
            return TextNode(
                [
                    f"{zerotic} {self.true_condition(2)}",
                    f"{zerotic} A_Jump(256, {num_st_bl + 1})\n",
                    TextNode([x.to_decorate() for x in self.states]),
                    zerotic,
                ]
            )
