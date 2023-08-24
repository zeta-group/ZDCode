"""ZDCode is a language which compilers to DECORATE.

DECORATE is a legacy scripting language used by the ZDoom family of source ports. While
modern source ports support ZScript, a more advanced scripting language which is much
more powerful and superior to both DECORATE and ZDCode, using DECORATE allows other
source ports to be supported by a mod as well. ZDCode makes the process of writing
DECORATE code less tedious,

This project is available in the MIT License. For more info, see the LICENSE.md file.

(c)2023 Gustavo Ramos Rehermann and contributors."""

__VERSION__ = "2.13.3"

import collections
import functools
import hashlib
import itertools
import queue
import random
import string
import warnings
from typing import Callable
from typing import Generator
from typing import Iterable
from typing import Literal
from typing import Protocol
from typing import Self

_user_var_setters = {
    "int": "A_SetUserVar",
    "float": "A_SetUserVarFloat",
}

_user_array_setters = {
    "int": "A_SetUserArray",
    "float": "A_SetUserArrayFloat",
}
