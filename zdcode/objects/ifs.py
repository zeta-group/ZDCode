from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateContainer
from ..types.basic import ZDStateObject
from ..util import TextNode
from .actor import ZDActor
from .state import zerotic


class ZDIfStatement(ZDStateContainer):
    """A ZDCode if block.

    Internally uses A_JumpIf."""

    def __init__(
        self,
        actor: "ZDActor",
        condition: str | None,
        states: Iterable[ZDStateObject] | None = (),
    ):
        self._actor = actor
        self.true_condition = condition
        self.states: list[ZDStateObject] = list(states or [])
        self.else_block = None

    def spawn_safe(self):
        return False

    def clone(self) -> Self:
        res = ZDIfStatement(
            self._actor, self.true_condition, (s.clone() for s in self.states)
        )
        res.set_else(self.else_block.clone())

        return res

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        yield self.states

        if self.else_block:
            yield from self.else_block.state_containers()

    def set_else(self, else_block: ZDStateObject):
        """Set a state object or container to act as an 'else' block."""
        self.else_block = else_block

    def num_block_states(self):
        """Number of states in the if block (not counting the else block)."""
        return sum(x.num_states() for x in self.states)

    def num_else_states(self):
        """Number of states in the else block only."""
        return self.else_block.num_states()

    def num_states(self):
        """Total number of states.

        Includes the else block if applicable."""
        if self.else_block:
            return self.num_block_states() + self.num_else_states() + 3

        else:
            return self.num_block_states() + 2

    def to_decorate(self) -> TextNode:
        num_st_bl = self.num_block_states()

        if self.else_block:
            num_st_el = self.num_else_states()

            return TextNode(
                [
                    f"{zerotic} A_JumpIf({self.true_condition}, {num_st_el + 2})",
                    self.else_block.to_decorate(),
                    f"{zerotic} A_Jump(256, {num_st_bl + 1})",
                    TextNode([x.to_decorate() for x in self.states]),
                    zerotic,
                ]
            )

        else:
            return TextNode(
                [
                    f"{zerotic} A_JumpIf(!({self.true_condition}), {num_st_bl + 1})\n",
                    TextNode([x.to_decorate() for x in self.states]),
                    zerotic,
                ]
            )
