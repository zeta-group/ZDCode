import sys
import argparse
import os

try:
    import zdcode
    from zdcode.bundle import Bundle

except ImportError:
    try:
        #import . as zdcode
        raise ImportError

    except ImportError:
        import __init__ as zdcode
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

def arg_parser():
    aparser = argparse.ArgumentParser(description='ZDCode compilation and bundling engine.')
    subparsers = aparser.add_subparsers(help='sub-command help')
    
    aparser_compile = subparsers.add_parser('compile', aliases=['c'], help='compile ZDCode input files (and any other files that may be included by the preprocessor) to a single DECORATE file')
    aparser_compile.add_argument('input', type=str, metavar='INFILES', nargs='+', help='input files for the compiler (zc2)')
    aparser_compile.add_argument('-o', '--output', type=str, required=True, metavar='OUTFILE', dest='out_compile', help='output file from the compiler (DECORATE)')
    aparser_compile.set_defaults(func=do_compile)
    
    aparser_bundle = subparsers.add_parser('bundle', aliases=['b'], help='bundle multiple files (asset folder, PK3 or ZDCode), alongside dependencies, to two output PK3 files: the assets file, and the code file')
    aparser_bundle.add_argument('input', type=str, metavar='INFILES', nargs='+', help='input files for the bundler (folder, pk3 or zc2)')
    aparser_bundle.add_argument('-a', '--asset-output', type=str, required=True, metavar='OUTFILE', dest='out_asset', help='asset output file from the bundler (pk3)')
    aparser_bundle.add_argument('-c', '--code-output', type=str, required=True, metavar='OUTFILE', dest='out_code', help='code output file from the bundler (pk3)')
    aparser_bundle.set_defaults(func=do_bundle)
    
    return aparser

def main():
    args = arg_parser().parse_args()
    return args.func(args)

# Actions

def do_compile(args):
    code = zdcode.ZDCode()
    
    for fn in args.input:
        with open(fn) as fp:
            if not code.add(fp.read(), os.path.basename(fn), os.path.dirname(fn), error_handler=print_parse_error):
                return 1
    
    dec = code.decorate()
    open(args.out_compile, "w").write(dec)
    print("Output compiled successfully.")
    
def do_bundle(args):
    bundle = Bundle(*args.input, error_handler=print_parse_error)
    status, msg = bundle.bundle(args.out_asset, args.out_code)
    
    print(msg)
    return status