"""A ZDCode class template."""
import hashlib
import itertools
from typing import TYPE_CHECKING
from typing import Iterable
from typing import TypedDict

from ..compiler.error import CompilerError
from ..util import make_id
from ..util import stringify
from .actor import ZDActor
from .actor import ZDBaseActor
from .actor import ZDObject

if TYPE_CHECKING:
    from ..compiler.compiler import ZDCode
    from ..compiler.context import ZDCodeParseContext


class UserArrayDefinition(TypedDict):
    """An internal object defining an abstract user array.

    Used in class templates only to allow overriding an array used by the template in
    the derivation."""

    name: str
    size: str
    type: str


class ZDClassTemplate(ZDBaseActor, ZDObject):
    """A ZDCode class template."""

    def __init__(
        self,
        template_parameters: Iterable[str],
        parse_data,
        abstract_label_names: Iterable[str],
        abstract_macro_names: dict[str, Iterable[str]],
        abstract_array_names: dict[str, UserArrayDefinition],
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
        """Duplicates this class template."""
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
        """Find a class template with these exact parameter  definitions."""
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
        """Register the hash of these parameter definitions."""
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
        """Hashes parameter definitions."""
        hashed = hashlib.sha256()

        hashed.update(self.name.encode("utf-8"))
        hashed.update(b"|")

        hashed.update(self.identifier.encode("utf-8"))
        hashed.update(b"|")

        if (
            self.abstract_macro_names
            or self.abstract_label_names
            or self.abstract_array_names
        ):
            hashed.update(make_id(80).encode("utf-8"))

        else:
            for parm in parameter_values:
                hashed.update(parm.encode("utf-8"))
                hashed.update(b"-")

            hashed.update(b"|")

            for name in itertools.chain(provided_label_names, provided_array_names):
                hashed.update(name.encode("utf-8"))
                hashed.update(b"-")

            hashed.update(b"|")

            for name, args in provided_macro_names.items():
                hashed.update(hex(len(args)).encode("utf-8"))
                hashed.update(name.encode("utf-8"))
                hashed.update(b"-")

        return hashed.hexdigest()

    def generate_class_name(
        self,
        parameter_values,
        provided_label_names: Iterable[str],
        provided_macro_names: Iterable[str],
        provided_array_names: Iterable[str],
    ):
        """Generates a class name for an anonymous class template."""
        hashed = self.parameter_hash(
            parameter_values,
            provided_label_names,
            provided_macro_names,
            provided_array_names,
        )
        return f"{self.name}__deriv_{hashed}"

    def generate_init_class(
        self,
        context: "ZDCodeParseContext",
        parameter_values,
        provided_label_names: Iterable[str] = (),
        provided_macro_names: Iterable[str] = (),
        provided_array_names: Iterable[str] = (),
        name: str | None = None,
        inherits: str | None = None,
        group: str | None = None,
    ):
        """Generates an initial ZDCode class object from this template."""
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
            else self.generate_class_name(
                parameter_values,
                provided_label_names,
                provided_macro_names,
                provided_array_names,
            )
        )

        ctx_str = (
            f"in {name and 'derivation ' + name or 'anonymous derivation'} "
            "of {self.name}",
        )

        if self.group_name:
            self.code.assert_group_exists(self.group_name, ctx_str, context)
            self.code.groups[self.group_name].append(stringify(new_name))

        if group and group != self.group_name:
            self.code.assert_group_exists(group, ctx_str, context)
            self.code.groups[group].append(stringify(new_name))

        context_new = context.derive(f"derivation of template {self.name}")

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

        for label_name in self.abstract_label_names:
            if label_name not in provided_label_names:
                raise CompilerError(
                    f"Tried to derive template {self.name} in {context.describe()}, "
                    f"but abstract label {label_name} does not have a definition!"
                )

        for macro_name, macro_defs in self.abstract_macro_names.items():
            if macro_name not in provided_macro_names:
                raise CompilerError(
                    f"Tried to derive template {self.name} in {context.describe()}, "
                    f"but abstract macro {macro_name} does not have a definition!"
                )

            if len(macro_defs) != len(provided_macro_names[macro_name]):
                raise CompilerError(
                    f"Tried to derive template {self.name} in {context.describe()}, "
                    f"but abstract macro {macro_name} has the "
                    f"wrong number of arguments: expected {len(macro_defs)}, "
                    f"got {len(provided_macro_names[macro_name])}!"
                )

        for macro_name, macro_defs in self.abstract_array_names.items():
            if macro_name not in provided_array_names:
                raise CompilerError(
                    f"Tried to derive template {self.name} in {context.describe()}, "
                    f"but abstract array {macro_name} is not defined!"
                )

            if (
                macro_defs["size"] != "any"
                and macro_defs["size"] != provided_array_names[macro_name]
            ):
                raise CompilerError(
                    f"Tried to derive template {self.name} in {context.describe()}, "
                    f"but abstract array {macro_name} has a size constraint; "
                    f"expected {macro_defs['size']} array elements, "
                    f"got {provided_array_names[macro_name]}!"
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
        """Corresponds the list of values to the template's parameters."""
        return dict(
            zip((p.upper() for p in self.template_parameters), parameter_values)
        )
