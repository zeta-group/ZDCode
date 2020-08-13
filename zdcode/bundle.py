try:
    from . import ZDCode
    
except ImportError:
    from zdcode import ZDCode

import zipfile
import tempfile
import pathlib
import subprocess
import shutil

from collections import deque



class BundleDependencyError(Exception):
    pass


class Bundle:
    def __init__(self, *mods, error_handler=None):
        self.mods = list(mods)
        self.error_handler = error_handler
        
    def _compile_task(self, code, zdc, error_handler, preproc_defs):
        def compile_mod_zdcode():
            with zdc.open() as zdc_fp:
                return code.add(zdc_fp.read(), zdc.name, zdc.parent, error_handler, preproc_defs=preproc_defs)
                
        return compile_mod_zdcode

    def bundle(self, out_asset_file=None, out_code_file=None, out_dec_file=None, error_handler=None, preproc_defs=()):
        code = ZDCode()
        build_tasks = []
        deps = list(self.mods)
        bundled = set()

        if not (hasattr(preproc_defs, '__getitem__') and hasattr(preproc_defs, '__setitem__')):
            preproc_defs = dict(preproc_defs)
        
        # Scan input
        with tempfile.TemporaryDirectory() as destname:
            dest = pathlib.Path(destname)
    
            while deps:
                mod = deps.pop()

                if mod in bundled:
                    continue
                    
                bundled.add(mod)
                
                mod_path = pathlib.Path(mod)
                    
                if mod_path.is_dir():
                    mod_dest = dest / mod_path.resolve().stem
                
                    for fn in mod_path.rglob('*'):
                        if fn.is_file():
                            dest_fpath = (mod_dest / fn.relative_to(mod_path))
                            
                            dest_fpath.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(fn, dest_fpath)
                            
                            if fn.stem.split('.')[0].upper() == 'ZDCODE':
                                build_tasks.append(self._compile_task(code, dest_fpath, error_handler or self.error_handler, preproc_defs))
                        
                    indx_path = mod_dest / 'DEPINDEX'
                    
                    if indx_path.is_file():
                        lines = indx_path.read().splitlines()
                        
                        for l in lines:
                            l = l.strip()
                            
                            if l:
                                dep_path = mod_path.parent / l
                                
                                if not dep_path.is_file():
                                    dep_path = pathlib.Path.cwd() / l
                                
                                if not dep_path.is_file():
                                    raise BundleDependencyError('The file {} depends on {}, which does not exist, neither in the dependent\'s dir, nor in the working one!')

                                deps.append(dep_path)
                                
                elif mod_path.suffix.upper() in ('.PK3', '.PKZ'):
                    mod_dest = dest / mod_path.stem
                    mod_dest.mkdir()
                
                    with zipfile.ZipFile(mod) as zmod:
                        zmod.extractall(mod_dest)
                    
                        for zdc in mod_dest.glob(''.join('[{}{}]'.format(c.lower(), c) for c in 'ZDCODE') + '*'):
                            build_tasks.append(self._compile_task(code, zdc, error_handler or self.error_handler, preproc_defs))
                            
                        indx_path = mod_dest / 'DEPINDEX'
                        
                        if indx_path.is_file():
                            lines = indx_path.read().splitlines()
                            
                            for l in lines:
                                l = l.strip()
                                
                                if l:
                                    dep_path = mod_path.parent / l
                                    
                                    if not dep_path.is_file():
                                        dep_path = pathlib.Path.cwd() / l
                                    
                                    if not dep_path.is_file():
                                        raise BundleDependencyError('The file {} depends on {}, which does not exist, neither in the dependent\'s dir, nor in the working one!')
                                        
                                    deps.append(dep_path)
                                    
                elif mod_path.suffix.upper() == '.ZC2':
                    build_tasks.append(self._compile_task(code, mod_path, error_handler or self.error_handler, preproc_defs))
                                    
            # Build ZDCode              
            for task in build_tasks:
                if not task():
                    return 1, 'Errors were found during the compilation of the ZDCode lumps!'
                
        # Bundle assets to zip (pk3)
        if out_asset_file:       
            with zipfile.ZipFile(out_asset_file, 'w') as asset_bundle:
                for asset in bundled:
                    asset_path = pathlib.Path(asset)
                    
                    if asset_path.is_dir():
                        for ipath in asset_path.rglob('*'):
                            if ipath.stem.split('.')[0].upper() != 'ZDCODE' and ipath.suffix.upper() != '.ZC2' and ipath.is_file():
                                asset_bundle.write(ipath, ipath.relative_to(asset_path))
                
                    elif asset_path.suffix.upper() == '.WAD':
                        # Just add wads instead of parsing their content
                        asset_bundle.write(asset_path, asset_path.name)
                
                    elif asset_path.suffix.upper() in ('.PK3', '.PKZ'):
                        with zipfile.ZipFile(asset) as asset_zip:
                            for info in asset_zip:
                                ipath = pathlib.Path(info.filename)
                                
                                if ipath.stem.split('.')[0].upper() != 'ZDCODE' and ipath.suffix.upper() != '.ZC2':
                                    with asset_zip.open(info) as info_fp:
                                        # check if file already exists in target;
                                        # if so, add extension

                                        # (ignore folders)

                                        p = zipfile.Path(asset_bundle, info.filename)

                                        if p.exists() and p.is_file():
                                            num = 1
                                            p = p.with_suffix(p.suffix + '.' + str(num))

                                            # keep checking until we find a vacant name
                                            while True:
                                                p = p.with_suffix('.' + str(num))

                                                if not (p.exists() and p.is_file()): break
                                                num += 1 # .num exists too, increment num

                                        asset_bundle.writestr(p, info_fp.read())
                        
        # Write compiled output to zip (pk3)
        if out_code_file:
            with zipfile.ZipFile(out_code_file, 'w') as code_bundle:
                code_bundle.writestr('DECORATE', code.decorate(), zipfile.ZIP_DEFLATED)

        # Write compiled output to plain text file
        if out_dec_file:
            out_dec_file.write(code.decorate())

        return 0, 'Bundled successfully!'

