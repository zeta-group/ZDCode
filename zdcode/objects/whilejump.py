"""The ZDCode whilejump statement."""
from typing import TYPE_CHECKING
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateObject
from ..util import TextNode
from ..util import stringify
from .actor import ZDActor
from .state import zerotic
from .whiles import num_whiles


class ZDWhileJumpStatement(object):
    """The ZDCode whilejump statement.

    Allows any conditional jump state action (such as A_JumpIfTargetCloser) to be used
    to run a segment of states until said condition is reached."""

    def __init__(
        self, actor: "ZDActor", condition_gen: Callable[[int], str], states=()
    ):
        self._actor = actor
        self.true_condition = condition_gen
        self.states: list[ZDStateObject] = list(states)
        self.else_block = None

        global num_whiles

        self._while_id = num_whiles
        num_whiles += 1

        self._loop_id = "_loop_while_" + str(self._while_id)

    def clone(self) -> Self:
        res = ZDWhileJumpStatement(
            self._actor, self.true_condition, (s.clone() for s in self.states)
        )
        res.set_else(self.else_block.clone())

        return res

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        yield self.states

        if self.else_block:
            yield from self.else_block.state_containers()

    def set_else(self, else_block):
        self.else_block = else_block

    @classmethod
    def generate(cls, actor, states=()):
        def _decorator(condition_gen):
            return cls(actor, condition_gen, states)

        return _decorator

    def num_block_states(self):
        return sum(x.num_states() for x in self.states)

    def num_else_states(self):
        return self.else_block.num_states()

    def num_states(self):
        if self.else_block:
            return self.num_block_states() + self.num_else_states() + 4

        else:
            return self.num_block_states() + 4

    def spawn_safe(self):
        return False

    def to_decorate(self):
        num_st_bl = self.num_block_states()

        if self.else_block:
            num_st_el = self.num_else_states()

            return TextNode(
                [
                    f"{zerotic} {self.true_condition(num_st_el + 2)}",
                    self.else_block.to_decorate(),
                    f"{zerotic} A_Jump(256, {num_st_bl + 2})",
                    f"{self._loop_id}:",
                    TextNode([x.to_decorate() for x in self.states]),
                    f"{zerotic} {self.true_condition(stringify(self._loop_id))}",
                    zerotic,
                ]
            )

        else:
            return TextNode(
                [
                    f"{zerotic} {self.true_condition(2)}",
                    f"{zerotic} A_Jump(256, {num_st_bl + 2})",
                    f"{self._loop_id}:",
                    TextNode([x.to_decorate() for x in self.states]),
                    f"{zerotic} {self.true_condition(stringify(self._loop_id))}",
                    zerotic,
                ]
            )
