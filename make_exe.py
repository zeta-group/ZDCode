import subprocess
import os
import shutil


try:
    import PyInstaller

except ImportError:
    subprocess.call(['python', '-m', 'pip', 'install', '-U', 'git+https://github.com/pyinstaller/pyinstaller.git'])


subprocess.call(['python', '-m', 'PyInstaller', 'zdcode/__main__.py', '-n', 'ZDCode', '-i', 'zdcode.ico', '-F', '--specpath', 'build'])

os.unlink('./ZDCode.exe')
shutil.move('dist/ZDCode.exe', './ZDCode.exe')
shutil.rmtree('dist')