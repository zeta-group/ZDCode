import sys
from enum import Enum
from configparser import ConfigParser, ExtendedInterpolation

try:
    from zdcode.bundle import Bundle

except ImportError:
    from bundle import Bundle



class ZakeException(Exception):
    pass

class ConfigError(ZakeException):
    pass


class OutputType(Enum):
    DECORATE = (0, 'out_dec_file', 'w')
    ASSET = (1, 'out_asset_file', 'wb')
    CODE = (2, 'out_code_file', 'wb')


class ZakeTarget:
    def __init__(self, name):
        self.name = name
        self.definitions = {}
        self.outputs = [None, None, None]
        self.inputs = []

    def output_kwargs(self):
        return {ot.value[1]: (open(self.outputs[ot.value[0]], ot.value[2]) if self.outputs[ot.value[0]] is not None else None) for ot in OutputType}

    def set_output(self, otype, filename):
        self.outputs[otype.value[0]] = filename

    def add_input(self, inp):
        self.inputs.append(inp)

    def add_definition(self, key, value):
        self.definitions[key] = value

    def bundle(self, **kwargs):
        bundle = Bundle(*self.inputs)

        return bundle.bundle(preproc_defs={k.upper(): v for k, v in self.definitions.items()}, **self.output_kwargs(), **kwargs)



class Zake:
    def __init__(self):
        self.targets = {}

    def add_target(self, name):
        return self.targets.setdefault(name, ZakeTarget(name))

    def read(self, fn, **kwargs):
        config = ConfigParser(interpolation=ExtendedInterpolation(), **kwargs, strict=False)
        config.read(fn)

        c_general = config['General']

        # general values
        name = c_general['name'].strip()
        version = c_general['version'].strip()
        targets = c_general['targets'].strip().split()

        # set values (for interpolation)
        interp = {
            'name': name,
            'version': version
        }

        # default values
        targs = {}

        # targets
        for tname in targets:
            targ = self.add_target(tname)
            targs[tname] = targ

            interp['target'] = tname # for interpolation
        
            s_pats = 'Paths.' + tname
            s_defs = 'Definitions.' + tname

            # section values
            pats = dict(config.items('Paths',       vars=interp)) if 'Paths'        in config else {}
            defs = dict(config.items('Definitions', vars=interp)) if 'Definitions'  in config else {}

            if s_pats in config:
                pats.update(config.items(s_pats, vars=interp))

            if s_defs in config:
                defs.update(config.items(s_defs, vars=interp))

            # fetch inputs and outputs
            if 'inputs' not in pats:
                raise ConfigError("Required Zake field 'inputs' missing from section Paths while reading target {}.".format(tname))
            
            for inp in pats['inputs'].strip().split():
                targ.add_input(inp)
            
            if 'decorate' in pats:
                targ.set_output(OutputType.DECORATE, pats['decorate'].strip())

            if 'bundle.asset' in pats:
                targ.set_output(OutputType.ASSET, pats['bundle.asset'].strip())

            if 'bundle.code' in pats:
                targ.set_output(OutputType.CODE, pats['bundle.code'].strip())

            # preprocessor definitions
            for k, v in defs.items():
                targ.add_definition(k.strip(), v.strip())

        # return parsed targets
        return targs

    def execute(self, **kwargs):
        for name, target in self.targets.items():
            yield name, target.bundle(**kwargs)


# main function for Zake
def main(print_status_code=True):
    filename = 'Zake.ini'

    if len(sys.argv) > 1:
        filename = sys.argv.pop(1)

    zake = Zake()
    zake.read(filename)

    acc_status = None

    total = 0
    success = 0
    error = 0

    for tname, (status, message) in zake.execute():
        if acc_status is None:
            acc_status = status

        else:
            acc_status = max(status, acc_status)

        if status == 0:
            success += 1

        else:
            error += 1

        total += 1

        print(' - {}: {}'.format(tname, message))

    print('{tot} targets processed ({successes}).{status}'.format(
        tot=total,
        
        successes=(
            '{} successful, {} failed'.format(success, error)
            if error else
            ('all successful' if success else 'nothing done')
        ),

        status=(
            ' Final status {}.'.format(acc_status)
            if print_status_code else ''
        )
    ))
    
    exit(acc_status)

if __name__ == '__main__':
    main()
