import zdcode
import os
import zipfile

from os import path


def get_changelog():
    if path.isfile('changelog.json'):
        try:
            import simplejson as json

        except ImportError:
            import json

        with open('changelog.json') as fp:
            changelog = json.load(fp)

    elif path.isfile('changelog.yaml'):
        try:
            import yaml

        except ImportError:
            raise ImportError("Module yaml not found to compile changelog.yml!")

        with open('changelog.json', 'w') as jfp:
            with open('changelog.yml') as yfp:
                changelog = yaml.load(yfp)
                json.dump(changelog, jfp)

    else:
        raise RuntimeError("Neither changelog.json nor changelog.yml found!")

    return changelog

version = get_changelog()['versions'][-1]['name']


def print_parse_error(e):
    print('{}: {}'.format(type(e).__name__, str(e)))


print("Compiling examples...")

for root, dirs, files in os.walk('examples'):
    if root == 'examples':
        for f in files:
            if f.endswith('.zc2'):
                print(' -  {} ({})'.format(f, root))
                apath = os.path.join(root, f)

                with open(apath) as ifp:
                    code = zdcode.ZDCode.parse(ifp.read(), f, root, error_handler=print_parse_error)

                if code:
                    with open(apath[:-4] + ".dec", 'w') as ofp:
                        ofp.write(zdcode.decorate(code))

print('\nBundling examples into single output...')

errors = 0
tot = 0

bundle_code = zdcode.ZDCode()

for root, dirs, files in os.walk('examples'):
    if root == 'examples':
        for f in files:
            if f.endswith('.zc2'):
                apath = os.path.join(root, f)

                with open(apath) as ifp:
                    if not bundle_code.add(ifp.read(), f, root, error_handler=print_parse_error):
                        errors += 1

                    tot += 1

                    print(' +  {} ({})              '.format(f, root))
                    print('  ({} total, {} succeeded, {} failed)'.format(tot, tot - errors, errors), end='\r')

if errors < tot:
    if errors:
        print('Errors were found in {errs} out of {tot} examples.'.format(errs=errors, tot=tot))

    with open('ZDCodeBundle_{}.dec'.format(version), 'w') as ofile:
        ofile.write(zdcode.decorate(bundle_code))

    with zipfile.ZipFile('ZDCodeBundle_{}.pk3'.format(version), 'w') as opkg:
        with opkg.open('DECORATE.Bundle', 'w') as odec:
            odec.write(zdcode.decorate(bundle_code).encode('utf-8'))

        for root, dirs, files in os.walk('examples'):
            if root == 'examples':
                for f in files:
                    if f.endswith('.zc2'):
                        pkgpath = 'ZDCode/{}'.format(f)

                        with opkg.open(pkgpath, 'w') as ofile:
                            with open(path.join(root, f), 'rb') as ifile:
                                ofile.write(ifile.read())

        for root, dirs, files in os.walk('examples/resources/'):
            rpath = os.path.relpath(root, 'examples/resources')

            for f in files:
                if rpath == '.':
                    pkgpath = f

                else:
                    pkgpath = path.join(rpath, f)

                with opkg.open(pkgpath, 'w') as ofile:
                    with open(path.join(root, f), 'rb') as ifile:
                        ofile.write(ifile.read())

    print("Bundle compiled {}.                               ".format('with partial success' if errors else 'succesfully'))

    if errors:
        exit(1)

else:
    print("Failed to build bundle: all the examples failed to compile!     ")
    exit(1)
