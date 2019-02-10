import sys
import os

try:
    import zdcode

except ImportError:
    import __init__ as zdcode

def print_parse_error(e):
    print('{}: {}'.format(type(e).__name__, str(e)))
    sys.exit(2)

if __name__ == "__main__":
    try:
        dec = zdcode.ZDCode.parse(open(sys.argv[1]).read(), os.path.dirname(sys.argv[1]), error_handler=print_parse_error).decorate()
        open(sys.argv[2], "w").write(dec)
        print("Wrote to file successfully.")

    except (IndexError, IOError):
        #print("Format: zdcode [<input file> <output file>]")
        #print("Caught following error:")
        #traceback.print_exc()
        #print("Using stdin -> parse -> stdout instead.")

        data = []

        for line in iter(sys.stdin.readline, ""):
            data.append(line)

        if not data:
            print("No data to use! Provide as stdin or as arguments.")
            sys.exit(1)
        
        print(zdcode.ZDCode.parse("\n".join(data), error_handler=print_parse_error).decorate())
