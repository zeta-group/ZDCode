import sys
import os

try:
    import zdcode

except ImportError:
    try:
        #import . as zdcode
        raise ImportError

    except ImportError:
        import __init__ as zdcode

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

def main():
    try:
        fnfrom = sys.argv[1]
        fnto  = sys.argv[2]
        print('[compiling from {} to {}]'.format(fnfrom, fnto), file=sys.stderr)

    except IndexError:
        print('[compiling stdin to stdout]', file==sys.stderr)
        from_stdin()

    else:
        try:
            dec = zdcode.ZDCode.parse(open(fnfrom).read(), os.path.basename(fnto), os.path.dirname(fnto), error_handler=print_parse_error)

            if dec:
                dec = dec.decorate()
                open(sys.argv[2], "w").write(dec)
                print("Wrote to file successfully.")

            else:
                print("Syntax error found, aborting.")

        except IOError:
            from_stdin()
