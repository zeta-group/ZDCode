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
    for f in files:
        if f.endswith('.zc2'):
            print(' -  {} ({})'.format(f, root))
            apath = os.path.join(root, f)

            with open(apath) as ifp:
                code = zdcode.ZDCode.parse(ifp.read(), os.path.dirname(apath), error_handler=print_parse_error)

            if code:
                with open(apath[:-4] + ".dec", 'w') as ofp:
                    ofp.write(zdcode.decorate(code))

print('Bundling examples into single output...')

includes = ''

for root, dirs, files in os.walk('examples'):
    for f in files:
        if f.endswith('.zc2'):
            print(' +  {} ({})'.format(f, root))
            apath = os.path.join(root, f)
            includes += '#INCLUDE {}\n'.format(repr(apath)[1:-1])

code = zdcode.ZDCode.parse(includes, '.', error_handler=print_parse_error)

if code:
    with zipfile.ZipFile('ZDCodeBundle_{}.pk3'.format(version), 'w') as opkg:
        with opkg.open('DECORATE.Bundle', 'w') as odec:
            odec.write(zdcode.decorate(code).encode('utf-8'))

    print("Examples compiled and bundled succesfully.")
