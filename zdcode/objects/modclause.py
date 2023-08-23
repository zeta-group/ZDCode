from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..compiler.compiler import ZDCode
    from ..compiler.context import ZDCodeParseContext


class ZDModClause:
    """A clause for a ZDCode state modifier."""

    def __init__(self, code: "ZDCode", ctx: "ZDCodeParseContext", selector, effects):
        self.code = code
        self.context = ctx
        self.selector = selector
        self.effects = effects

    def apply(self, ctx: "ZDCodeParseContext", target_states):
        clause_ctx = self.context.derive("mod clause")
        clause_ctx.update(ctx)

        res = []

        for s in target_states:
            if self.selector(self.code, clause_ctx, s):
                alist = [s]

                for effect in self.effects:
                    nlist = []

                    for a in alist:
                        list_part = list(effect(self.code, clause_ctx, a))
                        nlist.extend(list_part)

                    alist = nlist

                res.extend(alist)

            else:
                for container in s.state_containers():
                    self.apply(ctx, container)

                res.append(s)

        target_states.clear()
        target_states.extend(res)
