"""The ZDCode internal inventory object."""
from ..compiler.compiler import ZDCode
from ..types.basic import ZDObject
from ..util import TextNode


class ZDInventory(ZDObject):
    """An inventory class used internally by ZDCode.

    This is used in old-style functions to pass parameters and to identify return paths.
    """

    def __init__(self, code: "ZDCode", name):
        self.name = name.strip()
        self.code = code

        code.inventories.append(self)

    def to_decorate(self) -> TextNode:
        return TextNode([f"Actor {self.name} : Inventory {{Inventory.MaxAmount 1}}"])
