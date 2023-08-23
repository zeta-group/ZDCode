__VERSION__ = "2.13.3"

import collections
import functools
import hashlib
import itertools
import queue
import random
import string
import warnings
from typing import Callable, Generator, Iterable, Literal, Protocol, Self

from .compiler import *
from .types import *
from .util import *

_user_var_setters = {
    "int": "A_SetUserVar",
    "float": "A_SetUserVarFloat",
}

_user_array_setters = {
    "int": "A_SetUserArray",
    "float": "A_SetUserArrayFloat",
}
