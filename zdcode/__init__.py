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
