import collections
import itertools
from typing import TYPE_CHECKING
from typing import Literal

from ..types.basic import ZDStateObject
from .error import CompilerError

if TYPE_CHECKING:
    from ..objects.actor import ZDActor


class ZDCtxDescBlock:
    def __init__(self, ctx: "ZDCodeParseContext", desc: str):
        self.ctx = ctx
        self.desc = desc

    def __enter__(self):
        self.ctx.desc_stack.append(self.desc)

    def __exit__(self, _1, _2, _3):
        assert self.ctx.desc_stack.pop() == self.desc


class ZDCodeParseContext(object):
    def __init__(
        self,
        replacements=None,
        macros=None,
        templates=None,
        actors=None,
        mods=None,
        applied_mods=None,
        remote_offset=0,
        description=None,
        break_ctx=None,
        loop_ctx=None,
    ):
        self.replacements = (
            replacements.new_child()
            if replacements is not None
            else collections.ChainMap({})
        )
        self.macros = (
            macros.new_child() if macros is not None else collections.ChainMap({})
        )
        self.templates = (
            templates.new_child() if templates is not None else collections.ChainMap({})
        )
        self.mods = mods.new_child() if mods is not None else collections.ChainMap({})

        self.always_applied_mods = applied_mods
        self.applied_mods = []

        self.actor_lists = list(actors) if actors else []
        self.desc_stack = []
        self.states: list[ZDStateObject | ZDCodeParseContext] = []
        self.remote_children = []
        self.remote_offset = remote_offset

        self.break_ctx = self if break_ctx == "self" else break_ctx or self
        self.loop_ctx = self if loop_ctx == "self" else loop_ctx or self

        if description:
            self.add_description(description)

    def add_description(self, desc):
        self.desc_stack.append(desc)

    def get_applied_mods(self):
        if self.always_applied_mods is None:
            return iter(self.applied_mods)

        else:
            return itertools.chain(self.always_applied_mods, self.applied_mods)

    def print_state_tree(self, _print_low=print, _print=print, prefix="+ "):
        ended = 0

        _print_low = _print_low or print

        def _print_top(name):
            _print_low(prefix + name)

        def _branch(line="", end=False):
            if end:
                _print("'---+ " + line)

            else:
                _print("+---+ " + line)

        def _print_next(line=""):
            if ended == 0:
                _print("|   " + line)

            elif ended == 1 and self.remote_children:
                _print(":   " + line)

            else:
                _print("    " + line)

        _print_top(
            "{} ({}/{})".format(
                self.desc_stack[-1], self.num_states(), self.remote_num_states()
            )
        )

        if self.states:
            _print("|")

            imax = len(self.states)

            for i, s in enumerate(self.states):
                ended = 1 if i >= imax - 1 else 0

                if isinstance(s, ZDCodeParseContext):
                    s.print_state_tree(
                        _print, _print_next, "'---+ " if ended > 0 else "+---+ "
                    )

                else:
                    _branch("{} ({})".format(type(s).__name__, s.num_states()), ended)

                if not ended:
                    _print("|")

        if self.remote_children:
            _print("&")
            _print(":")

            imax = len(self.remote_children)

            for i, ch in enumerate(self.remote_children):
                ended = 2 if i >= imax - 1 else 1

                ch.print_state_tree(
                    _print,
                    _print_next,
                    "^---* (remote) " if ended > 1 else "%---* (remote) ",
                )

                if not ended:
                    _print(":")

    def num_states(self):
        return sum(s.num_states() for s in self.states)

    def remote_num_states(self):
        return (
            self.remote_offset
            + sum(
                s.remote_num_states()
                if isinstance(s, ZDCodeParseContext)
                else s.num_states()
                for s in self.states
            )
            + sum(c.remote_num_states() for c in self.remote_children)
        )

    def remote_derive(
        self,
        desc: str | None = None,
        remote_offset: int = 0,
        break_ctx: "ZDCodeParseContext" | Literal["self"] | None = None,
        loop_ctx: "ZDCodeParseContext" | Literal["self"] | None = None,
    ) -> "ZDCodeParseContext":
        # derives without adding to states
        res = ZDCodeParseContext(
            self.replacements,
            self.macros,
            self.templates,
            self.actor_lists,
            self.mods,
            self.applied_mods,
            remote_offset,
            break_ctx=break_ctx or self.break_ctx,
            loop_ctx=loop_ctx or self.loop_ctx,
        )
        res.desc_stack = list(self.desc_stack)

        if desc:
            res.desc_stack.append(desc)

        self.remote_children.append(res)

        return res

    def derive(
        self,
        desc: str | None = None,
        break_ctx: "ZDCodeParseContext" | Literal["self"] | None = None,
        loop_ctx: "ZDCodeParseContext" | Literal["self"] | None = None,
    ) -> "ZDCodeParseContext":
        res = ZDCodeParseContext(
            self.replacements,
            self.macros,
            self.templates,
            self.actor_lists,
            self.mods,
            self.applied_mods,
            break_ctx=break_ctx or self.break_ctx,
            loop_ctx=loop_ctx or self.loop_ctx,
        )
        res.desc_stack = list(self.desc_stack)

        if desc:
            res.desc_stack.append(desc)

        self.states.append(res)

        return res

    def __repr__(self):
        return "ZDCodeParseContext({})".format(self.repr_describe())

    def desc_block(self, desc: str):
        return ZDCtxDescBlock(self, desc)

    def update(self, other_ctx: "ZDCodeParseContext"):
        self.macros.maps.insert(-1, other_ctx.macros)
        self.replacements.maps.insert(-1, other_ctx.replacements)
        self.templates.maps.insert(-1, other_ctx.templates)
        self.mods.maps.insert(-1, other_ctx.mods)

    def add_actor(self, ac: "ZDActor"):
        for al in self.actor_lists:
            al.append(ac)

    def describe(self):
        return " at ".join(self.desc_stack[::-1])

    def repr_describe(self):
        return ", ".join(self.desc_stack[::-1])

    def resolve(self, name, desc="a parametrizable name"):
        while name[0] == "@":
            resolves = len(name) - len(name.lstrip("@"))
            casename = name[resolves:]
            name = name[resolves:].upper()

            if name in self.replacements:
                if resolves > 1:
                    name = "@" * (resolves - 1) + self.replacements[name]

                else:
                    name = self.replacements[name]

            else:
                raise CompilerError(
                    "No such replacement {} while trying to resolve {} in {}!".format(
                        repr(name), repr(casename), self.describe()
                    )
                )

        return name
