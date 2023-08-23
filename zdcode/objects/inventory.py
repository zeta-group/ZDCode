from ..types import *


class ZDInventory(object):
    def __init__(self, code: "ZDCode", name):
        self.name = name.strip()
        self.code = code

        code.inventories.append(self)

    def to_decorate(self):
        return TextNode(
            ["Actor {} : Inventory {{Inventory.MaxAmount 1}}".format(self.name)]
        )
