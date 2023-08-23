from ..types import *


class ZDClassTemplate(ZDBaseActor):
    def __init__(
        self,
        template_parameters: Iterable[str],
        parse_data,
        abstract_label_names: Iterable[str],
        abstract_macro_names: dict[str, Iterable[str]],
        abstract_array_names: dict[str, {"size": int, "type": str}],
        group_name: str | None,
        code: "ZDCode",
        name: str,
        inherit: str | None = None,
        replace: str | None = None,
        doomednum: int | None = None,
        _id: str | None = None,
    ):
        ZDBaseActor.__init__(self, code, name, inherit, replace, doomednum, _id)

        self.group_name = group_name or None

        self.template_parameters = list(template_parameters)

        self.abstract_label_names = set(abstract_label_names)
        self.abstract_macro_names = dict(abstract_macro_names)
        self.abstract_array_names = dict(abstract_array_names)

        self.parse_data = parse_data
        self.existing = {}

    def duplicate(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
    ):
        if (
            self.abstract_macro_names
            or self.abstract_label_names
            or self.abstract_array_names
        ):
            return False

        return (
            self.parameter_hash(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )
            in self.existing
        )

    def which_duplicate(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
    ):
        return self.existing[
            self.parameter_hash(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )
        ]

    def register(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
        result,
    ):
        self.existing[
            self.parameter_hash(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )
        ] = result

    def parameter_hash(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
    ) -> str:
        hash = hashlib.sha256()

        hash.update(self.name.encode("utf-8"))
        hash.update(b"|")

        hash.update(self.id.encode("utf-8"))
        hash.update(b"|")

        if (
            self.abstract_macro_names
            or self.abstract_label_names
            or self.abstract_array_names
        ):
            hash.update(make_id(80).encode("utf-8"))

        else:
            for parm in parameter_values:
                hash.update(parm.encode("utf-8"))
                hash.update(b"-")

            hash.update(b"|")

            for name in itertools.chain(provided_label_names, provided_array_names):
                hash.update(name.encode("utf-8"))
                hash.update(b"-")

            hash.update(b"|")

            for name, args in provided_macro_names.items():
                hash.update(hex(len(args)).encode("utf-8"))
                hash.update(name.encode("utf-8"))
                hash.update(b"-")

        return hash.hexdigest()

    def generated_class_name(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
    ):
        hash = self.parameter_hash(
            parameter_values,
            provided_label_names,
            provided_macro_names,
            provided_array_names,
        )
        return "{}__deriv_{}".format(self.name, hash)

    def assert_group_exists(
        self, groupname: str, ctx_str: str, context: "ZDCodeParseContext"
    ):
        if groupname not in self.code.groups:
            raise CompilerError(
                f"No such group '{groupname}' {ctx_str} (in f{context.describe()})!"
            )

    def generate_init_class(
        self,
        code: "ZDCode",
        context: "ZDCodeParseContext",
        parameter_values,
        provided_label_names: Iterable[str] = (),
        provided_macro_names: Iterable[str] = (),
        provided_array_names: Iterable[str] = (),
        name: str | None = None,
        pending: str | None = None,
        inherits: str | None = None,
        group: str | None = None,
    ):
        provided_label_names = set(provided_label_names)
        provided_macro_names = dict(provided_macro_names)

        if self.duplicate(
            parameter_values,
            provided_label_names,
            provided_macro_names,
            provided_array_names,
        ):
            return False, self.which_duplicate(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )

        new_name = (
            name
            if name is not None
            else self.generated_class_name(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )
        )

        ctx_str = (
            f"in {name and 'derivation ' + name or 'anonymous derivation'} of {self.name}",
        )

        if self.group_name:
            self.assert_group_exists(self.group_name, ctx_str, context)
            self.code.groups[self.group_name].append(stringify(new_name))

        if group and group != self.group_name:
            self.assert_group_exists(group, ctx_str, context)
            self.code.groups[group].append(stringify(new_name))

        context_new = context.derive("derivation of template {}".format(self.name))

        context_new.replacements.update(self.get_init_replacements(parameter_values))

        inh = inherits or (
            self.inherit
            and context_new.replacements.get(self.inherit.upper(), self.inherit)
            or None
        )
        rep = (
            self.replace
            and context_new.replacements.get(self.replace.upper(), self.replace)
            or None
        )

        context_new.replacements["SELF"] = stringify(new_name)

        res = ZDActor(self.code, new_name, inh, rep, self.num, context=context_new)

        for l in self.abstract_label_names:
            if l not in provided_label_names:
                raise CompilerError(
                    "Tried to derive template {} in {}, but abstract label {} does not have a definition!".format(
                        self.name, context.describe(), l
                    )
                )

        for m, a in self.abstract_macro_names.items():
            if m not in provided_macro_names.keys():
                raise CompilerError(
                    "Tried to derive template {} in {}, but abstract macro {} does not have a definition!".format(
                        self.name, context.describe(), m
                    )
                )

            if len(a) != len(provided_macro_names[m]):
                raise CompilerError(
                    "Tried to derive template {} in {}, but abstract macro {} has the wrong number of arguments: expected {}, got {}!".format(
                        self.name,
                        context.describe(),
                        m,
                        len(a),
                        len(provided_macro_names[m]),
                    )
                )

        for m, a in self.abstract_array_names.items():
            if m not in provided_array_names.keys():
                raise CompilerError(
                    "Tried to derive template {} in {}, but abstract array {} is not defined!".format(
                        self.name, context.describe(), m
                    )
                )

            if a["size"] != "any" and a["size"] != provided_array_names[m]:
                raise CompilerError(
                    "Tried to derive template {} in {}, but abstract array {} has a size constraint; expected {} array elements, got {}!".format(
                        self.name,
                        context.describe(),
                        m,
                        a["size"],
                        provided_array_names[m],
                    )
                )

        self.register(
            parameter_values,
            provided_label_names,
            provided_macro_names,
            provided_array_names,
            res,
        )

        self.code.actor_names[res.name.upper()] = res
        context.add_actor(res)

        return True, res

    def get_init_replacements(self, parameter_values):
        return dict(
            zip((p.upper() for p in self.template_parameters), parameter_values)
        )
