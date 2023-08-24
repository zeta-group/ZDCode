"""The command line interface for ZDCode and its build system Zake."""
import argparse
import os
import sys

from . import zake
from .bundle import Bundle
from .compiler.compiler import ZDCode


def print_parse_error(error):
    """Prints a parsing error."""
    print(f"{type(error).__name__}: {str(error)}")
    sys.exit(2)


def from_stdin():
    """Compiles ZDCode from the standard input."""
    data = []

    for line in iter(sys.stdin.readline, ""):
        data.append(line)

    if not data:
        print("No data to use! Provide as stdin or as arguments.")
        sys.exit(1)

    print(ZDCode.parse("\n".join(data), error_handler=print_parse_error).decorate())


class TupleTrue(argparse.Action):
    """Sets an item as true by passing a tuple (<item>, True)."""

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs != 1:
            raise ValueError("Invalid nargs for TupleTrue action (only 1 available)")

        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        option = getattr(namespace, self.dest, None) or []

        if not option:
            setattr(namespace, self.dest, option)

        option.append((values, True))


def arg_parser():
    """Produces the argument parser for the ZDCode command line interface."""
    aparser = argparse.ArgumentParser(
        description="ZDCode compilation and bundling engine. The following is the "
        "direct compilation and bundling interface - if no arguments are passed, "
        "Zake is run instead. If possible, use Zake to define a project's build."
    )

    aparser.add_argument(
        "--print-ast",
        type=bool,
        nargs="?",
        dest="print_ast",
        required=False,
        default=False,
        const=True,
        help="prints AST for the entire compilation unit, helpful for debugging",
    )
    aparser.add_argument(
        "-D",
        "--define",
        type=str,
        nargs=1,
        metavar="DEFNAMES",
        dest="prepdefs",
        action=TupleTrue,
        required=False,
        help="preprocessor definitions (set to True)",
    )
    aparser.add_argument(
        "-S",
        "--set",
        type=str,
        nargs=2,
        metavar=("DEFNAME", "DEFVALS"),
        dest="prepdefs",
        action="append",
        required=False,
        help="preprocessor definitions (set to a string value)",
    )

    aparser.add_argument(
        "input",
        type=argparse.FileType("r"),
        metavar="INFILES",
        nargs="+",
        help="input files for the compiler (zc2)",
    )
    aparser.add_argument(
        "-o",
        "--output",
        type=argparse.FileType("w"),
        required=False,
        metavar="OUTFILE",
        dest="out_compile",
        default=None,
        help="output plain text file from with compiled DECORATE",
    )
    aparser.set_defaults(func=do_compile)

    return aparser


def main():
    """The main entry point."""
    if len(sys.argv) > 1:
        args = arg_parser().parse_args()
        return args.func(args)

    print("Running Zake.")
    return main_zake()


def main_zake():
    """Calls Zake's main entry point."""
    return zake.main(print_status_code=False)


# Actions


def do_compile(args):
    """This argparse action calls the ZDCode compiler directly instead of Zake."""
    code = ZDCode()

    preproc_defs = dict(args.prepdefs or [])

    for file_obj in args.input:
        if not code.add(
            file_obj.read(),
            os.path.basename(file_obj.name),
            os.path.dirname(file_obj.name),
            preproc_defs=preproc_defs,
            error_handler=print_parse_error,
            debug=args.print_ast,
        ):
            # Compilation error found - it was already printed.
            return 1

    dec = code.decorate()
    args.out_compile.write(dec)
    print("Output compiled successfully.")

    return 0
