from typing import Generator
from typing import Iterable
from typing import Self

from ..types.basic import ZDStateObject
from ..util import TextNode


class ZDState(ZDStateObject):
    """A regular DECORATE state."""

    def __init__(
        self, sprite='"####"', frame='"#"', duration=0, keywords=None, action=None
    ):
        if sprite == "####":
            sprite = '"####"'

        if frame == "#":
            frame = '"#"'

        if not keywords:
            keywords = []

        self.sprite = sprite
        self.frame = frame
        self.keywords = keywords or []
        self.action = action
        self.duration = duration

    def spawn_safe(self):
        return self.sprite != '"####"' and self.frame != '"#"'

    @classmethod
    def zerotic(cls, keywords=None, action=None):
        """Constructs and returns a ''zero tic' state."""
        return cls(keywords=keywords, action=action)

    @classmethod
    def tnt1(cls, duration=0, keywords=None, action=None):
        """Constructs and returns a TNT1 (invisible) state."""
        return cls("TNT1", "A", duration=duration, keywords=keywords, action=action)

    def clone(self) -> Self:
        """Duplicates this ZDState."""
        return ZDState(
            self.sprite, self.frame, self.duration, list(self.keywords), self.action
        )

    def state_containers(self) -> Generator[Iterable[ZDStateObject], None, None]:
        return
        yield

    def num_states(self) -> int:
        return 1

    def to_decorate(self) -> TextNode:
        if self.keywords:
            keywords = [" "] + self.keywords

        else:
            keywords = []

        action = ""
        if self.action:
            action = " " + str(self.action)

        return TextNode(
            [
                "{} {} {}{}{}".format(
                    self.sprite.upper(),
                    self.frame.upper(),
                    str(self.duration),
                    " ".join(keywords),
                    action,
                )
            ]
        )

    def __str__(self):
        return str(self.to_decorate())

    def __repr__(self):
        return "<ZDState({} {} {}{}{})>".format(
            self.sprite,
            self.frame,
            self.duration,
            "+" if self.keywords else "",
            " ..." if self.action else "",
        )


zerotic = ZDState.zerotic()
zerotic = ZDState.zerotic()
