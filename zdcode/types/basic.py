from typing import TYPE_CHECKING
from typing import Generator
from typing import Iterable
from typing import Protocol
from typing import Self
from typing import Union

if TYPE_CHECKING:
    from ..compiler.context import ZDCodeParseContext


# ZDCode Classes
class ZDObject(Protocol):
    """Denotes a ZDCode object which can be converted to DECORATE."""

    def to_decorate(self) -> str:
        """Cconverts this ZDCode object to DECORATE."""
        ...

    def get_context(self) -> Union["ZDCodeParseContext", None]:
        """Returns the context of this ZDObject.

        If not applicable, returns None."""
        ...


class ZDStateObject(ZDObject, Protocol):
    """Denotes a ZDCode object which is or may ccontain DECORATE states."""

    def clone(self) -> Self:
        """Clone this state object."""
        ...

    def spawn_safe(self) -> bool:
        """Whether this collection is 'spawn safe'.

        Spawn safety denotes a state which can be used at the start of a Spawn label without causing issues. Non-spawn-safe Spawn labels will be automatically padded with TNT1 A 0 to prevent issues.
        """
        ...

    def num_states(self) -> int:
        """The number of states in this state object."""
        ...

    def state_containers(self) -> Generator[Iterable["ZDStateObject"], None, None]:
        """A list of mutable state containers with [ZDStateObject]s.

        Some of these are references to this data structure or children thereof. Others are constructed on the fly for the sake of interface compatibility.
        """
        ...


class ZDStateContainer(ZDStateObject, Protocol):
    """Denotes a ZDCode object which can hold multiple DECORATE states."""

    def add_state(self, state: ZDStateObject) -> None:
        """Adds a ZDCode state object to this container."""
        ...
