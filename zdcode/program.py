import sys
import argparse
import os

try:
    import zdcode
    import zdcode.zake as zake
    from zdcode.bundle import Bundle

except ImportError:
    import __init__ as zdcode
    import zake
    from bundle import Bundle

def print_parse_error(e):
    print('{}: {}'.format(type(e).__name__, str(e)))
    sys.exit(2)

def from_stdin():
    data = []

    for line in iter(sys.stdin.readline, ""):
        data.append(line)

    if not data:
        print("No data to use! Provide as stdin or as arguments.")
        sys.exit(1)

    print(zdcode.ZDCode.parse("\n".join(data), error_handler=print_parse_error).decorate())

class TupleTrue(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs != 1:
            raise ValueError("Invalid nargs for TupleTrue action (only 1 available)")

        super(TupleTrue, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        l = getattr(namespace, self.dest, None) or []

        if not l:
            setattr(namespace, self.dest, l)

        l.append((values, True))

def arg_parser():
    aparser = argparse.ArgumentParser(description='ZDCode compilation and bundling engine.')

    aparser.add_argument('input', type=str, metavar='INFILES', nargs='+', help='input files for the compiler (zc2)')
    aparser.add_argument('-od', '--output-decorate', type=argparse.FileType('w'), required=False, metavar='OUTFILE', dest='out_compile', default=None, help='output plain text file from with compiled DECORATE')
    aparser.add_argument('-oa', '--output-pk3-asset', type=argparse.FileType('wb'), required=False, metavar='OUTFILE', dest='out_asset', default=None, help='output file with assets bundled in a pk3')
    aparser.add_argument('-oc', '--output-pk3-code', type=argparse.FileType('wb'), required=False, metavar='OUTFILE', dest='out_code', default=None, help='output file with compiled DECORATE bundled in a pk3')
    aparser.add_argument('-D', '--define', type=str, nargs=1, metavar='DEFNAMES', dest='prepdefs', action=TupleTrue, required=False, help='preprocessor definitions (set to True)')
    aparser.add_argument('-S', '--set', type=str, nargs=2, metavar=('DEFNAME', 'DEFVALS'), dest='prepdefs', action='append', required=False, help='preprocessor definitions (set to a string value)')
    aparser.set_defaults(func=do_bundle)

    return aparser

def main():
    if len(sys.argv) > 1:
        args = arg_parser().parse_args()
        return args.func(args)

    return zake.main(print_status_code=False)

# Actions

def do_compile(args, preproc_defs=()):
    code = zdcode.ZDCode()

    for fn in args.input:
        with open(fn) as fp:
            if not code.add(fp.read(), os.path.basename(fn), os.path.dirname(fn), preproc_defs=preproc_defs, error_handler=print_parse_error):
                return 1

    dec = code.decorate()
    open(args.out_compile, "w").write(dec)
    print("Output compiled successfully.")

def do_bundle(args, preproc_defs=()):
    bundle = Bundle(*args.input, error_handler=print_parse_error)

    status, msg = bundle.bundle(args.out_asset, args.out_code, args.out_compile, preproc_defs={k.upper(): v for (k, v) in getattr(args, 'prepdefs', []) or []})
    print(msg)

    return status
