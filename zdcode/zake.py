"""The Zake build system.

Zake can walk your project, gathering assets and compiling ZDCode, and specify
multiple output types, automatically setting the appropriate paths and preprocessor
definitions for those.

It can also be used in non-ZDCode projects, as well as in conjunction with other
build system tools, such as Ninja or a C toolchain."""
import re
import sys
from configparser import ConfigParser
from configparser import ExtendedInterpolation

from .bundle import Bundle
from .bundle import BundleOutput


class ZakeException(Exception):
    """An error in Zake."""


class ZakeConfigError(ZakeException):
    """An error with Zake's configuration; the Zake.ini file."""


class ZakeTarget:
    """A target as specified in Zake configuration."""

    def __init__(self, name: str):
        self.name = name
        self.definitions: dict[str, str] = {}
        self.inputs: list[tuple[str, str]] = []
        self.outputs: dict[str, BundleOutput] = {}

    def add_input(self, inp):
        """Adds an input specification to this target."""
        self.inputs.append(inp)

    def add_definition(self, key, value):
        """Adds a preprocessor definition to this target."""
        self.definitions[key] = value

    def bundle(self, **kwargs):
        """Execute the bundling process for this target."""
        bundle = Bundle(*self.inputs, outputs=self.outputs)

        return bundle.bundle(
            preproc_defs={k.upper(): v for k, v in self.definitions.items()}, **kwargs
        )


class Zake:
    """The Zake build system.

    Handles the entire configuration file."""

    inj_field_pat = re.compile(r"^\"(.+)\":\"(.+)\"$")

    def __init__(self):
        self.targets: dict[str, ZakeTarget] = {}

    def add_target(self, name: str) -> ZakeTarget:
        """Creates and registers a target, before returning it."""
        return self.targets.setdefault(name, ZakeTarget(name))

    def read(self, filename, **kwargs):
        """Read a Zake configuration file."""
        config = ConfigParser(
            interpolation=ExtendedInterpolation(), **kwargs, strict=False
        )
        config.read(filename)

        c_general = config["General"]

        # general values
        name = c_general["name"].strip()
        version = c_general["version"].strip()
        targets = c_general["targets"].strip().split()

        if "partitions" in c_general:
            bundles = [x.lower() for x in c_general["partitions"].strip().split()]

        else:
            bundles = ["asset", "code"]

        # set values (for interpolation)
        interp = {"name": name, "version": version}

        # default values
        targs = {}

        def get_bundle_cfg(s_bundle_cfg, name):
            return config.get(
                s_bundle_cfg,
                name,
                vars=interp,
                fallback=config.get("Partition", name, vars=interp, fallback=None),
            )

        # targets
        for tname in targets:
            targ = self.add_target(tname)
            targs[tname] = targ

            interp["target"] = tname  # for interpolation
            interp["defaults"] = ""

            s_pats = "Paths." + tname
            s_defs = "Definitions." + tname
            s_bundle_cfg = "Partition." + tname

            # define bundle outputs
            for bundle in bundles:
                targ.outputs[bundle] = BundleOutput(
                    name=bundle,
                    output=None,
                )

            if "partitions" not in c_general:
                targ.outputs["asset"].priority = 1.0
                targ.outputs["code"].priority = 100.0
                targ.outputs["code"].add_matcher("DECORATE")
                targ.outputs["code"].add_matcher("DECORATE*")

            # section values
            pats = dict(config.items("Paths", vars=interp)) if "Paths" in config else {}

            defs = (
                dict(config.items("Definitions", vars=interp))
                if "Definitions" in config
                else {}
            )

            if s_pats in config:
                new_pat_keys = dict(config.items(s_pats, vars=interp)).keys()

                for key in new_pat_keys:
                    interp["defaults"] = ""

                    if key in pats:
                        interp["defaults"] = pats[key]

                    pats[key] = config.get(s_pats, key, vars=interp)

            if s_defs in config:
                defs.update(config.items(s_defs, vars=interp))

            # fetch inputs and outputs
            if "inputs" not in pats:
                raise ZakeConfigError(
                    "Required Zake field 'inputs' missing from section Paths "
                    f"while reading target {tname}."
                )

            for inp in pats["inputs"].strip().split():
                targ.add_input((inp, ""))

            if "injects" in pats:
                for injs in pats["injects"].strip().split():
                    match = self.inj_field_pat.match(injs)

                    if not match:
                        raise ZakeConfigError(
                            "Malformed value found in given Zake field 'injects': "
                            + injs
                        )

                    inp, out = match.groups()
                    targ.add_input((inp, out))

            for bundle in bundles:
                out_name = "output." + bundle
                matchers_name = "matchers." + bundle
                excluders_name = "excluders." + bundle
                excluders_global_name = "excluders"
                priority_name = "priority." + bundle

                priority = config.getfloat(
                    s_bundle_cfg,
                    priority_name,
                    vars=interp,
                    fallback=config.getfloat(
                        "Partition", priority_name, vars=interp, fallback=None
                    ),
                )

                if priority is not None:
                    targ.outputs[bundle].priority = priority

                if out_name in pats:
                    targ.outputs[bundle].output = pats[out_name].strip()

                else:
                    raise ZakeConfigError(
                        f"Required Zake field '{out_name}' missing from section Paths "
                        f"while reading target {tname}."
                    )

                matchers = get_bundle_cfg(s_bundle_cfg, matchers_name)
                excluders = get_bundle_cfg(s_bundle_cfg, excluders_name)
                excluders_global = get_bundle_cfg(s_bundle_cfg, excluders_global_name)

                if matchers:
                    for matcher in matchers.strip().split():
                        targ.outputs[bundle].add_matcher(matcher)

                if excluders:
                    for excluder in excluders.strip().split():
                        targ.outputs[bundle].add_excluder(excluder)

                if excluders_global:
                    for excluder in excluders_global.strip().split():
                        targ.outputs[bundle].add_excluder(excluder)

            # preprocessor definitions
            for name, value in defs.items():
                targ.add_definition(name.strip(), value.strip())

        # return parsed targets
        return targs

    def execute(self, **kwargs):
        """Execute the build process."""
        print(f"Starting ZDCode bundling barrage with {len(self.targets)} targets.")

        for name, target in self.targets.items():
            print("\n-- Bundling target: " + name)
            yield name, target.bundle(**kwargs)


def main(print_status_code=True):
    """Main entry point for Zake."""
    filename = "Zake.ini"

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

        print(f" - {tname}: {message}")

    short_status = (
        f"{success} successful, {error} failed"
        if error
        else "all successful"
        if success
        else "nothing done"
    )

    acc_status = f" Final status {acc_status}." if print_status_code else ""

    print(f"{total} targets processed ({short_status}).{acc_status}")

    sys.exit(acc_status)


if __name__ == "__main__":
    main()
