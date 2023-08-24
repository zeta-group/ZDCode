"""The clause for ZDCode state modifiers."""
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
        """Apply this modifier clause to a set of states."""
        clause_ctx = self.context.derive("mod clause")
        clause_ctx.update(ctx)

        res = []

        for state in target_states:
            if self.selector(self.code, clause_ctx, state):
                processing_states = [state]

                for effect in self.effects:
                    new_processing_states = []

                    for proc_state in processing_states:
                        new_states = list(effect(self.code, clause_ctx, proc_state))
                        new_processing_states.extend(new_states)

                    processing_states = new_processing_states

                res.extend(processing_states)

            else:
                for container in state.state_containers():
                    self.apply(ctx, container)

                res.append(state)

        target_states.clear()
        target_states.extend(res)
