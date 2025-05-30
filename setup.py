#!/usr/bin/env python3
# encoding: utf-8

import shutil
import os
import sys
import subprocess
from cx_Freeze import setup, Executable
import globalData

programName = "Melee Modding Wizard"
environIs64bit = sys.maxsize > 2**32

# figure out platform-specific base
if sys.platform == 'win32':
    base = 'Win32GUI'
elif sys.platform == 'darwin':
    base = 'Console'  # change to 'GUI' if you're making a mac app bundle
else:
    base = 'Console'

# figure out platform-specific include files
include_files = [
    '.include', 'bin', 'Code Library', 'File Descriptions', 'fonts', 'imgs', 'sfx',
    'Code Library Manual.txt', 'Command-Line Usage.txt', 'MMW Manual.txt'
]

if sys.platform == 'win32':
    include_files.append('- - Asset Test.bat')

# clean version string
simpleVersion = '.'.join(filter(str.isdigit, globalData.programVersion.split('.')))

# build options
buildOptions = dict(
    packages=[
        "ruamel.yaml",
        "pyglet.clock"
    ],
    excludes=[],
    include_files=include_files
)

# executable target
target_name = f"{programName}.exe" if sys.platform == 'win32' else programName

executable = Executable(
    script="main.py",
    target_name=target_name,
    icon="imgs/appIcon.ico" if sys.platform == 'win32' else None,
    base=base
)

# run the build
setup(
    name=programName,
    version=simpleVersion,
    description="Modding program for SSBM",
    options={"build_exe": buildOptions},
    executables=[executable]
)

print("\nCompilation complete.")

# post-build folder renaming & cleanup
scriptHomeFolder = os.path.abspath(os.path.dirname(sys.argv[0]))
buildPath = os.path.join(scriptHomeFolder, 'build')

if os.path.exists(buildPath):
    programFolder = next((d for d in os.listdir(buildPath) if d.startswith('exe.') or d == programName), None)
else:
    programFolder = None

if not programFolder:
    print("\nUnable to locate the new program folder!")
    sys.exit(1)

# make a nice final folder name
newFolderName = f"{programName} - v{globalData.programVersion} ({'x64' if environIs64bit else 'x86'})"
oldFolderPath = os.path.join(buildPath, programFolder)
newFolderPath = os.path.join(buildPath, newFolderName)

nameIndex = 2
while os.path.exists(newFolderPath):
    newFolderPath = f"{newFolderPath.rsplit(' ', 1)[0]} ({nameIndex})"
    nameIndex += 1

os.rename(oldFolderPath, newFolderPath)
print(f'\nNew program folder created: "{os.path.basename(newFolderPath)}"')

# rename asset test script if on windows
os.chdir(newFolderPath)
if sys.platform == 'win32':
    os.rename('- - Asset Test.bat', 'Asset Test.bat')

# remove temp stuff if present
try:
    os.remove(os.path.join(newFolderPath, 'bin', "Micro Melee.iso"))
except FileNotFoundError:
    pass

try:
    shutil.rmtree(os.path.join(newFolderPath, 'bin', 'tempFiles'))
except FileNotFoundError:
    pass

# open the new folder
if sys.platform == "win32":
    os.startfile(newFolderPath)
elif sys.platform == "darwin":
    subprocess.run(["open", newFolderPath], check=True)
else:
    subprocess.run(["xdg-open", newFolderPath], check=True)
