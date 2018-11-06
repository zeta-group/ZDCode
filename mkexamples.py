import zdcode
import os

print("Compiling examples...")

for root, dirs, files in os.walk('examples'):
    for f in files:
        if f.endswith('.zc2'):
            print(' -  {} ({})'.format(f, root))
            apath = os.path.join(root, f)

            with open(apath) as ifp:
                code = zdcode.ZDCode.parse(ifp.read())

            with open(apath[:-4] + ".dec", 'w') as ofp:
                ofp.write(zdcode.decorate(code))

print("Examples compiled succesfully.")