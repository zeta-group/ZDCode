from ..compiler.compiler import ZDCode
from ..types.basic import ZDObject
from ..util import TextNode


class ZDInventory(ZDObject):
    def __init__(self, code: "ZDCode", name):
        self.name = name.strip()
        self.code = code

        code.inventories.append(self)

    def to_decorate(self) -> TextNode:
        return TextNode(
            ["Actor {} : Inventory {{Inventory.MaxAmount 1}}".format(self.name)]
        )
