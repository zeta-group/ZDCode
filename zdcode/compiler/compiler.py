import queue

from .. import __VERSION__
from .. import parser as zdlexer
from ..objects.actor import ZDActor
from ..objects.block import ZDBlock
from ..objects.dummy import ZDDummyActor
from ..objects.dummy import ZDDummyLabel
from ..objects.ifjump import ZDIfJumpStatement
from ..objects.ifs import ZDIfStatement
from ..objects.label import ZDLabel
from ..objects.modclause import ZDModClause
from ..objects.property import ZDProperty
from ..objects.raw import ZDRawDecorate
from ..objects.skip import ZDSkip
from ..objects.sometimes import ZDSometimes
from ..objects.state import ZDState
from ..objects.template import ZDClassTemplate
from ..objects.whilejump import ZDWhileJumpStatement
from ..objects.whiles import ZDWhileStatement
from ..util import TextNode
from ..util import decorate
from ..util import make_id
from ..util import stringify
from ..util import unstringify
from .context import ZDCodeParseContext
from .error import CompilerError
from .task import pending_task


class ZDCode:
    class ZDCodeError(BaseException):
        pass

    @classmethod
    def parse(
        cls,
        code,
        fname=None,
        dirname=".",
        error_handler=None,
        preproc_defs=(),
        debug=False,
    ):
        res = cls()
        success = res.add(code, fname, dirname, error_handler, preproc_defs, debug)

        return res if success else None

    def add(
        self,
        code,
        fname=None,
        dirname=".",
        error_handler=None,
        preproc_defs=(),
        debug=False,
    ):
        data = zdlexer.parse_code(
            code.strip(" \t\n"),
            dirname=dirname,
            filename=fname,
            error_handler=error_handler,
            imports=self.includes,
            preproc_defs=preproc_defs,
        )

        if data:
            try:
                self._parse(data, debug=debug)

            except CompilerError as err:
                if error_handler:
                    error_handler(err)
                    return False

                else:
                    raise

        return bool(data)

    def _parse_operation(self, operation, context):
        ooper, oargs = operation

        oargs = (self._parse_evaluation(a, context) for a in oargs)

        return ooper(*oargs)

    def _parse_evaluation(self, evaluation, context):
        etype, econt = evaluation

        if etype == "literal":
            return self._parse_literal_numeric(econt, context)

        if etype == "operation":
            return self._parse_operation(econt, context)

        raise CompilerError(
            "Could not parse evaluation {} in {}".format(
                repr(evaluation), context.describe()
            )
        )

    def _parse_expression(self, expr, context):
        etype, exval = expr

        if etype == "expr":
            return " ".join(
                str(self._parse_expression(item, context)) for item in exval
            )

        if etype == "literal":
            return self._parse_literal(exval, context)

        if etype == "array index":
            return "[" + self._parse_expression(exval, context) + "]"

        if etype == "operator":
            return exval

        if etype == "paren expr":
            return "(" + self._parse_expression(exval, context) + ")"

        raise CompilerError(
            "Could not parse expression {} in {}".format(repr(expr), context.describe())
        )

    def _parse_argument(self, arg, context, name=None):
        atype, aval = arg

        if atype == "position arg":
            return self._parse_parameter(aval, context, name)

    def _parse_parameter(self, parm, context, name=None):
        ptype, pval = parm

        if ptype == "expression":
            return self._parse_expression(pval, context)

        if ptype == "template derivation":
            return self._parse_template_derivation(pval, context)

        if ptype == "anonymous class":
            return self._parse_anonym_class(pval, context)

        if ptype == "anonymous macro":
            return self._parse_anonym_macro(*pval, context, name)

    def _parse_anonym_macro(self, args, body, context, name=None):
        name = name or "ANONYMMACRO_{}_{}".format(
            self.id.upper(), self.num_anonym_macros
        )
        self.num_anonym_macros += 1

        context.macros[name.upper()] = (args, body)

        return stringify(name)

    def _parse_literal_numeric(self, literal, context):
        if literal[0] == "number":
            return literal[1]

        if literal[0] == "eval":
            return self._parse_evaluation(literal[1], context)

        if literal[0] == "format string":
            return float(self._parse_formatted_string(literal[1], context))

        if literal[0] == "actor variable":
            if literal[1].upper() in context.replacements:
                return float(context.replacements[literal[1].upper()])

            raise CompilerError(
                "Cannot get compile-time variable for evaluation, {}, in {}".format(
                    repr(literal[1]), context.describe()
                )
            )

        raise CompilerError(
            "Could not parse numeric expression {} at {}".format(
                repr(literal), context.describe()
            )
        )

    def _parse_literal(self, literal, context):
        if isinstance(literal, str):
            return literal

        if literal[0] == "number":
            return str(literal[1])

        if literal[0] == "string":
            return stringify(literal[1])

        if literal[0] == "eval":
            return self._parse_evaluation(literal[1], context)

        if literal[0] == "format string":
            return stringify(self._parse_formatted_string(literal[1], context))

        if literal[0] == "actor variable":
            if literal[1].upper() in context.replacements:
                return context.replacements[literal[1].upper()]

            else:
                return literal[1]

        if literal[0] == "call expr":
            return self._parse_action(literal[1], context)

        if literal[0] == "anonymous class":
            return self._parse_anonym_class(literal[1], context)

        if literal[0] == "template derivation":
            return self._parse_template_derivation(literal[1], context)

        raise CompilerError(
            "Could not parse literal {} in {}".format(repr(literal), context.describe())
        )

    def _parse_array(self, arr, context):
        arr = dict(arr)
        arr["value"] = (
            "array",
            [self._parse_expression(e, context) for e in arr["value"][1]],
        )

        return arr

    def _parse_template_derivation(
        self, deriv, context, pending=None, name=None, do_stringify=True
    ):
        template_name, template_parms, inherits, group, deriv_body = deriv

        inheritance = inherits[1] and self._parse_inherit(inherits[1], context)
        group = group[1] and context.resolve(
            group[1], "a parametrized group name in a template derivation"
        )

        try:
            template = context.templates[template_name]

        except KeyError:
            raise CompilerError(
                "Unknown template '{}' to derive in {}".format(
                    template_name, context.describe()
                )
            )

        if len(template_parms) != len(template.template_parameters):
            raise CompilerError(
                "Bad number of template parameters for '{}' in {}: expected {}, got {}".format(
                    template_name,
                    context.describe(),
                    len(template.template_parameters),
                    len(template_parms),
                )
            )

        template_parms = [
            self._parse_parameter(a, context, template.template_parameters[i])
            for i, a in enumerate(template_parms)
        ]
        template_labels = {}
        template_body = []
        template_macros = {}
        template_arrays = {}

        for btype, bdata in deriv_body:
            if btype == "array":
                bdata = self._parse_array(bdata, context)
                template_arrays[bdata["name"]] = bdata

            elif btype == "label":
                template_labels[bdata["name"]] = bdata

            elif btype == "macro":
                template_macros[bdata["name"]] = bdata

            template_body.append((btype, bdata))

        new_class = self._derive_class_from_template(
            template,
            template_parms,
            context,
            template_labels,
            template_macros,
            template_arrays,
            template_body,
            pending=pending,
            name=name,
            inherits=inheritance,
            group=group,
        )

        if do_stringify:
            return stringify(new_class.name)

        else:
            return new_class

    def _parse_action(self, a, context):
        aname = a[0]
        aname = context.replacements.get(aname.upper(), aname)

        args = list(a[1]) if a[1] else []
        args = [
            (context.replacements.get(x.upper(), x) if isinstance(x, str) else x)
            for x in args
        ]
        args = [self._parse_argument(x, context) for x in args]
        args = ", ".join(a for a in args if a)

        return "{}({})".format(aname, args)

    def _parse_state_action_or_body(self, a, context):
        if a[0] == "action":
            return [self._parse_state_action(a[1], context)]

        elif a[0] == "inline body":
            res = []

            for x in a[1]:
                res.extend(self._parse_state_action_or_body(x, context))

            return res

        elif a[0] == "repeated inline body":
            res = []

            cval, xidx, body = a[1]
            count = self._parse_replaceable_number(cval, context)

            if count >= 1:
                for idx in range(count):
                    ctx = context.derive()

                    if xidx:
                        ctx.replacements[xidx] = str(idx)

                    res.extend(self._parse_state_action_or_body(body, ctx))

            return res

    def _parse_state_action(self, a, context):
        args = list(a[1]) if a[1] else []
        args = [self._parse_argument(x, context) for x in args]
        args = [
            (context.replacements.get(x.upper(), x) if isinstance(x, str) else x)
            for x in args
        ]
        args = ", ".join(a for a in args if a)

        if len(args) > 0:
            return "{}({})".format(a[0], args)

        else:
            return a[0]

    def _parse_formatted_string(self, cval, context: ZDCodeParseContext):
        res = []

        for part in cval:
            ptype, pval = part

            if ptype == "str":
                res.append(pval)

            if ptype == "eval":
                res.append(str(self._parse_evaluation(pval, context=context)))

            if ptype == "fmt":
                if pval.upper() in context.replacements:
                    res.append(str(context.replacements[pval.upper()]))

                else:
                    raise CompilerError(
                        "Replacement {} not found while formatting string in {}".format(
                            pval, context.describe()
                        )
                    )

        return "".join(unstringify(x) for x in res)

    def _parse_formattable_string(self, cval, context: ZDCodeParseContext):
        if cval[0] == "string":
            return cval[1]

        elif cval[0] == "format":
            return self._parse_formatted_string(cval[1], context)

        raise CompilerError(
            "Could not parse formattable string {} in {}".format(
                repr(cval), context.describe()
            )
        )

    def _parse_replaceable_number(self, cval, context: ZDCodeParseContext):
        if isinstance(cval, str):
            cval = context.replacements.get(cval.upper(), cval)

        try:
            count = int(cval)

        except ValueError:
            raise CompilerError(
                "Invalid repeat count in {}: expected valid integer, got {}".format(
                    context.describe(), repr(cval)
                )
            )

        else:
            return count

    def _mutate_block(self, mut_func, block, *args):
        return [mut_func(s, *args) for s in block]

    def _maybe_mutate_block(self, mut_func, state, *args):
        state = list(state)

        if state[0] == "ifjump":
            jump, s_yes, s_no = state[1]
            state[1] = (
                jump,
                self._mutate_block(mut_func, s_yes, *args),
                s_no and self._mutate_block(mut_func, s_no, *args),
            )

        elif state[0] == "if":
            cond, s_yes, s_no = state[1]
            state[1] = (
                cond,
                self._mutate_block(mut_func, s_yes, *args),
                s_no and self._mutate_block(mut_func, s_no, *args),
            )

        elif state[0] == "sometimes":
            state[1] = dict(state[1])
            state[1]["body"] = self._mutate_block(mut_func, state[1]["body"], *args)

        elif state[0] == "repeat":
            cval, xidx, body = state[1]
            state[1] = (cval, xidx, self._mutate_block(mut_func, body, *args))

        return state

    def _maybe_mutate_block_or_loop(self, mut_func, state, *args):
        state = list(state)

        if state[0] in ("while", "whilejump"):
            cond, f_body, f_else = state[1]

            f_body = self._mutate_block(mut_func, f_body, *args)
            f_else = f_else and self._mutate_block(mut_func, f_else, *args)

            state[1] = (cond, f_body, f_else)

        elif state[0] == "for":
            itername, iteridx, itermode, f_body, f_else = state[1]

            f_body = self._mutate_block(mut_func, f_body, *args)
            f_else = f_else and self._mutate_block(mut_func, f_else, *args)

            state[1] = (itername, iteridx, itermode, f_body, f_else)

        return self._maybe_mutate_block(mut_func, state, *args)

    def _mutate_macro_state(self, state, inj_context):
        # Mutates each state in an injected macro, making things
        # like macro-scope return statements possible.

        if hasattr(state, "to_decorate"):
            return state.clone()

        if state[0] == "return":
            return ("skip", inj_context)

        return self._maybe_mutate_block_or_loop(
            self._mutate_macro_state, state, inj_context
        )

    def _mutate_iter_state(self, state, break_context, loop_context):
        # Mutates each state in a for loop, making things like
        # break and continue statements possible.

        if state[0] == "continue":
            return ("skip", loop_context.loop_ctx)

        if state[0] == "break":
            return ("skip", break_context.break_ctx)

        return self._maybe_mutate_block(
            self._mutate_iter_state, state, break_context, loop_context
        )

    def _parse_state_modifier(self, context: ZDCodeParseContext, modifier_chars):
        res = []

        def recurse(modifier_chars):
            for ctype, cval in modifier_chars:
                if ctype == "replace":
                    try:
                        res.append(context.replacements[cval.upper()])

                    except KeyError:
                        raise CompilerError(
                            "No parameter {} for replacement within modifier, in {}!".format(
                                cval, context.describe()
                            )
                        )

                elif ctype == "recurse":
                    recurse(cval)

                elif ctype == "part":
                    res.append(cval)

        recurse(modifier_chars)

        return "".join(res)

    def _parse_mod_clause(self, context: ZDCodeParseContext, selector, effects):
        return ZDModClause(self, context, selector, effects)

    def _parse_mod_block(self, context: ZDCodeParseContext, mod_block):
        mod_name, mod_body = mod_block
        new_clauses = []

        for selector, effects in mod_body:
            new_clauses.append(self._parse_mod_clause(context, selector, effects))

        context.mods[mod_name.upper()] = new_clauses

    def _parse_state_sprite(self, context: ZDCodeParseContext, sprite):
        sprite_type, sprite_name = sprite

        if sprite_type == "normal":
            name = sprite_name

        elif sprite_type == "parametrized":
            try:
                new_name = context.replacements[sprite_name.upper()]

                if new_name[0] == "'" and new_name[-1] == "'":
                    new_name = new_name[1:-1]

                elif new_name[0] == '"' and new_name[-1] == '"':
                    new_name = new_name[1:-1]

                else:
                    raise CompilerError(
                        "Parametrized sprite '{}' in {} needs to be passed a string; got {}".format(
                            sprite_name, context.describe(), repr(new_name)
                        )
                    )

                name = new_name

            except KeyError:
                raise CompilerError(
                    "No parameter {} for parametrized sprite name, in {}!".format(
                        repr(sprite_name), context.describe()
                    )
                )

        return name

    def _parse_state_expr(self, context: ZDCodeParseContext, s):
        label = ZDDummyLabel(self)
        actor = ZDDummyActor(self, context)

        for state in s:
            self._parse_state(actor, context, label, state)

        return label.states

    def _parse_state(self, actor, context: ZDCodeParseContext, label, s, func=None):
        def add_state(s, target=context):
            added = [s]

            for m in context.get_applied_mods():
                m.apply(context, added)

            target.states.extend(added)
            label.states.extend(added)

            return added

        if hasattr(s, "to_decorate"):
            add_state(s)
            return

        def pop_remote(target=context):
            assert target.remote_children
            target.remote_children.pop()

        def clear_remotes(target=context):
            target.remote_children.clear()

        if s[0] == "frames":
            sprite, frames, duration, modifiers, action = s[1]
            parsed_modifiers = []

            for modifier_chars in modifiers:
                parsed_modifiers.append(
                    self._parse_state_modifier(context, modifier_chars)
                )

            name = self._parse_state_sprite(context, sprite)

            if frames in ['"#"', "#"]:
                frames = ['"#"']

            for f in frames:
                if action is None:
                    add_state(ZDState(name, f, duration, parsed_modifiers))

                else:
                    body = self._parse_state_action_or_body(action, context)

                    for i, a in enumerate(body):
                        add_state(
                            ZDState(
                                name,
                                f,
                                (0 if i + 1 < len(body) else duration),
                                parsed_modifiers,
                                action=a,
                            )
                        )

        elif s[0] == "return":
            raise CompilerError(
                "Return statements are not valid in {}!".format(context.describe())
            )

        elif s[0] == "continue":
            raise CompilerError(
                "Continue statements are not valid in {}!".format(context.describe())
            )

        elif s[0] == "break":
            raise CompilerError(
                "Break statements are not valid in {}!".format(context.describe())
            )

        elif s[0] == "skip":
            # Skips to the end of this context, or the one supplied.
            if s[1]:
                # s[1] can only be an outer context, so don't bother checking
                add_state(ZDSkip(self, s[1], s[1].remote_num_states()))

            else:
                add_state(ZDSkip(self, context, context.remote_num_states()))

        elif s[0] == "call":
            raise CompilerError(
                "Functions and calls have been removed since ZDCode 2.11.0! ({})".format(
                    context.describe()
                )
            )

        elif s[0] == "flow":
            if s[1].upper().rstrip(";") == "LOOP":
                add_state(ZDRawDecorate("goto {}".format(label.name)))

            else:
                sf = s[1].rstrip(";").split(" ")
                sf[0] = sf[0].lower()

                add_state(ZDRawDecorate(" ".join(sf)))

        elif s[0] == "repeat":
            cval, xidx, body = s[1]

            break_ctx = context.derive("repeat", break_ctx="self")
            count = self._parse_replaceable_number(cval, context)

            if count >= 1:
                for idx in range(count):
                    loop_ctx = break_ctx.derive(
                        "body #{}".format(idx + 1), loop_ctx="self"
                    )

                    if xidx:
                        loop_ctx.replacements[xidx.upper()] = str(idx)

                    for a in body:
                        self._parse_state(
                            actor,
                            loop_ctx,
                            label,
                            self._mutate_iter_state(a, break_ctx, loop_ctx),
                            func,
                        )

        elif s[0] == "sometimes":
            s = dict(s[1])

            chance = self._parse_expression(s["chance"], context)
            sms = ZDSometimes(actor, chance, [])

            for a in s["body"]:
                self._parse_state(actor, context, sms, a, func)

            add_state(sms)

        elif s[0] == "apply":
            apply_mod, apply_block = s[1]

            try:
                mod = context.mods[apply_mod.strip().upper()]  # type: list[ZDModClause]

            except KeyError:
                raise CompilerError(
                    "Tried to apply unkown state mod {} in apply statement inside {}!".format(
                        repr(apply_mod), context.describe()
                    )
                )

            apply_ctx = context.derive("apply block")
            apply_ctx.applied_mods.extend(mod)

            apply = ZDBlock(actor)

            for a in apply_block:
                self._parse_state(actor, apply_ctx, apply, a, func)

            add_state(apply)

        elif s[0] == "if":
            ifs = ZDIfStatement(actor, self._parse_expression(s[1][0], context), [])
            if_ctx = context.remote_derive("if body", 3 if s[1][2] else 2)

            for a in s[1][1]:
                self._parse_state(actor, if_ctx, ifs, a, func)

            if s[1][2]:
                elses = ZDBlock(actor)

                for a in s[1][2]:
                    self._parse_state(actor, if_ctx, elses, a, func)

                ifs.set_else(elses)

            add_state(ifs)
            pop_remote()

        elif s[0] == "ifjump":
            jump, s_yes, s_no = s[1]

            @ZDIfJumpStatement.generate(actor)
            def ifs(jump_offset):
                jump_context = context.derive("ifjump check")
                jump_context.replacements["$OFFSET"] = str(jump_offset)

                return self._parse_state_action(jump, jump_context)

            if_ctx = context.remote_derive("ifjump body", 3)

            for a in s_yes:
                self._parse_state(actor, if_ctx, ifs, a, func)

            if s_no:
                elses = ZDBlock(actor)

                for a in s_no:
                    self._parse_state(actor, if_ctx, elses, a, func)

                ifs.set_else(elses)

            add_state(ifs)
            pop_remote()

        elif s[0] == "whilejump":
            break_ctx = context.remote_derive("whilejump", 4, break_ctx="self")
            jump, s_yes, s_no = s[1]

            @ZDWhileJumpStatement.generate(actor)
            def whs(jump_offset):
                jump_context = break_ctx.derive("whilejump check")
                jump_context.replacements["$OFFSET"] = str(jump_offset)

                return self._parse_state_action(jump, jump_context)

            if s_no is not None:
                elses = ZDBlock(actor)
                else_ctx = break_ctx.derive("else of whilejump")

                for a in s_no:
                    self._parse_state(actor, else_ctx, elses, a, func)

                whs.set_else(elses)

            body_ctx = break_ctx.derive("body of whilejump", loop_ctx="self")

            for a in s_yes:
                self._parse_state(
                    actor,
                    body_ctx,
                    whs,
                    self._mutate_iter_state(a, break_ctx, body_ctx),
                    func,
                )

            add_state(whs)
            clear_remotes(break_ctx)

        elif s[0] == "while":
            break_ctx = context.remote_derive(
                "while", 4 if s[1][2] else 3, break_ctx="self"
            )
            whs = ZDWhileStatement(
                actor, self._parse_expression(s[1][0], break_ctx), []
            )

            if s[1][2]:
                elses = ZDBlock(actor)
                else_ctx = break_ctx.derive("else of while")
                for a in s[1][2]:
                    self._parse_state(
                        actor,
                        else_ctx,
                        elses,
                        self._mutate_iter_state(a, else_ctx, else_ctx),
                        func,
                    )

                whs.set_else(elses)

            body = ZDBlock(actor)
            body_ctx = break_ctx.derive(
                "body of while",
                loop_ctx="self",
            )

            for a in s[1][1]:
                self._parse_state(
                    actor,
                    body_ctx,
                    body,
                    self._mutate_iter_state(a, break_ctx, body_ctx),
                    func,
                )

            whs.states.append(body)

            add_state(whs)
            clear_remotes(break_ctx)

        elif s[0] == "for":
            itername, iteridx, itermode, f_body, f_else = s[1]

            def do_for(iterator):
                break_ctx = context.derive(f"for {itermode[0]}", break_ctx="self")

                for i, item in enumerate(iterator):
                    iter_ctx = break_ctx.derive(
                        f"{itermode[0]} loop body #{i + 1}", loop_ctx="self"
                    )
                    iter_ctx.replacements[itername.upper()] = item

                    if iteridx:
                        iter_ctx.replacements[iteridx.upper()] = str(i)

                    for si, a in enumerate(f_body):
                        self._parse_state(
                            actor,
                            iter_ctx,
                            label,
                            self._mutate_iter_state(a, break_ctx, iter_ctx),
                            label,
                        )

            def do_else():
                else_ctx = context.derive("for-else")

                for a in f_else:
                    self._parse_state(actor, else_ctx, label, a, label)

            if itermode[0] == "group":
                group_name = context.resolve(itermode[1], "a parametrized group name")

                if group_name.upper() not in self.groups:
                    raise CompilerError(
                        "No such group {} to 3 in a for loop in {}!".format(
                            repr(group_name), context.describe()
                        )
                    )

                elif self.groups[group_name.upper()]:
                    do_for(iter(self.groups[group_name.upper()]))

                else:
                    do_else()

            elif itermode[0] == "range":
                rang = itermode[1]

                r_from = self._parse_replaceable_number(rang[0], context)
                r_to = rang[0] + self._parse_replaceable_number(rang[1], context)

                if r_to > r_from:
                    do_for(list(range(r_from, r_to, 1)))

                else:
                    do_else()

            else:
                raise CompilerError(
                    "Unknown internal for loop iteration mode '{}' in {}! Please report this issue to the author.".format(
                        itermode[0], context.describe()
                    )
                )

        elif s[0] == "inject":
            r_from, r_name, r_args = s[1]
            r_name = context.resolve(r_name, "a parametrized macro injection")

            if r_from:
                r_from = unstringify(
                    context.resolve(r_from, "a parametrized extern macro classname")
                )

                if r_from.upper() in self.actor_names:
                    act = self.actor_names[r_from.upper()]

                else:
                    raise CompilerError(
                        "Unknown extern macro classname {} in {}!".format(
                            repr(r_from), context.describe()
                        )
                    )

                macros = dict(act.context.macros)

            else:
                macros = dict(context.macros)

            if r_name.upper() in macros:
                if r_from:
                    new_context = context.derive(
                        "macro '{}' from {}".format(r_name, act.name)
                    )
                    new_context.update(act.context)
                    r_qualname = "{}.{}".format(r_from, r_name)

                else:
                    new_context = context.derive("macro '{}'".format(r_name))
                    r_qualname = r_name

                (m_args, m_body) = macros[r_name.upper()]

                if len(m_args) != len(r_args):
                    raise CompilerError(
                        "Bad number of arguments while trying to inject macro {}; expected {}, got {}! (in {})".format(
                            r_qualname, len(m_args), len(r_args), context.describe()
                        )
                    )

                for rn, an in zip(r_args, m_args):
                    new_context.replacements[an.upper()] = self._parse_argument(
                        rn, context, an
                    )

                for a in m_body:
                    self._parse_state(
                        actor,
                        new_context,
                        label,
                        self._mutate_macro_state(a, new_context),
                        label,
                    )

            else:
                if r_from:
                    raise CompilerError(
                        "Unknown macro {}.{} in {}!".format(
                            r_from, r_name, context.describe()
                        )
                    )

                else:
                    raise CompilerError(
                        "Unknown macro {} in {}!".format(r_name, context.describe())
                    )

    def _parse_inherit(self, inh, context):
        if inh is None:
            return None

        ptype, pval = inh

        if ptype == "classname":
            return context.replacements.get(pval.upper(), pval)

        elif ptype == "format":
            return self._parse_formatted_string(pval, context)

        elif ptype == "template derivation":
            with context.desc_block("template derivation inheritance"):
                return self._parse_template_derivation(
                    pval, context, do_stringify=False
                ).name

    def _parse_anonym_class(self, anonym_class, context) -> str:
        a = dict(anonym_class)
        new_context = context.derive("anonymous class")

        classname = "_AnonymClass_{}_{}".format(self.id, len(self.anonymous_classes))

        if a["group"]:
            g = unstringify(a["group"])

            if g.upper() in self.groups:
                self.groups[g.upper()].append(stringify(classname))

            else:
                raise CompilerError(
                    "Group '{}' not found while compiling anonymous class in {}!".format(
                        g, context.describe()
                    )
                )

        anonym_actor = ZDActor(
            self,
            classname,
            inherit=self._parse_inherit(a["inheritance"], context),
            context=new_context,
        )

        self._parse_class_body(anonym_actor, anonym_actor.get_context(), a["body"])

        context.add_actor(anonym_actor)

        self.anonymous_classes.append(anonym_actor)
        # self.actors.append(anonym_actor)
        # self.inventories.append(anonym_actor)

        return stringify(anonym_actor.name)

    def _derive_class_from_template(
        self,
        template,
        param_values,
        context,
        labels=(),
        macros=(),
        arrays=(),
        body=(),
        inherits=None,
        group=None,
        name=None,
        pending=None,
    ):
        labels = dict(labels)
        macros = dict(macros)
        arrays = dict(arrays)
        body = list(body)

        needs_init, actor = template.generate_init_class(
            self,
            context,
            param_values,
            {l.upper() for l in labels.keys()},
            {m["name"].upper(): m["args"] for m in macros.values()},
            {a["name"].upper(): len(a["value"][1]) for a in arrays.values()},
            name=name,
            inherits=inherits,
            group=group,
        )
        new_context = actor.get_context()

        if needs_init:

            def pending_oper_gen():
                act = actor
                new_ctx = new_context
                temp = template

                @pending_task(0)
                def pending_oper():
                    for btype, bdata in body:
                        if btype == "array":
                            try:
                                absarray = template.abstract_array_names[
                                    bdata["name"].upper()
                                ]

                            except KeyError:
                                raise CompilerError(
                                    "Tried to define an array {} in {} that is not abstractly declared in the template {}!".format(
                                        repr(bdata["name"]),
                                        new_ctx.describe(),
                                        repr(template.name),
                                    )
                                )

                            act.uservars.append(
                                {
                                    "name": bdata["name"],
                                    "size": len(bdata["value"][1]),
                                    "value": ("arr", bdata["value"][1]),
                                    "type": absarray["type"],
                                }
                            )

                    self._parse_class_body(act, new_ctx, temp.parse_data + body)

                return pending_oper

            if pending:
                pending.put_nowait(pending_oper_gen())

            else:
                pending_oper_gen().func()

        return actor

    def _parse_var_value(self, vval, context):
        vvtype, vvbody = vval

        if vvtype == "val":
            return ("val", self._parse_expression(vvbody, context))

        if vvtype == "arr":
            return self._parse_array(vval, context)

        raise CompilerError(
            "Could not parse user var value {} in {}".format(
                repr(vval), context.describe()
            )
        )

    def _parse_class_body(self, actor, context, body):
        for btype, bdata in body:
            if btype == "for":
                for ctx, unpacked_bdata in self.resolve_for(bdata, context):
                    self._parse_class_body(actor, ctx, [unpacked_bdata])

        for btype, bdata in body:
            if btype == "mod":
                self._parse_mod_block(context, bdata)

        for btype, bdata in body:
            if btype == "macro":
                context.macros[bdata["name"].upper()] = (bdata["args"], bdata["body"])

        for btype, bdata in body:
            if btype == "property":
                ZDProperty(
                    actor,
                    bdata["name"],
                    ", ".join(
                        self._parse_parameter(x, context) for x in bdata["value"]
                    ),
                )

            elif btype == "flag":
                actor.flags.add(bdata)

            elif btype == "flag combo":
                actor.raw.append(bdata)

            elif btype == "user var":
                bdata = {
                    **bdata,
                    "value": self._parse_var_value(bdata["value"], context),
                }
                actor.uservars.append(bdata)

            elif btype == "unflag":
                actor.antiflags.add(bdata)

            elif btype == "label":
                label = ZDLabel(actor, bdata["name"])

                with context.desc_block("label '{}'".format(label.name)):
                    for s in bdata["body"]:
                        self._parse_state(actor, context, label, s, None)

            elif btype == "function":
                raise CompilerError(
                    "Functions have been removed since ZDCode 2.11.0! ({})".format(
                        context.describe()
                    )
                )

            elif btype == "apply":
                mtype, mval = bdata

                if mtype == "name":
                    try:
                        mod = context.mods[
                            mval.strip().upper()
                        ]  # type: list[ZDModClause]

                    except KeyError:
                        raise CompilerError(
                            "Tried to apply unkown state mod {} in global apply statement inside {}!".format(
                                repr(mval.strip()), context.describe()
                            )
                        )

                elif mtype == "body":
                    mod = []

                    for selector, effects in mval:
                        mod.append(self._parse_mod_clause(context, selector, effects))

                context.applied_mods.extend(mod)

    # unpack static for loops
    def resolve_for(self, forbody, context):
        itername, iteridx, itermode, f_body, f_else = forbody

        def do_for(iterator):
            break_ctx = context.remote_derive("static for")

            for i, item in enumerate(iterator):
                iter_ctx = break_ctx.remote_derive(
                    "for-{} loop body".format(itermode[0]), loop_ctx="self"
                )
                iter_ctx.replacements[itername.upper()] = item

                if iteridx:
                    iter_ctx.replacements[iteridx.upper()] = str(i)

                for si, a in enumerate(f_body):
                    yield (iter_ctx, a)

        def do_else():
            else_ctx = context.remote_derive("static for-else")

            for a in f_else:
                yield (else_ctx, a)

        if itermode[0] == "group":
            group_name = context.remote_derive(itermode[1], "a parametrized group name")

            if group_name.upper() not in self.groups:
                raise CompilerError(
                    "No such group {} to 3 in a for loop in {}!".format(
                        repr(group_name), context.describe()
                    )
                )

            elif self.groups[group_name.upper()]:
                yield from do_for(iter(self.groups[group_name.upper()]))

            else:
                yield from do_else()

        elif itermode[0] == "range":
            rang = itermode[1]

            r_from = self._parse_replaceable_number(rang[0], context)
            r_to = rang[1][0] + self._parse_replaceable_number(rang[1][1], context)

            if r_to > r_from:
                r = list(range(r_from, r_to, 1))
                yield from do_for(r)

            else:
                yield from do_else()

    def _parse(self, actors, debug=False):
        parsed_actors = []

        context = ZDCodeParseContext(actors=[parsed_actors], description="global")

        actors = [(context, a) for a in actors]

        def unpack(vals, reslist):
            # always parse groups first,
            # to ensure they can be seen by
            # static for loops
            unpacked = True

            for ctx, (class_type, a) in vals:
                if class_type == "group":
                    a = dict(a)

                    gname = a["name"].upper()

                    if gname in self.groups:
                        self.groups[gname].extend(list(a["items"]))

                    else:
                        self.groups[gname] = list(a["items"])

            for ctx, (class_type, a) in vals:
                if class_type == "for":
                    unpacked = False
                    reslist.extend(self.resolve_for(a, ctx))

                elif class_type != "group":
                    reslist.append((ctx, (class_type, a)))

            return unpacked

        while True:
            reslist = []

            if unpack(actors, reslist):
                break

            else:
                actors = reslist
                reslist = []

        # read the unpacked list
        for ctx, (class_type, a) in actors:
            if class_type == "macro":
                a = dict(a)

                context.macros[a["name"]] = (a["args"], a["body"])

        for actx, (class_type, a) in actors:
            if class_type == "class template":
                a = dict(a)

                classname = self._parse_formattable_string(a["classname"], actx)

                abstract_labels = set()
                abstract_macros = {}
                abstract_arrays = {}
                template_body = []

                if a["group"]:
                    g = unstringify(a["group"])

                    if g.upper() not in self.groups:
                        raise CompilerError(
                            "Group '{}' not found while compiling template class {}!".format(
                                g, classname
                            )
                        )

                    g = g.upper()

                else:
                    g = None

                for btype, bdata in a["body"]:
                    if btype == "abstract label":
                        abstract_labels.add(bdata.upper())

                    elif btype == "abstract macro":
                        abstract_macros[bdata["name"].upper()] = bdata["args"]

                    elif btype == "abstract array":
                        abstract_arrays[bdata["name"].upper()] = bdata

                    else:
                        template_body.append((btype, bdata))

                template = ZDClassTemplate(
                    a["parameters"],
                    template_body,
                    abstract_labels,
                    abstract_macros,
                    abstract_arrays,
                    g,
                    self,
                    classname,
                    self._parse_inherit(a["inheritance"], actx),
                    a["replacement"],
                    a["class number"],
                )
                actx.templates[classname] = template

        pending = queue.PriorityQueue()

        for actx, (class_type, a) in actors:
            if class_type == "class":
                a = dict(a)
                classname = self._parse_formattable_string(a["classname"], actx)

                with actx.desc_block("class '{}'".format(classname)):
                    actor = ZDActor(
                        self,
                        classname,
                        self._parse_inherit(a["inheritance"], actx),
                        a["replacement"],
                        a["class number"],
                        context=actx,
                    )
                    ctx = actor.get_context()

                    if a["group"]:
                        g = a["group"]

                        if g.upper() in self.groups:
                            self.groups[g.upper()].append(stringify(classname))

                        else:
                            raise CompilerError(
                                "Group '{}' not found while compiling class '{}'!".format(
                                    g, classname
                                )
                            )

                    def pending_oper_gen():
                        actor_ = actor
                        ctx_ = ctx
                        body_ = a["body"]

                        @pending_task(2)
                        def pending_oper():
                            self._parse_class_body(actor_, ctx_, body_)

                        return pending_oper

                    pending.put_nowait(pending_oper_gen())

                    # self.actors.append(actor)
                    self.actor_names[actor.name.upper()] = actor
                    parsed_actors.append(actor)

            if class_type == "static template derivation":
                a = dict(a)

                new_name = a["classname"]
                gname = a["group"]

                new_name = self._parse_formattable_string(new_name, actx)

                with actx.desc_block(
                    "static template derivation '{}'".format(new_name)
                ):
                    self._parse_template_derivation(
                        a["source"][1],
                        actx,
                        pending=pending,
                        name=new_name,
                        do_stringify=False,
                    )

                    if gname:
                        g = unstringify(gname)

                        if g.upper() not in self.groups:
                            raise CompilerError(
                                "No such group {} to add the derivation {} to!".format(
                                    repr(g), new_name
                                )
                            )

                        self.groups[g.upper()].append(new_name)

        while not pending.empty():
            pending.get_nowait().func()

        for a in parsed_actors:
            a.prepare_spawn_label()

        self.actors.extend(parsed_actors)

        self.actors.sort(key=lambda actor: actor.name)  # predominantly alphabetic sort
        reorders = self.reorder_inherits()

        if debug:
            context.print_state_tree()

        # print("(Reordered {} actors)".format(reorders))

    def __init__(self):
        self.includes = {}
        self.inventories = []
        self.anonymous_classes = []
        self.actors = []
        self.actor_names = {}
        self.groups = {}
        self.id = make_id(35)
        self.num_anonym_macros = 0

    def reorder_inherits(self) -> int:
        new_order: list[ZDActor] = []
        positions: dict[str, int] = {}
        reorders = 0

        for actor in self.actors:
            new_pos = len(new_order)

            if actor.name in positions:
                new_pos = positions[actor.name]
                reorders += 1

            if actor.inherit is not None:
                if actor.inherit not in positions or positions[actor.inherit] > new_pos:
                    positions[actor.inherit] = new_pos

            new_order.insert(new_pos, actor)

        self.actors = new_order

        return reorders

    def to_decorate(self):
        res = TextNode(indent=0)

        res.add_line("// :ZDCODE version='{}' id='{}' ".format(__VERSION__, self.id))

        if self.inventories:
            for i in self.inventories:
                res.add_line(i.to_decorate())

        for a in self.actors:
            res.add_line(a.to_decorate())

        return res

    def decorate(self):
        return decorate(self)
