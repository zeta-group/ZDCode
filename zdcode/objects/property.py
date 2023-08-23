from ..types import *
from ..util import TextNode


class ZDProperty(ZDObject):
    """A propety of a DECORATE class."""

    def __init__(self, actor, name, value):
        self.actor = actor
        self.name = name.strip()
        self.value = value

        self.actor.properties.append(self)

    def to_decorate(self):
        return TextNode(["{} {}".format(self.name, self.value)])
