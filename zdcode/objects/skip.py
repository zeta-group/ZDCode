from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateObject
from .state import zerotic

if TYPE_CHECKING:
    from ..compiler.compiler import ZDCode


class ZDSkip:
    def __init__(self, code: "ZDCode", skip_context, curr_ind):
        self.code = code
        self.context = skip_context
        self.ind = curr_ind

    def clone(self) -> Self:
        raise NotImplementedError(
            "State group skipping (e.g. return in macros) could not be cloned. Injected macros cannot be cloned - please don't inject them until all else is resolved!"
        )

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        return
        yield

    def spawn_safe(self):
        return False

    def to_decorate(self):
        return f"{zerotic} A_Jump(256, {self.context.remote_num_states() - self.ind})"

    def num_states(self):
        return 1
