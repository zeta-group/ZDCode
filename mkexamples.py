import zdcode
import os
import sys


def print_parse_error(e):
    print('{}: {}'.format(type(e).__name__, str(e)))


print("Compiling examples...")

for root, dirs, files in os.walk('examples'):
    for f in files:
        if f.endswith('.zc2'):
            print(' -  {} ({})'.format(f, root))
            apath = os.path.join(root, f)

            with open(apath) as ifp:
                code = zdcode.ZDCode.parse(ifp.read(), os.path.dirname(apath), error_handler=print_parse_error)

            if code:
                with open(apath[:-4] + ".dec", 'w') as ofp:
                    ofp.write(zdcode.decorate(code))

print("Examples compiled succesfully.")
