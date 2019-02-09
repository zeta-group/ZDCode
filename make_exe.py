import subprocess
import os
import shutil
import sys


try:
    import PyInstaller

except ImportError:
    import pip
    pip.main(['install', '-U', 'PyInstaller'])

subprocess.call([sys.executable, '-m', 'PyInstaller', 'zdcode/__main__.py', '-n', 'ZDCode', '-i', 'zdcode.ico', '-F', '--specpath', 'build'])

if os.path.isfile('./ZDCode.exe'):
    os.unlink('./ZDCode.exe')

shutil.move('dist/ZDCode.exe', './ZDCode.exe')
shutil.rmtree('dist')
