import fnmatch
import functools
import heapq
import pathlib
import shutil
import subprocess
import tempfile
import typing
import zipfile
from collections import deque

import attr

from . import ZDCode


@functools.total_ordering
@attr.s(order=False)
class BundleOutput:
    name: str = attr.ib()
    output: str = attr.ib()
    priority: float = attr.ib(default=1.0)
    matchers: list[str] = attr.ib(factory=list)
    excluders: list[str] = attr.ib(factory=list)

    def add_matcher(self, matcher: str):
        self.matchers.append(matcher)

    def add_excluder(self, excluder: str):
        self.excluders.append(excluder)

    def matches(self, rel_path: str) -> bool:
        for excluder in self.excluders:
            if fnmatch.fnmatch(rel_path, excluder):
                return False

        if not self.matchers:
            return True

        for matcher in self.matchers:
            if fnmatch.fnmatch(rel_path, matcher):
                return True

        return False

    def __gt__(self, other: "BundleOutput") -> bool:
        if not isinstance(other, BundleOutput):
            return NotImplemented
        return self.priority < other.priority

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BundleOutput):
            return NotImplemented
        return self.priority == other.priority


class BundleDependencyError(Exception):
    pass


@attr.s
class BundleInputWalker:
    code: ZDCode = attr.ib()
    bundle: "Bundle" = attr.ib()
    deps: list[tuple[pathlib.Path, pathlib.PurePath]] = attr.ib(factory=list)
    bundled: set[str] = attr.ib(factory=set)
    build_tasks: list[typing.Callable[[], bool]] = attr.ib(factory=list)
    error_handler: typing.Optional[
        typing.Callable[[ZDCode.ZDCodeError], None]
    ] = attr.ib(default=None)
    preproc_defs: dict[str, str] = attr.ib(factory=dict)
    collected: typing.Deque[tuple[str, str, bytes]] = attr.ib(factory=list)

    @classmethod
    def new(self, bundle, error_handler=None, preproc_defs=None) -> "BundleInputWalker":
        return BundleInputWalker(
            bundled=set(),
            deps=[],
            code=ZDCode(),
            build_tasks=[],
            error_handler=error_handler,
            preproc_defs=preproc_defs or {},
            bundle=bundle,
            collected=deque(),
        )

    def add_dep(self, url: pathlib.Path, target: pathlib.PurePath) -> None:
        self.deps.append((url, target))

    def scan_deps(self):
        while self.deps:
            mod, target = self.deps.pop()
            self.scan_dep(mod, target)

    def build(self) -> typing.Optional[tuple[int, str]]:
        while self.build_tasks:
            task = self.build_tasks.pop()

            if not task():
                return (
                    1,
                    "Errors were found during the compilation of the ZDCode lumps!",
                )

        self.collect(pathlib.PurePath("DECORATE"), self.code.decorate().encode("utf-8"))

        return None

    def store_collected(self, out_zip: zipfile.ZipFile, target: str, data: bytes):
        # check if file already exists in target;
        # if so, add extension

        # (ignore folders)

        out_path = target
        num = 0

        names_list = out_zip.namelist()

        while out_path in names_list:
            num += 1
            out_path = target + "." + str(num)

        out_zip.writestr(out_path, data)

    def assemble(self):
        zips: dict[str, zipfile.ZipFile] = {}
        zipfiles = set()

        for oname, out in self.bundle.outputs.items():
            oname = oname.lower()

            zipf = zipfile.ZipFile(out.output, mode="w")
            zips[oname] = zipf
            zipfiles.add(zipf)

        while self.collected:
            target, oname, data = self.collected.popleft()
            out_zip = zips[oname.lower()]
            self.store_collected(out_zip, target, data)

    def scan_dep(self, url: pathlib.Path, target: pathlib.PurePath):
        url_str = str(url)

        if url_str in self.bundled:
            return

        self.bundled.add(url_str)
        self.scan_dep_url(url, target, url)

    def scan_dep_url(
        self, url: pathlib.Path, target: pathlib.PurePath, relative: pathlib.PurePath
    ):
        if url.is_dir():
            self.scan_dep_dir(url, target, relative)

        elif url.is_file():
            self.scan_dep_file(url, target, relative)

    def scan_dep_zip(
        self, url: pathlib.Path, target: pathlib.PurePath, relative: pathlib.PurePath
    ):
        with tempfile.TemporaryDirectory() as extract_out:
            extractdest = pathlib.Path(extract_out)

            with zipfile.ZipFile(url) as zipped:
                zipped.extractall(extractdest)

            self.scan_dep_dir(extractdest, target, relative)

    def scan_dep_file(
        self, url: pathlib.Path, target: pathlib.PurePath, relative: pathlib.PurePath
    ):
        if url.stem.split(".")[0].upper() == "ZDCODE":
            self.build_tasks.append(self._compile_task(url))

        if url.suffix.upper() in (".PK3", ".PKZ", ".ZIP"):
            self.scan_dep_zip(url, target, relative)
            return

        opath = target / url.name
        self.collect(opath, url.read_bytes())

    def collect(self, out_path: pathlib.PurePath, data: bytes):
        output = self.bundle.find_output(out_path.name)

        if output:
            self.collected.append((str(out_path), output.name.lower(), data))

    def _compile_task(self, zdc):
        def compile_mod_zdcode():
            with zdc.open() as zdc_fp:
                return self.code.add(
                    zdc_fp.read(),
                    zdc.name,
                    zdc.parent,
                    self.error_handler,
                    preproc_defs=self.preproc_defs,
                )

        return compile_mod_zdcode

    def scan_dep_dir(
        self, url: pathlib.Path, target: pathlib.PurePath, relative: pathlib.PurePath
    ):
        for filepath in url.rglob("*"):
            if filepath.is_file() and filepath.name != "DEPINDEX":
                self.scan_dep_file(
                    filepath, target / filepath.parent.relative_to(url), relative
                )

        indx_path = url / "DEPINDEX"

        if indx_path.is_file():
            lines = indx_path.read().splitlines()

            for l in lines:
                l = l.strip()

                if l:
                    dep_path = url.parent / l

                    if not dep_path.exists():
                        dep_path = pathlib.Path.cwd() / l

                    if not dep_path.exists():
                        raise BundleDependencyError(
                            "The file {} depends on {}, which does not exist, neither as a sibling of the dependent's dir, nor under the working one!"
                        )

                    self.deps.append(dep_path)


class Bundle:
    def __init__(self, *mods: list[tuple[str, str]], outputs=None, error_handler=None):
        self.mods = list(mods)
        self.error_handler = error_handler

        self.outputs: dict[str, BundleOutput] = outputs or {}

        self.output_heap: list[BundleOutput] = list(self.outputs.values())
        self.output_heap.sort()

    def add_output(self, name: str, output: str, priority: float = 1.0) -> BundleOutput:
        res = self.outputs.setdefault(
            name, BundleOutput(name=name, output=output, priority=priority)
        )

        if res not in self.output_heap:
            heapq.heappush(self.output_heap, res)
            self.output_heap.sort()

        return res

    def find_output(self, rel_path: str) -> typing.Optional[BundleOutput]:
        for bundle in self.output_heap:
            if bundle.matches(rel_path):
                return bundle

        return None

    def bundle(
        self,
        error_handler=None,
        preproc_defs=(),
    ):
        walker = BundleInputWalker.new(
            error_handler=error_handler or self.error_handler,
            preproc_defs=dict(preproc_defs),
            bundle=self,
        )

        for mod, modtarg in self.mods:
            walker.add_dep(pathlib.Path(mod), pathlib.Path(modtarg))

        # scan input paths
        print("Scanning inputs...")
        walker.scan_deps()

        # build any zdcode found into decorate
        print("Building ZDCode...")
        err = walker.build()

        if err:
            return err

        # count files bundled
        print("Collected {} files.".format(len(walker.collected)))

        # assemble outputs
        print("Assembling...")
        walker.assemble()

        return (0, "Success!")
