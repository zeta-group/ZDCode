from ..types import *
from .whiles import num_whiles


class ZDWhileJumpStatement(object):
    def __init__(self, actor, condition_gen, states=()):
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

    def state_containers(self):
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
                    "{}:".format(self._loop_id),
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
                    "{}:".format(self._loop_id),
                    TextNode([x.to_decorate() for x in self.states]),
                    f"{zerotic} {self.true_condition(stringify(self._loop_id))}",
                    zerotic,
                ]
            )
